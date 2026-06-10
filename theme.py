"""Portfolio-matched theme for Streamlit apps.

Single-file, reusable: drop `theme.py` + `.streamlit/config.toml` into any
Streamlit app to get the tiennguyentt.github.io design language — dark
editor surface, indigo accent, IBM Plex Sans headings, JetBrains Mono
labels, git-diff details. Call `theme.inject()` once at the top of the app,
then build blocks with the helpers below (they return HTML strings; pass
them to `theme.card(...)` / `st.markdown(..., unsafe_allow_html=True)`).
"""

import html as _html

import streamlit as st

PALETTE = {
    "bg": "#0B0E14",
    "panel": "#0E1219",
    "line": "#1E2430",
    "text": "#E7EAF0",
    "dim": "#9AA4B2",
    "accent": "#7C8CFF",
    "add": "#3FB950",
    "del": "#F85149",
    "warn": "#F2A65A",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #0B0E14; --surface: #11151F; --raised: #161B27;
  --ink: #E7EAF0; --muted: #9AA3B2; --dim: #6B7585;
  --accent: #7C8CFF; --line: #1E2430; --line-strong: #2A3140;
  --add: #3FB950; --del: #F85149; --warn: #F2A65A;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg); color: var(--ink);
  font-family: 'Inter', sans-serif; font-size: 15px; line-height: 1.65;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1120px; padding-top: 3rem; padding-bottom: 6rem; }

/* breathing glow behind the top of the page */
[data-testid="stAppViewContainer"]::before {
  content: ""; position: fixed; inset: -30% -20% auto -20%; height: 60%;
  background: radial-gradient(ellipse at 30% 0%, rgba(124,140,255,.07), transparent 60%);
  pointer-events: none;
}

h1, h2, h3 { font-family: 'IBM Plex Sans', sans-serif !important; letter-spacing: -0.01em; }

[data-testid="stSidebar"] {
  background: var(--surface); border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  font-family: 'JetBrains Mono', monospace !important; font-size: 11.5px !important;
  text-transform: uppercase; letter-spacing: .16em; color: var(--accent) !important;
}
[data-testid="stSidebar"] .block-container { padding-top: 2.4rem; }

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  letter-spacing: .08em; color: var(--muted); background: transparent;
  padding: 10px 14px; transition: color .18s ease;
}
.stTabs [aria-selected="true"] { color: var(--accent) !important; }

.stButton button, .stDownloadButton button {
  font-family: 'JetBrains Mono', monospace; font-size: 13px;
  border-radius: 8px; border: 1px solid var(--line-strong);
  transition: border-color .18s ease, transform .18s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
  border-color: var(--accent); transform: translateY(-1px);
}
[data-testid="stExpander"] {
  border: 1px solid var(--line); border-radius: 12px; background: var(--surface);
  margin-top: 10px;
}
[data-testid="stExpander"] summary {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
  padding: 14px 16px; transition: color .18s ease;
}
[data-testid="stExpander"] summary:hover { color: var(--accent); }
.stTextInput input, .stSelectbox div { font-family: 'Inter', sans-serif; }

/* ---- motion ----------------------------------------------------------- */
@keyframes seUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes seBlink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
.se-card, .se-catch, .se-turn, .se-stat, .se-spechead { animation: seUp .5s ease both; }
.se-catch:nth-of-type(1), .se-stat:nth-child(1) { animation-delay: .05s; }
.se-stat:nth-child(2) { animation-delay: .1s; } .se-stat:nth-child(3) { animation-delay: .15s; }
.se-stat:nth-child(4) { animation-delay: .2s; } .se-stat:nth-child(5) { animation-delay: .25s; }
@media (prefers-reduced-motion: reduce) {
  .se-card, .se-catch, .se-turn, .se-stat, .se-spechead { animation: none; }
}

/* ---- voice ------------------------------------------------------------ */
.se-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: var(--muted);
  text-transform: uppercase; letter-spacing: .18em; margin: 0 0 18px;
}
.se-kicker::before { content: '+ '; color: var(--add); }
.se-kicker::after {
  content: ''; display: inline-block; width: 8px; height: 14px;
  background: var(--accent); margin-left: 8px; vertical-align: -2px;
  animation: seBlink 1.1s steps(1) infinite;
}
.se-hero-head {
  font-family: 'IBM Plex Sans', sans-serif; font-weight: 700;
  font-size: clamp(28px, 4vw, 42px); letter-spacing: -0.015em;
  color: var(--ink); line-height: 1.18; margin: 0 0 18px;
}
.se-hero-sub { color: var(--muted); font-size: 16px; max-width: 70ch; line-height: 1.7; margin-bottom: 8px; }

