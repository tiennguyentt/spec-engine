"""Spec Engine — workflow 01 of an agent-operated product team.

Transcript -> source-traced wiki -> truth-hierarchy conflict check ->
spec draft -> automated grading -> autonomous role debate -> human sign-off.

Replay mode needs no API key. Live mode runs the real pipeline through any
OpenAI-compatible endpoint (OpenRouter by default) with a key you provide.
"""

import json
import time

import streamlit as st

import theme
from engine.debate import ROLES
from engine.llm import DEFAULT_BASE_URL, SUGGESTED_MODELS, LLM
from engine.pipeline import (
    STAGE_TITLES,
    list_runs,
    load_run,
    load_transcripts,
    run_pipeline,
    save_run,
)

st.set_page_config(page_title="Spec Engine", page_icon="📐", layout="wide")
theme.inject()

theme.kicker("Agent-operated product team · workflow 01 / spec")
st.markdown("# Not AI-assisted. Agent-operated.")
st.markdown(
    '<p style="color:#9AA4B2;max-width:760px">Raw transcripts in — a graded, '
    "source-backed, debate-hardened spec out. Role agents run the work "
    "autonomously and argue with each other; a human reads the diff and signs "
    "off.</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Mode")
    mode = st.radio(
        "How do you want to see the pipeline?",
        ["Replay a recorded run", "Run live"],
        label_visibility="collapsed",
    )

    api_key = ""
    if mode == "Run live":
        st.divider()
        st.header("Model")
        base_url = st.text_input("API base URL (OpenAI-compatible)", value=DEFAULT_BASE_URL)
        api_key = st.text_input("API key", type="password", help="Never stored; used for this run only.")
        model = st.selectbox("Model", SUGGESTED_MODELS, accept_new_options=True)
        st.caption("Defaults target OpenRouter so cheap models work out of the box.")

    st.divider()
    st.header("About")
    st.markdown(
        "A public, fully synthetic rebuild of the PM intelligence system I "
        "operate at work. Fictional project: **FlowBook**, a salon booking "
        "app, with two contradictions planted in the transcripts — watch "
        "stage 2 catch them and stage 5 argue about the rest."
    )

# ---------------------------------------------------------------- inputs
transcripts = load_transcripts()

with st.expander("input transcripts · synthetic"):
    tabs = st.tabs(list(transcripts))
    for tab, (name, text) in zip(tabs, transcripts.items()):
        with tab:
            st.markdown(text)

esc = theme.esc


# ---------------------------------------------------------------- renderers
def render_wiki(wiki: dict) -> None:
    theme.section("01", "Source-traced wiki", f"{len(wiki['claims'])} claims")
    st.markdown(f'<p class="se-body">{esc(wiki["project_summary"])}</p>', unsafe_allow_html=True)
    for claim in wiki["claims"]:
        sources = "".join(
            f'<div class="se-quote">{esc(s["speaker"])} · {esc(s["transcript"])} — '
            f"“{esc(s['quote'])}”</div>"
            for s in claim["sources"]
        )
        theme.card(
            f'<div class="rowtop"><span class="se-id">{esc(claim["id"])}</span>'
            f'<span class="se-topic">{esc(claim["topic"])}</span>'
            f'<span class="se-chip">{esc(claim["authority"])}</span></div>'
            f'<div class="se-body">{esc(claim["claim"])}</div>{sources}'
        )


def render_conflicts(report: dict) -> None:
    theme.section("02", "Truth-hierarchy conflict check", f"{len(report['conflicts'])} conflicts")
    if not report["conflicts"]:
        st.success("No conflicts found.")
    for c in report["conflicts"]:
        flag = (
            '<div class="se-flag">⚑ needs human confirmation</div>'
            if c["needs_human_confirmation"] else ""
        )
        theme.card(
            f'<div class="rowtop"><span class="se-id">{esc(c["id"])}</span>'
            f'<span class="se-topic" style="color:#F85149">claims {esc(" × ".join(c["claim_ids"]))}</span></div>'
            f'<div class="se-body">{esc(c["description"])}</div>'
            f'<div class="se-conflict-win">wins → {esc(c["winning_claim_id"])} · {esc(c["winning_authority"])}</div>'
            f'<div class="se-body">{esc(c["resolution"])}</div>{flag}'
        )
    if report.get("notes"):
        st.markdown(f'<p class="se-trace">checked, not in conflict: {esc(report["notes"])}</p>', unsafe_allow_html=True)


