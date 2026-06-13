"""Portfolio-matched theme for Streamlit apps.

Single-file, reusable: drop `theme.py` + `.streamlit/config.toml` into any
Streamlit app to get the "Forensic Ledger" design language — warm near-black
ink, signal-gold accent, Schibsted Grotesk (display + body),
JetBrains Mono data, git-diff details. Call `theme.inject()` once at the top,
then build blocks with the helpers below (they return HTML strings; pass
them to `theme.card(...)` / `st.markdown(..., unsafe_allow_html=True)`).
"""

import hashlib as _hashlib
import html as _html
import json as _json

import streamlit as st

PALETTE = {
    "bg": "#0A0B0D",
    "panel": "#0F1113",
    "line": "rgba(236,234,227,.08)",
    "text": "#ECEAE3",
    "dim": "#9C9A92",
    "accent": "#D6A03C",
    "add": "#8E9A92",
    "del": "#C0685C",
    "warn": "#D6A03C",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..600,0..1,-25..0&display=block');

/* ── "Forensic Ledger" ─ instrument-grade, two faces only.
   Words: Schibsted Grotesk (display = heavy + tight, body = regular).
   Data/machine truth: JetBrains Mono. Accent: signal gold = the
   highlighter / "caught it" / human-decision thread. */
:root {
  --bg: #0A0B0D; --surface: #0F1113; --raised: #15171B;
  --ink: #ECEAE3; --muted: #9C9A92; --dim: #6A6962;
  --accent: #D6A03C; --accent-lift: #E6C079;
  --line: rgba(236,234,227,.08); --line-strong: rgba(236,234,227,.16);
  --add: #8E9A92; --del: #C0685C; --warn: #D6A03C;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg); color: var(--ink);
  font-family: 'Schibsted Grotesk', sans-serif; font-size: 15px; line-height: 1.66;
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1120px; padding-top: 3rem; padding-bottom: 6rem; }

/* warm light cast from the top + a fine film grain for paper-like depth */
[data-testid="stAppViewContainer"]::before {
  content: ""; position: fixed; inset: -30% -20% auto -20%; height: 62%; z-index: 0;
  background: radial-gradient(ellipse at 32% 0%, rgba(214,160,60,.08), transparent 62%);
  pointer-events: none;
}
[data-testid="stAppViewContainer"]::after {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: .035;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  mix-blend-mode: overlay;
}
[data-testid="stAppViewContainer"] .main { position: relative; z-index: 1; }

h1, h2, h3 {
  font-family: 'Schibsted Grotesk', sans-serif !important; font-weight: 700 !important;
  letter-spacing: -0.02em;
}

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
.stTextInput input, .stSelectbox div { font-family: 'Schibsted Grotesk', sans-serif; }

/* ── mobile-first: the sidebar is hidden behind a hamburger on phones, so the
   page must stand on its own. Tighten padding, scale type, full-width taps. */
@media (max-width: 640px) {
  .block-container { padding-top: 1.1rem !important; padding-left: .85rem !important; padding-right: .85rem !important; padding-bottom: 3rem !important; }
  .se-hero-head { font-size: 27px; }
  .se-flow-cap { font-size: 23px; }
  .se-stats { gap: 8px; }
  .se-stat { min-width: 0; flex: 1 1 44%; padding: 12px 13px; }
  .se-stat .v { font-size: 23px; }
  .se-card { padding: 15px 14px; }
  .se-catch { padding: 17px 15px; }
  .se-reason { padding: 14px 13px; }
  .se-rstep { font-size: 12px; }
  .se-telemetry { font-size: 10.5px; gap: 7px 10px; padding: 8px 11px; }
  .se-runbar { padding: 9px 12px; gap: 8px; }
  .se-runbar .idn { font-size: 11px; }
  /* full-width, thumb-sized tap targets */
  .stButton button, .stDownloadButton button { width: 100%; min-height: 44px; }
  /* let the workspace tabs wrap instead of overflowing */
  .stRadio [role="radiogroup"] { flex-wrap: wrap; gap: 4px 10px; }
  /* no sideways bleed on a phone (the data-flow pipeline is already vertical) */
  html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
  /* keep wide mono content (telemetry, reasoning) from forcing a sideways scroll */
  .se-telemetry, .se-reason, .se-leadfix { overflow-wrap: anywhere; }
  /* Streamlit has no hamburger — it opens the sidebar via a tiny chevron. Turn
     that control into an obvious gold menu button on mobile so the (optional)
     advanced panel is discoverable. Multiple testids = robust across versions;
     if none match it simply no-ops. */
  [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]{
    background:var(--accent)!important;border-radius:11px!important;padding:6px 7px!important;
    box-shadow:0 4px 14px rgba(0,0,0,.45)!important;display:flex!important;align-items:center!important;}
  [data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg,
  [data-testid="stSidebarCollapsedControl"] path, [data-testid="collapsedControl"] path{
    fill:#0A0B0D!important;color:#0A0B0D!important;width:24px!important;height:24px!important;}
}

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
/* gate-scan sweep removed — no colored animations in the status layer */

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
  font-family: 'Schibsted Grotesk', sans-serif; font-weight: 760;
  font-size: clamp(32px, 4.6vw, 52px); letter-spacing: -0.028em;
  color: var(--ink); line-height: 1.08; margin: 0 0 20px;
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
  font-family: 'Schibsted Grotesk', sans-serif; font-weight: 600; font-size: 21px; color: var(--ink);
}
.se-spechead .sstatus {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin-left: auto;
  letter-spacing: .06em;
}

/* ---- stats ------------------------------------------------------------- */
.se-stats { display: flex; gap: 14px; flex-wrap: wrap; margin: 28px 0 8px; }
.se-stat {
  border: 1px solid var(--line); background: rgba(15,17,19,.7); border-radius: 12px;
  padding: 16px 22px; min-width: 150px;
  transition: border-color .2s ease, transform .2s ease;
}
.se-stat:hover { border-color: var(--line-strong); transform: translateY(-2px); }
.se-stat .v { font-family: 'Schibsted Grotesk', sans-serif; font-weight: 700; font-size: 30px; color: var(--ink); letter-spacing: -0.02em; }
.se-stat .v .from { color: var(--dim); font-size: 16px; font-weight: 500; }
.se-stat .v .delta { color: var(--accent); }
.se-stat .l { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin-top: 6px; }

/* ---- open cards (default surface) -------------------------------------- */
.se-card {
  border: 1px solid var(--line); background: rgba(15,17,19,.55);
  border-radius: 12px; padding: 20px 22px; margin: 0 0 14px;
  transition: border-color .2s ease;
}
.se-card:hover { border-color: var(--line-strong); }
.se-card .rowtop { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.se-id { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent); letter-spacing: .04em; }
.se-topic { font-family: 'Schibsted Grotesk', sans-serif; font-weight: 600; font-size: 15.5px; color: var(--ink); }
.se-body { color: #CDCAC0; font-size: 14.5px; line-height: 1.7; margin-top: 8px; }
.se-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .06em;
  border: 1px solid var(--line-strong); border-radius: 999px; padding: 3px 11px;
  color: var(--muted); margin-left: auto; white-space: nowrap;
}
.se-quote {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #8E8C82;
  border-left: 2px solid var(--line-strong); padding: 6px 0 6px 14px; margin: 12px 0 0;
  line-height: 1.7;
}
.se-ac { color: #CDCAC0; font-size: 14px; margin: 8px 0 0 2px; line-height: 1.65; }
.se-ac::before { content: '▸ '; color: var(--accent); }
.se-trace { font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin-top: 12px; line-height: 1.7; }
.se-issue { color: #CDCAC0; font-size: 13.5px; margin-top: 6px; }
.se-issue::before { content: '! '; font-family: 'JetBrains Mono', monospace; color: var(--warn); font-weight: 600; }
.se-bar { height: 6px; border-radius: 3px; background: var(--line); margin-top: 8px; overflow: hidden; }
.se-bar > div { height: 6px; border-radius: 3px; background: var(--accent); }
.se-verdict-ship { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--add); }
.se-verdict-revise { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--warn); }
.se-block {
  border-left: 3px solid var(--del); background: rgba(192,104,92,.06);
  border-radius: 0 10px 10px 0; padding: 16px 18px; margin-top: 16px;
  color: var(--ink); font-size: 14px; line-height: 1.7;
}
.se-conflict-win { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--add); margin-top: 10px; }
.se-flag {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--warn);
  border: 1px dashed rgba(214,160,60,.5); border-radius: 8px;
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
.se-catch:hover { border-color: #3A382F; transform: translateY(-2px); }
.se-catch .chead { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.se-catch .cnum { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--del); font-weight: 600; letter-spacing: .08em; }
.se-catch .ctitle { font-family: 'Schibsted Grotesk', sans-serif; font-weight: 600; font-size: 16.5px; color: var(--ink); line-height: 1.5; }
.se-vs { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--dim); margin: 16px 0 2px; letter-spacing: .1em; }
.se-diff-del {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #B57E78;
  background: rgba(192,104,92,.08); border-left: 2px solid var(--del);
  padding: 10px 14px; margin-top: 10px; white-space: pre-wrap; line-height: 1.7; border-radius: 0 8px 8px 0;
}
.se-diff-del::before { content: '- '; color: var(--del); font-weight: 600; }
.se-diff-add {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #8E9A90;
  background: rgba(142,154,146,.08); border-left: 2px solid var(--add);
  padding: 10px 14px; margin-top: 4px; white-space: pre-wrap; line-height: 1.7; border-radius: 0 8px 8px 0;
}
.se-diff-add::before { content: '+ '; color: var(--add); font-weight: 600; }
.se-summon {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--del);
  border: 1px solid rgba(192,104,92,.4); border-radius: 999px;
  padding: 5px 14px; display: inline-block; margin-top: 14px;
}
.se-gatehit { font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #CDCAC0; margin-top: 9px; line-height: 1.65; }
.se-gatehit .rid { color: var(--del); font-weight: 600; }
.se-gatehit .warn { color: var(--warn); font-weight: 600; }
.se-stepper { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 12px 0 20px; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .06em; }
.se-step { border: 1px solid var(--line-strong); border-radius: 999px; padding: 5px 14px; color: var(--dim); transition: all .2s ease; }
.se-step.done { color: var(--add); border-color: rgba(142,154,146,.4); }
.se-step.active { color: var(--accent); border-color: var(--accent); }
.se-step-arrow { color: var(--line-strong); }
.se-notes {
  border-top: 1px dashed var(--line-strong); margin-top: 14px; padding-top: 12px;
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #8E8C82; line-height: 1.75;
}
.se-notes b { color: var(--muted); font-weight: 600; }
.se-noobj { font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--dim); margin: 6px 0; }
.se-noobj::before { content: '○ '; color: var(--add); }