/* open section heads: hairline + ghost number, lots of air */
.se-spechead {
  display: flex; align-items: baseline; gap: 14px;
  border-top: 1px solid var(--line-strong); padding-top: 22px;
  margin: 56px 0 22px;
}
.se-spechead .sid {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px;
  color: var(--accent); letter-spacing: .14em; text-transform: uppercase;
}
.se-spechead .stitle {
  font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 21px; color: var(--ink);
}
.se-spechead .sstatus {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin-left: auto;
  letter-spacing: .06em;
}

/* ---- stats ------------------------------------------------------------- */
.se-stats { display: flex; gap: 14px; flex-wrap: wrap; margin: 28px 0 8px; }
.se-stat {
  border: 1px solid var(--line); background: rgba(17,21,31,.7); border-radius: 12px;
  padding: 16px 22px; min-width: 150px;
  transition: border-color .2s ease, transform .2s ease;
}
.se-stat:hover { border-color: var(--line-strong); transform: translateY(-2px); }
.se-stat .v { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 24px; color: var(--ink); }
.se-stat .v .from { color: var(--dim); font-size: 16px; font-weight: 500; }
.se-stat .v .delta { color: var(--add); text-shadow: 0 0 18px rgba(63,185,80,.45); }
.se-stat .l { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin-top: 6px; }

/* ---- open cards (default surface) -------------------------------------- */
.se-card {
  border: 1px solid var(--line); background: rgba(17,21,31,.55);
  border-radius: 12px; padding: 20px 22px; margin: 0 0 14px;
  transition: border-color .2s ease;
}
.se-card:hover { border-color: var(--line-strong); }
.se-card .rowtop { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.se-id { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent); letter-spacing: .04em; }
.se-topic { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 15.5px; color: var(--ink); }
.se-body { color: #C3CAD6; font-size: 14.5px; line-height: 1.7; margin-top: 8px; }
.se-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .06em;
  border: 1px solid var(--line-strong); border-radius: 999px; padding: 3px 11px;
  color: var(--muted); margin-left: auto; white-space: nowrap;
}
.se-quote {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #8A94A6;
  border-left: 2px solid var(--line-strong); padding: 6px 0 6px 14px; margin: 12px 0 0;
  line-height: 1.7;
}
.se-ac { color: #C3CAD6; font-size: 14px; margin: 8px 0 0 2px; line-height: 1.65; }
.se-ac::before { content: '▸ '; color: var(--accent); }
.se-trace { font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin-top: 12px; line-height: 1.7; }
.se-issue { color: #C3CAD6; font-size: 13.5px; margin-top: 6px; }
.se-issue::before { content: '! '; font-family: 'JetBrains Mono', monospace; color: var(--warn); font-weight: 600; }
.se-bar { height: 6px; border-radius: 3px; background: var(--line); margin-top: 8px; overflow: hidden; }
.se-bar > div { height: 6px; border-radius: 3px; background: linear-gradient(90deg, var(--accent), #A3B3FF); }
.se-verdict-ship { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--add); }
.se-verdict-revise { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--warn); }
.se-block {
  border-left: 3px solid var(--del); background: rgba(248,81,73,.06);
  border-radius: 0 10px 10px 0; padding: 16px 18px; margin-top: 16px;
  color: var(--ink); font-size: 14px; line-height: 1.7;
}
.se-conflict-win { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--add); margin-top: 10px; }
.se-flag {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--warn);
  border: 1px dashed rgba(242,166,90,.5); border-radius: 8px;
  padding: 10px 14px; margin-top: 14px; display: inline-block; line-height: 1.6;
}

