# design-src — reference workspace

Reconstructed output of the "Boarding Soft" design export
(`TP_Careers_KR.html`), produced by:

    python3 tools/unbundle.py TP_Careers_KR.html -o design-src

**This is reference material, not a deploy target.** Nothing here is served by
GitHub Pages. It exists so the shipped site can be diffed against the original
design.

## What the export turned out to contain

The bundle's blocks do not match the roles their names suggest:

| block                     | actual contents                                        |
| ------------------------- | ------------------------------------------------------ |
| `__bundler/manifest`      | the resource store — 24 base64 entries, mostly gzipped  |
| `__bundler/ext_resources` | UUID → original CDN URL, for React and ReactDOM         |
| `__bundler/template`      | the page markup, as a JSON-encoded escaped string       |
| `__bundler/page_order`    | empty (`[]`)                                            |

The page is **React-dependent**: it renders through a `dc-runtime` bundle that
compiles a `<script type="text/x-dc">` component, `<sc-for>` / `<sc-if>`
template directives, `{{ }}` interpolation, and `<x-import>` references to a
`TPDesignSystem_9211d8` component library (Button, Card, Badge, Input, Select).
None of that ships — it was ported to vanilla HTML/CSS/JS for the live site, as
the brief requires.

Design props confirmed from the `data-dc-script` block, both defaulting to
`true` and both treated as `true` in the port:

    showOpenPositions, showJourneyLine

## Checked in vs. regenerable

Committed:

- `index.html` — the reconstructed design, the thing worth diffing against
- `design-props.json` — extracted design props
- `assets/asset-16-a39f096f.png` — the TP wordmark used by the design

Ignored (see `.gitignore`) — ~2.5 MB of vendor blobs that add nothing to a
design diff and are reproducible at any time by re-running the unbundler:

- 18 × TP Sans TTF (~1.8 MB). The shipped site uses Noto Sans KR + IBM Plex
  Mono from Google Fonts instead, per the brief.
- `react.production.min.js`, `react-dom.production.min.js` (~142 KB)
- lucide v1.28.0 UMD (~414 KB). The icons the design actually uses were
  extracted from it and inlined as SVG into the site.
- `dc-runtime` and the design-system bundle (~121 KB)

## Deliberate deviations in the shipped port

Carried over from the brief, which overrides the export:

- `170+ 거점 국가` → `100+` in the stats strip, and the matching `170여 개국`
  phrase in the benefits copy → `100+`. The site standard is 100+.
- The design's footer line (`전 세계 170여 개 시장…`) is replaced by the SSM
  registration line.
- The three GATE cards link to `open-jobs.html`, `relocation-visa.html` and
  `salary-and-benefits.html` rather than all pointing at `#apply`.
- Position rows link to the iCIMS search, not `#apply`.
- TP Sans → Noto Sans KR (Korean) + IBM Plex Mono (airport codes only).
