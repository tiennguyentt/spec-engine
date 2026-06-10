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
import time
from pathlib import Path

import streamlit as st

import intro
import theme
from engine import handoff, ledger, team, timemachine
from engine.llm import DEFAULT_BASE_URL, SUGGESTED_MODELS, LLM
from engine.pipeline import DATA_DIR, list_runs, load_run, run_pipeline, save_run
from engine.schemas import DraftSpec

st.set_page_config(page_title="Knowledge Engine", page_icon="📐", layout="wide")
theme.inject()

esc = theme.esc

if st.session_state.get("view", "demo") == "intro":
    intro.render()
    st.stop()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    if st.button("← What this system solves", use_container_width=True):
        st.session_state["view"] = "intro"
        st.rerun()

    st.header("Run")
    runs = list_runs()
    chosen = st.selectbox("Recorded run", runs, format_func=lambda p: p.stem) if runs else None

    st.divider()
    st.header("Run live")
    with st.expander("on your own evidence pack"):
        base_url = st.text_input("API base URL", value=DEFAULT_BASE_URL)
        api_key = st.text_input("API key", type="password", help="Never stored. OpenRouter keys start with sk-or-.")
        model = st.selectbox("Model", SUGGESTED_MODELS, accept_new_options=True)
        run_live = st.button("▶ Run the red team", type="primary", disabled=not api_key, use_container_width=True)
        st.caption("Hard budget 150k tokens, live burn shown. Cheap models work: every call is schema-validated with retries.")

    st.divider()
    st.header("About")
    st.markdown(
        "A public, fully synthetic rebuild of the PM intelligence system I "
        "operate at work. The case: **AnDigi**, an agent-operated insurance "
        "app. Every defect shown was planted in the evidence pack — and "
        "caught by the machinery, not by hand."
    )


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