/* ---- debate bubbles ----------------------------------------------------- */
.se-turn {
  border: 1px solid var(--line); border-left-width: 3px; background: rgba(15,17,19,.55);
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
.se-turn .tmsg { color: #CDCAC0; font-size: 14.5px; line-height: 1.7; margin-top: 10px; }

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

/* ── animated data-flow pipeline ────────────────────────────────────
   A vertical timeline (not boxes): gold "data" continuously flows DOWN the
   path; node markers light the code-gate (gold) and the signed spec (green). */
.se-pipe { position: relative; padding-left: 30px; margin: 14px 0 6px; }
.se-pipe::before { content: ''; position: absolute; left: 9px; top: 9px; bottom: 11px; width: 2px; background: var(--line-strong); border-radius: 2px; }
.se-pipe::after {
  content: ''; position: absolute; left: 8px; top: 9px; bottom: 11px; width: 4px; border-radius: 4px;
  background: linear-gradient(180deg, transparent 0%, var(--accent) 48%, transparent 100%);
  background-size: 100% 68px; background-repeat: no-repeat; opacity: .95;
  animation: sePipeFlow 2.6s linear infinite;
}
@keyframes sePipeFlow { from { background-position: 0 -68px; } to { background-position: 0 calc(100% + 68px); } }
.se-pnode { position: relative; padding: 9px 0 20px; animation: seUp .5s ease both; }
.se-pnode .se-pmark { position: absolute; left: -25px; top: 13px; width: 12px; height: 12px; border-radius: 50%; background: var(--bg); border: 2px solid var(--dim); }
.se-pnode.gate .se-pmark { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(214,160,60,.18); }
.se-pnode.out .se-pmark { border-color: var(--add); }
.se-pnode .pk { font-family: 'JetBrains Mono', monospace; font-size: 9.5px; letter-spacing: .16em; text-transform: uppercase; color: var(--dim); }
.se-pnode .pt { font-family: 'Schibsted Grotesk', sans-serif; font-weight: 700; font-size: 19px; letter-spacing: -.02em; color: var(--ink); margin-top: 3px; line-height: 1.1; }
.se-pnode .ps { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--muted); margin-top: 5px; }
.se-pnode.gate .pt, .se-pnode.gate .pk { color: var(--accent); }
.se-pnode.out .pt { color: var(--add); }
@media (prefers-reduced-motion: reduce) { .se-pipe::after { animation: none; } }
.se-flow-cap { font-family: 'Schibsted Grotesk', sans-serif; font-weight: 740; font-size: clamp(24px, 3.4vw, 38px); letter-spacing: -0.028em; color: var(--ink); line-height: 1.1; margin: 6px 0 10px; }

/* ── inference-trace telemetry strip: real run, real numbers ──────── */
.se-telemetry {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; letter-spacing: .02em;
  color: var(--muted); border: 1px solid var(--line);
  background: rgba(15,17,19,.6); border-radius: 10px; padding: 9px 15px; margin: 2px 0 16px;
}
.se-telemetry .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: seBlink 1.4s steps(1) infinite; }
.se-telemetry .lbl { color: var(--dim); text-transform: uppercase; letter-spacing: .15em; font-size: 9.5px; }
.se-telemetry b { color: var(--ink); font-weight: 600; }
.se-telemetry .gold { color: var(--accent); }
.se-telemetry .sep { color: var(--line-strong); }

