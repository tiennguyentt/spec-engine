"""Knowledge Engine — an evidence-backed spec red team.

Default view: the hero catch. A cold viewer lands on the defects the agent
team caught in an approved-looking insurance spec — with verbatim receipts,
the corrected diff, and the readiness delta — within seconds, no key, no
mode choice. The full machinery (gate, D1-D5 grading, phase-gated debate,
eval-log) is inspectable depth behind expanders.

Live mode runs the real pipeline through any OpenAI-compatible endpoint
(OpenRouter by default) with a key you provide, streaming real tokens.
"""

import json
import re
import time
from pathlib import Path

import streamlit as st

import intro
import theme
from engine import compiler, drift, evals, handoff, ledger, sponsored, standards, team, timemachine
from engine.llm import DEFAULT_BASE_URL, SUGGESTED_MODELS, LLM
from engine.pipeline import DATA_DIR, list_runs, load_run, run_pipeline, save_run
from engine.schemas import DraftSpec

st.set_page_config(page_title="Knowledge Engine", page_icon="assets/favicon.png", layout="wide")
theme.inject()
theme.inject_chat()

esc = theme.esc

if st.session_state.get("view", "demo") == "intro":
    intro.render()
    st.stop()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    if st.button(":material/arrow_back: What this system solves", use_container_width=True):
        st.session_state["view"] = "intro"
        st.rerun()

    st.header("Run")
    runs = list_runs()
    # default to a real recorded run (anything but the scripted "demo-*") so the
    # landing proves real inference; fall back to whatever exists
    _default_idx = next((i for i, p in enumerate(runs) if not p.stem.startswith("demo")), 0)
    chosen = (st.selectbox("Recorded run", runs, index=_default_idx, format_func=lambda p: p.stem)
              if runs else None)

    st.divider()
    st.header("Run live")
    # The PRIMARY "Run it live — on us" control lives in the MAIN column (see
    # render_hero) so it's reachable on mobile without opening this sidebar.
    st.caption("▶ The “Run it live — on us” button is on the main screen (no key "
               "needed). The option below is only for your own private evidence.")

    # EDGE CASE: bring your own key — only for running your OWN private evidence.
    with st.expander("Run on your own evidence (your key, private)", expanded=False):
        st.caption("For your own spec/evidence. Your key is used only for this session's "
                   "calls — never stored, never committed. Leave the pack empty to run the AnDigi case.")
        base_url = st.text_input("API base URL", value=DEFAULT_BASE_URL)
        api_key = st.text_input("API key", type="password", help="OpenRouter keys start with sk-or-. Never stored.")
        model = st.selectbox("Model", SUGGESTED_MODELS, accept_new_options=True)
        byo_files = st.file_uploader(
            "Your evidence pack (optional)", accept_multiple_files=True,
            type=["md", "txt", "sql", "py", "json"],
            help="Transcripts/docs (.md .txt) are enough — code (.py .txt) and schema (.sql) add depth. "
                 "Optionally include a draft-spec.json to red-team your own spec; without one, the engine "
                 "drafts a spec from your evidence first. Leave empty to run the AnDigi pack.",
        )
        st.download_button("draft-spec.json template",
                           (DATA_DIR / "andigi" / "draft-spec.json").read_text(encoding="utf-8"),
                           "draft-spec.json", use_container_width=True)
        run_live = st.button(":material/play_arrow: Run on my key", disabled=not api_key, use_container_width=True)
        st.caption("Hard budget 150k tokens, live burn shown. Cheap models work: every call is "
                   "schema-validated with retries. Uploaded files stay in this session only — "
                   "never stored server-side, never committed.")

    st.divider()
    st.header("About")
    st.markdown(
        "A public, fully synthetic rebuild of the PM intelligence system I "
        "operate at work. The case: **AnDigi**, an agent-operated insurance "
        "app. Every defect shown was planted in the evidence pack — and "
        "caught by the machinery, not by hand."
    )
    st.markdown(
        "Built by **Tien Nguyen** — AI-native Product Manager · "
        "[tiennguyentt.github.io](https://tiennguyentt.github.io/)"
    )


# Models offered for the no-key live run (verified OpenRouter ids). Default is
# deepseek-chat — fastest/most reliable inside the ~5-min capped run. Kimi is a
# solid alt. V4 is stronger but SLOWER (often won't finish in the cap). Free-text
# entry allows any other id.
SPON_MODELS = ["deepseek/deepseek-chat", "moonshotai/kimi-k2",
               "deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro",
               "google/gemini-2.0-flash-001"]

# The main-column "watch it run live" button (see render_hero) sets this flag and
# reruns; we read it here, after the sidebar, so the routing can start the run.
# This keeps the primary action reachable on mobile, where the sidebar is hidden.
run_sponsored = False
if st.session_state.pop("_trigger_sponsored", False):
    run_sponsored = True


# ---------------------------------------------------------------- helpers
def stat(value_html: str, label: str) -> str:
    return f'<div class="se-stat"><div class="v">{value_html}</div><div class="l">{esc(label)}</div></div>'


def work_notes_html(wn: dict) -> str:
    return (
        '<div class="se-notes">'
        f'<b>observation</b> {esc(wn["observation"])}<br>'
        f'<b>evidence</b> {esc(", ".join(wn["evidence_refs"]) or "—")} · '
        f'<b>confidence</b> {esc(wn["confidence"])}<br>'
        f'<b>risk</b> {esc(wn["risk"])}<br>'
        + (f'<b>proposed</b> {esc(wn["proposed_change"])}<br>' if wn["proposed_change"] else "")
        + (f'<b>open assumption</b> {esc(wn["open_assumption"])}' if wn["open_assumption"] else "")
        + "</div>"
    )


def turn_html(t: dict, show_notes: bool = True) -> str:
    label = team.role_label(t["role"])
    color = team.role_color(t["role"])
    notes = work_notes_html(t["work_notes"]) if show_notes else ""
    return (
        f'<div class="se-turn" style="border-left-color:{color}">'
        f'<div class="thead"><span class="trole" style="color:{color}">{esc(label)}</span>'
        f'<span class="tstance">{esc(t["stance"])} · {esc(", ".join(t["refs"]))}</span>'
        f'<span class="tround">{esc(t.get("phase", ""))}</span></div>'
        f'<div class="tmsg">{esc(t["message"])}</div>{notes}</div>'
    )


def source_quote_html(s: dict) -> str:
    who = f'{s["speaker"]} · ' if s["speaker"] else ""
    return (f'<div class="se-quote">{esc(who)}{esc(s["source_file"])} · {esc(s["locator"])} '
            f'<span class="se-chip" style="margin-left:6px">{esc(s["source_type"])}</span><br>“{esc(s["quote"])}”</div>')


def find_claim(run: dict, cid: str) -> dict | None:
    return next((c for c in run["stages"]["wiki"]["claims"] if c["id"] == cid), None)


def _clip(text: str, n: int = 110) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _reasoning_steps(run: dict) -> list[dict]:
    """Build the run's real logic chain — every step derived from the run data,
    so the hero shows how the model actually reasoned, not a staged script."""
    s = run["stages"]
    steps: list[dict] = []
    files = run["meta"].get("evidence_files", [])
    if files:
        steps.append({"k": "scan", "t": f'scanning <b>{len(files)}</b> evidence sources — transcripts · policy · code · DB'})
    confs = s["conflicts"]["conflicts"]
    # lead with the sharpest contradiction: spec-vs-code, else one needing a human
    conf = (next((c for c in confs if c["kind"] == "artifact-state-gap"), None)
            or next((c for c in confs if c.get("needs_human_confirmation")), None)
            or (confs[0] if confs else None))
    if conf:
        win = find_claim(run, conf["winning_claim_id"])
        if win and win.get("sources"):
            src = win["sources"][0]
            loc = src.get("locator") or src.get("source_file", "")
            steps.append({"k": "ground",
                          "t": f'grounding <span class="id">{esc(conf["winning_claim_id"])}</span> ← '
                               f'<b>{esc(loc)}</b>: “{esc(_clip(src.get("quote", ""), 64))}”'})
        steps.append({"k": "conflict", "t": esc(_clip(conf["description"], 130))})
    # the most diagnostic gate hit: a structural/grounding one if present
    hits = s["gate"]["hits"]
    gh = next((h for h in hits if h["rule_id"] in ("G7", "G8")), None) or (hits[0] if hits else None)
    if gh:
        steps.append({"k": "gate", "t": f'code gate — <b>{esc(gh["rule_id"])}</b> {esc(_clip(gh.get("message", ""), 80))}'})
    # a real line of the model's debate reasoning
    turns = s["debate"]["turns"]
    dturn = (next((t for t in turns if t.get("message") and ("48" in t["message"] or "must" in t["message"].lower())), None)
             or next((t for t in turns if t.get("message")), None))
    if dturn:
        steps.append({"k": "debate", "t": f'<b>{esc(team.role_label(dturn["role"]))}</b>: {esc(_clip(dturn["message"], 120))}'})
    if conf:
        steps.append({"k": "resolve",
                      "t": f'resolved — <b>{esc(conf.get("winning_authority", ""))}</b> wins · {esc(_clip(conf["resolution"], 80))}'})
    ams = s["debate"]["arbiter"]["amendments"]
    if ams:
        steps.append({"k": "fix", "t": f'corrected — “{esc(_clip(ams[0]["after"], 104))}”'})
    return steps


