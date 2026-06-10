"""Structured-output schemas for every pipeline stage.

These pydantic models are passed to `client.messages.parse(output_format=...)`
so the API guarantees valid, parseable JSON at each stage.
"""

from pydantic import BaseModel, Field


# ---- Stage 1: transcript -> source-traced wiki ----------------------------

class SourceRef(BaseModel):
    transcript: str = Field(description="Filename of the transcript this claim comes from")
    speaker: str = Field(description="Who said it")
    quote: str = Field(description="Short verbatim quote backing the claim")


class WikiClaim(BaseModel):
    id: str = Field(description="Stable id like W1, W2, ...")
    topic: str = Field(description="Short topic label, e.g. 'Deposits', 'Cancellation'")
    claim: str = Field(description="One atomic, declarative statement of fact or decision")
    authority: str = Field(
        description="Authority level of the source, one of the levels in the truth hierarchy"
    )
    sources: list[SourceRef]


class Wiki(BaseModel):
    project_summary: str = Field(description="2-3 sentence summary of what is being built")
    claims: list[WikiClaim]


# ---- Stage 2: truth-hierarchy conflict check -------------------------------

class Conflict(BaseModel):
    id: str = Field(description="Stable id like C1, C2, ...")
    claim_ids: list[str] = Field(description="Ids of the wiki claims that contradict each other")
    description: str = Field(description="What the contradiction is, in one or two sentences")
    winning_claim_id: str = Field(
        description="The claim that wins under the truth hierarchy"
    )
    winning_authority: str = Field(description="Authority level of the winning claim")
    resolution: str = Field(
        description="How the spec should resolve this, and what to confirm with humans"
    )
    needs_human_confirmation: bool = Field(
        description="True when the hierarchy resolves it but a human should still confirm"
    )


class ConflictReport(BaseModel):
    conflicts: list[Conflict]
    notes: str = Field(description="Anything reviewed and found NOT to be in conflict")


# ---- Stage 3: spec draft ----------------------------------------------------

class Requirement(BaseModel):
    id: str = Field(description="Stable id like R1, R2, ...")
    title: str
    statement: str = Field(
        description="Single testable requirement statement, active voice, no hedging"
    )
    acceptance_criteria: list[str] = Field(
        description="Given/When/Then style criteria, each independently verifiable"
    )
    source_claim_ids: list[str] = Field(
        description="Wiki claim ids this requirement traces back to"
    )


class SpecDraft(BaseModel):
    feature_name: str
    summary: str
    out_of_scope: list[str]
    requirements: list[Requirement]


# ---- Stage 4: automated spec grading ---------------------------------------

class RequirementGrade(BaseModel):
    requirement_id: str
    clarity: int = Field(description="0-5: unambiguous, active voice, no vague quantities")
    source_coverage: int = Field(
        description="0-5: every assertion traces to a wiki claim with a real source"
    )
    testability: int = Field(description="0-5: acceptance criteria are independently verifiable")
    issues: list[str] = Field(description="Concrete problems found; empty when clean")
    verdict: str = Field(description="'ship' or 'revise'")


class GradeReport(BaseModel):
    grades: list[RequirementGrade]
    overall_score: int = Field(description="0-100 weighted overall score for the spec")
    blocking_issues: list[str] = Field(
        description="Issues that must be fixed before engineering handoff"
    )