/* ── lead artifact: one defect, struck out and corrected, in 3s ───── */
.se-leadfix {
  border: 1px solid var(--line-strong); border-left: 2px solid var(--accent);
  background: linear-gradient(180deg, var(--raised), var(--surface));
  border-radius: 0 12px 12px 12px; padding: 18px 20px; margin: 14px 0 18px;
}
.se-leadfix .lf-k { font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: .16em; text-transform: uppercase; color: var(--dim); margin-bottom: 13px; }
.se-leadfix .lf-del { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--del); text-decoration: line-through; text-decoration-color: rgba(192,104,92,.55); opacity: .82; line-height: 1.6; }
.se-leadfix .lf-arrow { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--dim); margin: 9px 0 7px; }
.se-leadfix .lf-add { font-family: 'JetBrains Mono', monospace; font-size: 13.5px; color: var(--accent); line-height: 1.6; font-weight: 500; }
.se-leadfix .lf-badge { margin-top: 13px; padding-top: 11px; border-top: 1px solid var(--line); font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--muted); }

/* ── live reasoning trace: the model's actual logic, replayed step by step ── */
.se-reason {
  border: 1px solid var(--line-strong); border-left: 2px solid var(--accent);
  background: linear-gradient(180deg, var(--raised), var(--surface));
  border-radius: 0 12px 12px 12px; padding: 16px 18px 14px; margin: 14px 0 16px;
  font-family: 'JetBrains Mono', monospace;
}
.se-rhead { font-size: 10px; letter-spacing: .15em; text-transform: uppercase; color: var(--dim); margin-bottom: 13px; display: flex; align-items: center; gap: 8px; }
.se-rhead .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: seBlink 1.4s steps(1) infinite; }
.se-rstep { display: flex; gap: 10px; align-items: flex-start; font-size: 12.5px; color: var(--muted); line-height: 1.55; padding: 5px 0; opacity: 0; animation: seReasonIn .45s cubic-bezier(.16,1,.3,1) both; }
.se-rstep .rmark { color: var(--dim); flex: 0 0 auto; margin-top: 1px; }
.se-rstep .rtxt b { color: var(--ink); font-weight: 600; }
.se-rstep .rtxt .id { color: var(--accent); }
.se-rstep.warn .rmark { color: var(--del); }
.se-rstep.warn .rtxt { color: #D8B0AB; }
.se-rstep.fix { color: var(--ink); }
.se-rstep.fix .rmark { color: var(--accent); }
@keyframes seReasonIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.se-rcursor { width: 9px; height: 15px; background: var(--accent); margin-top: 4px; opacity: 0; animation: seReasonIn .01s linear both, seBlink 1.1s steps(1) infinite; }
@media (prefers-reduced-motion: reduce) { .se-rstep, .se-rcursor { animation: none; opacity: 1; } }

/* ── try/audit callout: make verification one glance away ─────────── */
.se-try {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  border: 1px solid rgba(214,160,60,.4); border-radius: 10px;
  background: rgba(214,160,60,.05); padding: 11px 15px; margin: 4px 0 20px;
  font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted);
}
.se-try .gold { color: var(--accent); font-weight: 600; }
@media (prefers-reduced-motion: reduce) { .se-fnode, .se-flink::after, .se-fnode.gate::after { animation: none; } }
</style>
"""

ROLE_COLORS = {
    "po": PALETTE["accent"],   # gold
    "eng": "#7E9CC2",          # cool slate-blue, distinct from the gold accent
    "qa": PALETTE["add"],      # green
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


def reasoning_trace(steps: list[dict], model: str = "") -> str:
    """Replay the run's actual logic as an animated, step-by-step trace —
    evidence → grounding → contradiction → gate → debate → resolution → fix.
    Each step's `t` is pre-built HTML; `k` selects the marker/styling."""
    icon = {"scan": "search", "ground": "link", "conflict": "warning",
            "gate": "gavel", "debate": "forum", "resolve": "balance", "fix": "check"}
    rows = []
    for i, stp in enumerate(steps):
        k = stp["k"]
        cls = "se-rstep" + (" warn" if k == "conflict" else "") + (" fix" if k == "fix" else "")
        rows.append(
            f'<div class="{cls}" style="animation-delay:{i * 0.5:.2f}s">'
            f'<span class="rmark">{micon(icon.get(k, "chevron_right"), size="14px")}</span>'
            f'<span class="rtxt">{stp["t"]}</span></div>'
        )
    cursor_delay = len(steps) * 0.5
    head = (f'<div class="se-rhead"><span class="dot"></span>'
            f'live reasoning · replayed from the {esc(model)} run</div>')
    return (f'<div class="se-reason">{head}{"".join(rows)}'
            f'<div class="se-rcursor" style="animation-delay:{cursor_delay:.2f}s,{cursor_delay:.2f}s"></div></div>')


