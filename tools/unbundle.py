#!/usr/bin/env python3
"""Unbundle a Claude Design self-extracting export into a plain static page.

The export (e.g. ``TP_Careers_KR.html``) is a wrapper: the real page lives
inside ``<script type="__bundler/*">`` blocks.

    __bundler/template        the page HTML, stored as an escaped JS string
    __bundler/manifest        fonts/images/scripts as base64, keyed by UUID
    __bundler/ext_resources   original URLs for the UUIDs pulled from a CDN
    __bundler/page_order      metadata

Exports disagree about which block holds the payload bytes, so both the
manifest and ext_resources blocks are scanned and whichever entries carry a
``data`` field are treated as the resource store. Entries may be gzipped
(``"compressed": true``); entries that only carry an ``id``/``uuid`` pair are
used to give the decoded file a meaningful name.

This script pulls those apart and writes a clean, self-contained page:

    design-src/index.html     reconstructed markup
    design-src/assets/        decoded resources, UUID refs rewritten to paths

Usage:
    python3 tools/unbundle.py TP_Careers_KR.html
    python3 tools/unbundle.py TP_Careers_KR.html -o design-src
    python3 tools/unbundle.py TP_Careers_KR.html --inspect   # report only

``--inspect`` prints the shape of every bundler block without writing files,
which is the quickest way to sanity-check a new export before extracting it.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import html
import json
import os
import re
import sys
import zlib
from pathlib import Path
from urllib.parse import unquote, urlsplit

# --------------------------------------------------------------------------
# block extraction
# --------------------------------------------------------------------------

BLOCK_RE_TMPL = (
    r'<script[^>]*\btype\s*=\s*["\']__bundler/{name}["\'][^>]*>(.*?)</script\s*>'
)

# UUID as it appears in src="..." / href="..." attributes. Some exports prefix
# the id with a scheme-ish marker, so the prefix is optional and tolerated.
UUID_RE = re.compile(
    r'(?:[a-z][a-z0-9+.-]*:)?'
    r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.I,
)

BARE_UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I
)

DATA_URI_RE = re.compile(r'^data:([^;,]*)(;[^,]*)?,', re.I)


def find_block(source: str, name: str) -> str | None:
    """Return the raw inner text of a ``__bundler/<name>`` script block."""
    match = re.search(
        BLOCK_RE_TMPL.format(name=re.escape(name)), source, re.S | re.I
    )
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# template decoding
# --------------------------------------------------------------------------

JS_ESCAPES = {
    'n': '\n',
    't': '\t',
    'r': '\r',
    'b': '\b',
    'f': '\f',
    'v': '\v',
    '0': '\0',
    '\\': '\\',
    '"': '"',
    "'": "'",
    '`': '`',
    '/': '/',
    '\n': '',  # line continuation
}


def unescape_js_string(text: str) -> str:
    """Decode JS string escapes (\\n, \\uXXXX, \\xNN, ...) by hand.

    Used as a fallback when the payload is not valid JSON. Walking the string
    once avoids the classic bug of chained ``.replace()`` calls, where an
    already-decoded backslash gets re-interpreted as the start of a new escape.
    """
    out: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if char != '\\' or i + 1 >= length:
            out.append(char)
            i += 1
            continue

        nxt = text[i + 1]
        if nxt == 'u':
            # \uXXXX, or \u{XXXXX}
            if text[i + 2 : i + 3] == '{':
                end = text.find('}', i + 3)
                if end != -1:
                    try:
                        out.append(chr(int(text[i + 3 : end], 16)))
                        i = end + 1
                        continue
                    except ValueError:
                        pass
            hex4 = text[i + 2 : i + 6]
            if len(hex4) == 4:
                try:
                    out.append(chr(int(hex4, 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
        elif nxt == 'x':
            hex2 = text[i + 2 : i + 4]
            if len(hex2) == 2:
                try:
                    out.append(chr(int(hex2, 16)))
                    i += 4
                    continue
                except ValueError:
                    pass
        elif nxt in JS_ESCAPES:
            out.append(JS_ESCAPES[nxt])
            i += 2
            continue

        # Unknown escape: JS drops the backslash and keeps the character.
        out.append(nxt)
        i += 2
    return ''.join(out)


def decode_template(raw: str) -> str:
    """Turn the raw template block into clean HTML."""
    text = raw.strip()

    # The block often holds a JSON value (a bare string, or an object with the
    # markup under a key). JSON parsing handles every escape correctly, so it
    # is always worth trying first.
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        parsed = None

    if isinstance(parsed, str):
        text = parsed
    elif isinstance(parsed, dict):
        for key in ('template', 'html', 'content', 'source', 'body', 'page'):
            value = parsed.get(key)
            if isinstance(value, str):
                text = value
                break
        else:
            raise SystemExit(
                'template block is a JSON object with no recognised markup '
                f'key; keys present: {sorted(parsed)}'
            )
    else:
        # Not JSON. Strip a surrounding quote pair if the payload is a bare JS
        # string literal, then unescape manually.
        if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'`':
            text = text[1:-1]
        text = unescape_js_string(text)

    # HTML entities survive both paths (the markup was entity-encoded so it
    # could sit inside a <script> tag without closing it early).
    text = html.unescape(text)

    # Neutralise the split-tag trick the bundler uses to avoid a premature
    # </script>, if the export happens to use it.
    text = text.replace('<\\/', '</').replace('<\\!--', '<!--')
    return text.strip()


# --------------------------------------------------------------------------
# resource decoding
# --------------------------------------------------------------------------

MIME_EXT = {
    'application/javascript': '.js',
    'application/json': '.json',
    'application/pdf': '.pdf',
    'font/otf': '.otf',
    'font/ttf': '.ttf',
    'font/woff': '.woff',
    'font/woff2': '.woff2',
    'image/avif': '.avif',
    'image/gif': '.gif',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/svg+xml': '.svg',
    'image/webp': '.webp',
    'text/css': '.css',
    'text/javascript': '.js',
    'text/plain': '.txt',
}

# (offset, signature, extension) — enough to cover what a design export ships.
MAGIC = [
    (0, b'\x89PNG\r\n\x1a\n', '.png'),
    (0, b'\xff\xd8\xff', '.jpg'),
    (0, b'GIF87a', '.gif'),
    (0, b'GIF89a', '.gif'),
    (0, b'wOFF', '.woff'),
    (0, b'wOF2', '.woff2'),
    (0, b'\x00\x01\x00\x00', '.ttf'),
    (0, b'OTTO', '.otf'),
    (0, b'%PDF', '.pdf'),
    (8, b'WEBP', '.webp'),
]


def sniff_extension(blob: bytes, mime: str | None, name: str | None) -> str:
    """Best-effort file extension for a decoded resource."""
    if name:
        suffix = Path(name).suffix.lower()
        if suffix and len(suffix) <= 6:
            return suffix

    if mime:
        base = mime.split(';')[0].strip().lower()
        if base in MIME_EXT:
            return MIME_EXT[base]

    for offset, signature, ext in MAGIC:
        if blob[offset : offset + len(signature)] == signature:
            return ext

    head = blob[:512].lstrip()
    if head.startswith(b'<svg') or head.startswith(b'<?xml'):
        return '.svg'
    if head.startswith(b'{') or head.startswith(b'['):
        return '.json'
    return '.bin'


def clean_stem(value: str, fallback: str) -> str:
    """Filesystem-safe stem, without directory traversal."""
    stem = Path(value).stem if value else ''
    stem = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('-._')
    return stem or fallback


def maybe_decompress(blob: bytes, flagged: bool) -> bytes:
    """Gunzip a resource body when the entry is marked compressed.

    The flag is trusted only as a hint: the gzip magic number is the real
    test, so a mislabelled entry still comes out correct either way.
    """
    if blob[:2] != b'\x1f\x8b':
        return blob
    try:
        return gzip.decompress(blob)
    except (OSError, EOFError, zlib.error) as exc:
        if flagged:
            print(f'  ! gzip decompress failed: {exc}', file=sys.stderr)
        return blob


def decode_base64(payload: str) -> bytes | None:
    """Decode a base64 payload, tolerating data: URIs and stray whitespace."""
    text = payload.strip()
    match = DATA_URI_RE.match(text)
    if match:
        if ';base64' not in (match.group(2) or '').lower():
            # Plain (percent-encoded) data URI — not base64.
            from urllib.parse import unquote_to_bytes

            return unquote_to_bytes(text[match.end() :])
        text = text[match.end() :]

    text = re.sub(r'\s+', '', text)
    text = text.replace('-', '+').replace('_', '/')  # urlsafe variant
    text += '=' * (-len(text) % 4)
    try:
        return base64.b64decode(text, validate=False)
    except (binascii.Error, ValueError):
        return None


def normalise_resources(parsed: object) -> dict[str, dict]:
    """Flatten the ext_resources block into ``{uuid: {...fields}}``.

    Exports vary: a mapping of uuid to a string, a mapping of uuid to an
    object, or a list of objects each carrying its own id.
    """
    resources: dict[str, dict] = {}

    def as_entry(value: object) -> dict | None:
        if isinstance(value, str):
            return {'data': value}
        if isinstance(value, dict):
            return dict(value)
        return None

    if isinstance(parsed, dict):
        # Unwrap a single container key, e.g. {"resources": {...}}.
        if len(parsed) == 1:
            (only_value,) = parsed.values()
            only_key = next(iter(parsed))
            if isinstance(only_value, (dict, list)) and not BARE_UUID_RE.fullmatch(
                only_key
            ):
                return normalise_resources(only_value)

        for key, value in parsed.items():
            entry = as_entry(value)
            if entry is None:
                continue
            entry.setdefault('id', key)
            resources[str(key)] = entry

    elif isinstance(parsed, list):
        for index, value in enumerate(parsed):
            entry = as_entry(value)
            if entry is None:
                continue
            key = None
            for field in ('id', 'uuid', 'key', 'name', 'path'):
                candidate = entry.get(field)
                if isinstance(candidate, str):
                    found = BARE_UUID_RE.search(candidate)
                    if found:
                        key = found.group(0)
                        break
                    key = key or candidate
            resources[str(key or index)] = entry

    return resources


def pick(entry: dict, *fields: str) -> str | None:
    for field in fields:
        value = entry.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def parse_resource_block(raw: str | None) -> dict[str, dict]:
    """Parse one bundler block into ``{uuid: entry}``, tolerating escaping."""
    if not raw or not raw.strip():
        return {}
    text = raw.strip()
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        try:
            parsed = json.loads(decode_template(text))
        except (json.JSONDecodeError, ValueError):
            return {}
    return normalise_resources(parsed)


def name_from_url(url: str) -> str | None:
    """Filename hint from an original CDN URL, e.g. react.production.min.js."""
    if not url or '://' not in url:
        return None
    tail = unquote(urlsplit(url).path).rsplit('/', 1)[-1]
    return tail or None


def extract_resources(
    blocks: dict[str, str | None], assets_dir: Path, verbose: bool
) -> dict[str, str]:
    """Write every resource to ``assets_dir``; return ``{uuid: relative path}``.

    ``blocks`` maps a block name to its raw text. Entries are merged across
    blocks by UUID so that a payload in one block can be named by metadata in
    another (the CDN-backed scripts arrive that way).
    """
    resources: dict[str, dict] = {}
    for raw in blocks.values():
        for key, entry in parse_resource_block(raw).items():
            resources.setdefault(key, {}).update(entry)

    # Entries with no payload are metadata for a payload stored elsewhere.
    resources = {
        key: entry
        for key, entry in resources.items()
        if pick(entry, 'data', 'content', 'base64', 'b64', 'body', 'value', 'src')
    }
    if not resources:
        return {}

    assets_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    used: set[str] = set()

    for index, (key, entry) in enumerate(sorted(resources.items())):
        payload = pick(
            entry, 'data', 'content', 'base64', 'b64', 'body', 'value', 'src'
        )
        if payload is None:
            print(f'  ! {key}: no payload field ({sorted(entry)})', file=sys.stderr)
            continue

        blob = decode_base64(payload)
        if blob is None:
            print(f'  ! {key}: payload is not valid base64', file=sys.stderr)
            continue

        packed = len(blob)
        blob = maybe_decompress(blob, bool(entry.get('compressed')))

        mime = pick(entry, 'mime', 'mimeType', 'mime_type', 'type', 'contentType')
        if mime is None:
            data_uri = DATA_URI_RE.match(payload.strip())
            mime = data_uri.group(1) if data_uri else None

        original = pick(entry, 'name', 'filename', 'file', 'path', 'url')
        if original is None:
            original = name_from_url(entry.get('id', '') or '')
        extension = sniff_extension(blob, mime, original)

        uuid_match = BARE_UUID_RE.search(str(key))
        short = (uuid_match.group(0) if uuid_match else str(key))[:8]
        stem = clean_stem(original or '', f'asset-{index:02d}')
        filename = f'{stem}-{short}{extension}' if stem else f'{short}{extension}'

        counter = 2
        while filename in used:
            filename = f'{stem}-{short}-{counter}{extension}'
            counter += 1
        used.add(filename)

        (assets_dir / filename).write_bytes(blob)
        relative = f'{assets_dir.name}/{filename}'
        mapping[str(key)] = relative
        if uuid_match:
            mapping[uuid_match.group(0)] = relative

        if verbose:
            note = f' (gz {packed:,})' if packed != len(blob) else ''
            print(f'  · {short}  {len(blob):>9,} B{note}  -> {relative}')

    return mapping


# --------------------------------------------------------------------------
# rewriting
# --------------------------------------------------------------------------

def rewrite_references(markup: str, mapping: dict[str, str]) -> tuple[str, int, list[str]]:
    """Swap UUID references for relative asset paths.

    Returns the rewritten markup, the number of substitutions, and any UUIDs
    that had no matching resource.
    """
    lowered = {key.lower(): value for key, value in mapping.items()}
    replaced = 0
    missing: list[str] = []

    def substitute(match: re.Match) -> str:
        nonlocal replaced
        uuid = match.group(1).lower()
        target = lowered.get(uuid)
        if target is None:
            if uuid not in missing:
                missing.append(uuid)
            return match.group(0)
        replaced += 1
        return target

    markup = UUID_RE.sub(substitute, markup)
    return markup, replaced, missing


def strip_bundler_blocks(markup: str) -> str:
    """Remove any bundler plumbing that leaked into the template itself."""
    markup = re.sub(
        r'<script[^>]*\btype\s*=\s*["\']__bundler/[^"\']*["\'][^>]*>.*?</script\s*>',
        '',
        markup,
        flags=re.S | re.I,
    )
    return markup


# --------------------------------------------------------------------------
# design props
# --------------------------------------------------------------------------

def read_design_props(source: str) -> dict:
    """Pull the ``data-dc-script`` design props block, if present."""
    match = re.search(
        r'<script[^>]*\bdata-dc-script\b[^>]*>(.*?)</script\s*>', source, re.S | re.I
    )
    if not match:
        return {}

    body = match.group(1)
    props: dict[str, object] = {}
    for name, value in re.findall(
        r'["\']?([A-Za-z_$][\w$]*)["\']?\s*[:=]\s*(true|false|-?\d+(?:\.\d+)?|"[^"]*"|\'[^\']*\')',
        body,
    ):
        if value in ('true', 'false'):
            props[name] = value == 'true'
        elif value[:1] in ('"', "'"):
            props[name] = value[1:-1]
        else:
            props[name] = float(value) if '.' in value else int(value)
    return props


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def inspect(source: str) -> None:
    """Report the shape of each bundler block without writing anything."""
    print(f'bundle size: {len(source):,} chars')
    for name in ('manifest', 'page_order', 'template', 'ext_resources'):
        block = find_block(source, name)
        if block is None:
            print(f'\n[{name}] MISSING')
            continue

        stripped = block.strip()
        print(f'\n[{name}] {len(stripped):,} chars')
        print(f'  head: {stripped[:200]!r}')

        if name == 'page_order':
            try:
                print(f'  json: {json.dumps(json.loads(stripped))[:600]}')
            except (json.JSONDecodeError, ValueError):
                pass
        elif name in ('manifest', 'ext_resources'):
            resources = parse_resource_block(block)
            if not resources:
                print('  (no resource entries)')
                continue
            print(f'  {len(resources)} entr(ies)')
            for key, entry in sorted(resources.items()):
                fields = ', '.join(sorted(entry))
                payload = pick(entry, 'data', 'content', 'base64', 'b64')
                size = f'{len(payload):>9,} b64' if payload else 'metadata only'
                mime = entry.get('mime', '-')
                print(f'    {key[:8]}  {mime:<24} {size}   [{fields}]')

    props = read_design_props(source)
    print(f'\n[design props] {props or "none found"}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('bundle', help='path to the Claude Design export HTML')
    parser.add_argument(
        '-o',
        '--out',
        default='design-src',
        help='output directory (default: design-src)',
    )
    parser.add_argument(
        '--inspect',
        action='store_true',
        help='report bundle structure without writing files',
    )
    parser.add_argument('-q', '--quiet', action='store_true', help='less output')
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.is_file():
        parser.error(f'no such file: {bundle_path}')

    source = bundle_path.read_text(encoding='utf-8', errors='replace')

    if args.inspect:
        inspect(source)
        return 0

    verbose = not args.quiet
    out_dir = Path(args.out)
    assets_dir = out_dir / 'assets'

    template_raw = find_block(source, 'template')
    if template_raw is None:
        print('error: no __bundler/template block found', file=sys.stderr)
        return 1

    markup = decode_template(template_raw)
    if verbose:
        print(f'template: {len(markup):,} chars of HTML')

    blocks = {
        name: find_block(source, name) for name in ('manifest', 'ext_resources')
    }
    if verbose:
        print('resources:')
    mapping = extract_resources(blocks, assets_dir, verbose)
    if verbose and not mapping:
        print('  (none)')

    markup, replaced, missing = rewrite_references(markup, mapping)
    markup = strip_bundler_blocks(markup)

    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / 'index.html'
    index_path.write_text(markup, encoding='utf-8')

    props = read_design_props(source)
    if props:
        (out_dir / 'design-props.json').write_text(
            json.dumps(props, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
        )

    if verbose:
        print(f'\nwrote {index_path} ({os.path.getsize(index_path):,} B)')
        print(f'rewrote {replaced} UUID reference(s)')
        if props:
            print(f'design props: {props}')
        if missing:
            print(f'\nWARNING: {len(missing)} unresolved UUID(s):', file=sys.stderr)
            for uuid in missing[:10]:
                print(f'  {uuid}', file=sys.stderr)
        leftover = markup.count('__bundler')
        if leftover:
            print(f'\nWARNING: {leftover} "__bundler" mention(s) remain', file=sys.stderr)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
