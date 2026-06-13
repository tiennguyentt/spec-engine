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
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..600,0..1,-25..0&display=block');

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
  min-width: 270px; max-width: 340px;
}
/* narrow window: keep the sidebar a fixed sliver so the chat never gets pushed off-screen */
@media (max-width: 860px) {
  [data-testid="stSidebar"] { width: 270px !important; min-width: 270px !important; }
}
/* the pinned bottom input strip: solid app background, never wider than the view */
[data-testid="stBottom"], [data-testid="stBottom"] > div { background: var(--bg); }
[data-testid="stBottomBlockContainer"] { max-width: 1120px; }
[data-testid="stChatInput"] { max-width: 100%; }
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
/* score count-up: registered custom property animates the counter itself */
@property --se-n { syntax: '<integer>'; initial-value: 0; inherits: false; }
.se-countup { --se-n: var(--se-target, 0); counter-reset: sen var(--se-n);
  animation: seCount .9s cubic-bezier(.16,1,.3,1) .25s both; }
.se-countup::after { content: counter(sen); }
@keyframes seCount { from { --se-n: 0; } to { --se-n: var(--se-target, 0); } }

/* verdict lock-in: stamps into place after the score settles */
@keyframes seLock { 0% { opacity: 0; transform: scale(1.45); }
  60% { opacity: 1; transform: scale(.96); } 100% { opacity: 1; transform: scale(1); } }
.se-lockin { display: inline-block; animation: seLock .55s cubic-bezier(.2,1.4,.4,1) .9s both; }

/* gate scanline: one sweep over the code-enforced chips */
.se-gatescan { position: relative; overflow: hidden; border-radius: 8px; }
.se-gatescan::after { content: ''; position: absolute; top: 0; bottom: 0; width: 34%; left: -40%;
  background: linear-gradient(90deg, transparent, rgba(124,140,255,.12), transparent);
  pointer-events: none; animation: seScan 1.5s ease-out .3s 2; }
@keyframes seScan { to { left: 110%; } }