def telemetry(meta: dict) -> str:
    """Inference-trace strip. Shows REAL run telemetry (model, exact tokens,
    duration, content-hash trace id) when the run came from a live model;
    otherwise labels itself honestly as a scripted replay."""
    kind = meta.get("kind", "")
    model = meta.get("model", "")
    u = meta.get("usage", {}) or {}
    tin, tout = u.get("input_tokens", 0), u.get("output_tokens", 0)
    dur = meta.get("duration_seconds", 0)
    real = kind in ("live", "real-inference") and (tin + tout) > 0
    if real:
        tid = _hashlib.sha1(_json.dumps(meta, sort_keys=True).encode()).hexdigest()[:7]
        # No "real inference" claim — words don't prove anything. Just the
        # checkable facts (model, exact tokens, duration, content-hash trace);
        # the page tells the viewer to verify by downloading the raw run.
        return (
            '<div class="se-telemetry"><span class="lbl">recorded run</span>'
            f'<b class="gold">{esc(model)}</b><span class="sep">·</span>'
            f'<span><b>{tin:,}</b> in / <b>{tout:,}</b> out tokens</span><span class="sep">·</span>'
            f'<span><b>{dur}</b>s</span><span class="sep">·</span>'
            f'<span>trace <b>{tid}</b></span><span class="sep">·</span>'
            f'<span class="gold">{micon("download", size="12px")} download &amp; verify</span></div>'
        )
    return (
        '<div class="se-telemetry"><span class="lbl">replay</span>'
        '<span>scripted · deterministic — every number is reproducible</span>'
        '<span class="sep">·</span>'
        '<span class="gold">run live on your key to see model inference →</span></div>'
    )


