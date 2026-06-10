"""The four LLM stages of the spec engine.

Each stage is one structured call: prompt in, schema-validated object out.
The truth hierarchy is injected wherever authority matters.
"""

from engine.llm import LLM
from engine.schemas import ConflictReport, GradeReport, SpecDraft, Wiki

TRUTH_HIERARCHY = """\
Truth hierarchy (highest authority first). When sources disagree, the higher
level wins, and the conflict must still be flagged - never silently dropped:
1. CTO decision           - explicit decisions stated by the CTO
2. Written policy/contract - signed documents and published policy
3. Ops lead statement     - operational practice described by the ops lead
4. Team anecdote          - individual recollections, support stories
"""


def build_wiki(llm: LLM, transcripts: dict[str, str]) -> Wiki:
    corpus = "\n\n".join(
        f"=== TRANSCRIPT: {name} ===\n{text}" for name, text in transcripts.items()
    )
    return llm.complete_json(
        system=(
            "You compile raw meeting transcripts into a source-traced project wiki. "
            "Extract every atomic decision, constraint, and fact as a separate claim. "
            "Each claim must carry a verbatim quote and its speaker - a claim without "
            "a source does not exist. Assign each claim an authority level using the "
            f"hierarchy below.\n\n{TRUTH_HIERARCHY}"
        ),
        user=corpus,
        schema=Wiki,
    )


def check_conflicts(llm: LLM, wiki: Wiki) -> ConflictReport:
    return llm.complete_json(
        system=(
            "You are the conflict checker of a spec pipeline. Compare every pair of "
            "wiki claims and report contradictions - direct or implied. Resolve each "
            "conflict strictly by the truth hierarchy, name the winning claim, and "
            "flag it for human confirmation when the losing source reflects current "
            f"real-world practice.\n\n{TRUTH_HIERARCHY}"
        ),
        user=wiki.model_dump_json(indent=2),
        schema=ConflictReport,
    )


def draft_spec(llm: LLM, wiki: Wiki, conflicts: ConflictReport) -> SpecDraft:
    return llm.complete_json(
        system=(
            "You draft engineering-ready functional specs. Every requirement must "
            "trace to wiki claim ids, follow conflict resolutions exactly, use active "
            "voice, and avoid vague quantities (no 'fast', 'some', 'user-friendly'). "
            "Acceptance criteria are Given/When/Then and independently testable. "
            "List explicit out-of-scope items so engineering asks zero follow-ups."
        ),
        user=(
            f"WIKI:\n{wiki.model_dump_json(indent=2)}\n\n"
            f"CONFLICT RESOLUTIONS:\n{conflicts.model_dump_json(indent=2)}"
        ),
        schema=SpecDraft,
    )


def grade_spec(llm: LLM, wiki: Wiki, spec: SpecDraft) -> GradeReport:
    return llm.complete_json(
        system=(
            "You are an adversarial spec grader. Your job is to find problems, not "
            "to be agreeable. Grade each requirement 0-5 on clarity, source coverage "
            "(does every assertion trace to a real wiki claim?), and testability. "
            "Report every issue you find, including low-severity ones - a human "
            "reviewer filters them later. Verdict 'revise' whenever any dimension "
            "scores 3 or below."
        ),
        user=(
            f"WIKI (ground truth):\n{wiki.model_dump_json(indent=2)}\n\n"
            f"SPEC TO GRADE:\n{spec.model_dump_json(indent=2)}"
        ),
        schema=GradeReport,
    )