def render_spec(spec: dict) -> None:
    theme.section("03", spec["feature_name"], f"{len(spec['requirements'])} requirements")
    st.markdown(f'<p class="se-body">{esc(spec["summary"])}</p>', unsafe_allow_html=True)
    for req in spec["requirements"]:
        acs = "".join(f'<div class="se-ac">{esc(ac)}</div>' for ac in req["acceptance_criteria"])
        theme.card(
            f'<div class="rowtop"><span class="se-id">{esc(req["id"])}</span>'
            f'<span class="se-topic">{esc(req["title"])}</span></div>'
            f'<div class="se-body">{esc(req["statement"])}</div>{acs}'
            f'<div class="se-trace">traces → {esc(", ".join(req["source_claim_ids"]))}</div>'
        )
    if spec.get("out_of_scope"):
        items = "".join(f'<div class="se-ac">{esc(i)}</div>' for i in spec["out_of_scope"])
        theme.card(f'<div class="rowtop"><span class="se-topic">Out of scope</span></div>{items}')


def render_grades(report: dict) -> None:
    theme.section("04", "Automated spec grading", f"score {report['overall_score']}/100")
    for g in report["grades"]:
        verdict_cls = "se-verdict-ship" if g["verdict"].lower() == "ship" else "se-verdict-revise"
        dims = "".join(
            f'<div style="flex:1"><div class="se-trace">{label}: {g[key]}/5</div>{theme.bar(g[key])}</div>'
            for label, key in [("clarity", "clarity"), ("sources", "source_coverage"), ("testability", "testability")]
        )
        issues = "".join(f'<div class="se-issue">{esc(i)}</div>' for i in g["issues"])
        theme.card(
            f'<div class="rowtop"><span class="se-id">{esc(g["requirement_id"])}</span>'
            f'<span class="{verdict_cls}" style="margin-left:auto">● {esc(g["verdict"])}</span></div>'
            f'<div style="display:flex;gap:16px;margin-top:8px">{dims}</div>{issues}'
        )
    if report["blocking_issues"]:
        blocks = "".join(f"<div>− {esc(b)}</div>" for b in report["blocking_issues"])
        st.markdown(f'<div class="se-block"><b>blocking before handoff</b>{blocks}</div>', unsafe_allow_html=True)


def render_debate(debate: dict) -> None:
    n_amend = sum(1 for r in debate["outcome"]["rulings"] if r["decision"] == "amend")
    theme.section("05", "Autonomous role debate", f"{len(debate['turns'])} turns · {n_amend} amendments")
    legend = " ".join(
        f'<span class="se-chip" style="border-color:{theme.ROLE_COLORS[k]};color:{theme.ROLE_COLORS[k]}">{esc(v["label"])}</span>'
        for k, v in ROLES.items()
    )
    st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:12px">{legend}</div>', unsafe_allow_html=True)
    for t in debate["turns"]:
        st.markdown(
            theme.bubble(t["role"], ROLES[t["role"]]["label"], t["stance"], t["message"], t["refs"], t["round"]),
            unsafe_allow_html=True,
        )
    theme.section("", "Arbiter rulings", "")
    for r in debate["outcome"]["rulings"]:
        color = {"accept": "#3FB950", "amend": "#F2A65A", "reject": "#F85149"}[r["decision"]]
        amendment = f'<div class="se-quote">{esc(r["amendment"])}</div>' if r["amendment"] else ""
        theme.card(
            f'<div class="rowtop"><span class="se-id">{esc(r["requirement_id"])}</span>'
            f'<span class="se-chip" style="border-color:{color};color:{color}">{esc(r["decision"])}</span></div>'
            f'<div class="se-body">{esc(r["rationale"])}</div>{amendment}'
        )
    st.markdown(f'<p class="se-body" style="margin-top:8px">{esc(debate["outcome"]["summary"])}</p>', unsafe_allow_html=True)