def flow_diagram(g1: int, g2: int, defects: int) -> str:
    """The pipeline as an animated vertical data-flow timeline — gold data flows
    down the path; the code gate and the signed spec light up. Not boxes."""
    nodes = [
        ("", "evidence", "Messy in", "transcripts · policy · code · DB"),
        ("", "trace", "Source-traced", "every claim → a receipt"),
        ("gate", "code gate", "Un-gameable", "models can't override"),
        ("", "11 agents", "Red-team debate", "adversarial · graded"),
        ("out", "verified", "Signed spec", f"{g1} → {g2} · {defects} caught"),
    ]
    rows = []
    for i, (kind, fk, ft, fs) in enumerate(nodes):
        cls = ("se-pnode " + kind).strip()
        rows.append(
            f'<div class="{cls}" style="animation-delay:{i * 0.12:.2f}s">'
            f'<span class="se-pmark"></span>'
            f'<div class="pk">{esc(fk)}</div>'
            f'<div class="pt">{esc(ft)}</div>'
            f'<div class="ps">{esc(fs)}</div></div>'
        )
    return f'<div class="se-pipe">{"".join(rows)}</div>'


# ---- chat terminal additions (round-7 + chat pivot) -------------------------
CHAT_CSS = """
<style>
.se-rail { display: flex; flex-direction: column; gap: 10px; }
.se-rail-title { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--dim); }
.se-rail-chips { display: flex; flex-wrap: wrap; gap: 6px; }
@keyframes seRolePulse { 0%,100% { box-shadow: 0 0 0 0 rgba(214,160,60,.0); } 50% { box-shadow: 0 0 12px 2px var(--pulse, rgba(214,160,60,.35)); } }
.se-rail-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .04em;
  border: 1px solid var(--line-strong); border-radius: 999px; padding: 3px 10px;
  color: var(--dim); transition: all .25s ease;
}
.se-rail-chip.active { color: var(--ink); border-color: var(--c, var(--accent)); animation: seRolePulse 1.6s ease infinite; }
.se-rail-chip.done { color: var(--c, var(--add)); border-color: var(--line-strong); }
@keyframes seTick { 0% { transform: scale(1.12); color: #E6C079; } 100% { transform: scale(1); } }
.se-odo { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--ink); }
.se-odo b { animation: seTick .16s ease; display: inline-block; }
.se-runbar {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  border: 1px solid var(--line); background: rgba(15,17,19,.75); border-radius: 12px;
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
.se-gmsg .tmsg { color: #D8D5CB; font-size: 15px; line-height: 1.72; max-width: 70ch; }
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
  border: 1px solid var(--line); border-radius: 16px; background: rgba(15,17,19,.6);
  padding: 18px 22px; margin: 8px 0 18px; max-width: 70ch;
}
.se-casebrief .k { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 8px; }
.se-casebrief .t { color: #D8D5CB; font-size: 15px; line-height: 1.7; }
.se-casebrief .s { color: var(--dim); font-size: 13px; line-height: 1.65; margin-top: 8px; }
/* human message: right-aligned rounded pill, Grok-style */
.se-human {
  width: fit-content; max-width: 72%; margin: 0 0 22px auto;
  border: 1px solid var(--line-strong); background: #1A1A17;
  border-radius: 22px; padding: 12px 18px;
  color: var(--ink); font-size: 14.5px; line-height: 1.65;
}

/* bottom input as a rounded pill — flatten Streamlit's nested baseweb
   layers, whose own opaque background and border otherwise paint over the
   pill border (border appears "under" the background) */
[data-testid="stChatInput"] {
  border: 1px solid var(--line-strong); border-radius: 26px;
  background: #141512; overflow: hidden;
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
  text-transform: uppercase; color: #E6C079;
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
.se-reply { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #D6A03C; margin: 0 0 4px; }

/* evidence-id chips: instant CSS tooltip with the underlying claim/conflict/finding */
.se-ref {
  position: relative; font-family: 'JetBrains Mono', monospace; font-size: .92em;
  color: var(--accent); border-bottom: 1px dotted rgba(214,160,60,.6);
  cursor: help; white-space: nowrap;
}
.se-ref:hover { background: rgba(214,160,60,.12); border-bottom-style: solid; }
.se-ref::after {
  content: attr(data-tip); position: absolute; left: 0; bottom: calc(100% + 8px);
  z-index: 999; width: max-content; max-width: 380px; white-space: normal;
  background: var(--raised); border: 1px solid var(--line-strong); border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0,0,0,.5);
  padding: 10px 13px; font-family: 'Schibsted Grotesk', sans-serif; font-size: 12px;
  line-height: 1.6; color: #D2CFC5; letter-spacing: 0; text-transform: none;
  opacity: 0; pointer-events: none; transform: translateY(4px);
  transition: opacity .12s ease, transform .12s ease;
}
.se-ref:hover::after { opacity: 1; transform: none; }

/* visible thinking: live stream + collapsed work notes per message */
.se-think-live { color: #8E8C82; font-style: italic; font-size: 13.5px; }
.se-think { margin-top: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #6A6962; }
.se-think summary { cursor: pointer; color: #8E8C82; list-style: none; outline: none; }
.se-think summary::-webkit-details-marker { display: none; }
.se-think summary::before { content: '▸ '; color: var(--accent); }
.se-think[open] summary::before { content: '▾ '; }
.se-think .tbody { border-left: 1px solid var(--line-strong); margin: 6px 0 0 3px; padding: 4px 0 4px 12px; line-height: 1.7; }
</style>
"""


def inject_chat() -> None:
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
