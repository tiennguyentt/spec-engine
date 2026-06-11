"""Engine tests — pure code, no model calls, deterministic.

Covers the claims the README makes: the gate catches the planted defects,
detection recall is measured honestly, the compiled baseline flips behavior
with a ruling, standards mapping covers every rule, and the evidence pack
matches its drift snapshot.
"""

import copy
import json
from pathlib import Path

import pytest

from engine import drift, evals, standards
from engine.compiler import acceptance_vectors, compile_baseline, evaluate, run_acceptance
from engine.gate import RULES, run_gate
from engine.pipeline import DATA_DIR, load_evidence

DEMO_RUN = DATA_DIR / "runs" / "demo-andigi.json"


@pytest.fixture(scope="module")
def run() -> dict:
    return json.loads(DEMO_RUN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def andigi_spec():
    _, spec = load_evidence()
    return spec


def test_gate_catches_planted_defects(andigi_spec):
    report = run_gate(andigi_spec)
    hits = {(h["rule_id"], h["requirement_id"]) for h in report.hits}
    assert ("G1", "R2") in hits  # hedge word
    assert ("G2", "R2") in hits  # vague quantity
    assert ("G7", "R3") in hits  # zero provenance
    assert ("G6", "R5") in hits  # untagged tech prescription
    assert report.errors >= 5


def test_detection_recall_is_full_on_demo_run(run):
    report = evals.score_run(run)
    assert report["caught"] == report["total"] == 10
    assert report["recall"] == 1.0


def test_detection_recall_reports_misses_honestly(run):
    gutted = copy.deepcopy(run)
    gutted["stages"]["grade_round1"]["findings"] = []
    gutted["stages"]["grade_round2"]["findings"] = []
    gutted["stages"]["conflicts"]["conflicts"] = [
        c for c in gutted["stages"]["conflicts"]["conflicts"] if c["kind"] != "business-rule"
    ]
    report = evals.score_run(gutted)
    missed = [d["id"] for d in report["defects"] if not d["caught"]]
    assert missed == ["GT5", "GT7", "GT8", "GT9", "GT10"]
    assert report["recall"] == 0.5


def test_standards_mapping_covers_every_gate_rule():
    mapped = set(standards.GATE_TO_INCOSE)
    assert set(RULES).issubset(mapped)          # G1-G6 from the regex table
    assert {"G7", "G8"}.issubset(mapped)        # structural rules


def test_corrected_spec_acs_are_given_when_then(run):
    report = standards.alignment_report(run)
    assert report["acs_total"] > 0
    assert report["acs_gwt"] == report["acs_total"]


def test_compiled_baseline_flips_with_ruling(run):
    clean_claim = {"amount": 3_800_000, "policy": "active", "photo": True,
                   "precondition": True, "description": "fender dent"}

    table_a = compile_baseline(run, {"baseline_id": "BL-A", "rulings": []}, [])
    assert table_a.auto_approval_enabled
    assert evaluate(table_a, clean_claim).verdict == "approve"
    assert all(r["passed"] for r in run_acceptance(table_a))

    reversal = {"baseline_id": "BL-B", "rulings": [
        {"decision_text": "the published policy wins", "choice": "Reverse: human review every claim"}]}
    table_b = compile_baseline(run, reversal, [])
    assert not table_b.auto_approval_enabled
    assert table_b.version == 2
    assert evaluate(table_b, clean_claim).verdict == "review"
    assert all(r["passed"] for r in run_acceptance(table_b))

    # the old baseline's auto-approve vector is incompatible with the new table
    old_vector = next(v for v in acceptance_vectors(table_a) if v["id"] == "V-R2-AC1")
    assert evaluate(table_b, old_vector["claim"]).verdict != old_vector["expect"]


def test_evidence_matches_drift_snapshot(run):
    deltas = drift.check(run)
    assert [d["kind"] for d in deltas] == ["ok"], deltas


def test_evidence_only_pack_loads_without_spec(tmp_path: Path):
    (tmp_path / "transcript-meeting.md").write_text("# Meeting\nCEO: ship it.\n", encoding="utf-8")
    sources, spec = load_evidence(tmp_path)
    assert spec is None  # pipeline will synthesize the draft from the wiki
    assert "transcript-meeting.md" in sources


def test_byo_evidence_dir_loads_and_gates(tmp_path: Path):
    src = DATA_DIR / "andigi" / "draft-spec.json"
    (tmp_path / "draft-spec.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "transcript-kickoff.md").write_text("# Kickoff\nCEO: ship it fast.\n", encoding="utf-8")
    sources, spec = load_evidence(tmp_path)
    assert sources["transcript-kickoff.md"]["type"] == "transcript"
    assert run_gate(spec).errors >= 5