# ---------------------------------------------------------------- hero
def render_hero(run: dict) -> None:
    s = run["stages"]
    g1, g2 = s["grade_round1"], s["grade_round2"]
    gate1, gate2 = s["gate"], s["gate_round2"]
    arbiter = s["debate"]["arbiter"]
    p0_1 = sum(1 for f in g1["findings"] if f["priority"] == "P0")
    p0_2 = sum(1 for f in g2["findings"] if f["priority"] == "P0")

    theme.kicker("Knowledge Engine · evidence-backed spec red team · synthetic case: AnDigi insurance")
    st.markdown(
        f'<div class="se-hero-head">{len(arbiter["amendments"])} defects were hiding in this '
        "approved-looking insurance spec.<br>The agent team caught them — with receipts.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="se-hero-sub">An AI team red-teams a draft spec against the evidence. '
        "Case: <b style=\'color:#E7EAF0\'>AnDigi insurance — claims + AI triage</b>.</p>",
        unsafe_allow_html=True,
    )
    pipe = " ".join(
        f'<span class="se-id">{p}</span>' + ('<span style="color:#2A3140"> → </span>' if i < 4 else "")
        for i, p in enumerate(["evidence", "gate", "11-agent debate", "corrected spec", "you sign off"])
    )
    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11.5px;margin:2px 0 10px;line-height:2">{pipe}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="se-stats">'
        + stat(f'<span class="from">{g1["overall_score"]} →</span> {g2["overall_score"]} <span class="delta">+{g2["overall_score"] - g1["overall_score"]}</span>', "spec readiness")
        + stat(f'<span class="from">{p0_1} →</span> {p0_2}', "P0 blockers")
        + stat(f'<span class="from">{gate1["errors"]} →</span> {gate2["errors"]}', "gate errors (code-enforced)")
        + stat(f'{len(arbiter["unresolved_human_decisions"])}', "decisions left to the human")
        + stat(esc(g2["verdict"].replace("_", " ").lower()), "verdict")
        + "</div>",
        unsafe_allow_html=True,
    )
    n_turns = len(s["debate"]["turns"])
    pc1, pc2, pc3, _ = st.columns([2.2, 2, 1, 2])
    if pc1.button(f"▶ Watch the agents work · {n_turns} turns", type="primary", use_container_width=True):
        st.session_state["playback"] = True
    if pc2.button("🧪 Test the shipped feature", use_container_width=True):
        st.session_state["show_feature_top"] = True
    speed = pc3.selectbox("speed", ["2×", "1×", "4×"], label_visibility="collapsed")
    st.markdown(f'<p class="se-trace">{esc(run["meta"].get("note", ""))[:110]}</p>', unsafe_allow_html=True)
    if st.session_state.pop("playback", False):
        render_playback(run, {"1×": 32, "2×": 64, "4×": 128}[speed])
    if st.session_state.pop("show_feature_top", False):
        render_shipped_feature(run)

    # ---- catch 1: the evidence conflict ------------------------------------
    theme.section("catch 01", "The policy forbids what the spec promises", "truth-hierarchy conflict")
    c1 = next((c for c in s["conflicts"]["conflicts"] if c["kind"] == "business-rule"), None)
    if c1:
        win = find_claim(run, c1["winning_claim_id"])
        lose_id = next((cid for cid in c1["claim_ids"] if cid != c1["winning_claim_id"]), "")
        lose = find_claim(run, lose_id)
        inner = ""
        if win:
            inner += f'<div class="se-vs">WINS BY AUTHORITY — {esc(win["authority"])}</div>' + source_quote_html(win["sources"][0])
        if lose:
            inner += f'<div class="se-vs">LOSES — BUT AUDITORS READ THIS ({esc(lose["authority"])})</div>' + source_quote_html(lose["sources"][0])
        summary = (
            f'<div class="chead"><span class="cnum">{esc(c1["id"])}</span>'
            f'<span class="ctitle">CEO says auto-approve · policy 4.1 says human review</span>'
            + ('<span class="se-chip" style="border-color:#F2A65A;color:#F2A65A">⚑ human decision</span>' if c1["needs_human_confirmation"] else "")
            + "</div>"
        )
        st.markdown(f'<div class="se-catch">{summary}</div>', unsafe_allow_html=True)
        with st.expander("view receipt — both sources, verbatim"):
            st.markdown(inner + f'<div class="se-body" style="margin-top:8px">{esc(c1["resolution"])}</div>', unsafe_allow_html=True)

    # ---- catch 2: the invented regulation ----------------------------------
    theme.section("catch 02", "A confident, invented regulation", "P0 · grounding")
    f1 = next((f for f in g1["findings"] if f["priority"] == "P0"), None)
    if f1:
        ev = find_claim(run, f1["evidence_ref"])
        comp_turn = next((t for t in s["debate"]["turns"] if t["role"] == "compliance"), None)
        st.markdown(
            f'<div class="se-catch"><div class="chead"><span class="cnum">{esc(f1["id"])} · P0</span>'
            f'<span class="ctitle">“Circular 14/2026” does not exist — the spec invented a regulation</span>'
            f'<span class="se-summon" style="margin:0">⚡ Compliance summoned</span></div></div>',
            unsafe_allow_html=True,
        )
        with st.expander("view receipt — the corpus says the opposite"):
            inner = f'<div class="se-body">{esc(f1["description"])}</div>'
            inner += f'<div class="se-trace">claim-class violation: {esc(f1["claim_class_violation"])} · requirement {esc(f1["requirement_id"])}</div>'
            if ev:
                inner += '<div class="se-vs">THE CORPUS SAYS THE OPPOSITE</div>' + source_quote_html(ev["sources"][0])
            st.markdown(inner, unsafe_allow_html=True)
            if comp_turn:
                st.markdown(turn_html(comp_turn), unsafe_allow_html=True)

    # ---- catch 3: code disagrees with the promise --------------------------
    theme.section("catch 03", "The code disagrees with the promise", "artifact-state gap")
    c2 = next((c for c in s["conflicts"]["conflicts"] if c["kind"] == "artifact-state-gap"), None)
    if c2:
        intended = find_claim(run, c2["winning_claim_id"])
        artifacts = [find_claim(run, cid) for cid in c2["claim_ids"]]
        artifacts = [a for a in artifacts if a and a["claim_class"] == "artifact-state"]
        st.markdown(
            f'<div class="se-catch"><div class="chead"><span class="cnum">{esc(c2["id"])}</span>'
            f'<span class="ctitle">Spec promises 48h payout · code pays in 5 days</span>'
            f'<span class="se-chip">sla.py:5 · DB default 5</span></div></div>',
            unsafe_allow_html=True,
        )
        with st.expander("view receipt — intended vs artifact state"):
            inner = ""
            if intended:
                inner += f'<div class="se-vs">THE INTENDED BEHAVIOR ({esc(intended["authority"])})</div>' + source_quote_html(intended["sources"][0])
            for a in artifacts:
                inner += '<div class="se-vs">WHAT THE SYSTEM ACTUALLY DOES (artifact state — cannot be out-talked)</div>' + source_quote_html(a["sources"][0])
            inner += f'<div class="se-body" style="margin-top:8px">{esc(c2["resolution"])}</div>'
            st.markdown(inner, unsafe_allow_html=True)

    # ---- gate strip ---------------------------------------------------------
    theme.section("the gate", "Code-enforced. Models cannot override these results.", f'{gate1["errors"]} errors → {gate2["errors"]}')
    chips = " ".join(f'<span class="se-chip" style="border-color:{"#F85149" if h["severity"] == "error" else "#F2A65A"};color:{"#F85149" if h["severity"] == "error" else "#F2A65A"};margin-left:0">{esc(h["rule_id"])} {esc(h["requirement_id"])}</span>' for h in gate1["hits"])
    st.markdown(f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">{chips}</div>', unsafe_allow_html=True)
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

    # ---- the human: Decision Console ----------------------------------------
    render_console(run)

    # ---- finale: the spec ships ----------------------------------------------
    render_shipped_feature(run)

    # ---- depth ----------------------------------------------------------------
    st.write("")
    theme.section("depth", "For the technical reviewer", "")
    with st.expander("🔍 Inspect the full run — gate, D1-D5 grading, 11-role debate, evidence"):
        render_trace(run)
    with st.expander("⚙ How it works — architecture, budget, eval-log"):
        render_how(run)



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
FRAUD_KEYWORDS = ["staged", "fake", "collusion", "pre-arranged", "insurance fraud", "witness paid"]


def render_shipped_feature(run: dict) -> None:
    theme.section("the spec ships", "Executable acceptance-test slice — pure code, every path cites the baseline",
                  "no model at runtime")
    st.markdown('<p class="se-trace">built from the signed spec · every verdict cites its requirement · try to break it</p>', unsafe_allow_html=True)
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
        precond = c4.checkbox("Policy 4.1 amended (simulates your C1 ruling)", value=precond)
        go = st.form_submit_button("Submit FNOL → run triage", type="primary")

    if not go:
        return
    trace = {"amount_vnd": amount, "policy": policy, "photo": photo, "precondition_met": precond, "description": desc}

    def verdict(kind, title, body, cite):
        color = {"approve": "#3FB950", "reject": "#F85149", "human": "#F2A65A"}[kind]
        st.markdown(
            f'<div class="se-catch" style="border-left-color:{color}">'
            f'<div class="chead"><span class="cnum" style="color:{color}">{esc(title)}</span></div>'
            f'<div class="se-body">{esc(body)}</div>'
            f'<div class="se-trace">{esc(cite)}</div></div>',
            unsafe_allow_html=True,
        )
        trace["verdict"] = title

    if policy == "lapsed":
        verdict("reject", "REJECTED — lapsed policy",
                "Submission rejected with the lapse reason. This rejection IS R1-AC2.",
                "executes R1-AC2 · born from W1 (CEO: customers file the loss in the app) · localized copy per UX turn (F9)")
    elif not photo:
        verdict("reject", "BLOCKED — no photo attached",
                "FNOL requires at least one photo before a claim record is created.",
                "executes R1-AC1 · born from W1")
    elif any(k in desc.lower() for k in FRAUD_KEYWORDS):
        verdict("human", "ASSIGNED TO HUMAN INVESTIGATOR",
                "The AI never clears its own fraud flag. Investigator receives a redacted ticket; "
                "full payload is RBAC-gated and access-logged. Record retained ten years.",
                "executes R4-AC1/AC2 · born from W6, W7 · redaction per Security turn (F11) · flag immutable once set")
    elif amount < 5_000_000 and precond:
        verdict("approve", "INSTANT APPROVED — payout due in 48:00:00",
                "No human in the path (launch precondition met). Exactly one disbursement per claim id, "
                "measured approved_at → paid_at; a structured decision_event was emitted to the audit log.",
                "executes R2-AC1 · born from W2/W3 · idempotency per Eng turn (F4) · audit event per DevOps turn (F10) · 48h bound per QA turn (F3)")
    elif amount < 5_000_000:
        verdict("human", "ROUTED TO HUMAN ADJUSTER — precondition unmet",
                "Policy 4.1 is not yet amended, so the manual-review fallback applies until your launch "
                "precondition is satisfied.",
                "executes the R2 amendment (F2) · your C1 ruling is the gate")
    else:
        verdict("human", "ROUTED TO HUMAN ADJUSTER — decision within 3 business days",
                "High-value claims get a human decision; escalates to claims ops on breach.",
                "executes R6-AC1/AC2 · born from W8")
    st.download_button("⬇ Download execution trace (test vector)", json.dumps(trace, indent=2), "fnol-trace.json")
    st.markdown(
        '<p class="se-trace">100% deterministic Python — no model ran. The rules this simulator enforces '
        "are the signed corrected spec of this run plus your Decision Console rulings.</p>",
        unsafe_allow_html=True,
    )


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
                st.markdown(f'<div class="se-flag" style="display:block">⚑ {esc(d)}</div>', unsafe_allow_html=True)
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
                f'<span class="se-chip" style="border-color:{"#F85149" if rule.severity == "blocking" else "#9AA3B2"}">{esc(rule.severity)}</span></div>'
                f'<div class="se-body">{esc(rule.rule_text)}</div>'
                f'<div class="se-trace">born from: {esc(rule.born_item)} · by you · {esc(rule.born_date)}</div>'
            )
            approvals.append(st.checkbox(f"Approve {rule.id}", value=True, key=f"appr_{rule.id}"))
        if st.button("✍ Approve baseline & create handoff", type="primary"):
            approved = [r for r, ok in zip(proposed, approvals) if ok]
            ledger.commit_rules(approved)
            signoff = {
                "status": "complete", "baseline_id": handoff.baseline_id(),
                "signed_at": time.strftime("%Y-%m-%d %H:%M"), "by": "you",
                "rulings": draft["rulings"], "reviews": draft["reviews"],
                "rules_approved": [r.id for r in approved],
            }
            run["signoff"] = signoff
            seq = len(run["events"])
            for i, r in enumerate(draft["rulings"]):
                run["events"].append({"seq": seq + i + 1, "type": "decision_ruled", "choice": r["choice"]})
            run["events"].append({"seq": len(run["events"]) + 1, "type": "signoff_completed",
                                   "baseline": signoff["baseline_id"], "rules": signoff["rules_approved"]})
            run["lifecycle"].append({"state": "shipped", "note": signoff["baseline_id"]})
            save_run(run, f"signed-{time.strftime('%Y%m%d-%H%M%S')}")
            st.session_state["signoff"] = signoff
            st.session_state["signoff_state"] = "signed"
            st.rerun()
        if st.button("← Back to rulings"):
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
    c1.download_button("⬇ Signed spec (MD)", handoff.signed_spec_md(run, signoff), "signed-spec.md")
    c2.download_button("⬇ Decision record", handoff.decision_record_md(run, signoff), "decision-record.md")
    c3.download_button("⬇ Jira/Linear stubs", handoff.ticket_stubs_md(run, signoff), "ticket-stubs.md")

    # ---- the compounding proof: rules fire on the NEXT draft -----------------
    theme.section("the loop", "Your judgment, applied to the next draft", "preflight · pure code")
    if st.button("⚡ Preflight the next AnDigi draft (v1.1) with your rules"):
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

    with st.expander("⏳ Decision Time Machine — what if you ruled differently on C1?"):
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
    order = ["draft", "graded", "advisor", "sign-off", "shipped"]
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
                f'<div class="se-gatehit"><span class="{ "rid" if c["result"] == "FAIL" else "" }" style="color:{"#F85149" if c["result"] == "FAIL" else "#3FB950"}">'
                f'{ "✗" if c["result"] == "FAIL" else "✓"} {esc(c["dimension"])}</span> {esc(c["item"])}'
                + (f' — <i>{esc(c["note"])}</i>' if c["note"] else "") + "</div>"
                for c in g["checklist"]
            )
            theme.card(checks)
            for f in g["findings"]:
                color = {"P0": "#F85149", "P1": "#F2A65A", "P2": "#9AA4B2"}[f["priority"]]
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
                color = {"S0": "#F85149", "S1": "#F2A65A", "S2": "#9AA4B2"}[item["severity"]]
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
        "⬇ Download the full run (eval-log JSON)",
        data=json.dumps(run, indent=2, ensure_ascii=False),
        file_name="knowledge-engine-run.json",
        mime="application/json",
    )


