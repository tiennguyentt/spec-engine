"""Stage 5: autonomous role debate.

Three role agents argue over the drafted spec — Eng Lead attacks feasibility,
QA attacks testability, the PO defends or concedes with concrete amendments.
They run automatically, turn by turn, for a fixed number of rounds; an
arbiter then issues per-requirement rulings. Every turn is one structured
LLM call, so the whole debate works on cheap models.
"""

from collections.abc import Callable

from engine.llm import LLM
from engine.schemas import DebateOutcome, GradeReport, SpecDraft, TurnContent, Wiki

ROLES = {
    "eng": {
        "label": "Eng Lead",
        "system": (
            "You are the Engineering Lead in a spec debate. Attack feasibility: "
            "hidden complexity, race conditions, missing failure paths, integration "
            "risk, anything underspecified to implement. Reference specific "
            "requirement ids. Max 120 words. If a previous defense genuinely "
            "resolves your point, concede it and move to your next strongest attack. "
            "Never repeat an argument already made."
        ),
    },
    "qa": {
        "label": "QA Lead",
        "system": (
            "You are the QA Lead in a spec debate. Attack testability: vague or "
            "invented quantities, acceptance criteria that cannot be independently "
            "verified, missing negative paths, undefined rounding/boundary rules. "
            "Reference specific requirement ids. Max 120 words. Concede points that "
            "have been genuinely resolved. Never repeat an argument already made."
        ),
    },
    "po": {
        "label": "Product Owner",
        "system": (
            "You are the Product Owner in a spec debate. Triage the standing "
            "challenges: defend requirements that are right as written, concede the "
            "ones that are not, and for every concession propose a concrete "
            "amendment (exact behavior, numbers, bounds). Stay loyal to the wiki "
            "ground truth and the truth hierarchy. Max 120 words."
        ),
    },
}

TURN_ORDER = ["eng", "qa", "po"]

ARBITER_SYSTEM = (
    "You are the neutral arbiter of a spec debate. Rule on every requirement id: "
    "'accept' as written, 'amend' with the exact amendment text (synthesize the "
    "best version from the debate), or 'reject'. Ground every ruling in the "
    "debate transcript and the wiki ground truth only."
)

OnTurn = Callable[[dict], None]


def _transcript(turns: list[dict]) -> str:
    if not turns:
        return "(debate has not started)"
    return "\n\n".join(
        f"[round {t['round']}] {ROLES[t['role']]['label']} ({t['stance']}): {t['message']}"
        for t in turns
    )


def run_debate(
    llm: LLM,
    wiki: Wiki,
    spec: SpecDraft,
    grades: GradeReport,
    rounds: int = 2,
    on_turn: OnTurn | None = None,
) -> dict:
    context = (
        f"WIKI (ground truth):\n{wiki.model_dump_json(indent=2)}\n\n"
        f"SPEC UNDER DEBATE:\n{spec.model_dump_json(indent=2)}\n\n"
        f"GRADER FINDINGS:\n{grades.model_dump_json(indent=2)}"
    )

    turns: list[dict] = []
    for rnd in range(1, rounds + 1):
        for role in TURN_ORDER:
            content = llm.complete_json(
                system=ROLES[role]["system"],
                user=(
                    f"{context}\n\nDEBATE SO FAR:\n{_transcript(turns)}\n\n"
                    f"This is round {rnd} of {rounds}. Make your strongest move now."
                ),
                schema=TurnContent,
            )
            turn = {"round": rnd, "role": role, **content.model_dump()}
            turns.append(turn)
            if on_turn:
                on_turn(turn)

    outcome = llm.complete_json(
        system=ARBITER_SYSTEM,
        user=f"{context}\n\nFULL DEBATE:\n{_transcript(turns)}\n\nIssue your rulings.",
        schema=DebateOutcome,
    )
    return {"turns": turns, "outcome": outcome.model_dump()}
