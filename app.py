"""Spec Engine — agent-operated PM pipeline demo.

Transcript -> source-traced wiki -> truth-hierarchy conflict check ->
spec draft -> automated grading -> human sign-off.

Replay mode needs no API key. Live mode runs the real pipeline through any
OpenAI-compatible endpoint (OpenRouter by default) with a key you provide.
"""

import time

import streamlit as st

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

st.title("📐 Spec Engine")
st.caption(
    "Not AI-assisted. Agent-operated. — raw transcripts in, a graded, "
    "source-backed spec out. A human reads the diff and signs off."
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Mode")
    mode = st.radio(
        "How do you want to see the pipeline?",
        ["Replay a recorded run", "Run live"],
        label_visibility="collapsed",
    )

    if mode == "Run live":
        st.divider()
        st.subheader("Model")
        base_url = st.text_input("API base URL (OpenAI-compatible)", value=DEFAULT_BASE_URL)
        api_key = st.text_input("API key", type="password", help="Never stored; used for this run only.")
        model = st.selectbox("Model", SUGGESTED_MODELS, accept_new_options=True)
        st.caption("Defaults target OpenRouter, so cheap models work out of the box. Any OpenAI-compatible endpoint and model id is accepted.")

    st.divider()
    st.subheader("About")
    st.markdown(
        "This is a public, fully synthetic rebuild of the PM intelligence "
        "system I operate at work. The fictional project is **FlowBook**, "
        "a salon booking app. Two intentional contradictions are planted "
        "in the transcripts — watch stage 2 catch them."
    )

# ---------------------------------------------------------------- inputs
transcripts = load_transcripts()

with st.expander("📄 Input transcripts (synthetic)"):
    tabs = st.tabs(list(transcripts))
    for tab, (name, text) in zip(tabs, transcripts.items()):
        with tab:
            st.markdown(text)


# ---------------------------------------------------------------- helpers
def render_wiki(wiki: dict) -> None:
    st.markdown(f"**Project summary:** {wiki['project_summary']}")
    for claim in wiki["claims"]:
        with st.container(border=True):
            top = st.columns([1, 6, 2])
            top[0].markdown(f"`{claim['id']}`")
            top[1].markdown(f"**{claim['topic']}** — {claim['claim']}")
            top[2].markdown(f"🏛 _{claim['authority']}_")
            for src in claim["sources"]:
                st.caption(f"› {src['speaker']} ({src['transcript']}): “{src['quote']}”")


def render_conflicts(report: dict) -> None:
    if not report["conflicts"]:
        st.success("No conflicts found.")
    for c in report["conflicts"]:
        with st.container(border=True):
            st.markdown(f"🔴 **{c['id']}** · claims {', '.join(c['claim_ids'])}")
            st.markdown(c["description"])
            st.markdown(
                f"✅ Wins: `{c['winning_claim_id']}` under **{c['winning_authority']}**"
            )
            st.markdown(f"**Resolution:** {c['resolution']}")
            if c["needs_human_confirmation"]:
                st.warning("Flagged for human confirmation — the hierarchy resolves it, a human still decides.")
    if report.get("notes"):
        st.caption(f"Checked, not in conflict: {report['notes']}")


def render_spec(spec: dict) -> None:
    st.markdown(f"### {spec['feature_name']}")
    st.markdown(spec["summary"])
    for req in spec["requirements"]:
        with st.container(border=True):
            st.markdown(f"**{req['id']} · {req['title']}**")
            st.markdown(req["statement"])
            for ac in req["acceptance_criteria"]:
                st.markdown(f"- {ac}")
            st.caption(f"Traces to wiki claims: {', '.join(req['source_claim_ids'])}")
    if spec.get("out_of_scope"):
        st.markdown("**Out of scope:**")
        for item in spec["out_of_scope"]:
            st.markdown(f"- {item}")


def render_grades(report: dict) -> None:
    st.metric("Overall spec score", f"{report['overall_score']} / 100")
    for g in report["grades"]:
        with st.container(border=True):
            head = st.columns([2, 2, 2, 2, 2])
            head[0].markdown(f"**{g['requirement_id']}**")
            head[1].metric("Clarity", f"{g['clarity']}/5")
            head[2].metric("Sources", f"{g['source_coverage']}/5")
            head[3].metric("Testability", f"{g['testability']}/5")
            verdict = g["verdict"].lower()
            head[4].markdown("✅ **ship**" if verdict == "ship" else "🟠 **revise**")
            for issue in g["issues"]:
                st.markdown(f"- ⚠️ {issue}")
    if report["blocking_issues"]:
        st.error("**Blocking before handoff:**\n\n" + "\n".join(f"- {b}" for b in report["blocking_issues"]))


def render_run(run: dict) -> None:
    meta = run["meta"]
    cols = st.columns(4)
    cols[0].metric("Run type", meta["kind"])
    cols[1].metric("Model", meta["model"].split("/")[-1][:24])
    cols[2].metric("Tokens", f"{meta['usage']['input_tokens'] + meta['usage']['output_tokens']:,}")
    cols[3].metric("Duration", f"{meta['duration_seconds']}s")
    if meta.get("note"):
        st.info(meta["note"])

    stage_tabs = st.tabs(list(STAGE_TITLES.values()) + ["5 · Human sign-off"])
    with stage_tabs[0]:
        render_wiki(run["stages"]["wiki"])
    with stage_tabs[1]:
        render_conflicts(run["stages"]["conflicts"])
    with stage_tabs[2]:
        render_spec(run["stages"]["spec"])
    with stage_tabs[3]:
        render_grades(run["stages"]["grade"])
    with stage_tabs[4]:
        st.markdown(
            "The last stage is deliberately **not** automated. The agent compiled, "
            "checked, drafted and graded — a human reads the diff and stays accountable."
        )
        needs_human = [
            c["id"] for c in run["stages"]["conflicts"]["conflicts"]
            if c["needs_human_confirmation"]
        ]
        if needs_human:
            st.warning(f"Open items requiring a human call: {', '.join(needs_human)}")
        if st.button("✍️ Sign off this spec", type="primary"):
            st.success("Signed off. Agents do the work. Humans stay accountable.")
            st.balloons()


# ---------------------------------------------------------------- modes
if mode == "Replay a recorded run":
    runs = list_runs()
    if not runs:
        st.error("No recorded runs found in data/runs/.")
        st.stop()
    chosen = st.selectbox("Recorded run", runs, format_func=lambda p: p.stem)
    render_run(load_run(chosen))

else:
    st.subheader("Run the pipeline live")
    if st.button("▶️ Run pipeline", type="primary", disabled=not api_key):
        llm = LLM(api_key=api_key, model=model, base_url=base_url)
        status_boxes = {}
        progress_area = st.container()

        def on_progress(stage: str, state: str) -> None:
            title = STAGE_TITLES[stage]
            if state == "start":
                status_boxes[stage] = progress_area.status(title, state="running")
            else:
                status_boxes[stage].update(label=f"{title} — done", state="complete")

        try:
            run = run_pipeline(llm, transcripts, on_progress)
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
        import json as _json
        st.download_button(
            "⬇️ Download run JSON",
            data=_json.dumps(run, indent=2, ensure_ascii=False),
            file_name="spec-engine-run.json",
            mime="application/json",
        )
    elif not api_key:
        st.info("Enter an API key in the sidebar to enable the run button. OpenRouter keys start with `sk-or-`.")