# ---------------------------------------------------------------- hero
def render_hero(run: dict) -> None:
    s = run["stages"]
    g1, g2 = s["grade_round1"], s["grade_round2"]
    gate1, gate2 = s["gate"], s["gate_round2"]
    arbiter = s["debate"]["arbiter"]
    p0_1 = sum(1 for f in g1["findings"] if f["priority"] == "P0")
    p0_2 = sum(1 for f in g2["findings"] if f["priority"] == "P0")

    theme.kicker("Evidence-backed spec red team · AnDigi insurance (synthetic case)")
    # (1) proof it's a real model run — exact tokens/model/duration, or an honest "scripted" label
    st.markdown(theme.telemetry(run["meta"]), unsafe_allow_html=True)
    # (2) PRIMARY action up top + mobile-reachable: pick a model, run it live on a
    # no-key sponsored key. The recorded run renders below instantly to read/audit.
    if sponsored.available():
        _left = sponsored.remaining_runs()
        st.selectbox("Model for the live run", SPON_MODELS, key="spon_model", accept_new_options=True,
                     help="No-key live run uses this. deepseek-chat is fastest for the ~5-min cap; "
                          "Kimi is a good alt; V4 is stronger but slower. Type any OpenRouter id.")
        if st.button(f"▶ Watch it run live — ~5 min · no key  ·  {_left} free left",
                     key="hero_live", type="primary", disabled=_left <= 0, use_container_width=True):
            st.session_state["_trigger_sponsored"] = True
            st.rerun()
        st.markdown(
            '<div class="se-try">Pick a model and watch the real red team run — no key needed. '
            "Below is a <b>recorded real run</b> (instant) you can read and audit right now.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="se-try"><span class="gold">▶ Audit it yourself</span> — open any receipt below to '
            "trace a claim to its source. (Live runs need a sponsored key configured on the deployment.)</div>",
            unsafe_allow_html=True,
        )
    # (3) the intelligence, alive: replay the model's real reasoning chain —
    # evidence → grounding → contradiction → gate → debate → resolution → fix
    steps = _reasoning_steps(run)
    if steps:
        st.markdown(theme.reasoning_trace(steps, run["meta"].get("model", "")), unsafe_allow_html=True)
    st.markdown('<div class="se-flow-cap">Messy evidence in. A verified, signed spec out.</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="se-stats">'
        + stat(f'<span class="from">{g1["overall_score"]} →</span> '
               f'<span class="se-countup" style="--se-target:{g2["overall_score"]}"></span> '
               f'<span class="delta">+{g2["overall_score"] - g1["overall_score"]}</span>', "spec readiness")
        + stat(f'<span class="from">{p0_1} →</span> {p0_2}', "P0 blockers")
        + stat(f'<span class="from">{gate1["errors"]} →</span> {gate2["errors"]}', "gate errors (code-enforced)")
        + stat(f'{len(arbiter["unresolved_human_decisions"])}', "decisions left to the human")
        + stat(f'<span class="se-lockin">{esc(g2["verdict"].replace("_", " ").lower())}</span>', "verdict")
        + "</div>",
        unsafe_allow_html=True,
    )
    # the pipeline, demoted to "how it runs"
    st.markdown('<div class="se-trace" style="margin:18px 0 -4px">how it runs</div>', unsafe_allow_html=True)
    st.markdown(theme.flow_diagram(g1["overall_score"], g2["overall_score"], len(arbiter["amendments"])),
                unsafe_allow_html=True)


    # Catch titles are DATA-DRIVEN — derived from the run itself — so this view
    # works on any run (curated replay or a messy real-model run), not just the
    # scripted case. Generic section frames; the card copy comes from the data.

    # ---- catch 1: a stakeholder conflict resolved by authority --------------
    c1 = next((c for c in s["conflicts"]["conflicts"] if c["kind"] == "business-rule"), None)
    if c1:
        theme.section("catch 01", "A stakeholder conflict — resolved by authority, flagged for a human",
                      "truth-hierarchy")
        win = find_claim(run, c1["winning_claim_id"])
        lose_id = next((cid for cid in c1["claim_ids"] if cid != c1["winning_claim_id"]), "")
        lose = find_claim(run, lose_id)
        inner = ""
        if win and win.get("sources"):
            inner += f'<div class="se-vs">WINS BY AUTHORITY — {esc(win["authority"])}</div>' + source_quote_html(win["sources"][0])
        if lose and lose.get("sources"):
            inner += f'<div class="se-vs">LOSES — BUT AUDITORS READ THIS ({esc(lose["authority"])})</div>' + source_quote_html(lose["sources"][0])
        summary = (
            f'<div class="chead"><span class="cnum">{esc(c1["id"])}</span>'
            f'<span class="ctitle">{esc(c1["description"])}</span>'
            + (f'<span class="se-chip" style="border-color:#D6A03C;color:#D6A03C">{theme.micon("flag", size="13px")} human decision</span>' if c1["needs_human_confirmation"] else "")
            + "</div>"
        )
        st.markdown(f'<div class="se-catch">{summary}</div>', unsafe_allow_html=True)
        with st.expander("view receipt — both sources, verbatim", expanded=True):
            st.markdown(inner + f'<div class="se-body" style="margin-top:8px">{esc(c1["resolution"])}</div>', unsafe_allow_html=True)

    # ---- catch 2: the strongest grounding finding the grader caught ---------
    f1 = next((f for f in g1["findings"] if f["priority"] == "P0"), None) \
        or (g1["findings"][0] if g1["findings"] else None)
    if f1:
        prio, role = f1["priority"], f1.get("assigned_role", "")
        theme.section("catch 02", "An ungrounded claim the adversarial grader caught", f"{prio} · grounding")
        ev = find_claim(run, f1["evidence_ref"])
        role_turn = next((t for t in s["debate"]["turns"] if t["role"] == role), None) if role else None
        summon = (f'<span class="se-summon" style="margin:0">{theme.micon("bolt", size="14px")} '
                  f'{esc(team.role_label(role))} summoned</span>') if role else ""
        st.markdown(
            f'<div class="se-catch"><div class="chead"><span class="cnum">{esc(f1["id"])} · {esc(prio)}</span>'
            f'<span class="ctitle">{esc(f1["description"])}</span>{summon}</div></div>',
            unsafe_allow_html=True,
        )
        with st.expander("view receipt — finding, violation, and the evidence it rests on"):
            inner = f'<div class="se-body">{esc(f1["suggested_fix"])}</div>' if f1.get("suggested_fix") else ""
            if f1.get("claim_class_violation"):
                inner += f'<div class="se-trace">claim-class violation: {esc(f1["claim_class_violation"])} · requirement {esc(f1["requirement_id"])}</div>'
            if ev and ev.get("sources"):
                inner += '<div class="se-vs">WHAT THE EVIDENCE ACTUALLY SAYS</div>' + source_quote_html(ev["sources"][0])
            st.markdown(inner, unsafe_allow_html=True)
            if role_turn:
                st.markdown(turn_html(role_turn), unsafe_allow_html=True)

    # ---- catch 3: spec vs the artifacts (code/DB) ---------------------------
    c2 = next((c for c in s["conflicts"]["conflicts"] if c["kind"] == "artifact-state-gap"), None)
    if c2:
        theme.section("catch 03", "Spec says one thing — the code and data say another", "artifact-state gap")
        intended = find_claim(run, c2["winning_claim_id"])
        artifacts = [find_claim(run, cid) for cid in c2["claim_ids"]]
        artifacts = [a for a in artifacts if a and a.get("claim_class") == "artifact-state"]
        locator = ""
        if artifacts and artifacts[0].get("sources"):
            src0 = artifacts[0]["sources"][0]
            locator = src0.get("locator") or src0.get("source_file", "")
        chip = f'<span class="se-chip">{esc(locator)}</span>' if locator else ""
        st.markdown(
            f'<div class="se-catch"><div class="chead"><span class="cnum">{esc(c2["id"])}</span>'
            f'<span class="ctitle">{esc(c2["description"])}</span>{chip}</div></div>',
            unsafe_allow_html=True,
        )
        with st.expander("view receipt — intended vs artifact state"):
            inner = ""
            if intended and intended.get("sources"):
                inner += f'<div class="se-vs">THE INTENDED BEHAVIOR ({esc(intended["authority"])})</div>' + source_quote_html(intended["sources"][0])
            for a in artifacts:
                inner += '<div class="se-vs">WHAT THE SYSTEM ACTUALLY DOES (artifact state — cannot be out-talked)</div>' + source_quote_html(a["sources"][0])
            inner += f'<div class="se-body" style="margin-top:8px">{esc(c2["resolution"])}</div>'
            st.markdown(inner, unsafe_allow_html=True)

    # ---- gate strip ---------------------------------------------------------
    theme.section("the gate", "Code-enforced. Models cannot override these results.", f'{gate1["errors"]} errors → {gate2["errors"]}')
    chips = " ".join(f'<span class="se-chip" style="border-color:{"#C0685C" if h["severity"] == "error" else "#D6A03C"};color:{"#C0685C" if h["severity"] == "error" else "#D6A03C"};margin-left:0">{esc(h["rule_id"])} {esc(h["requirement_id"])}</span>' for h in gate1["hits"])
    st.markdown(f'<div class="se-gatescan" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px;padding:4px 2px">{chips}</div>', unsafe_allow_html=True)
    with st.expander("inspect the deterministic gate log"):
        hits_html = "".join(
            f'<div class="se-gatehit"><span class="{ "rid" if h["severity"] == "error" else "warn" }">'
            f'{esc(h["rule_id"])} {esc(h["severity"])}</span> · {esc(h["requirement_id"])} · '
            f'{esc(h["message"])} — <i>“{esc(h["excerpt"][:90])}”</i></div>'
            for h in gate1["hits"]
        )
        st.markdown(hits_html + '<div class="se-trace" style="margin-top:8px">deterministic regex/structural checks · gate version '
                    + esc(gate1["gate_version"]) + " · runs before any model grading</div>", unsafe_allow_html=True)

    # ---- corrected diff ------------------------------------------------------
    theme.section("the fix", "Corrected diff, ready for engineering", f'{len(arbiter["amendments"])} amendments · +{len(arbiter["new_requirements"])} migration requirement')
    def _am_card(am):
        theme.card(
            f'<div class="rowtop"><span class="se-id">{esc(am["requirement_id"])}</span>'
            f'<span class="se-topic">{esc(am["rationale"])}</span>'
            f'<span class="se-chip">{esc(", ".join(am["finding_ids"]))}</span></div>'
            f'<div class="se-diff-del">{esc(am["before"])}</div>'
            f'<div class="se-diff-add">{esc(am["after"])}</div>'
        )
    if arbiter["amendments"]:
        _am_card(arbiter["amendments"][0])
    strip = " · ".join(f'{am["requirement_id"]}' for am in arbiter["amendments"][1:])
    with st.expander(f"all corrected diffs — {strip} + new requirements"):
        for am in arbiter["amendments"][1:]:
            _am_card(am)
        for nr in arbiter["new_requirements"]:
            acs = "".join(f'<div class="se-ac">{esc(ac)}</div>' for ac in nr["acceptance_criteria"])
            theme.card(
                f'<div class="rowtop"><span class="se-id">{esc(nr["id"])} · NEW</span>'
                f'<span class="se-topic">{esc(nr["title"])}</span></div>'
                f'<div class="se-diff-add">{esc(nr["statement"])}</div>{acs}'
                f'<div class="se-trace">traces → {esc(", ".join(nr["source_claim_ids"]))}</div>'
            )



    # ---- eval: detection recall (AnDigi ground truth only) -------------------
    try:
        ev = None if run["meta"].get("evidence_pack") == "byo" else evals.score_run(run)
    except Exception:
        ev = None
    if ev:
        theme.section("the eval", "Detection recall on the planted-defect benchmark",
                      f'{ev["caught"]}/{ev["total"]} caught · recall {ev["recall"]:.0%}')
        with st.expander("per-defect scorecard — what was caught, and through which channel"):
            rows = "".join(
                f'<div class="se-gatehit"><span class="{"rid" if d["caught"] else "warn"}" '
                f'style="color:{"#8E9A92" if d["caught"] else "#C0685C"}">'
                f'{theme.micon("check", size="14px") if d["caught"] else theme.micon("close", size="14px") + " MISSED"}</span> · {esc(d["id"])} [{esc(d["channel"])}] '
                f'{esc(d["title"])} → <i>{esc(d["where"])}</i></div>'
                for d in ev["defects"]
            )
            st.markdown(rows + '<div class="se-trace" style="margin-top:8px">ground truth: '
                        "data/evals/andigi-ground-truth.json · scorer: engine/evals.py · pure code, no model</div>",
                        unsafe_allow_html=True)

    # ---- depth ----------------------------------------------------------------
    st.write("")
    theme.section("depth", "For the technical reviewer", "")
    with st.expander("Inspect the full run — gate, D1-D5 grading, 11-role debate, evidence", icon=":material/frame_inspect:"):
        render_trace(run)
    with st.expander("How it works — architecture, budget, eval-log", icon=":material/settings:"):
        render_how(run)
    with st.expander("Standards alignment — INCOSE characteristics & EARS patterns", icon=":material/architecture:"):
        st.markdown(
            '<p class="se-body">What the gate and rubric enforce, read in the vocabulary an '
            "enterprise reviewer audits against. The mapping is ours, at the characteristic "
            "level — a reading aid, not a certification.</p>",
            unsafe_allow_html=True,
        )
        gate_rows = "".join(
            f'<div class="se-gatehit"><span class="rid">{esc(gid)}</span> → <b>{esc(char)}</b> · {esc(why)}</div>'
            for gid, (char, why) in standards.GATE_TO_INCOSE.items()
        )
        dim_rows = "".join(
            f'<div class="se-gatehit"><span class="rid">{esc(did)}</span> → <b>{esc(char)}</b> · {esc(why)}</div>'
            for did, (char, why) in standards.DIMENSION_TO_INCOSE.items()
        )
        st.markdown('<div class="se-vs">CODE GATE → INCOSE QUALITY CHARACTERISTICS</div>' + gate_rows
                    + '<div class="se-vs" style="margin-top:14px">D1–D5 RUBRIC → INCOSE QUALITY CHARACTERISTICS</div>' + dim_rows,
                    unsafe_allow_html=True)
        al = standards.alignment_report(run)
        req_rows = "".join(
            f'<div class="se-gatehit"><span class="rid">{esc(r["id"])}</span> {esc(r["title"])} · '
            f'EARS: <b>{esc(r["ears"])}</b> · ACs {r["acs_gwt"]}/{r["acs_total"]} Given-When-Then</div>'
            for r in al["requirements"]
        )
        st.markdown(
            f'<div class="se-vs" style="margin-top:14px">CORRECTED SPEC → EARS SHAPE (heuristic) · '
            f'{al["acs_gwt"]}/{al["acs_total"]} ACS IN GIVEN-WHEN-THEN</div>' + req_rows
            + '<div class="se-trace" style="margin-top:8px">statements are declarative rules (EARS Ubiquitous); '
            "triggers and conditions live in the Given/When clauses of each AC · engine/standards.py · pure code</div>",
            unsafe_allow_html=True,
        )



