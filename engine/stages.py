"""Evidence and grading stages (v2 — red-team flow).

Each stage is one structured call: prompt in, schema-validated object out.
The truth hierarchy is injected wherever authority matters.
"""

from engine.llm import LLM
from engine.schemas import AdvisorReport, ConflictReport, DraftSpec, GradeReport, Wiki

TRUTH_HIERARCHY = """\
Truth hierarchy. Two categories of truth, never to be confused:

BUSINESS RULES (what the system SHOULD do) - higher authority wins, conflicts
must still be flagged, never silently dropped:
1. CEO/CTO decision        - explicit decisions stated by the decision-maker
2. Written policy/contract - signed documents and published policy
3. Ops statement           - operational practice described by leads
4. Anecdote                - individual recollections, support stories

ARTIFACT STATE (what the system CURRENTLY does) - code and database are
absolute facts about current behavior; no spoken claim can override them.
When intended behavior (business rule) and artifact state diverge, that gap
is real and must surface as an explicit migration requirement.
"""

CLAIM_CLASSES = """\
Every claim carries exactly one claim_class:
- fact: verifiable statement traced to a source
- decision: an authority chose this; traced to who and when
- domain-assumption: plausible domain knowledge without a source in the corpus
- regulatory-assumption: legal/regulatory statement NOT traced to a source in
  the corpus - these are dangerous and must be flagged for verification
- recommendation: an agent's suggestion, not ground truth
- artifact-state: extracted from code or database; absolute for current behavior
"""


def build_wiki(llm: LLM, sources: dict[str, dict]) -> Wiki:
    corpus = "\n\n".join(
        f"=== SOURCE: {name} (type: {meta['type']}) ===\n{meta['text']}"
        for name, meta in sources.items()
    )
    return llm.complete_json(
        system=(
            "You compile heterogeneous evidence (meeting transcripts, policy "
            "documents, source code, database schemas) into a source-traced "
            "project wiki. Extract every atomic decision, constraint, fact and "
            "current-behavior observation as a separate claim. Each claim must "
            "carry source_file, source_type, a locator (line/section/table) and "
            "a verbatim quote or code snippet - a claim without a source does "
            "not exist. Code and DB claims get authority 'Artifact state' and "
            f"claim_class 'artifact-state'.\n\n{TRUTH_HIERARCHY}\n{CLAIM_CLASSES}"
        ),
        user=corpus,
        schema=Wiki,
    )


def draft_from_wiki(llm: LLM, wiki: Wiki) -> DraftSpec:
    """No draft spec provided: synthesize one STRICTLY from the wiki, then red-team it."""
    return llm.complete_json(
        system=(
            "You are a senior product analyst. Draft a feature spec strictly "
            "from the wiki claims provided - nothing else exists. Every "
            "requirement must list the claim ids it derives from in "
            "source_claim_ids; if the evidence is silent on something, put it "
            "in out_of_scope instead of inventing it. Acceptance criteria must "
            "be testable Given/When/Then with explicit numbers. State exact "
            "behaviors in active voice; no hedge words (should/may), no vague "
            "timing (promptly/quickly), no untagged implementation choices."
        ),
        user=wiki.model_dump_json(indent=2),
        schema=DraftSpec,
    )


def check_conflicts(llm: LLM, wiki: Wiki) -> ConflictReport:
    return llm.complete_json(
        system=(
            "You are the conflict checker. Compare every pair of wiki claims "
            "and report contradictions of BOTH kinds: 'business-rule' (spoken/"
            "written intents disagree - resolve by the hierarchy, flag for "
            "human confirmation when practice diverges from policy) and "
            "'artifact-state-gap' (an intended behavior disagrees with what "
            "code/DB currently does - the winning claim is the INTENDED "
            "behavior, and the resolution must demand an explicit migration "
            f"requirement).\n\n{TRUTH_HIERARCHY}"
        ),
        user=wiki.model_dump_json(indent=2),
        schema=ConflictReport,
    )


GRADER_SYSTEM = """\
You are the adversarial Grading Lead of a spec red team. Your job is to find
problems, not to be agreeable. Grade the draft spec against the wiki (ground
truth), the conflict report, and the deterministic gate results, on five
dimensions, each as concrete checklist items with PASS/FAIL:

D1 Direction Coverage: every source requirement/decision addressed; no silent
   claim drops; conflict resolutions reflected.
D2 Expert Translation: >=3 edge cases beyond sources; failure path per major
   requirement; measurable success criteria.
D3 Grounding Discipline: every domain fact traces to a claim id; no invented
   numbers or SLAs; regulatory claims MUST trace to a source in the corpus or
   be tagged as assumptions needing verification - an untraced regulatory
   claim is always P0 with claim_class_violation 'regulatory-assumption
   without source' and assigned_role 'compliance'.
D4 Scope Discipline: explicit out-of-scope; no unplanned dependencies.
D5 Dev-Readiness: testable ACs; explicit numbers; no hedge words; active voice.

Each FAIL becomes a typed finding with priority (P0 blocks ship: grounding/
compliance; P1: a dev would ask; P2: polish), an evidence_ref, a suggested_fix
and the role best placed to argue it. Score each dimension 0-100, overall
0-100. Verdict: SATISFIED (no findings), SATISFIED_WITH_DEFERRED (only P2),
NEEDS_REVISION (any P0/P1). Gate errors always force NEEDS_REVISION.
Report everything you find - a human filters later.
"""


def grade_spec(llm: LLM, wiki: Wiki, conflicts: ConflictReport, spec: DraftSpec, gate_dict: dict, round_no: int) -> GradeReport:
    return llm.complete_json(
        system=GRADER_SYSTEM,
        user=(
            f"GRADING ROUND: {round_no}\n\n"
            f"WIKI (ground truth):\n{wiki.model_dump_json(indent=2)}\n\n"
            f"CONFLICTS:\n{conflicts.model_dump_json(indent=2)}\n\n"
            f"DETERMINISTIC GATE RESULT (code-enforced, cannot be overridden):\n{gate_dict}\n\n"
            f"DRAFT SPEC TO GRADE:\n{spec.model_dump_json(indent=2)}"
        ),
        schema=GradeReport,
    )


def advise(llm: LLM, spec: DraftSpec, grade: GradeReport) -> AdvisorReport:
    return llm.complete_json(
        system=(
            "You are a senior product advisor reviewing AFTER grading. You "
            "never block - the human decides. Evaluate: framing altitude, "
            "alternatives visibility, tradeoff surfacing, risk asymmetry "
            "(compliance/revenue/trust risks elevated over polish), industry "
            "pattern match, scope boundary clarity. Severity: S0 = reframe "
            "recommended before ship, S1 = the owner should consider, S2 = "
            "minor polish."
        ),
        user=(
            f"SPEC (post-amendment):\n{spec.model_dump_json(indent=2)}\n\n"
            f"GRADE: overall {grade.overall_score}, verdict {grade.verdict}"
        ),
        schema=AdvisorReport,
    )