/* ---- hero catches: the only raised boxes on the page ------------------- */
.se-catch {
  border: 1px solid var(--line-strong); border-left: 3px solid var(--del);
  background: linear-gradient(180deg, var(--raised), var(--surface));
  border-radius: 0 14px 14px 14px; padding: 24px 26px; margin: 0 0 18px;
  box-shadow: 0 12px 36px rgba(0,0,0,.35);
  transition: border-color .2s ease, transform .25s ease;
}
.se-catch:hover { border-color: #38415A; transform: translateY(-2px); }
.se-catch .chead { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.se-catch .cnum { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--del); font-weight: 600; letter-spacing: .08em; }
.se-catch .ctitle { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 16.5px; color: var(--ink); line-height: 1.5; }
.se-vs { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--dim); margin: 16px 0 2px; letter-spacing: .1em; }
.se-diff-del {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #FCA5A5;
  background: rgba(248,81,73,.08); border-left: 2px solid var(--del);
  padding: 10px 14px; margin-top: 10px; white-space: pre-wrap; line-height: 1.7; border-radius: 0 8px 8px 0;
}
.se-diff-del::before { content: '- '; color: var(--del); font-weight: 600; }
.se-diff-add {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #86EFAC;
  background: rgba(63,185,80,.08); border-left: 2px solid var(--add);
  padding: 10px 14px; margin-top: 4px; white-space: pre-wrap; line-height: 1.7; border-radius: 0 8px 8px 0;
}
.se-diff-add::before { content: '+ '; color: var(--add); font-weight: 600; }
.se-summon {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--del);
  border: 1px solid rgba(248,81,73,.4); border-radius: 999px;
  padding: 5px 14px; display: inline-block; margin-top: 14px;
}
.se-gatehit { font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #C3CAD6; margin-top: 9px; line-height: 1.65; }
.se-gatehit .rid { color: var(--del); font-weight: 600; }
.se-gatehit .warn { color: var(--warn); font-weight: 600; }
.se-stepper { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 12px 0 20px; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .06em; }
.se-step { border: 1px solid var(--line-strong); border-radius: 999px; padding: 5px 14px; color: var(--dim); transition: all .2s ease; }
.se-step.done { color: var(--add); border-color: rgba(63,185,80,.4); }
.se-step.active { color: var(--accent); border-color: var(--accent); box-shadow: 0 0 14px rgba(124,140,255,.25); }
.se-step-arrow { color: var(--line-strong); }
.se-notes {
  border-top: 1px dashed var(--line-strong); margin-top: 14px; padding-top: 12px;
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #8A94A6; line-height: 1.75;
}
.se-notes b { color: var(--muted); font-weight: 600; }
.se-noobj { font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin: 6px 0; }
.se-noobj::before { content: '○ '; color: var(--add); }

/* ---- debate bubbles ----------------------------------------------------- */
.se-turn {
  border: 1px solid var(--line); border-left-width: 3px; background: rgba(17,21,31,.55);
  border-radius: 0 12px 12px 12px; padding: 18px 20px; margin: 0 0 14px;
  transition: border-color .2s ease;
}
.se-turn:hover { border-color: var(--line-strong); }
.se-turn .thead {
  display: flex; gap: 12px; align-items: baseline;
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .08em;
}
.se-turn .trole { font-weight: 600; text-transform: uppercase; }
.se-turn .tstance { color: var(--muted); }
.se-turn .tround { color: var(--dim); margin-left: auto; }
.se-turn .tmsg { color: #C3CAD6; font-size: 14.5px; line-height: 1.7; margin-top: 10px; }
</style>
"""

ROLE_COLORS = {
    "po": PALETTE["accent"],
    "eng": PALETTE["warn"],
    "qa": PALETTE["add"],
    "arbiter": PALETTE["text"],
}


def esc(value) -> str:
    return _html.escape(str(value))


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def kicker(text: str) -> None:
    st.markdown(f'<p class="se-kicker">{esc(text)}</p>', unsafe_allow_html=True)


def section(sid: str, title: str, status: str = "") -> None:
    status_html = f'<span class="sstatus">{esc(status)}</span>' if status else ""
    st.markdown(
        f'<div class="se-spechead"><span class="sid">{esc(sid)}</span>'
        f'<span class="stitle">{esc(title)}</span>{status_html}</div>',
        unsafe_allow_html=True,
    )


def card(inner_html: str) -> None:
    st.markdown(f'<div class="se-card">{inner_html}</div>', unsafe_allow_html=True)


def bubble(role_key: str, role_label: str, stance: str, message: str, refs: list[str], rnd, color: str | None = None) -> str:
    color = color or ROLE_COLORS.get(role_key, PALETTE["dim"])
    refs_html = f' · {esc(", ".join(refs))}' if refs else ""
    return (
        f'<div class="se-turn" style="border-left-color:{color}">'
        f'<div class="thead"><span class="trole" style="color:{color}">{esc(role_label)}</span>'
        f'<span class="tstance">{esc(stance)}{refs_html}</span>'
        f'<span class="tround">round {rnd}</span></div>'
        f'<div class="tmsg">{esc(message)}</div></div>'
    )


def bar(value: int, max_value: int = 5) -> str:
    pct = max(0, min(100, round(value / max_value * 100)))
    return f'<div class="se-bar"><div style="width:{pct}%"></div></div>'