# ---------------------------------------------------------------- playback
def render_playback(run: dict, chars_per_sec: int) -> None:
    """Recorded-sequence playback: only agent messages stream; artifacts snap.
    Honest by construction — the label never claims live inference."""
    s = run["stages"]
    st.markdown(
        '<div class="se-flag" style="display:block">RECORDED REPLAY · deterministic scripted run · '
        "original engine sequence preserved · animation is not live inference</div>",
        unsafe_allow_html=True,
    )
    pane = st.container()
    turn_no, total = 0, len(s["debate"]["turns"])
    for phase in s["debate"]["phases"]:
        pane.markdown(f'<div class="se-spechead" style="margin:18px 0 10px"><span class="sid">{esc(phase["key"])}</span>'
                      f'<span class="stitle" style="font-size:16px">{esc(phase["title"])}</span></div>',
                      unsafe_allow_html=True)
        time.sleep(0.5)
        for ev in phase["events"]:
            if ev["type"] == "router" and not ev.get("close_phase"):
                pane.markdown(f'<p class="se-trace">router → {esc(ev["focused_question"])}</p>', unsafe_allow_html=True)
                time.sleep(0.7)
            elif ev["type"] == "turn":
                turn_no += 1
                label = team.role_label(ev["role"])
                ph = pane.empty()
                msg = ev["message"]
                budget = min(len(msg) / chars_per_sec, 5.0)
                step = max(2, int(len(msg) / max(budget * 20, 1)))
                shown = ""
                ph.markdown(f'<p class="se-trace">Replaying {esc(label)} · turn {turn_no} of {total}</p>', unsafe_allow_html=True)
                for i in range(0, len(msg), step):
                    shown = msg[: i + step]
                    ph.markdown(turn_html({**ev, "message": shown + " ▌"}, show_notes=False), unsafe_allow_html=True)
                    time.sleep(budget / max(len(msg) / step, 1))
                ph.markdown(turn_html(ev, show_notes=True), unsafe_allow_html=True)
                time.sleep(0.3)
            elif ev["type"] == "router" and ev.get("close_phase"):
                pane.markdown(f'<div class="se-noobj">net movement — {esc(ev["net_movement"])}</div>', unsafe_allow_html=True)
                time.sleep(0.5)
    pane.markdown(f'<div class="se-card"><div class="se-body">{esc(s["debate"]["arbiter"]["summary"])}</div>'
                  '<div class="se-trace">arbiter ruling assembled · playback complete</div></div>',
                  unsafe_allow_html=True)


