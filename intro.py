"""Intro / landing page: the problems this system solves.

Rendered as the default view. Pure presentation — all copy lives here so the
demo code stays clean.
"""

import json
from pathlib import Path

import streamlit as st

import theme


def _teaser_stats() -> tuple | None:
    """Headline numbers from the shipped demo run, so the payoff is legible
    before the viewer clicks. Returns None if the run isn't present."""
    try:
        p = Path(__file__).parent / "data" / "runs" / "demo-andigi.json"
        r = json.loads(p.read_text(encoding="utf-8"))
        s = r["stages"]
        g1, g2 = s["grade_round1"]["overall_score"], s["grade_round2"]["overall_score"]
        arb = s["debate"]["arbiter"]
        return (g1, g2, g2 - g1, len(arb["amendments"]),
                s["gate"]["errors"], len(arb["unresolved_human_decisions"]))
    except Exception:
        return None


PROBLEMS = [
    {
        "id": "01",
        "pain": "Stakeholders contradict each other — and specs silently pick a side.",
        "detail": "The CEO decides one thing, written policy says another, ops does a third. Most specs bury the conflict; the team discovers it in production.",
        "answer": "A truth hierarchy resolves every contradiction by authority and never hides one: each conflict is surfaced, resolved, and flagged for a human ruling.",
        "proof": "Conflict cards · needs-human flags",
    },
    {
        "id": "02",
        "pain": "AI writes confident specs with invented facts.",
        "detail": "Hallucinated SLAs, imaginary regulatory caveats, numbers no one ever said. Unreviewed AI content is a liability, especially in regulated domains.",
        "answer": "Claims without sources do not exist here. Every statement traces to a verbatim quote, a document, code, or a tagged assumption — and an adversarial grader hunts for the ones that don't.",
        "proof": "Click any claim → source quote · P0 grounding blocks",
    },
    {
        "id": "03",
        "pain": "Quality depends on who wrote the doc.",
        "detail": "One PM writes testable acceptance criteria, another writes 'system should handle it appropriately'. Standards live in people's heads.",
        "answer": "A deterministic quality gate enforces standards as code — hedge words, vague quantities, missing scope, untagged prescriptions. Models cannot sweet-talk it; neither can deadlines.",
        "proof": "Inline rule hits · 'Code-enforced' gate",
    },
    {
        "id": "04",
        "pain": "Documentation ships weeks after the feature.",
        "detail": "Docs and specs are treated as downstream cleanup, so they lag, drift, and stop being trusted.",
        "answer": "The pipeline makes documentation a release gate, not an afterthought: nothing advances to sign-off until it passes grading — max three revision rounds, then it blocks loudly.",
        "proof": "Lifecycle stepper · locked gates",
    },
    {
        "id": "05",
        "pain": "The spec says one thing, the code does another.",
        "detail": "Requirements describe the intended system; the repo and database are the actual system. The gap between them is where incidents live.",
        "answer": "Evidence comes from every source — transcripts, documents, code, schemas. Spoken decisions argue by authority; code and data are artifact-state facts no one can out-talk. Gaps become explicit migration requirements.",
        "proof": "Multi-source claims · code/DB locators",
    },
    {
        "id": "06",
        "pain": "Corrections die in chat threads.",
        "detail": "A reviewer fixes the same mistake for the tenth time. The knowledge never compounds; it leaves when people do.",
        "answer": "Every human edit at sign-off is distilled into a persistent rule the system applies on the next run — corrections become institutional memory, automatically enforced.",
        "proof": "'Learned from your last sign-off' banner",
    },
]

PIPELINE = [
    ("Evidence", "transcripts · docs · code · DB"),
    ("Wiki", "source-traced claims"),
    ("Conflicts", "truth hierarchy"),
    ("Gate", "code-enforced, un-gameable"),
    ("Grade", "D1–D5 · P0/P1/P2"),
    ("Debate", "bounded router · full roster"),
    ("Diff", "corrected, dev-ready"),
    ("Sign-off", "human authority"),
]


