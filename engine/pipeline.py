"""Red-team pipeline orchestration + eval-log (v2).

Flow: evidence -> wiki -> conflicts -> deterministic GATE -> grade round 1
-> phase-gated debate (once) -> amendments applied -> re-grade -> advisor.
Lifecycle: draft -> graded (<=3 rounds, else BLOCKED) -> advisor -> sign-off
-> shipped. The run dict (with its append-only eval-log) is plain JSON: it
can be saved, downloaded and replayed without the engine installed.
Sign-off is intentionally NOT automated.
"""

import json
import time
from collections.abc import Callable
from pathlib import Path

from engine import team
from engine.debate import apply_amendments, run_debate
from engine.gate import run_gate
from engine.llm import LLM, BudgetExhausted
from engine.schemas import AmendmentSet, DraftSpec
from engine.stages import TRUTH_HIERARCHY, advise, build_wiki, check_conflicts, draft_from_wiki, grade_spec

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RUNS_DIR = DATA_DIR / "runs"
EVIDENCE_DIR = DATA_DIR / "andigi"

SOURCE_TYPES = {".md": "doc", ".txt": "code", ".sql": "db"}

ProgressCb = Callable[[str, str], None]  # (stage, "start"|"done")


def load_evidence(evidence_dir: Path = EVIDENCE_DIR) -> tuple[dict, DraftSpec | None]:
    """Load typed evidence sources + the draft spec (the red-team target).

    The draft spec is optional: with evidence only, the pipeline synthesizes
    a draft from the wiki and red-teams its own draft."""
    sources: dict[str, dict] = {}
    for p in sorted(evidence_dir.iterdir()):
        if p.name == "draft-spec.json" or p.name.startswith("."):
            continue
        stype = "transcript" if p.name.startswith("transcript") else SOURCE_TYPES.get(p.suffix, "doc")
        if p.suffix == ".py" or p.name.endswith(".py.txt"):
            stype = "code"
        sources[p.name] = {"type": stype, "text": p.read_text(encoding="utf-8")}
    spec_path = evidence_dir / "draft-spec.json"
    spec = (DraftSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
            if spec_path.exists() else None)
    return sources, spec


def list_runs() -> list[Path]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(RUNS_DIR.glob("*.json"), reverse=True)