# ---------------------------------------------------------------- the spec ships
def render_shipped_feature(run: dict) -> None:
    signoff = st.session_state.get("signoff")
    if st.session_state.get("tm_reverse_c1"):
        signoff = {"baseline_id": (signoff or {}).get("baseline_id", "BL-counterfactual"),
                   "rulings": [{"decision_text": "Policy section 4.1 contradicts the CEO decision",
                                 "choice": "Reverse: the published policy wins; disable the automated behavior in v1",
                                 "rationale": "Time Machine counterfactual"}]}
    table = compiler.compile_baseline(run, signoff, ledger.load_rules())

    theme.section("the spec ships", "Compiled from the signed baseline — pure code, every path cites it",
                  f"{table.baseline_id} · rule table v{table.version}")
    st.markdown('<p class="se-trace">spec + your rulings compile into this behavior · no model at runtime · flip the ruling and watch it propagate</p>', unsafe_allow_html=True)

    tm = st.toggle(":material/history: Executable Time Machine — reverse the C1 ruling (published policy wins)",
                   value=st.session_state.get("tm_reverse_c1", False))
    if tm != st.session_state.get("tm_reverse_c1", False):
        st.session_state["tm_reverse_c1"] = tm
        st.rerun()
    if not table.auto_approval_enabled:
        st.markdown('<div class="se-flag" style="display:block">rule table v2 active — auto-approval DISABLED by the reversed ruling; every clean claim now takes the human path</div>', unsafe_allow_html=True)

    with st.expander(f"decision table v{table.version} — the compiled IR this engine executes", icon=":material/balance:"):
        for e in sorted(table.entries, key=lambda x: x.order):
            conds = " AND ".join(f'{c["field"]} {c["op"]} {c["value"]}' for c in e.conditions) or "always"
            st.markdown(f'<div class="se-gatehit"><span class="rid">{esc(e.id)}</span> · IF {esc(conds)} → '
                        f'<b>{esc(e.verdict.upper())}</b> · <i>{esc(e.cites[:90])}</i></div>', unsafe_allow_html=True)

    if st.button(":material/play_arrow: Run acceptance board (vectors derived independently from the baseline)"):
        results = compiler.run_acceptance(table)
        for r in results:
            color = "#8E9A92" if r["passed"] else "#C0685C"
            mark = theme.micon("check", size="15px") if r["passed"] else theme.micon("close", size="15px")
            st.markdown(f'<div class="se-gatehit"><span style="color:{color};font-weight:600">{mark} {esc(r["id"])}</span> '
                        f'· {esc(r["ac"])} · expected <b>{esc(r["expect"])}</b> got <b>{esc(r["got"])}</b></div>',
                        unsafe_allow_html=True)
        n_pass = sum(1 for r in results if r["passed"])
        st.markdown(f'<p class="se-trace">{n_pass}/{len(results)} acceptance vectors green · table v{table.version} · 0 model calls</p>', unsafe_allow_html=True)

    presets = {
        "Clean claim < 5M": (3_800_000, "rear fender dent from parking incident", True, "active", True),
        "Fraud keyword": (4_200_000, "staged collision with witness statement", True, "active", True),
        "Lapsed policy": (2_000_000, "water damage from roof leak", True, "lapsed", True),
        "High-value 8M": (8_000_000, "engine damage after flood", True, "active", True),
    }
    cols = st.columns(4)
    for col, name in zip(cols, presets):
        if col.button(name, key=f"preset_{name}"):
            st.session_state["fnol"] = presets[name]
    amount, desc, photo, policy, precond = st.session_state.get("fnol", presets["Clean claim < 5M"])

    with st.form("fnol"):
        c1, c2 = st.columns(2)
        amount = c1.number_input("Claim amount (VND)", value=amount, step=100_000)
        policy = c2.selectbox("Policy status", ["active", "lapsed"], index=0 if policy == "active" else 1)
        desc = st.text_input("Incident description", value=desc)
        c3, c4 = st.columns(2)
        photo = c3.checkbox("Photo(s) attached", value=photo)
        precond = c4.checkbox("Policy 4.1 amended (your C1 ruling)", value=precond)
        go = st.form_submit_button("Submit FNOL → run triage", type="primary")

    if not go:
        return
    claim = {"amount": amount, "policy": policy, "photo": photo, "precondition": precond, "description": desc}
    entry = compiler.evaluate(table, claim)
    color = {"approve": "#8E9A92", "reject": "#C0685C", "block": "#C0685C",
             "investigate": "#D6A03C", "review": "#D6A03C"}[entry.verdict]
    st.markdown(
        f'<div class="se-catch" style="border-left-color:{color}">'
        f'<div class="chead"><span class="cnum" style="color:{color}">{esc(entry.title)}</span></div>'
        f'<div class="se-body">{esc(entry.body)}</div>'
        f'<div class="se-trace">{esc(entry.cites)} · table v{table.version} · {esc(table.baseline_id)}</div></div>',
        unsafe_allow_html=True,
    )
    event = {"seq": len(run["events"]) + 1, "type": "decision_event", "rule": entry.id,
             "verdict": entry.verdict, "table_version": table.version, "claim": claim}
    run["events"].append(event)
    st.download_button("Download decision_event (audit trail)", json.dumps(event, indent=2), "decision-event.json")
    st.markdown('<p class="se-trace">deterministic execution · the decision_event above was appended to this run\'s eval-log (B4 capture)</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------- chat terminal
ROLE_SHORT = {"po": "PO", "ba": "BA", "ux": "UX", "sa": "SA", "eng": "ENG", "qa": "QA",
              "devops": "DO", "security": "SEC", "compliance": "CMP", "sm": "SM", "arbiter": "ARB"}

ROLE_KEYWORDS = {
    "security": ["fraud", "security", "photo", "attack", "leak", "rbac"],
    "compliance": ["regulation", "circular", "compliance", "legal", "audit", "e-kyc", "ekyc"],
    "eng": ["code", "sla", "payout", "migration", "idempot", "retry", "database", "schema"],
    "qa": ["test", "ac", "measur", "verify", "edge"],
    "devops": ["monitor", "observab", "log", "deploy", "cost"],
    "ux": ["copy", "screen", "customer", "localiz", "message", "ui"],
}


def _pick_role(question: str) -> str:
    q = question.lower()
    for role, kws in ROLE_KEYWORDS.items():
        if any(k in q for k in kws):
            return role
    return "po"


def presence_rail_html(active: set, done: set) -> str:
    chips = ""
    for key_, short in ROLE_SHORT.items():
        color = team.role_color(key_)
        cls = "active" if key_ in active else ("done" if key_ in done else "")
        chips += (f'<span class="se-rail-chip {cls}" style="--c:{color};--pulse:{color}55">'
                  f'{esc(short)}</span>')
    return f'<div class="se-rail-chips">{chips}</div>'


def _findings_by_id(run: dict) -> dict:
    out: dict = {}
    for rnd in ("grade_round1", "grade_round2"):
        for f in run["stages"].get(rnd, {}).get("findings", []):
            out.setdefault(f["id"], f)
    return out


def _reply_line(run: dict, role: str, refs: list | None) -> str:
    """Thread marker: this turn answers a finding raised by another role."""
    fmap = _findings_by_id(run)
    for r in refs or []:
        f = fmap.get(r)
        if f and f.get("assigned_role") and f["assigned_role"] != role:
            return f'↩ on {r} — raised by {team.role_label(f["assigned_role"])}'
    return ""


_D_RUBRIC = {
    "D1": "Direction coverage — every source requirement and decision addressed, none silently dropped",
    "D2": "Expert translation — edge cases and failure paths beyond what sources literally said",
    "D3": "Grounding discipline — every domain fact traces to a claim id; invented facts are P0",
    "D4": "Scope discipline — explicit out-of-scope, no unplanned dependencies",
    "D5": "Dev-readiness — testable ACs, explicit numbers, no hedge words, active voice",
}

_ACTIVE_REFS: dict[str, str] = {}
_REF_RX = re.compile(r"\b([WCFR]\d+|G[1-8]|D[1-5]|JR-\d+)\b")


def _ref_index(run: dict) -> dict[str, str]:
    """id -> human tooltip: what W4/C1/F3/R2/G1 actually say, so nobody has to decode ids."""
    s = run["stages"]
    idx: dict[str, str] = dict(_D_RUBRIC)
    for c in s.get("wiki", {}).get("claims", []):
        src = (c.get("sources") or [{}])[0]
        who = src.get("speaker") or src.get("source_file", "")
        quote = (src.get("quote") or "")[:150]
        idx[c["id"]] = f'{c["claim"]} — {who}: “{quote}”'
    for c in s.get("conflicts", {}).get("conflicts", []):
        idx[c["id"]] = f'conflict ({c["kind"]}): {c["description"][:220]}'
    for rnd in ("grade_round1", "grade_round2"):
        for f in s.get(rnd, {}).get("findings", []):
            idx.setdefault(f["id"], f'finding {f["priority"]} · {f["dimension"]} on {f["requirement_id"]}: '
                                    f'{f["description"][:220]}')
    spec = s.get("corrected_spec") or {}
    for r in spec.get("requirements", []):
        idx[r["id"]] = f'requirement “{r["title"]}”: {r["statement"][:200]}'
    for h in s.get("gate", {}).get("hits", []):
        idx.setdefault(h["rule_id"], f'gate rule ({h["rule_class"]}): {h["message"][:180]}')
    return idx


def _set_refs(run: dict) -> None:
    global _ACTIVE_REFS
    try:
        _ACTIVE_REFS = _ref_index(run)
    except Exception:
        _ACTIVE_REFS = {}


def _linkify(escaped_text: str) -> str:
    """Wrap W/C/F/R/G/D ids in hover chips whose tooltip is the underlying content."""
    def sub(m: re.Match) -> str:
        tip = _ACTIVE_REFS.get(m.group(1))
        if not tip:
            return m.group(1)
        return f'<span class="se-ref" data-tip="{esc(tip)}">{m.group(1)}</span>'
    return _REF_RX.sub(sub, escaped_text)


MACHINE_ROLES = {
    "wiki": ("Evidence Wiki", "#D6A03C"),
    "conflicts": ("Conflict Check", "#D6A03C"),
    "gate": ("Code Gate", "#C0685C"),
    "grader": ("Grader · D1–D5", "#D6A03C"),
    "advisor": ("Advisor", "#8E9A92"),
}

LEGEND = ("hover any underlined id to read what it is — W evidence claim · C conflict · "
          "G gate rule · F grader finding · R requirement · D1–D5 rubric")


def _role_label(key: str) -> str:
    return MACHINE_ROLES[key][0] if key in MACHINE_ROLES else team.role_label(key)


def _role_color(key: str) -> str:
    return MACHINE_ROLES[key][1] if key in MACHINE_ROLES else team.role_color(key)


def chat_msg_html(role_key: str, message: str, stance: str = "", cursor: bool = False,
                  reply: str = "", work_notes: dict | None = None, thinking: bool = False) -> str:
    label = _role_label(role_key)
    color = _role_color(role_key)
    cur = " ▌" if cursor else ""
    stance_html = f' · {esc(stance)}' if stance else ""
    reply_html = f'<div class="se-reply">{_linkify(esc(reply))}</div>' if reply else ""
    body_cls = "tmsg se-think-live" if thinking else "tmsg"
    think = ""
    if work_notes:
        wn = work_notes
        rows = f'<b>observation</b> {_linkify(esc(wn.get("observation", "")))}<br>'
        rows += (f'<b>evidence</b> {_linkify(esc(", ".join(wn.get("evidence_refs") or []) or "—"))} · '
                 f'<b>confidence</b> {esc(wn.get("confidence", ""))}<br>')
        rows += f'<b>risk</b> {_linkify(esc(wn.get("risk", "")))}'
        if wn.get("proposed_change"):
            rows += f'<br><b>proposed</b> {_linkify(esc(wn["proposed_change"]))}'
        if wn.get("open_assumption"):
            rows += f'<br><b>open assumption</b> {_linkify(esc(wn["open_assumption"]))}'
        think = (f'<details class="se-think"><summary>thinking — how {esc(label)} got here</summary>'
                 f'<div class="tbody">{rows}</div></details>')
    return (f'<div class="se-gmsg"><div class="who" style="--c:{color};color:{color}">{esc(label)}'
            f'<span class="st">{stance_html}</span></div>'
            f'{reply_html}<div class="{body_cls}">{_linkify(esc(message))}{cur}</div>{think}</div>')


def _exec_text(run: dict, tokens: int | None = None) -> str:
    s = run["stages"]
    usage = run["meta"]["usage"]
    n = (usage["input_tokens"] + usage["output_tokens"]) if tokens is None else tokens
    return (f'tokens <b>{n:,}</b> · gate <b>{s["gate"]["errors"]}→{s["gate_round2"]["errors"]}</b>'
            f' · score <b>{s["grade_round1"]["overall_score"]}→{s["grade_round2"]["overall_score"]}</b>')


def _strip_html(active: set, done: set, exec_html: str) -> str:
    chips = ""
    for key_, short in ROLE_SHORT.items():
        color = team.role_color(key_)
        cls = "active" if key_ in active else ("done" if key_ in done else "")
        chips += (f'<span class="se-rail-chip {cls}" style="--c:{color};--pulse:{color}55">'
                  f'{esc(short)}</span>')
    return f'<div class="se-strip">{chips}<span class="exec">{exec_html}</span></div>'


CASE_BRIEF = (
    '<div class="se-casebrief">'
    '<div class="k">the case · synthetic</div>'
    '<div class="t"><b>AnDigi</b> is a digital insurance app; motorbike cover is one of its '
    "product lines. The feature being specced, for motorbike claims: "
    '<b>file a claim in the app → AI triage → clean claims under 5,000,000 VND auto-approve '
    'and pay within 48h → fraud or high-value goes to a human adjuster</b>.</div>'
    '<div class="s">The draft spec of that feature has planted defects. This team red-teams it '
    'against 6 evidence sources (founder transcript, ops transcript, published policy, code, DB schema) '
    'and hands you a corrected, dev-ready spec. You hold the final ruling.</div>'
    "</div>"
)


def render_chat(run: dict) -> None:
    _set_refs(run)
    feed = st.session_state.setdefault("chat_feed", [])
    _, col, _ = st.columns([1, 10, 1], gap="small")

    with col:
        strip_ph = st.empty()
        strip_ph.markdown(_strip_html(set(), set(ROLE_SHORT), _exec_text(run)), unsafe_allow_html=True)
        with st.popover("⋯ run tools"):
            st.download_button("eval-log (full run JSON)", json.dumps(run, indent=2, ensure_ascii=False),
                               "run.json", use_container_width=True)
            if run["meta"].get("evidence_pack") == "byo":
                st.caption("drift watch is off for uploaded packs — files live in this session only")
            elif st.button("Check evidence drift", use_container_width=True):
                for d in drift.check(run):
                    feed.append({"kind": "system", "text": d["text"]})
                    run["events"].append({"seq": len(run["events"]) + 1, "type": "drift_check", **d})
                st.rerun()
            if sponsored.available():
                st.caption(f"sponsored live: {sponsored.remaining_runs()} runs left today")

        if not feed:
            st.markdown(CASE_BRIEF, unsafe_allow_html=True)
            b1, b2, _sp = st.columns([1.6, 1.4, 3])
            play = b1.button(":material/play_arrow: Play the run", type="primary", use_container_width=True)
            instant = b2.button("Show transcript", use_container_width=True)
            if play or instant:
                st.session_state["chat_played"] = True
                _play_into_chat(run, col, strip_ph, animate=play)
                st.rerun()
        else:
            for item in feed:
                _render_feed_item(item)

    prompt = st.chat_input("Type your thought into the debate… (your message carries top authority)")
    if prompt:
        _handle_human_message(run, prompt)
        st.rerun()


def _render_feed_item(item: dict) -> None:
    kind = item["kind"]
    if kind == "system":
        st.markdown(f'<p class="se-sysmsg">— {esc(item["text"])} —</p>', unsafe_allow_html=True)
    elif kind == "phase":
        cast = f'<span class="cast">{esc(item["cast"])}</span>' if item.get("cast") else ""
        st.markdown(f'<div class="se-phasehead">{esc(item["text"])}{cast}</div>', unsafe_allow_html=True)
    elif kind == "router":
        st.markdown(f'<div class="se-router"><b>router</b> → {_linkify(esc(item["text"]))}</div>', unsafe_allow_html=True)
    elif kind == "turn":
        st.markdown(chat_msg_html(item["role"], item["message"], item.get("stance", ""),
                                  reply=item.get("reply", ""), work_notes=item.get("work_notes")),
                    unsafe_allow_html=True)
    elif kind == "human":
        st.markdown(f'<div class="se-human"><div class="who" style="color:#E6C079;font-family:JetBrains Mono,monospace;'
                    f'font-size:11px;text-transform:uppercase;letter-spacing:.08em">You · authority: highest</div>'
                    f'{esc(item["text"])}</div>', unsafe_allow_html=True)


def _build_feed(run: dict) -> list[dict]:
    """The whole pipeline as one conversation: machinery stages speak, then the team debates."""
    s = run["stages"]
    kind = run["meta"].get("kind", "run")
    live = kind in ("live", "real-inference")
    label = ("LIVE MODEL RUN · real tokens · " + str(run["meta"].get("model", ""))
             if live else "RECORDED REPLAY · real engine sequence · not live inference")
    items: list[dict] = [{"kind": "system", "text": label},
                         {"kind": "system", "text": LEGEND}]

    claims = s["wiki"]["claims"]
    srcs = {src_["source_file"] for c in claims for src_ in c["sources"]}
    items.append({"kind": "turn", "role": "wiki", "stance": "stage 1 · evidence",
                  "message": f"Built {len(claims)} claims (W1–W{len(claims)}) from {len(srcs)} sources — "
                             "every claim carries a verbatim quote. From here, the team may only argue "
                             "from these ids; unsourced facts do not exist."})
    for c in s["conflicts"]["conflicts"]:
        flag = " ⚑ needs your ruling." if c.get("needs_human_confirmation") else ""
        items.append({"kind": "turn", "role": "conflicts", "stance": f'{c["id"]} · {c["kind"]}',
                      "message": f'{c["description"]} Resolution: {c["resolution"]}{flag}'})

    g = s["gate"]
    warn = sum(1 for h in g["hits"] if h["severity"] == "warning")
    hits = " · ".join(f'{h["rule_id"]} {h["rule_class"]} ({h["requirement_id"]})' for h in g["hits"])
    items.append({"kind": "turn", "role": "gate", "stance": "code-enforced",
                  "message": f'{g["errors"]} errors, {warn} warnings before any model grades: {hits}. '
                             "Deterministic code — no model can talk its way past it."})

    g1 = s["grade_round1"]
    ftags = " · ".join(f'{f["id"]} ({f["priority"]}·{f["dimension"]}·{f["requirement_id"]})'
                       for f in g1["findings"])
    items.append({"kind": "turn", "role": "grader", "stance": "adversarial review · round 1",
                  "message": f'{g1["overall_score"]}/100 — {g1["verdict"].replace("_", " ")}. '
                             f'{len(g1["findings"])} findings: {ftags}. Full text in Report; '
                             "the debate below works through them, role by role."})

    for phase in s["debate"]["phases"]:
        phase_roles = [ev["role"] for ev in phase["events"] if ev["type"] == "turn"]
        cast = " · ".join(dict.fromkeys(team.role_label(r) for r in phase_roles))
        items.append({"kind": "phase", "text": phase["title"], "cast": cast, "roles": phase_roles})
        for ev in phase["events"]:
            if ev["type"] == "router" and not ev.get("close_phase"):
                items.append({"kind": "router", "text": ev["focused_question"]})
            elif ev["type"] == "turn":
                items.append({"kind": "turn", "role": ev["role"], "message": ev["message"],
                              "stance": ev["stance"], "work_notes": ev.get("work_notes") or {},
                              "reply": _reply_line(run, ev["role"], ev.get("refs"))})

    arb = s["debate"]["arbiter"]
    items.append({"kind": "turn", "role": "arbiter", "message": arb["summary"], "stance": "ruling"})

    g2 = s["grade_round2"]
    items.append({"kind": "turn", "role": "grader", "stance": "re-grade · round 2",
                  "message": f'After the amendments: {g1["overall_score"]} → {g2["overall_score"]}/100 — '
                             f'{g2["verdict"].replace("_", " ")}. '
                             f'Gate: {g["errors"]} → {s["gate_round2"]["errors"]} errors.'})

    adv = s.get("advisor") or {}
    if adv.get("items"):
        a_txt = " ".join(f'[{a["severity"]}] {a["concern"]}' for a in adv["items"][:2])
        more = f' (+{len(adv["items"]) - 2} more in Report)' if len(adv["items"]) > 2 else ""
        items.append({"kind": "turn", "role": "advisor", "stance": "advises · never blocks",
                      "message": a_txt + more})

    items.append({"kind": "system",
                  "text": "sequence complete · type below to challenge the team, or open Decide to rule"})
    return items


def _play_into_chat(run: dict, container, strip_ph, animate: bool) -> None:
    feed = st.session_state["chat_feed"]
    items = _build_feed(run)

    usage = run["meta"]["usage"]
    total_tokens = usage["input_tokens"] + usage["output_tokens"]
    total_chars = sum(len(i["message"]) for i in items if i["kind"] == "turn") or 1
    spent = 0
    done: set = set()

    def _paint(active: set, chars: int) -> None:
        tokens = min(total_tokens, int(total_tokens * chars / total_chars))
        strip_ph.markdown(_strip_html(active, done, _exec_text(run, tokens)), unsafe_allow_html=True)

    if animate:
        _paint(set(), 0)
    with container:
        for item in items:
            feed.append(item)
            if not animate:
                continue
            kind = item["kind"]
            if kind == "system":
                st.markdown(f'<p class="se-sysmsg">— {esc(item["text"])} —</p>', unsafe_allow_html=True)
                time.sleep(0.3)
            elif kind == "phase":
                _paint(set(item.get("roles", [])), spent)
                st.markdown(f'<div class="se-phasehead">{esc(item["text"])}'
                            f'<span class="cast">{esc(item.get("cast", ""))}</span></div>',
                            unsafe_allow_html=True)
                time.sleep(0.5)
            elif kind == "router":
                st.markdown(f'<div class="se-router"><b>router</b> → {_linkify(esc(item["text"]))}</div>',
                            unsafe_allow_html=True)
                time.sleep(0.5)
            elif kind == "turn":
                role, msg = item["role"], item["message"]
                wn = item.get("work_notes") or {}
                reply = item.get("reply", "")
                if role in MACHINE_ROLES:
                    # machinery reports snap in — they are stages, not speakers
                    st.markdown(chat_msg_html(role, msg, item.get("stance", "")), unsafe_allow_html=True)
                    spent += len(msg)
                    _paint(set(), spent)
                    time.sleep(0.7)
                    continue
                _paint({role}, spent)
                ph = st.empty()
                obs = wn.get("observation", "")
                if obs:  # visible thinking: the role's real work notes stream first, dim
                    tstep = max(4, len(obs) // 24)
                    for i in range(0, len(obs), tstep):
                        ph.markdown(chat_msg_html(role, obs[: i + tstep], "thinking…",
                                                  cursor=True, thinking=True), unsafe_allow_html=True)
                        time.sleep(0.022)
                    time.sleep(0.35)
                step = max(3, len(msg) // 60)
                for n, i in enumerate(range(0, len(msg), step)):
                    ph.markdown(chat_msg_html(role, msg[: i + step], item.get("stance", ""),
                                              cursor=True, reply=reply), unsafe_allow_html=True)
                    if n % 4 == 0:
                        _paint({role}, spent + i)
                    time.sleep(0.03)
                ph.markdown(chat_msg_html(role, msg, item.get("stance", ""), reply=reply,
                                          work_notes=wn or None), unsafe_allow_html=True)
                spent += len(msg)
                done.add(role)
                _paint(set(), spent)
        if animate:
            _paint(set(), total_chars)


def _handle_human_message(run: dict, prompt: str) -> None:
    feed = st.session_state.setdefault("chat_feed", [])
    feed.append({"kind": "human", "text": prompt})
    run["events"].append({"seq": len(run["events"]) + 1, "type": "human_interjection", "text": prompt})
    api_key_ = sponsored.key()
    role = _pick_role(prompt)
    if not api_key_:
        feed.append({"kind": "system",
                     "text": f"recorded to the eval-log · {team.role_label(role)} would answer here — "
                             "no inference key on this deployment (add one in Run live, or sponsored mode)"})
        return
    s = run["stages"]
    from engine.schemas import Turn as TurnSchema
    llm = LLM(api_key=api_key_, model=sponsored.SPONSORED_MODEL, token_budget=sponsored.PER_RUN_TOKEN_BUDGET)
    try:
        turn = llm.complete_json(
            system=(f"You are the {team.role_label(role)} answering the HUMAN OWNER directly in the team chat. "
                    "Their word carries the highest authority in the truth hierarchy. Answer their point "
                    "concretely against the run context, max 90 words, cite requirement/claim ids."),
            user=(f"RUN CONTEXT (claims + findings, abbreviated):\n"
                  f"{[c['id'] + ': ' + c['claim'] for c in s['wiki']['claims']]}\n"
                  f"{[f['id'] + ': ' + f['description'][:80] for f in s['grade_round1']['findings']]}\n\n"
                  f"HUMAN SAYS: {prompt}"),
            schema=TurnSchema,
        )
        wn = getattr(turn, "work_notes", None)
        feed.append({"kind": "turn", "role": role, "message": turn.message, "stance": "answers you",
                     "work_notes": wn.model_dump() if wn is not None else None})
        run["events"].append({"seq": len(run["events"]) + 1, "type": "role_answer", "role": role})
        sponsored.record_run(llm.usage.total)
    except Exception as err:
        feed.append({"kind": "system", "text": f"inference failed: {err}"})


# ---------------------------------------------------------------- run bar
# Viewer-facing workspaces. Overview (the verdict + receipts) is first, so a
# cold viewer lands on what the system *found* — not a chat frame. "Debate" is
# the argument that produced the fixes, reachable on demand, never the front door.
WORKSPACES = ["Overview", "Debate", "Verify", "Sign-off"]


def render_run_bar(run: dict) -> str:
    meta = run["meta"]
    kind = meta.get("kind", "run")
    kcolor = {"scripted-demo": "#D6A03C", "live": "#8E9A92", "real-inference": "#8E9A92"}.get(kind, "#9C9A92")
    score = run["stages"]["grade_round2"]["overall_score"]
    c_back, c_bar, c_dl = st.columns([0.6, 9.6, 1.8], gap="small")
    if c_back.button(":material/arrow_back:", help="Back to the start screen (case brief + play)",
                     use_container_width=True):
        # Reset the chat to its first screen so the run can be re-tested.
        # The intro page stays reachable from the sidebar.
        st.session_state.pop("chat_feed", None)
        st.session_state.pop("chat_played", None)
        st.rerun()
    c_bar.markdown(
        f'<div class="se-runbar" style="margin-top:0"><span class="idn"><b style="color:#ECEAE3">AnDigi</b> · '
        f'feature: in-app claim → AI triage → instant payout</span>'
        f'<span class="kind" style="color:{kcolor};border-color:{kcolor}66">{esc(kind)}</span>'
        f'<span class="idn">11 agents · 5 phases · {score}/100</span>'
        f'<span class="idn" style="margin-left:auto">agents do the work · you sign off</span></div>',
        unsafe_allow_html=True,
    )
    c_dl.download_button(
        ":material/download: replay", data=json.dumps(run, indent=2, ensure_ascii=False),
        file_name=f"knowledge-engine-{kind}.json", mime="application/json",
        use_container_width=True,
        help="Download this run as a self-contained JSON bundle — replayable and "
             "diffable anywhere, no engine install needed.",
    )
    ws = st.radio("workspace", WORKSPACES, horizontal=True, label_visibility="collapsed",
                  key="workspace")
    return ws


# ---------------------------------------------------------------- decision console
def _decision_options(text: str) -> list[str]:
    low = text.lower()
    if "policy" in low:
        return [
            "Approve with explicit launch precondition — policy must be amended first (recommended)",
            "Reverse: the published policy wins; disable the automated behavior in v1",
            "Defer — assign an owner and a due date; blocks unconditional shipment",
        ]
    if "counsel" in low or "e-kyc" in low or "confirm" in low:
        return [
            "Confirm the evidence-backed position (recommended)",
            "Require a legal citation — block the requirement until provided",
            "Defer to counsel with owner and date",
        ]
    return ["Approve as resolved (recommended)", "Reverse the resolution", "Defer with owner and date"]


def render_console(run: dict) -> None:
    arbiter = run["stages"]["debate"]["arbiter"]
    decisions = arbiter["unresolved_human_decisions"]
    amendments = arbiter["amendments"]
    state = st.session_state.get("signoff_state", "pending")

    if state == "signed":
        render_baseline(run, st.session_state["signoff"])
        return

    theme.section("the human", "Decision Console — your authority, recorded",
                  f"{len(decisions)} rulings + {len(amendments)} reviews · ≈60 seconds")
    st.markdown('<p class="se-trace">your rulings rewrite the baseline and become permanent rules</p>', unsafe_allow_html=True)

    if state == "pending":
        with st.form("console"):
            rulings: list[dict] = []
            for i, d in enumerate(decisions):
                st.markdown(f'<div class="se-flag" style="display:block">{theme.micon("flag", size="14px")} {esc(d)}</div>', unsafe_allow_html=True)
                choice = st.radio("Your ruling", _decision_options(d), key=f"rule_{i}", label_visibility="collapsed")
                rationale = st.text_input("One-line rationale (permanent record)", key=f"rat_{i}",
                                          placeholder="e.g. CEO confirmed in standup; Legal ticket L-42 opened")
                rulings.append({"decision_index": i, "decision_text": d, "choice": choice, "rationale": rationale})
                st.write("")
            st.markdown('<p class="se-trace">amendment reviews — Accept enters the baseline; Edit re-runs the gate; Reject requires a reason</p>', unsafe_allow_html=True)
            reviews: list[dict] = []
            for i, am in enumerate(amendments):
                cols = st.columns([3, 2])
                cols[0].markdown(f'<span class="se-id">{esc(am["requirement_id"])}</span> · {esc(am["rationale"][:70])}', unsafe_allow_html=True)
                action = cols[1].selectbox("action", ["accept", "edit", "reject", "defer"], key=f"act_{i}", label_visibility="collapsed")
                reviews.append({"amendment_index": i, "action": action, "edited_after": "", "rationale": ""})
            submitted = st.form_submit_button("Review rulings → propose rules", type="primary")
        if submitted:
            st.session_state["signoff_draft"] = {"rulings": rulings, "reviews": reviews}
            st.session_state["signoff_state"] = "rules"
            st.rerun()

    elif state == "rules":
        draft = st.session_state["signoff_draft"]
        needs_text = [r for r in draft["reviews"] if r["action"] in ("edit", "reject")]
        if needs_text:
            st.markdown('<p class="se-trace">your edits / rejection reasons</p>', unsafe_allow_html=True)
            for r in needs_text:
                am = amendments[r["amendment_index"]]
                if r["action"] == "edit":
                    r["edited_after"] = st.text_area(f'{am["requirement_id"]} — your text', value=am["after"], key=f"edit_{r["amendment_index"]}")
                r["rationale"] = st.text_input(f'{am["requirement_id"]} — why ({r["action"]})', key=f"why_{r["amendment_index"]}")

        proposed = ledger.propose_rules(run, draft["rulings"], draft["reviews"])
        st.markdown('<p class="se-trace">rules distilled from YOUR judgment — approve, or decline learning. Rules are scoped, versioned, revocable.</p>', unsafe_allow_html=True)
        approvals = []
        for rule in proposed:
            theme.card(
                f'<div class="rowtop"><span class="se-id">{esc(rule.id)}</span>'
                f'<span class="se-topic">{esc(rule.title)}</span>'
                f'<span class="se-chip" style="border-color:{"#C0685C" if rule.severity == "blocking" else "#9C9A92"}">{esc(rule.severity)}</span></div>'
                f'<div class="se-body">{esc(rule.rule_text)}</div>'
                f'<div class="se-trace">born from: {esc(rule.born_item)} · by you · {esc(rule.born_date)}</div>'
            )
            approvals.append(st.checkbox(f"Approve {rule.id}", value=True, key=f"appr_{rule.id}"))
        if st.button(":material/stylus_note: Approve baseline & create handoff", type="primary"):
            approved = [r for r, ok in zip(proposed, approvals) if ok]
            ledger.commit_rules(approved)
            signoff = {
                "status": "complete", "baseline_id": handoff.baseline_id(),
                "signed_at": time.strftime("%Y-%m-%d %H:%M"), "by": "you",
                "rulings": draft["rulings"], "reviews": draft["reviews"],
                "rules_approved": [r.id for r in approved],
            }
            # materialize accepted/edited reviews into the corrected spec (trust gap fix)
            from engine.debate import apply_amendments as _apply
            from engine.schemas import AmendmentSet as _ASet, DraftSpec as _DSpec
            arb_set = _ASet.model_validate(run["stages"]["debate"]["arbiter"])
            kept = []
            for i, am in enumerate(arb_set.amendments):
                rv = next((r for r in draft["reviews"] if r["amendment_index"] == i), None)
                if rv and rv["action"] == "reject":
                    continue
                if rv and rv["action"] == "edit" and rv.get("edited_after"):
                    am = am.model_copy(update={"after": rv["edited_after"]})
                kept.append(am)
            arb_set = arb_set.model_copy(update={"amendments": kept})
            run["stages"]["corrected_spec"] = _apply(
                _DSpec.model_validate(run["stages"]["draft_spec"]), arb_set).model_dump()
            run["signoff"] = signoff
            seq = len(run["events"])
            for i, r in enumerate(draft["rulings"]):
                run["events"].append({"seq": seq + i + 1, "type": "decision_ruled", "choice": r["choice"]})
            run["events"].append({"seq": len(run["events"]) + 1, "type": "signoff_completed",
                                   "baseline": signoff["baseline_id"], "rules": signoff["rules_approved"]})
            run["lifecycle"].append({"state": "baseline_signed", "note": signoff["baseline_id"]})
            save_run(run, f"signed-{time.strftime('%Y%m%d-%H%M%S')}")
            st.session_state["signoff"] = signoff
            st.session_state["signoff_state"] = "signed"
            st.rerun()
        if st.button(":material/arrow_back: Back to rulings"):
            st.session_state["signoff_state"] = "pending"
            st.rerun()


def render_baseline(run: dict, signoff: dict) -> None:
    spec = run["stages"]["corrected_spec"]
    theme.section("release baseline", f"{spec['feature_name']} — governed & ready", signoff["baseline_id"])
    st.markdown(
        '<div class="se-stats">'
        + stat(str(len(spec["requirements"])), "requirements")
        + stat(str(len(signoff["rulings"])), "human rulings")
        + stat(str(len(signoff["rules_approved"])), "rules distilled")
        + stat(esc(signoff["signed_at"]), "signed")
        + "</div>",
        unsafe_allow_html=True,
    )
    for r in signoff["rulings"]:
        theme.card(
            f'<div class="rowtop"><span class="se-id">RULING</span>'
            f'<span class="se-topic">{esc(r["choice"])}</span></div>'
            f'<div class="se-trace">{esc(r["decision_text"][:160])} · rationale: {esc(r["rationale"] or "—")} · recorded by you, {esc(signoff["signed_at"])}</div>'
        )

    c1, c2, c3 = st.columns(3)
    c1.download_button("Signed spec (MD)", handoff.signed_spec_md(run, signoff), "signed-spec.md")
    c2.download_button("Decision record", handoff.decision_record_md(run, signoff), "decision-record.md")
    c3.download_button("Jira/Linear stubs", handoff.ticket_stubs_md(run, signoff), "ticket-stubs.md")

    # ---- the compounding proof: rules fire on the NEXT draft -----------------
    theme.section("the loop", "Your judgment, applied to the next draft", "preflight · pure code")
    if st.button(":material/bolt: Preflight the next AnDigi draft (v1.1) with your rules"):
        v2 = DraftSpec.model_validate_json((DATA_DIR / "andigi-v2" / "draft-spec.json").read_text(encoding="utf-8"))
        hits = ledger.preflight(v2)
        if not hits:
            st.info("No ledger rules matched this draft.")
        for h in hits:
            rule = h["rule"]
            st.markdown(
                f'<div class="se-catch"><div class="chead"><span class="cnum">{esc(rule["id"])}</span>'
                f'<span class="ctitle">{esc(rule["title"])} — fired on {esc(h["requirement_id"])}</span></div>'
                f'<div class="se-body">{esc(rule["rule_text"])}</div>'
                f'<div class="se-trace">matched: {esc(", ".join(h["matched_keywords"]))} · effect: {esc(h["effect"])} · '
                f'born from {esc(rule["born_item"])}, by {esc(rule["born_by"])}, {esc(rule["born_date"])} — '
                "your past self just reviewed this draft before any model ran.</div></div>",
                unsafe_allow_html=True,
            )

    with st.expander("Decision Time Machine — what if you ruled differently on C1?", icon=":material/history:"):
        branch = timemachine.alternative_branch(run, "C1")
        if branch:
            st.markdown(f'<p class="se-body"><b>What if:</b> {esc(branch["what_if"])}</p>', unsafe_allow_html=True)
            for ch in branch["requirements_rewritten"]:
                theme.card(
                    f'<div class="rowtop"><span class="se-id">{esc(ch["requirement_id"])}</span>'
                    f'<span class="se-topic">rewrites in this branch</span></div>'
                    f'<div class="se-diff-del">{esc(ch["original_after"])}</div>'
                    f'<div class="se-diff-add">{esc(ch["counterfactual_after"])}</div>'
                )
            if branch["launch_conditions_removed"]:
                st.markdown('<p class="se-trace">launch conditions removed in this branch:</p>', unsafe_allow_html=True)
                for d in branch["launch_conditions_removed"]:
                    st.markdown(f'<div class="se-noobj">{esc(d[:160])}</div>', unsafe_allow_html=True)
            st.markdown(f'<p class="se-trace">rules never born: {esc(", ".join(branch["rules_never_born"]))} · {esc(branch["note"])}</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------- trace depth
def render_trace(run: dict) -> None:
    s = run["stages"]
    states = [x["state"] for x in run["lifecycle"]]
    order = ["draft", "graded", "advisor", "sign-off", "baseline_signed"]
    last = states[-1] if states else "draft"
    stepper = '<span class="se-step-arrow"> → </span>'.join(
        f'<span class="se-step {"active" if st_ == last else ("done" if st_ in states else "")}">{esc(st_)}</span>'
        for st_ in order
    )
    st.markdown(f'<div class="se-stepper">{stepper}<span class="se-step-arrow"> · max 3 grading rounds, else BLOCKED</span></div>', unsafe_allow_html=True)

    tabs = st.tabs(["Grading D1–D5", "Debate (full roster)", "Evidence wiki", "Spec before/after", "Advisor"])

    with tabs[0]:
        for rnd, key in (("round 1", "grade_round1"), ("round 2 (post-debate)", "grade_round2")):
            g = s[key]
            theme.section("", f"Grading {rnd}", f'{g["overall_score"]}/100 · {g["verdict"]}')
            dims = "".join(
                f'<div style="flex:1;min-width:110px"><div class="se-trace">{d}: {g["scores"].get(d, 0)}</div>{theme.bar(g["scores"].get(d, 0), 100)}</div>'
                for d in ("D1", "D2", "D3", "D4", "D5")
            )
            st.markdown(f'<div class="se-card"><div style="display:flex;gap:14px;flex-wrap:wrap">{dims}</div></div>', unsafe_allow_html=True)
            checks = "".join(
                f'<div class="se-gatehit"><span class="{ "rid" if c["result"] == "FAIL" else "" }" style="color:{"#C0685C" if c["result"] == "FAIL" else "#8E9A92"}">'
                f'{ theme.micon("close", size="14px") if c["result"] == "FAIL" else theme.micon("check", size="14px")} {esc(c["dimension"])}</span> {esc(c["item"])}'
                + (f' — <i>{esc(c["note"])}</i>' if c["note"] else "") + "</div>"
                for c in g["checklist"]
            )
            theme.card(checks)
            for f in g["findings"]:
                color = {"P0": "#C0685C", "P1": "#D6A03C", "P2": "#9C9A92"}[f["priority"]]
                theme.card(
                    f'<div class="rowtop"><span class="se-id">{esc(f["id"])}</span>'
                    f'<span class="se-chip" style="border-color:{color};color:{color}">{esc(f["priority"])} · {esc(f["dimension"])}</span>'
                    f'<span class="se-topic">{esc(f["requirement_id"])}</span>'
                    f'<span class="se-chip">→ {esc(team.role_label(f["assigned_role"]))}</span></div>'
                    f'<div class="se-body">{esc(f["description"])}</div>'
                    f'<div class="se-trace">evidence: {esc(f["evidence_ref"] or "none — the absence is the finding")} · fix: {esc(f["suggested_fix"])}</div>'
                )

    with tabs[1]:
        legend = " ".join(
            f'<span class="se-chip" style="border-color:{team.role_color(k)};color:{team.role_color(k)}">{esc(team.role_label(k))}</span>'
            for k in team.load_team()["roles"]
        )
        st.markdown(f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">{legend}</div>', unsafe_allow_html=True)
        for phase in s["debate"]["phases"]:
            theme.section("", phase["title"], f'eligible: {", ".join(team.role_label(r) for r in phase["eligible"])}')
            for ev in phase["events"]:
                if ev["type"] == "router":
                    if ev.get("close_phase"):
                        theme.card(f'<div class="se-trace">ROUTER · phase closed</div><div class="se-body">{esc(ev["net_movement"])}</div>')
                    else:
                        theme.card(
                            f'<div class="se-trace">ROUTER · iteration {ev.get("iteration", 1)} · issue {esc(ev["issue_id"])} '
                            f'→ summons {esc(", ".join(team.role_label(r) for r in ev["summoned_roles"]))}</div>'
                            f'<div class="se-body">{esc(ev["focused_question"])}</div>'
                        )
                elif ev["type"] == "turn":
                    st.markdown(turn_html(ev), unsafe_allow_html=True)
                elif ev["type"] == "no_objection":
                    st.markdown(f'<div class="se-noobj">{esc(team.role_label(ev["role"]))} — no standing issue, no objection (0 tokens)</div>', unsafe_allow_html=True)
        theme.section("", "Arbiter", "")
        theme.card(f'<div class="se-body">{esc(s["debate"]["arbiter"]["summary"])}</div>')

    with tabs[2]:
        st.markdown(f'<p class="se-body">{esc(s["wiki"]["project_summary"])}</p>', unsafe_allow_html=True)
        for claim in s["wiki"]["claims"]:
            sources = "".join(source_quote_html(src) for src in claim["sources"])
            theme.card(
                f'<div class="rowtop"><span class="se-id">{esc(claim["id"])}</span>'
                f'<span class="se-topic">{esc(claim["topic"])}</span>'
                f'<span class="se-chip">{esc(claim["claim_class"])}</span>'
                f'<span class="se-chip">{esc(claim["authority"])}</span></div>'
                f'<div class="se-body">{esc(claim["claim"])}</div>{sources}'
            )
        if s["conflicts"].get("notes"):
            st.markdown(f'<p class="se-trace">checked, not in conflict: {esc(s["conflicts"]["notes"])}</p>', unsafe_allow_html=True)

    with tabs[3]:
        for label, key in (("Draft (red-team target)", "draft_spec"), ("Corrected (post-debate)", "corrected_spec")):
            theme.section("", label, f'{len(s[key]["requirements"])} requirements')
            for req in s[key]["requirements"]:
                acs = "".join(f'<div class="se-ac">{esc(ac)}</div>' for ac in req["acceptance_criteria"])
                theme.card(
                    f'<div class="rowtop"><span class="se-id">{esc(req["id"])}</span>'
                    f'<span class="se-topic">{esc(req["title"])}</span></div>'
                    f'<div class="se-body">{esc(req["statement"])}</div>{acs}'
                    f'<div class="se-trace">traces → {esc(", ".join(req["source_claim_ids"]) or "∅")}</div>'
                )

    with tabs[4]:
        if "advisor" in s:
            for item in s["advisor"]["items"]:
                color = {"S0": "#C0685C", "S1": "#D6A03C", "S2": "#9C9A92"}[item["severity"]]
                theme.card(
                    f'<div class="rowtop"><span class="se-chip" style="border-color:{color};color:{color}">{esc(item["severity"])}</span>'
                    f'<span class="se-topic">{esc(item["concern"])}</span></div>'
                    f'<div class="se-body">{esc(item["suggestion"])}</div>'
                )
            st.markdown('<p class="se-trace">the advisor never blocks — S0/S1/S2 are inputs to the human sign-off</p>', unsafe_allow_html=True)


def render_how(run: dict) -> None:
    meta = run["meta"]
    usage = meta["usage"]
    st.markdown(
        '<div class="se-body">'
        "<b>Flow:</b> evidence (transcripts · policy docs · code · DB) → source-traced wiki → "
        "truth-hierarchy conflict check → deterministic code gate → adversarial D1–D5 grading → "
        "phase-gated debate (bounded router, full enterprise roster in <code>engine/team.yaml</code>) → "
        "arbiter amendments → re-grade → advisor → human sign-off.<br><br>"
        "<b>Reliability:</b> every model call is schema-validated JSON with bounded retries "
        "(any cheap OpenAI-compatible model works); the gate is pure code and runs before any "
        "model; failed turns log as FAILED and the run continues; hard token budget with "
        "graceful stop.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="se-stats">'
        + stat(esc(meta["model"].split("/")[-1][:24]), "model")
        + stat(f'{usage["input_tokens"] + usage["output_tokens"]:,}', "tokens used")
        + stat(f'{meta["token_budget"]:,}', "hard budget")
        + stat(f'{meta["duration_seconds"]}s', "duration")
        + stat(esc(meta["kind"]), "run kind")
        + "</div>",
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download the full run (eval-log JSON)",
        data=json.dumps(run, indent=2, ensure_ascii=False),
        file_name="knowledge-engine-run.json",
        mime="application/json",
    )


# ---------------------------------------------------------------- live mode
def render_live(sponsored_run: bool = False) -> None:
    evidence_dir = DATA_DIR / "andigi"
    byo = False
    if sponsored_run:
        # routing has verified availability/cap and is holding the slot; we run
        # on the server-side key (capped budget) and release the slot when done.
        eff_key = sponsored.key()
        eff_model = st.session_state.get("spon_model") or sponsored.SPONSORED_MODEL
        eff_base, eff_budget = DEFAULT_BASE_URL, sponsored.PER_RUN_TOKEN_BUDGET
    else:
        eff_key, eff_model, eff_base, eff_budget = api_key, model, base_url, 0
        byo = bool(byo_files)
        if byo:
            names = [f.name for f in byo_files]
            has_spec = "draft-spec.json" in names
            if len(names) - (1 if has_spec else 0) < 1:
                st.error("Upload at least one evidence file — a transcript, doc, code or schema "
                         "(.md/.txt is enough).")
                st.stop()
            import tempfile
            evidence_dir = Path(tempfile.mkdtemp(prefix="ke-byo-"))
            for f in byo_files:
                (evidence_dir / Path(f.name).name).write_bytes(f.getvalue())
            if has_spec:
                try:
                    DraftSpec.model_validate_json((evidence_dir / "draft-spec.json").read_text(encoding="utf-8"))
                except Exception as err:
                    st.error(f"draft-spec.json does not match the schema: {err}")
                    st.stop()
                st.info(f"BYO evidence pack: {len(names) - 1} evidence files + your draft spec · "
                        "processed in this session only")
            else:
                st.info(f"BYO evidence pack: {len(names)} evidence files, no draft spec — the engine "
                        "will draft a spec from your evidence first, then red-team its own draft · "
                        "processed in this session only")

    llm = LLM(api_key=eff_key, model=eff_model, base_url=eff_base, token_budget=eff_budget)

    # live run streams in the same chat-terminal layout as the replay
    col_chat, col_rail = st.columns([2.6, 1.05], gap="large")
    with col_rail:
        st.markdown('<div class="se-rail-title">team</div>', unsafe_allow_html=True)
        rail_ph = st.empty()
        rail_ph.markdown(presence_rail_html(set(), set()), unsafe_allow_html=True)
        st.markdown('<div class="se-rail-title" style="margin-top:14px">execution</div>', unsafe_allow_html=True)
        odo_ph = st.empty()
        st.markdown('<p class="se-trace" style="margin-top:10px">LIVE MODEL RUN · real tokens · '
                    f'{esc(eff_model)}{" · on us" if sponsored_run else ""}</p>', unsafe_allow_html=True)
    with col_chat:
        _whose = "the AnDigi case — free, on us" if sponsored_run else "your evidence"
        st.markdown(f'<p class="se-sysmsg">— live run · the full roster is working on {_whose} —</p>',
                    unsafe_allow_html=True)
        status_area = st.container()
        stream_area = st.container()

    boxes: dict = {}
    typing = {"ph": None, "buf": "", "chars": 0}
    done_roles: set = set()

    def _odo() -> None:
        odo_ph.markdown(f'<div class="se-odo">tokens <b>{llm.usage.total:,}</b> · '
                        f'budget <b>{(llm.token_budget or 0):,}</b></div>', unsafe_allow_html=True)

    _odo()

    titles = {"wiki": "Evidence → wiki", "draft": "Drafting spec from evidence", "conflicts": "Conflict check", "gate": "Code gate",
              "grade": "Grading round 1", "debate": "Role debate", "regrade": "Re-grade", "advisor": "Advisor"}

    def on_progress(stage: str, state: str) -> None:
        if state == "start":
            boxes[stage] = status_area.status(titles.get(stage, stage), state="running")
        elif stage in boxes:
            boxes[stage].update(label=f"{titles.get(stage, stage)} — done · {llm.usage.total:,} tokens burned", state="complete")
        _odo()

    def on_event(ev: dict) -> None:
        if ev["type"] == "turn_start":
            rail_ph.markdown(presence_rail_html({ev["role"]}, done_roles), unsafe_allow_html=True)
            typing["ph"] = stream_area.empty()
            typing["buf"] = f"**{team.role_label(ev['role'])}** is thinking…\n\n"
            typing["ph"].markdown(typing["buf"])
        elif ev["type"] == "turn" and typing["ph"] is not None:
            typing["ph"].markdown(turn_html(ev), unsafe_allow_html=True)
            typing["ph"] = None
            done_roles.add(ev["role"])
            rail_ph.markdown(presence_rail_html(set(), done_roles), unsafe_allow_html=True)
            _odo()
        elif ev["type"] == "no_objection":
            done_roles.add(ev["role"])
            stream_area.markdown(f'<div class="se-noobj">{esc(team.role_label(ev["role"]))} — no objection (0 tokens)</div>', unsafe_allow_html=True)
        elif ev["type"] == "router" and not ev.get("close_phase"):
            stream_area.markdown(f'<p class="se-trace">router → {esc(ev["focused_question"])}</p>', unsafe_allow_html=True)

    def on_text(ch: str) -> None:
        if typing["ph"] is not None:
            typing["buf"] += ch
            typing["ph"].markdown(typing["buf"] + "▌")
            typing["chars"] += 1
            if typing["chars"] % 24 == 0:
                _odo()

    try:
        run = run_pipeline(llm, on_progress, on_event, on_text, evidence_dir=evidence_dir)
    except Exception as err:  # surface provider errors readably
        if sponsored_run:
            sponsored.release_slot()
        st.error(f"Run failed: {err}")
        st.stop()

    if sponsored_run:
        sponsored.record_run(llm.usage.total)
        sponsored.release_slot()
        run["meta"]["evidence_pack"] = "sponsored"
    if byo:
        run["meta"]["evidence_pack"] = "byo"
    import time as _time
    name = f"live-{_time.strftime('%Y%m%d-%H%M%S')}"
    save_run(run, name)
    # hand the whole pipeline conversation to the Chat workspace
    feed = _build_feed(run)
    if byo:
        feed.insert(1, {"kind": "system", "text": "your evidence pack · processed in this session only"})
    st.session_state["chat_feed"] = feed
    st.session_state["active_run"] = run
    st.session_state["active_run_name"] = name
    st.session_state["workspace"] = "Overview"
    st.success(f"Run complete — saved as {name}.json. Showing the verdict + catches…")
    st.rerun()


# ---------------------------------------------------------------- routing
# Sponsored guards live here so a busy/capped slot falls through to the recorded
# run instead of blanking the page. render_live(sponsored_run=True) assumes the
# slot is held and releases it.
_live_started = False
if run_sponsored:
    if sponsored.available() and sponsored.remaining_runs() > 0 and sponsored.acquire_slot():
        render_live(sponsored_run=True)
        _live_started = True
    else:
        st.warning("Free live runs are busy or used up right now — here's a recorded run instead. "
                   "Try again in a moment, or use your own key.")
elif run_live and api_key:
    render_live()
    _live_started = True

if _live_started:
    pass
elif chosen:
    _run = st.session_state.get("active_run")
    if st.session_state.get("active_run_name") != str(chosen):
        _run = load_run(chosen)
        st.session_state["active_run"] = _run
        st.session_state["active_run_name"] = str(chosen)
        st.session_state["chat_feed"] = []
    ws = render_run_bar(_run)
    if ws == "Overview":
        render_hero(_run)
    elif ws == "Debate":
        render_chat(_run)
    elif ws == "Verify":
        render_shipped_feature(_run)
    else:
        render_console(_run)
else:
    st.error("No recorded runs found in data/runs/ — run scripts/make_demo_run.py first.")
