#!/usr/bin/env python3
"""Assemble the new Boarding Soft index.html.

Ported sections are lifted verbatim out of the current index.html so no
Korean copy is retyped; they are restyled via CSS rather than rewritten.
"""
import json, re, pathlib

ROOT = pathlib.Path("/home/user/KLP")
SCR = pathlib.Path("/tmp/claude-0/-home-user-KLP/067ed698-cedb-531a-9f16-620269cf5d42/scratchpad")
SEC = SCR / "sections"
old = (ROOT / "index.html").read_text(encoding="utf-8")
ICONS = json.loads((SCR / "icons.json").read_text(encoding="utf-8"))


def svg(name, cls="icon", extra=""):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true"{extra}>{ICONS[name]}</svg>')


def sec(name):
    return (SEC / f"{name}.html").read_text(encoding="utf-8").strip()


# --- verbatim GA4 block ----------------------------------------------------
# Two script tags: the gtag loader, then the config + tracking helpers. Anchor
# on the trailing <meta charset> so neither is clipped.
ga4 = re.search(r'<!-- Google Analytics 4 - KLP -->.*?</script>\n(?=<meta charset)',
                old, re.S).group(0)
for required in ('trackCustomEvent', 'page_engagement', 'trackPageEngagement'):
    assert required in ga4, f'GA4 block lost {required}'
assert ga4.count('G-SPPNGS1L2L') == 2, 'GA4 block should mention the ID twice'

# --- verbatim apply markup + script ---------------------------------------
apply_markup = sec("klp-apply-section")
apply_script = re.search(
    r"\(function\(\)\{\n  var APPS_SCRIPT_URL.*?\n\}\)\(\);", old, re.S).group(0)
hero_rotate = re.search(r"\(function\(\)\{const el=document\.getElementById\('hero-rotate'\).*?\}\)\(\);", old, re.S).group(0)
gptw_script = re.search(r"\(function\(\)\{const el=document\.getElementById\('gptwYears'\).*?\}\)\(\);", old, re.S).group(0)

# --- FAQ: rebuild markup from the old copy, keep questions/answers exact ---
faq_src = sec("faq-section")
pairs = re.findall(
    r'<div class="faq-question">(.*?)</div><div class="faq-answer"><p>(.*?)</p></div>',
    faq_src, re.S)
assert len(pairs) == 6, f"expected 6 FAQ items, found {len(pairs)}"
faq_items = "\n".join(
    f'''        <div class="faq-item">
          <button class="faq-question" type="button">{q}{svg("chevron-down")}</button>
          <div class="faq-answer"><p>{a}</p></div>
        </div>''' for q, a in pairs)

NAV = [
    ("index.html", "홈"), ("open-jobs.html", "채용공고"), ("about-tp.html", "기업소개"),
    ("salary-and-benefits.html", "근무조건·복지"), ("hiring-process.html", "채용프로세스"),
    ("why-malaysia-thailand.html", "도시안내"), ("relocation-visa.html", "이주·비자"),
]
ICIMS = "https://careerseng-teleperformance.icims.com/jobs/search?ss=1&amp;searchKeyword=korean"


def nav_links(current, cls=""):
    out = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        out.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    out.append(f'<li><a href="{ICIMS}" target="_blank" rel="noopener noreferrer" class="btn btn-accent btn-sm">지원하기</a></li>')
    return "".join(out)


DEPARTURE_BOARD = f'''<div class="departure-board">
    <div class="inner">
      <span class="board-chip">TP-2026</span>
      <span class="board-route">{svg("plane-takeoff")}SEOUL <span aria-hidden="true">→</span> KUALA LUMPUR</span>
      <span class="board-status"><span class="dot"></span>NOW BOARDING</span>
    </div>
  </div>'''

HEADER = f'''<header class="site-header" role="banner">
    <div class="header-inner">
      <a class="brand" href="index.html">
        <img src="photos/tp-logo.png" alt="TP" width="34" height="34">
        <span class="brand-text"><span class="brand-name">TP</span><span class="brand-tagline">말레이시아·태국</span></span>
      </a>
      <nav class="site-nav" aria-label="주요 내비게이션"><ul>{nav_links("index.html")}</ul></nav>
      <button class="mobile-toggle" id="mobileToggle" aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobileMenu"><span></span><span></span><span></span></button>
    </div>
    <nav class="mobile-menu" id="mobileMenu" aria-label="모바일 내비게이션"><ul>{nav_links("index.html")}</ul></nav>
  </header>'''