def render() -> None:
    theme.kicker("Agent-operated product & knowledge team")
    st.markdown("# Knowledge Engine")
    st.markdown(
        '<p style="color:#9C9A92;max-width:680px;font-size:17px">Messy evidence in — a '
        "graded, source-backed, <b>buildable</b> spec out. Agents do the work; a human "
        "signs off.</p>",
        unsafe_allow_html=True,
    )

    pipe = " ".join(
        f'<span class="se-id">{theme.esc(name)}</span>'
        f'<span style="color:#6A6962;font-size:11px"> {theme.esc(sub)}</span>'
        f'{"<span style=\'color:#2E2D27\'> → </span>" if i < len(PIPELINE) - 1 else ""}'
        for i, (name, sub) in enumerate(PIPELINE)
    )
    st.markdown(
        f'<div class="se-card" style="font-family:JetBrains Mono,monospace;font-size:12px;'
        f'line-height:2">{pipe}</div>',
        unsafe_allow_html=True,
    )

    ts = _teaser_stats()
    if ts:
        g1, g2, delta, defects, gate_err, humans = ts
        st.markdown(
            '<div class="se-card" style="display:flex;flex-wrap:wrap;gap:26px;'
            'align-items:baseline;font-family:JetBrains Mono,monospace;margin-top:10px">'
            '<span style="font-size:21px;color:#ECEAE3">'
            f'<span style="color:#6A6962;font-size:12px">readiness </span>{g1} '
            f'<span style="color:#2E2D27">→</span> <b style="color:#8E9A92">{g2}</b> '
            f'<span style="color:#8E9A92;font-size:13px">+{delta}</span></span>'
            f'<span style="color:#9C9A92;font-size:13px"><b style="color:#ECEAE3">{defects}</b> '
            'defects caught — with receipts</span>'
            f'<span style="color:#9C9A92;font-size:13px"><b style="color:#ECEAE3">{gate_err}</b> '
            'code-gate errors flagged</span>'
            f'<span style="color:#9C9A92;font-size:13px"><b style="color:#ECEAE3">{humans}</b> '
            'decisions only a human can make</span>'
            '<span style="color:#6A6962;font-size:11px;margin-left:auto">in the AnDigi case ↓</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    theme.section("the problems", "What this system solves", "6 entries")

    cols = st.columns(2)
    for i, p in enumerate(PROBLEMS):
        with cols[i % 2]:
            theme.card(
                f'<div class="rowtop"><span class="se-id">{theme.esc(p["id"])}</span>'
                f'<span class="se-topic">{theme.esc(p["pain"])}</span></div>'
                f'<div class="se-body" style="margin-top:10px">'
                f'<span style="color:#8E9A92;font-family:JetBrains Mono,monospace;font-size:11px">+ </span>'
                f"{theme.esc(p['answer'])}</div>"
                f'<div class="se-trace">on screen: {theme.esc(p["proof"])}</div>'
            )

    theme.section("for whom", "Built for", "")
    st.markdown(
        '<p class="se-body" style="max-width:760px">Product, documentation, and '
        "knowledge teams shipping in regulated or complex domains — anywhere a "
        "wrong sentence in a spec costs real money, and "
        "“the AI wrote it” is not an acceptable excuse.</p>",
        unsafe_allow_html=True,
    )

    st.write("")
    c1, _ = st.columns([4, 3])
    if c1.button(":material/fact_check: Inspect the red-team report — catches with receipts",
                 type="primary", use_container_width=True):
        st.session_state["view"] = "demo"
        st.session_state["workspace"] = "Overview"
        st.rerun()
    st.markdown(
        '<p class="se-trace" style="margin-top:18px">All demo data is synthetic. '
        "The default view needs no API key; live mode uses your own OpenRouter "
        "key and costs pennies on cheap models.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="se-trace">Built by <a href="https://tiennguyentt.github.io/" '
        'style="color:#D6A03C" target="_blank">Tiên Nguyễn — tiennguyentt.github.io</a> · '
        "Not AI-assisted. Agent-operated.</p>",
        unsafe_allow_html=True,
    )