def render_signoff(run: dict) -> None:
    theme.section("06", "Human sign-off", "not automated, on purpose")
    st.markdown(
        '<p class="se-body">The agents compiled, checked, drafted, graded and '
        "debated. The last stage stays human: read the diff, rule on the open "
        "flags, sign off.</p>",
        unsafe_allow_html=True,
    )
    needs_human = [c["id"] for c in run["stages"]["conflicts"]["conflicts"] if c["needs_human_confirmation"]]
    if needs_human:
        st.markdown(
            f'<div class="se-flag">⚑ open items requiring a human call: {esc(", ".join(needs_human))}</div>',
            unsafe_allow_html=True,
        )
    st.write("")
    if st.button("✍ Sign off this spec", type="primary"):
        st.success("Signed off. Agents do the work. Humans stay accountable.")


def render_run(run: dict) -> None:
    meta = run["meta"]
    cols = st.columns(4)
    cols[0].metric("Run type", meta["kind"])
    cols[1].metric("Model", meta["model"].split("/")[-1][:22])
    cols[2].metric("Tokens", f"{meta['usage']['input_tokens'] + meta['usage']['output_tokens']:,}")
    cols[3].metric("Duration", f"{meta['duration_seconds']}s")
    if meta.get("note"):
        st.markdown(f'<p class="se-trace">{esc(meta["note"])}</p>', unsafe_allow_html=True)

    labels = list(STAGE_TITLES.values()) + ["6 · Sign-off"]
    stage_tabs = st.tabs(labels)
    with stage_tabs[0]:
        render_wiki(run["stages"]["wiki"])
    with stage_tabs[1]:
        render_conflicts(run["stages"]["conflicts"])
    with stage_tabs[2]:
        render_spec(run["stages"]["spec"])
    with stage_tabs[3]:
        render_grades(run["stages"]["grade"])
    with stage_tabs[4]:
        if run["stages"].get("debate"):
            render_debate(run["stages"]["debate"])
        else:
            st.info("This run predates the debate stage — run live to generate one.")
    with stage_tabs[5]:
        render_signoff(run)


# ---------------------------------------------------------------- modes
if mode == "Replay a recorded run":
    runs = list_runs()
    if not runs:
        st.error("No recorded runs found in data/runs/.")
        st.stop()
    chosen = st.selectbox("Recorded run", runs, format_func=lambda p: p.stem)
    render_run(load_run(chosen))

else:
    theme.section("live", "Run the pipeline", "agents run autonomously, debate included")
    if st.button("▶ Run pipeline", type="primary", disabled=not api_key):
        llm = LLM(api_key=api_key, model=model, base_url=base_url)
        status_boxes = {}
        progress_area = st.container()
        debate_area = st.container()

        def on_progress(stage: str, state: str) -> None:
            title = STAGE_TITLES[stage]
            if state == "start":
                status_boxes[stage] = progress_area.status(title, state="running")
            else:
                status_boxes[stage].update(label=f"{title} — done", state="complete")

        def on_turn(turn: dict) -> None:
            debate_area.markdown(
                theme.bubble(
                    turn["role"], ROLES[turn["role"]]["label"], turn["stance"],
                    turn["message"], turn["refs"], turn["round"],
                ),
                unsafe_allow_html=True,
            )

        try:
            run = run_pipeline(llm, transcripts, on_progress, on_turn)
        except Exception as err:  # surface provider errors readably
            st.error(f"Pipeline failed: {err}")
            st.stop()

        name = f"live-{time.strftime('%Y%m%d-%H%M%S')}"
        save_run(run, name)
        st.session_state["last_live_run"] = run
        st.success(f"Run complete — saved as {name}.json")

    if "last_live_run" in st.session_state:
        run = st.session_state["last_live_run"]
        render_run(run)
        st.download_button(
            "⬇ Download run JSON",
            data=json.dumps(run, indent=2, ensure_ascii=False),
            file_name="spec-engine-run.json",
            mime="application/json",
        )
    elif not api_key:
        st.info("Enter an API key in the sidebar to enable the run button. OpenRouter keys start with `sk-or-`.")