HERO = f'''<section class="hero">
    <div class="hero-inner">
      <div>
        <span class="hero-eyebrow">{svg("plane-takeoff")}TP MALAYSIA / THAILAND CAREERS</span>
        <h1>당신의 커리어,<br>여기서 이륙합니다</h1>
        <p class="hero-sub">서류부터 비자, 항공권, 첫 숙소까지 — 해외 취업의 모든 단계를 TP 한국팀이 함께합니다.</p>
        <div class="hero-cta">
          <a href="{ICIMS}" target="_blank" rel="noopener noreferrer" class="btn btn-accent btn-lg">지원하기</a>
          <a href="#positions" class="btn btn-secondary btn-lg">포지션 둘러보기</a>
        </div>
      </div>
      <div class="pass">
        <div class="pass-head">
          <span><span class="board-chip">TP-2026</span> <span class="label">BOARDING PASS</span></span>
          <span class="board-status"><span class="dot"></span>NOW BOARDING</span>
        </div>
        <div class="pass-body">
          <div class="route-ends">
            <div class="airport"><div class="code">ICN</div><div class="city">SEOUL</div></div>
            <div class="airport"><div class="code">KUL</div><div class="city">KUALA LUMPUR</div></div>
          </div>
          <div class="route" aria-hidden="true">
            <div class="track"></div>
            <div class="progress"></div>
            {svg("plane", cls="icon plane")}
          </div>
          <div class="pass-meta">
            <div><div class="k">PASSENGER</div><div class="v">FUTURE TP EXPERT</div></div>
            <div style="text-align:right"><div class="k">GATE</div><div class="v">2026</div></div>
          </div>
        </div>
      </div>
    </div>
  </section>'''

STATS = '''<section class="section-tight section-softer">
    <div class="container">
      <div class="stat-chips">
        <span class="stat-chip"><span class="n">100+</span><span class="l">거점 국가 수</span></span>
        <span class="stat-chip"><span class="n">500K+</span><span class="l">전 세계 임직원 수</span></span>
        <span class="stat-chip"><span class="n">7,000+</span><span class="l">말레이시아·태국 임직원 수</span></span>
        <span class="stat-chip"><span class="n">200+</span><span class="l">명의 한국팀 동료</span></span>
        <span class="stat-chip"><span class="n">6</span><span class="l">년 연속 Great Place to Work® 인증</span></span>
        <span class="stat-chip"><span class="n">5</span><span class="l">년 연속 World\'s Best Workplaces<sup>TM</sup> 선정</span></span>
      </div>
    </div>
  </section>'''

TICKETS = [
    ("GATE 01", "briefcase", "채용공고", "한국어 인재 포지션을 확인하세요.", "open-jobs.html"),
    ("GATE 02", "luggage", "이주 · 비자", "항공권부터 비자까지 전 과정을 지원합니다.", "relocation-visa.html"),
    ("GATE 03", "palmtree", "근무조건 · 복지", "급여, 수당, 휴가를 상세히 안내합니다.", "salary-and-benefits.html"),
]
tickets_html = "\n".join(f'''        <a class="ticket" href="{href}">
          <div class="ticket-head">
            <span class="ticket-name">{svg(icon)}{title}</span>
            <span class="ticket-gate">{gate}</span>
          </div>
          <div class="ticket-body">
            <p>{desc}</p>
            <span class="ticket-go">보러가기 {svg("arrow-right")}</span>
          </div>
        </a>''' for gate, icon, title, desc, href in TICKETS)

GATES = f'''<section class="section section-soft">
    <div class="container">
      <div class="section-head"><h2 class="section-title">어디부터 시작할까요?</h2></div>
      <div class="grid grid-3">
{tickets_html}
      </div>
    </div>
  </section>'''