@media (prefers-reduced-motion: reduce) {
  .se-card, .se-catch, .se-turn, .se-stat, .se-spechead { animation: none; }
  .se-countup, .se-lockin { animation: none; }
  .se-gatescan::after { display: none; }
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

/* Material Symbols Rounded — the icon set. Use via theme.micon() in custom
   HTML, or `:material/name:` directly in Streamlit component labels. */
.ms {
  font-family: 'Material Symbols Rounded';
  font-weight: normal; font-style: normal;
  font-size: 1.15em; line-height: 1;
  vertical-align: -0.20em;
  letter-spacing: normal; text-transform: none; white-space: nowrap;
  display: inline-block; direction: ltr;
  -webkit-font-smoothing: antialiased;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}
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


def micon(name: str, *, size: str | None = None, color: str | None = None,
          fill: bool = False, weight: int | None = None) -> str:
    """A Material Symbols Rounded glyph for use inside custom HTML.
    `name` is the icon's codepoint name, e.g. 'play_arrow', 'download'."""
    settings = []
    if fill:
        settings.append("'FILL' 1")
    if weight:
        settings.append(f"'wght' {weight}")
    style = ""
    if size:
        style += f"font-size:{size};"
    if color:
        style += f"color:{color};"
    if settings:
        style += "font-variation-settings:" + ",".join(settings) + ";"
    style_attr = f' style="{style}"' if style else ""
    return f'<span class="ms"{style_attr}>{esc(name)}</span>'


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


# ---- chat terminal additions (round-7 + chat pivot) -------------------------
CHAT_CSS = """
<style>
.se-rail { display: flex; flex-direction: column; gap: 10px; }
.se-rail-title { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--dim); }
.se-rail-chips { display: flex; flex-wrap: wrap; gap: 6px; }
@keyframes seRolePulse { 0%,100% { box-shadow: 0 0 0 0 rgba(124,140,255,.0); } 50% { box-shadow: 0 0 12px 2px var(--pulse, rgba(124,140,255,.35)); } }
.se-rail-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .04em;
  border: 1px solid var(--line-strong); border-radius: 999px; padding: 3px 10px;
  color: var(--dim); transition: all .25s ease;
}
.se-rail-chip.active { color: var(--ink); border-color: var(--c, var(--accent)); animation: seRolePulse 1.6s ease infinite; }
.se-rail-chip.done { color: var(--c, var(--add)); border-color: var(--line-strong); }
@keyframes seTick { 0% { transform: scale(1.12); color: #A3B3FF; } 100% { transform: scale(1); } }
.se-odo { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--ink); }
.se-odo b { animation: seTick .16s ease; display: inline-block; }
.se-runbar {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  border: 1px solid var(--line); background: rgba(17,21,31,.75); border-radius: 12px;
  padding: 12px 18px; margin: 6px 0 18px; backdrop-filter: blur(6px);
}
.se-runbar .idn { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); }
.se-runbar .kind { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; border-radius: 999px; padding: 3px 10px; border: 1px solid; }
.se-chatmsg { margin: 0 0 12px; }
.se-chatmsg .who { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 4px; }

/* Grok-style chat: borderless typographic agent blocks in one centered column */
.se-gmsg { margin: 0 0 28px; animation: seUp .35s ease both; }
.se-gmsg .who {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .12em;
  text-transform: uppercase; color: var(--c, var(--accent)); margin-bottom: 7px;
}
.se-gmsg .who .st { color: var(--dim); letter-spacing: .06em; }
.se-gmsg .tmsg { color: #D2D8E2; font-size: 15px; line-height: 1.72; max-width: 70ch; }
@media (prefers-reduced-motion: reduce) { .se-gmsg { animation: none; } }

/* presence strip: one slim row above the feed (chips + execution numbers) */
.se-strip {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 4px 0 16px; border-bottom: 1px solid var(--line); margin: 0 0 26px;
}
.se-strip .exec { margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); }
.se-strip .exec b { color: var(--ink); animation: seTick .16s ease; display: inline-block; }

/* the case brief shown before play — what feature is being red-teamed */
.se-casebrief {
  border: 1px solid var(--line); border-radius: 16px; background: rgba(17,21,31,.6);
  padding: 18px 22px; margin: 8px 0 18px; max-width: 70ch;
}
.se-casebrief .k { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 8px; }
.se-casebrief .t { color: #D2D8E2; font-size: 15px; line-height: 1.7; }
.se-casebrief .s { color: var(--dim); font-size: 13px; line-height: 1.65; margin-top: 8px; }
/* human message: right-aligned rounded pill, Grok-style */
.se-human {
  width: fit-content; max-width: 72%; margin: 0 0 22px auto;
  border: 1px solid #2A3242; background: #1B2130;
  border-radius: 22px; padding: 12px 18px;
  color: var(--ink); font-size: 14.5px; line-height: 1.65;
}

/* bottom input as a rounded pill — flatten Streamlit's nested baseweb
   layers, whose own opaque background and border otherwise paint over the
   pill border (border appears "under" the background) */
[data-testid="stChatInput"] {
  border: 1px solid var(--line-strong); border-radius: 26px;
  background: #131826; overflow: hidden;
}
[data-testid="stChatInput"]:focus-within { border-color: var(--accent); }
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {
  background: transparent !important; border: none !important;
  box-shadow: none !important;
}
[data-testid="stChatInput"] textarea { background: transparent; }
.se-sysmsg { font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin: 10px 0; }

/* phase divider: a real room change, not another dim line */
.se-phasehead {
  display: flex; align-items: center; gap: 12px; margin: 26px 0 14px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .16em;
  text-transform: uppercase; color: #A3B3FF;
}
.se-phasehead::before, .se-phasehead::after { content: ''; flex: 1; border-top: 1px solid var(--line-strong); }
.se-phasehead .cast { color: var(--dim); letter-spacing: .04em; text-transform: none; }

/* router asks become compact prompts, not body text */
.se-router {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--dim);
  border-left: 2px dotted var(--line-strong); padding: 2px 0 2px 12px; margin: 4px 0 10px;
}
.se-router b { color: var(--muted); }

/* replying-to thread line */
.se-reply { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #7C8CFF; margin: 0 0 4px; }

/* evidence-id chips: instant CSS tooltip with the underlying claim/conflict/finding */
.se-ref {
  position: relative; font-family: 'JetBrains Mono', monospace; font-size: .92em;
  color: var(--accent); border-bottom: 1px dotted rgba(124,140,255,.6);
  cursor: help; white-space: nowrap;
}
.se-ref:hover { background: rgba(124,140,255,.12); border-bottom-style: solid; }
.se-ref::after {
  content: attr(data-tip); position: absolute; left: 0; bottom: calc(100% + 8px);
  z-index: 999; width: max-content; max-width: 380px; white-space: normal;
  background: #161B27; border: 1px solid #2A3140; border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0,0,0,.5);
  padding: 10px 13px; font-family: 'Inter', sans-serif; font-size: 12px;
  line-height: 1.6; color: #C9D0DC; letter-spacing: 0; text-transform: none;
  opacity: 0; pointer-events: none; transform: translateY(4px);
  transition: opacity .12s ease, transform .12s ease;
}
.se-ref:hover::after { opacity: 1; transform: none; }

/* visible thinking: live stream + collapsed work notes per message */
.se-think-live { color: #8A94A6; font-style: italic; font-size: 13.5px; }
.se-think { margin-top: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #6B7585; }
.se-think summary { cursor: pointer; color: #8A94A6; list-style: none; outline: none; }
.se-think summary::-webkit-details-marker { display: none; }
.se-think summary::before { content: '▸ '; color: var(--accent); }
.se-think[open] summary::before { content: '▾ '; }
.se-think .tbody { border-left: 1px solid #2A3242; margin: 6px 0 0 3px; padding: 4px 0 4px 12px; line-height: 1.7; }
</style>
"""


def inject_chat() -> None:
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