def load_run(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_run(run: dict, name: str) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{name}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


class _EvalLog:
    """Append-only event log; ground truth for replay."""

    def __init__(self):
        self.events: list[dict] = []
        self._seq = 0

    def append(self, type_: str, **payload) -> None:
        self._seq += 1
        self.events.append({"seq": self._seq, "type": type_, **payload})


def run_pipeline(
    llm: LLM,
    on_progress: ProgressCb | None = None,
    on_event: Callable[[dict], None] | None = None,
    on_text: Callable[[str], None] | None = None,
    evidence_dir: Path = EVIDENCE_DIR,
) -> dict:
    progress = on_progress or (lambda s, st: None)
    log = _EvalLog()
    lifecycle: list[dict] = []
    started = time.time()
    lim = team.limits()
    llm.token_budget = llm.token_budget or lim["token_budget"]

    def set_state(state: str, note: str = "") -> None:
        lifecycle.append({"state": state, "note": note})
        log.append("lifecycle", state=state, note=note)
        if on_event:
            on_event({"type": "lifecycle", "state": state, "note": note})

    sources, draft = load_evidence(evidence_dir)
    set_state("draft", f"loaded {len(sources)} evidence sources"
                       + (" + draft spec" if draft else " — no draft spec, will synthesize one"))
    run: dict = {"meta": {}, "stages": {}, "events": [], "lifecycle": lifecycle,
                 "signoff": {"status": "pending", "by": None}}
    partial_reason = ""

    try:
        progress("wiki", "start")
        wiki = build_wiki(llm, sources)
        log.append("stage_done", stage="wiki", claims=len(wiki.claims))
        progress("wiki", "done")

        if draft is None:
            progress("draft", "start")
            draft = draft_from_wiki(llm, wiki)
            log.append("stage_done", stage="draft", requirements=len(draft.requirements))
            set_state("draft", "synthesized from evidence — every requirement traces to wiki claims")
            run["meta"]["draft_synthesized"] = True
            progress("draft", "done")

        progress("conflicts", "start")
        conflicts = check_conflicts(llm, wiki)
        log.append("stage_done", stage="conflicts", conflicts=len(conflicts.conflicts))
        progress("conflicts", "done")

        progress("gate", "start")
        gate = run_gate(draft).to_dict()
        log.append("gate", **{k: gate[k] for k in ("errors", "warnings", "verdict")})
        progress("gate", "done")

        progress("grade", "start")
        set_state("graded", "round 1 of 3")
        grade1 = grade_spec(llm, wiki, conflicts, draft, gate, round_no=1)
        if gate["errors"] and grade1.verdict != "NEEDS_REVISION":
            grade1.verdict = "NEEDS_REVISION"  # the gate cannot be overridden
        log.append("grade", round=1, overall=grade1.overall_score, verdict=grade1.verdict,
                   p0=sum(1 for f in grade1.findings if f.priority == "P0"))
        progress("grade", "done")

        progress("debate", "start")
        debate = run_debate(llm, wiki, conflicts, draft, grade1.findings,
                            on_event=on_event, on_text=on_text)
        log.append("debate_done", turns=len(debate["turns"]),
                   amendments=len(debate["arbiter"]["amendments"]))
        progress("debate", "done")

        corrected = apply_amendments(draft, AmendmentSet.model_validate(debate["arbiter"]))
        log.append("amendments_applied", count=len(debate["arbiter"]["amendments"]),
                   new_requirements=len(debate["arbiter"]["new_requirements"]))

        progress("regrade", "start")
        set_state("graded", "round 2 of 3 (post-debate re-grade)")
        gate2 = run_gate(corrected).to_dict()
        grade2 = grade_spec(llm, wiki, conflicts, corrected, gate2, round_no=2)
        if gate2["errors"] and grade2.verdict == "SATISFIED":
            grade2.verdict = "SATISFIED_WITH_DEFERRED"
        log.append("grade", round=2, overall=grade2.overall_score, verdict=grade2.verdict,
                   p0=sum(1 for f in grade2.findings if f.priority == "P0"))
        progress("regrade", "done")

        if grade2.verdict == "NEEDS_REVISION":
            set_state("blocked", "round-2 grade still NEEDS_REVISION; round 3 reserved for human-directed revision")
        else:
            progress("advisor", "start")
            set_state("advisor", "")
            advisor = advise(llm, corrected, grade2)
            log.append("advisor", verdict=advisor.verdict,
                       s0=sum(1 for i in advisor.items if i.severity == "S0"))
            progress("advisor", "done")
            run["stages"]["advisor"] = advisor.model_dump()
            set_state("sign-off", "awaiting human")

        run["stages"].update({
            "wiki": wiki.model_dump(),
            "conflicts": conflicts.model_dump(),
            "gate": gate,
            "grade_round1": grade1.model_dump(),
            "debate": debate,
            "corrected_spec": corrected.model_dump(),
            "gate_round2": gate2,
            "grade_round2": grade2.model_dump(),
            "draft_spec": draft.model_dump(),
        })

    except BudgetExhausted as err:
        partial_reason = str(err)
        log.append("budget_exhausted", detail=partial_reason)
        set_state("blocked", partial_reason)

    run["meta"] = {
        "kind": "live",
        "concept": "spec-red-team",
        "model": llm.model,
        "base_url": llm.base_url,
        "duration_seconds": round(time.time() - started, 1),
        "usage": {"input_tokens": llm.usage.input_tokens,
                  "output_tokens": llm.usage.output_tokens},
        "token_budget": llm.token_budget,
        "partial_reason": partial_reason,
        "truth_hierarchy": TRUTH_HIERARCHY,
        "evidence_files": list(sources),
        "gate_version": run["stages"].get("gate", {}).get("gate_version", ""),
    }
    run["events"] = log.events
    return run
