#!/usr/bin/env python3
"""Apply the Boarding Soft shell to the KLP subpages.

Each subpage keeps its own body content and Korean copy untouched. What
changes is the shell and the palette:

  * head      — Google Fonts + assets/klp-theme.css, theme-color to slate
  * header    — departure board strip + the shared slate header
  * footer    — the shared footer (already identical across pages)
  * floating  — pink/slate pills and the round back-to-top
  * palette   — the legacy gold/black custom properties are remapped onto the
                Boarding Soft tokens, so every existing rule restyles itself
  * scripts   — the duplicated mobile-menu and back-to-top IIFEs are dropped
                in favour of assets/klp-theme.js

Usage:  python3 tools/apply-theme.py [page.html ...]
Run with no arguments to process every subpage.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICONS = json.loads((ROOT / 'tools' / 'icons.json').read_text(encoding='utf-8'))

PAGES = [
    'open-jobs.html', 'about-tp.html', 'salary-and-benefits.html',
    'hiring-process.html', 'why-malaysia-thailand.html', 'relocation-visa.html',
    'testimonials.html', 'office-environment.html', 'cost-of-living.html',
    'area-around-office.html', 'daily-life-malaysia.html',
]

NAV = [
    ('index.html', '홈'), ('open-jobs.html', '채용공고'), ('about-tp.html', '기업소개'),
    ('salary-and-benefits.html', '근무조건·복지'), ('hiring-process.html', '채용프로세스'),
    ('why-malaysia-thailand.html', '도시안내'), ('relocation-visa.html', '이주·비자'),
]
ICIMS = ('https://careerseng-teleperformance.icims.com/jobs/search'
         '?ss=1&amp;searchKeyword=korean')

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Noto+Sans+KR:wght@300;400;500;700;900&'
    'family=IBM+Plex+Mono:wght@500;600&display=swap">\n'
    '<link rel="stylesheet" href="assets/klp-theme.css">'
)


def svg(name: str) -> str:
    return ('<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{ICONS[name]}</svg>')


def nav_links(current: str) -> str:
    out = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ''
        out.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    out.append(f'<li><a href="{ICIMS}" target="_blank" rel="noopener noreferrer" '
               f'class="btn btn-accent btn-sm">지원하기</a></li>')
    return ''.join(out)


def header_for(page: str) -> str:
    links = nav_links(page)
    return f'''<div class="departure-board">
  <div class="inner">
    <span class="board-chip">TP-2026</span>
    <span class="board-route">{svg("plane-takeoff")}SEOUL <span aria-hidden="true">→</span> KUALA LUMPUR</span>
    <span class="board-status"><span class="dot"></span>NOW BOARDING</span>
  </div>
</div>
<header class="site-header" role="banner">
  <div class="header-inner">
    <a class="brand" href="index.html">
      <img src="photos/tp-logo.png" alt="TP" width="34" height="34">
      <span class="brand-text"><span class="brand-name">TP</span><span class="brand-tagline">말레이시아·태국</span></span>
    </a>
    <nav class="site-nav" aria-label="주요 내비게이션"><ul>{links}</ul></nav>
    <button class="mobile-toggle" id="mobileToggle" aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobileMenu"><span></span><span></span><span></span></button>
  </div>
  <nav class="mobile-menu" id="mobileMenu" aria-label="모바일 내비게이션"><ul>{links}</ul></nav>
</header>'''


def footer_for(page: str) -> str:
    """The shared footer, with aria-current marking the page you are on."""
    def link(href: str, label: str) -> str:
        cur = ' aria-current="page"' if href.split('#')[0] == page else ''
        return f'<li><a href="{href}"{cur}>{label}</a></li>'

    return f'''<footer role="contentinfo">
  <div class="footer-content">
    <div class="footer-brand"><div class="footer-logo"><img src="photos/tp-logo.png" alt="TP"><span class="footer-logo-text">TP</span></div><p class="footer-desc">전 세계 100개국에서 함께하는 글로벌 BPO 리더<br>한국어 역량을 보유한 인재의 새로운 커리어를 지원합니다</p><div class="badges"><span class="badge-item">🏆 6년 연속 말레이시아에서 가장 일하기 좋은 기업</span><span class="badge-item">🏆 5년 연속 세계에서 가장 일하기 좋은 기업</span></div><div class="footer-cta"><a href="{ICIMS}" target="_blank" rel="noopener noreferrer" class="btn btn-accent">지원하기</a></div></div>
    <div class="footer-section"><h3>기업정보</h3><ul>{link("about-tp.html", "기업소개")}{link("salary-and-benefits.html#benefits", "근무조건·복지")}{link("office-environment.html", "근무환경")}</ul></div>
    <div class="footer-section"><h3>채용·지원</h3><ul>{link("open-jobs.html", "채용공고")}{link("hiring-process.html", "채용프로세스")}{link("klp-apply-form.html", "카카오톡 상담 신청")}</ul></div>
    <div class="footer-section"><h3>현지 생활</h3><ul>{link("why-malaysia-thailand.html", "도시안내")}{link("relocation-visa.html", "이주·비자")}{link("daily-life-malaysia.html", "생활가이드")}</ul></div>
  </div>
  <div class="footer-bottom"><p class="ssm-info">Teleperformance Malaysia Sdn Bhd의 SSM(말레이시아 기업위원회) 등록번호: 201601023769 (1194708-K)</p><p>© 2026 TP. All rights reserved.</p></div>
</footer>'''


FLOATING = f'''<div class="floating">
  <button class="back-to-top" id="backToTop" type="button" aria-label="맨 위로">{svg("arrow-up")}</button>
  <a class="float-btn float-contact" href="klp-apply-form.html">{svg("message-circle")}문의하기</a>
  <a class="float-btn float-apply" href="{ICIMS}" target="_blank" rel="noopener noreferrer">{svg("plane-takeoff")}지원하기</a>
</div>'''


# The legacy pages are built entirely on these custom properties, so pointing
# them at the Boarding Soft palette restyles every existing rule at once.
REMAP = '''
/* ==== Boarding Soft remap ==================================================
   The page's own rules are unchanged; the tokens underneath them now resolve
   to the Boarding Soft palette. Appended last so it wins over the legacy
   button and surface rules above.
   ========================================================================= */
:root{
  --tp-black:#4B4C6A;--tp-dark:#4B4C6A;--tp-charcoal:#34354a;
  --tp-gray-dark:#5f607d;--tp-gray:#676767;--tp-gray-light:#8b8a9c;
  --tp-silver:#C2C7CD;--tp-light:#EAE8F1;--tp-off:#F3F1F7;--tp-white:#fff;
  --gold-primary:#FF0082;--gold-light:#e0007a;--gold-dark:#c40068;--gold-pale:#FFF0F7;
  --accent-blue:#4B4C6A;--accent-green:#00AF9B;
  --shadow-xs:0 1px 2px rgba(75,76,106,.05);
  --shadow-sm:0 2px 8px rgba(75,76,106,.06);
  --shadow-md:0 8px 24px rgba(75,76,106,.10);
  --shadow-lg:0 16px 40px rgba(75,76,106,.14);
  --shadow-gold:0 10px 24px rgba(255,0,130,.28);
}

body{font-family:var(--font-sans);color:var(--ink);line-height:1.7}

/* The shared shell must not inherit the page's own header/footer rules —
   those still resolve --tp-black to slate, which would paint slate on slate. */
.site-header .brand-name{color:#fff}
.site-header .brand-tagline{color:rgba(255,255,255,.62)}
.site-header .brand img{width:34px;height:34px}
.site-nav a{color:rgba(255,255,255,.82);font-size:.86rem;font-weight:400}
.site-nav a:hover{color:#fff}
.site-nav a[aria-current="page"]{color:#fff;font-weight:700}
.site-nav a::after{background:var(--pink)}
.mobile-menu a{color:rgba(255,255,255,.82);border-bottom:1px solid rgba(255,255,255,.07)}
.mobile-menu a:hover,.mobile-menu a:focus{background:rgba(255,255,255,.07);color:#fff}
.departure-board,.departure-board .inner{font-family:var(--font-mono)}
.board-chip,.board-status{color:#fff}
footer .footer-desc,footer .footer-section a{color:rgba(255,255,255,.62)}
footer .footer-section a:hover{color:var(--pink)}
footer .footer-logo-text,footer .footer-section h3{color:#fff}
footer .footer-bottom,footer .ssm-info{color:rgba(255,255,255,.5)}

/* Buttons follow the shared pill system rather than the old 4px squares. */
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:12px 26px;border-radius:var(--r-pill);
  font-family:inherit;font-size:.9rem;font-weight:700;
  border:1.5px solid transparent;cursor:pointer;white-space:nowrap;
  transition:background .2s var(--ease),color .2s var(--ease),
             border-color .2s var(--ease),transform .2s var(--ease),
             box-shadow .2s var(--ease);
}
.btn:hover{transform:translateY(-2px)}
.btn-gold,.btn-accent{background:var(--pink);color:#fff;border-color:var(--pink)}
.btn-gold:hover,.btn-accent:hover{background:var(--pink-hover);border-color:var(--pink-hover);color:#fff;box-shadow:var(--shadow-gold)}
.btn-primary{background:var(--slate);color:#fff;border-color:var(--slate)}
.btn-primary:hover{background:var(--slate-hover);border-color:var(--slate-hover);color:#fff}
.btn-secondary{background:#fff;color:var(--slate);border-color:var(--n-400)}
.btn-secondary:hover{border-color:var(--slate);color:var(--slate)}
.btn-ghost{background:transparent;color:var(--slate);border-color:var(--n-400)}
.btn-ghost:hover{background:var(--slate);color:#fff;border-color:var(--slate)}
.btn-sm{padding:8px 18px;font-size:.8rem}

/* Rounded surfaces */
.card,.city-card,.office-card,.testimonial,.job-card,.benefit-card,
.info-card,.contact-card,.cost-card,.area-card,.step-card,.faq-item,
.stat-card,.award-item,.tip-card{border-radius:var(--r-card)}
img.card-img,.card>img,.city-card>img,.office-image{border-radius:0}

/* Legacy section headings pick up the shared type scale. */
.section-title{font-weight:900;letter-spacing:-.02em;color:var(--slate)}
.section-subtitle{font-weight:300;color:var(--ink-soft)}

/* The old gold underline decoration becomes a pink one. */
.section-title-decorated::after{background:var(--pink)!important}

/* Hero blocks on subpages sit on the Boarding Soft gradient. */
.page-hero,.hero{background:var(--hero-gradient)!important}
.page-hero h1,.hero h1{color:var(--slate)}

/* A few numbers were painted with a hardcoded gold gradient clipped to the
   text, so they sit outside the token remap. Solid slate instead. */
.stat-number,.gptw-stat-number,.gptw-highlight{
  background:none!important;-webkit-background-clip:initial!important;
  background-clip:initial!important;-webkit-text-fill-color:currentColor!important;
  color:var(--slate)!important;
}
.gptw-highlight{color:var(--pink)!important}
'''

SKIP_LINK = '<a class="skip-link" href="#main">본문 바로가기</a>'

# Inline behaviours that assets/klp-theme.js now owns. Leaving them in place
# would double-bind the toggle and fight over the back-to-top class name.
DROP_SCRIPTS = [
    re.compile(r"\(function\(\)\{const toggle=document\.getElementById\('mobileToggle'\).*?\}\)\(\);\n?", re.S),
    re.compile(r"\(function\(\)\{const backToTop=document\.getElementById\('backToTop'\).*?\}\)\(\);\n?", re.S),
]


def transform(path: pathlib.Path) -> list[str]:
    page = path.name
    src = path.read_text(encoding='utf-8')
    notes: list[str] = []

    # --- head -------------------------------------------------------------
    src = re.sub(r'<meta name="theme-color" content="[^"]*">',
                 '<meta name="theme-color" content="#4B4C6A">', src)

    pretendard = re.search(r'<link rel="stylesheet" href="https://cdn\.jsdelivr\.net[^>]*>', src)
    if pretendard:
        src = src.replace(pretendard.group(0), FONTS)
    else:
        src = src.replace('<style>', FONTS + '\n<style>', 1)
        notes.append('no Pretendard link found; inserted fonts before <style>')

    # --- palette remap ----------------------------------------------------
    close = src.rfind('</style>')
    if close == -1:
        notes.append('NO </style> — remap not applied')
    else:
        src = src[:close] + REMAP + src[close:]

    # --- shell ------------------------------------------------------------
    src, n = re.subn(r'<header\b.*?</header>', lambda _: header_for(page), src, count=1, flags=re.S)
    if not n:
        notes.append('NO <header> replaced')

    src, n = re.subn(r'<footer\b.*?</footer>', lambda _: footer_for(page), src, count=1, flags=re.S)
    if not n:
        notes.append('NO <footer> replaced')

    # Floating pills + back-to-top, however the page spelled them.
    src, n = re.subn(
        r'<a[^>]*class="floating-casual".*?</a>\s*<a[^>]*class="floating-apply".*?</a>\s*'
        r'<button class="back-to-top"[^>]*>.*?</button>',
        lambda _: FLOATING, src, count=1, flags=re.S)
    if not n:
        src, n = re.subn(
            r'<a[^>]*class="floating-apply".*?</a>\s*<a[^>]*class="floating-casual".*?</a>\s*'
            r'<button class="back-to-top"[^>]*>.*?</button>',
            lambda _: FLOATING, src, count=1, flags=re.S)
    if not n:
        notes.append('NO floating buttons replaced')

    # --- skip link --------------------------------------------------------
    if 'skip-link' not in src:
        src = re.sub(r'(<body[^>]*>)', r'\1\n' + SKIP_LINK, src, count=1)

    # --- scripts ----------------------------------------------------------
    for pattern in DROP_SCRIPTS:
        src = pattern.sub('', src)

    # Match the shared scroll-margin so JS smooth-scroll lands consistently.
    src = src.replace('const offset=70;', 'const offset=100;')

    if 'assets/klp-theme.js' not in src:
        src = src.replace('</body>', '<script src="assets/klp-theme.js" defer></script>\n</body>', 1)

    path.write_text(src, encoding='utf-8')
    return notes


def main() -> int:
    targets = sys.argv[1:] or PAGES
    failed = False
    for name in targets:
        path = ROOT / name
        if not path.is_file():
            print(f'{name:30} MISSING')
            failed = True
            continue
        notes = transform(path)
        status = '; '.join(notes) if notes else 'ok'
        if notes:
            failed = True
        print(f'{name:30} {status}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