# ---------------------------------------------------------------- live mode
def render_live() -> None:
    llm = LLM(api_key=api_key, model=model, base_url=base_url)
    status_area = st.container()
    stream_area = st.container()
    boxes: dict = {}
    typing = {"ph": None, "buf": ""}

    titles = {"wiki": "Evidence → wiki", "conflicts": "Conflict check", "gate": "Code gate",
              "grade": "Grading round 1", "debate": "Role debate", "regrade": "Re-grade", "advisor": "Advisor"}

    def on_progress(stage: str, state: str) -> None:
        if state == "start":
            boxes[stage] = status_area.status(titles.get(stage, stage), state="running")
        elif stage in boxes:
            boxes[stage].update(label=f"{titles.get(stage, stage)} — done · {llm.usage.total:,} tokens burned", state="complete")

    def on_event(ev: dict) -> None:
        if ev["type"] == "turn_start":
            typing["ph"] = stream_area.empty()
            typing["buf"] = f"**{team.role_label(ev['role'])}** is thinking…\n\n"
            typing["ph"].markdown(typing["buf"])
        elif ev["type"] == "turn" and typing["ph"] is not None:
            typing["ph"].markdown(turn_html(ev), unsafe_allow_html=True)
            typing["ph"] = None
        elif ev["type"] == "no_objection":
            stream_area.markdown(f'<div class="se-noobj">{esc(team.role_label(ev["role"]))} — no objection (0 tokens)</div>', unsafe_allow_html=True)
        elif ev["type"] == "router" and not ev.get("close_phase"):
            stream_area.markdown(f'<p class="se-trace">router → {esc(ev["focused_question"])}</p>', unsafe_allow_html=True)

    def on_text(ch: str) -> None:
        if typing["ph"] is not None:
            typing["buf"] += ch
            typing["ph"].markdown(typing["buf"] + "▌")

    try:
        run = run_pipeline(llm, on_progress, on_event, on_text)
    except Exception as err:  # surface provider errors readably
        st.error(f"Run failed: {err}")
        st.stop()

    import time as _time
    name = f"live-{_time.strftime('%Y%m%d-%H%M%S')}"
    save_run(run, name)
    st.success(f"Run complete — saved as {name}.json. Rendering the catch view…")
    render_hero(run)


# ---------------------------------------------------------------- routing
if run_live and api_key:
    render_live()
elif chosen:
    render_hero(load_run(chosen))
else:
    st.error("No recorded runs found in data/runs/ — run scripts/make_demo_run.py first.")