# Design benefit copy, with the 170여 개국 figure brought to the site standard.
BENEFITS = [
    ("plane-takeoff", "출국 전 과정 지원", "항공권 · 비자 · 초기 정착까지 전담팀이 함께합니다."),
    ("languages", "한국 채용팀", "채용부터 온보딩까지 모든 과정을 한국어로 안내합니다."),
    ("globe", "글로벌 커리어", "외국계 기업에서의 해외근무 경력을 쌓을 수 있습니다."),
    ("hand-heart", "복지 · 수당", "다양한 복리후생과 경쟁력 있는 급여 패키지를 제공합니다."),
    ("graduation-cap", "체계적인 교육", "입사 후 직무 트레이닝 프로그램을 지원합니다."),
    ("users", "다국적 기업문화", "전 세계에서 모인 200여 명의 한국팀 동료가 함께합니다."),
]
benefits_html = "\n".join(f'''        <div class="card card-hover" data-reveal>
          <div class="card-body">
            <div class="icon-tile">{svg(icon)}</div>
            <div class="card-title" style="margin-top:16px">{t}</div>
            <div class="card-desc">{d}</div>
          </div>
        </div>''' for icon, t, d in BENEFITS)

BENEFITS_SEC = f'''<section class="section" id="benefits">
    <div class="container">
      <div class="section-head">
        <div class="section-eyebrow">WHY TP</div>
        <h2 class="section-title">복리후생</h2>
        <p class="section-subtitle">안심 · 성장 · 행복</p>
      </div>
      <div class="grid grid-3">
{benefits_html}
      </div>
    </div>
  </section>'''

STEPS = [
    ("file-text", "서류 심사", "이력서 제출"),
    ("monitor", "온라인 테스트", "언어 · 역량"),
    ("message-square", "1차 면접", "채용팀"),
    ("user-check", "2차 면접", "실무팀"),
    ("plane-takeoff", "비자 · 출국", "전 과정 동행"),
]
steps_html = "\n".join(f'''        <div class="journey-step" data-reveal>
          <div class="tile">{svg(icon)}</div>
          <div class="t">{t}</div>
          <div class="s">{s}</div>
        </div>''' for icon, t, s in STEPS)

JOURNEY = f'''<section class="section section-softer" id="interview">
    <div class="container" style="max-width:1000px">
      <div class="section-head">
        <div class="section-eyebrow">HIRING JOURNEY</div>
        <h2 class="section-title">채용 여정</h2>
        <p class="section-subtitle">전 과정 온라인 · 모든 단계 한국어 지원</p>
      </div>
      <div class="journey">
        <div class="journey-line" aria-hidden="true"></div>
{steps_html}
      </div>
    </div>
  </section>'''

POSITIONS = f'''<section class="section section-soft" id="positions">
    <div class="container" style="max-width:920px">
      <div class="section-head">
        <div class="section-eyebrow">OPEN ROLES</div>
        <h2 class="section-title">채용 중인 포지션</h2>
      </div>
      <div class="positions" id="positionList"></div>
    </div>
  </section>'''

# The same footer every other page uses, so there is exactly one of them.
FOOTER = f'''<footer role="contentinfo">
  <div class="footer-content">
    <div class="footer-brand"><div class="footer-logo"><img src="photos/tp-logo.png" alt="TP"><span class="footer-logo-text">TP</span></div><p class="footer-desc">전 세계 100개국에서 함께하는 글로벌 BPO 리더<br>한국어 역량을 보유한 인재의 새로운 커리어를 지원합니다</p><div class="badges"><span class="badge-item">🏆 6년 연속 말레이시아에서 가장 일하기 좋은 기업</span><span class="badge-item">🏆 5년 연속 세계에서 가장 일하기 좋은 기업</span></div><div class="footer-cta"><a href="{ICIMS}" target="_blank" rel="noopener noreferrer" class="btn btn-accent">지원하기</a></div></div>
    <div class="footer-section"><h3>기업정보</h3><ul><li><a href="about-tp.html">기업소개</a></li><li><a href="salary-and-benefits.html#benefits">근무조건·복지</a></li><li><a href="office-environment.html">근무환경</a></li></ul></div>
    <div class="footer-section"><h3>채용·지원</h3><ul><li><a href="open-jobs.html">채용공고</a></li><li><a href="hiring-process.html">채용프로세스</a></li><li><a href="klp-apply-form.html">카카오톡 상담 신청</a></li></ul></div>
    <div class="footer-section"><h3>현지 생활</h3><ul><li><a href="why-malaysia-thailand.html">도시안내</a></li><li><a href="relocation-visa.html">이주·비자</a></li><li><a href="daily-life-malaysia.html">생활가이드</a></li></ul></div>
  </div>
  <div class="footer-bottom"><p class="ssm-info">Teleperformance Malaysia Sdn Bhd의 SSM(말레이시아 기업위원회) 등록번호: 201601023769 (1194708-K)</p><p>© 2026 TP. All rights reserved.</p></div>
</footer>'''

FLOATING = f'''<div class="floating">
  <button class="back-to-top" id="backToTop" type="button" aria-label="맨 위로">{svg("arrow-up")}</button>
  <a class="float-btn float-contact" href="#apply">{svg("message-circle")}문의하기</a>
  <a class="float-btn float-apply" href="{ICIMS}" target="_blank" rel="noopener noreferrer">{svg("plane-takeoff")}지원하기</a>
</div>'''

PAGE_CSS = (SCR / "index-page.css").read_text(encoding="utf-8")

doc = f'''<!DOCTYPE html><html lang="ko"><head>

{ga4}<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TP 채용 | 말레이시아·태국 한국어 채용</title>
<meta name="description" content="Teleperformance(TP) – 전 세계 100개국에서 함께하는 글로벌 BPO 리더 | 말레이시아·태국 한국어 인재 채용">
<meta name="theme-color" content="#4B4C6A">
<link rel="icon" href="photos/tp-logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=IBM+Plex+Mono:wght@500;600&display=swap">
<link rel="stylesheet" href="assets/klp-theme.css">
<style>
{PAGE_CSS}</style>
</head>
<body>
<a class="skip-link" href="#main">본문 바로가기</a>

  {DEPARTURE_BOARD}

  {HEADER}

<main id="main">

  {HERO}

  {STATS}

  {GATES}

  {BENEFITS_SEC}

  {JOURNEY}

  {POSITIONS}

  {sec("gptw-section")}

  {sec("korean-community")}

  {sec("priority-menu")}

  {sec("social-connect")}

  {sec("icon-grid")}

  {sec("cities")}

  {sec("video-section")}

  {sec("world-map-section")}

  {sec("office-section")}

  {sec("lifestyle-section")}

  {sec("testimonials")}

  <section class="section section-softer" id="faq">
    <div class="container">
      <div class="section-head">
        <div class="section-eyebrow">FAQ</div>
        <h2 class="section-title">자주 묻는 질문</h2>
      </div>
      <div class="faq">
{faq_items}
      </div>
    </div>
  </section>

  {sec("contact-min")}

  {apply_markup}

</main>

  {FOOTER}

{FLOATING}

<script src="assets/klp-theme.js" defer></script>
<script>
/* ------------------------------------------------------------------
   Open positions — edit this list to change what the site advertises.
   Every 지원하기 button points at the iCIMS Korean-language search.
   ------------------------------------------------------------------ */
var KLP_POSITIONS = [
  {{ title: '한국어 고객 지원 (CS)',    location: '말레이시아 쿠알라룸푸르' }},
  {{ title: '한국어 테크 서포트',       location: '말레이시아 쿠알라룸푸르' }},
  {{ title: '한국어 콘텐츠 모더레이터', location: '태국 방콕' }},
  {{ title: '한국어 세일즈 서포트',     location: '말레이시아 페낭' }}
];
var KLP_APPLY_URL = 'https://careerseng-teleperformance.icims.com/jobs/search?ss=1&searchKeyword=korean';

(function () {{
  var list = document.getElementById('positionList');
  if (!list) return;
  var pin = '{svg("map-pin")}';
  var clock = '{svg("clock")}';
  list.innerHTML = KLP_POSITIONS.map(function (p) {{
    return '<div class="position" data-reveal>' +
      '<div style="min-width:0">' +
        '<div class="t">' + p.title + '</div>' +
        '<div class="meta">' +
          '<span>' + pin + p.location + '</span>' +
          (p.type ? '<span>' + clock + p.type + '</span>' : '') +
          '<span class="badge">한국어</span>' +
        '</div>' +
      '</div>' +
      '<a class="btn btn-accent btn-sm" href="' + KLP_APPLY_URL + '" target="_blank" rel="noopener noreferrer">지원하기</a>' +
    '</div>';
  }}).join('');
}})();
{hero_rotate}
{gptw_script}
{apply_script}
</script>


</body></html>
'''

(ROOT / "index.html").write_text(doc, encoding="utf-8")
print(f"wrote index.html  {len(doc):,} chars")
