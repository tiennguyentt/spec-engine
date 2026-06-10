"""Detection-recall eval harness (PM-audit P1).

The AnDigi draft spec ships with deliberately planted defects; the ground
truth lives in data/evals/ (outside the evidence pack, so it is never
ingested as a claim and never trips drift). score_run() checks a finished
run against that ground truth and reports, per defect, whether it was
caught and through which channel — gate rule, conflict, or graded finding.

Recall here is honest and narrow: it measures detection of KNOWN planted
defects on this benchmark case, not general defect coverage. Pure code,
no model calls, so it can score scripted and live runs identically.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GROUND_TRUTH_FILE = DATA_DIR / "evals" / "andigi-ground-truth.json"


def load_ground_truth() -> dict:
    return json.loads(GROUND_TRUTH_FILE.read_text())


def _match_gate(expect: dict, gate: dict) -> str | None:
    for h in gate["hits"]:
        if h["rule_id"] == expect["rule_id"] and h["requirement_id"] == expect["requirement_id"]:
            return f'gate {h["rule_id"]} ({h["severity"]}) on {h["requirement_id"]}'
    return None


def _match_conflict(expect: dict, conflicts: list[dict]) -> str | None:
    for c in conflicts:
        if c["kind"] == expect["kind"]:
            return f'conflict {c["id"]} ({c["kind"]})'
    return None


def _match_finding(expect: dict, findings: list[dict]) -> str | None:
    for f in findings:
        if f["requirement_id"] != expect["requirement_id"]:
            continue
        if "priority" in expect and f["priority"] != expect["priority"]:
            continue
        if "dimension" in expect and f["dimension"] != expect["dimension"]:
            continue
        if "keyword" in expect and expect["keyword"].lower() not in f["description"].lower():
            continue
        return f'finding {f["id"]} ({f["priority"]}, {f["dimension"]}) on {f["requirement_id"]}'
    return None


def score_run(run: dict, ground_truth: dict | None = None) -> dict:
    gt = ground_truth or load_ground_truth()
    s = run["stages"]
    findings = s["grade_round1"]["findings"] + s.get("grade_round2", {}).get("findings", [])

    defects = []
    for d in gt["planted_defects"]:
        e = d["expect"]
        if e["channel"] == "gate":
            where = _match_gate(e, s["gate"])
        elif e["channel"] == "conflict":
            where = _match_conflict(e, s["conflicts"]["conflicts"])
        else:
            where = _match_finding(e, findings)
        defects.append({"id": d["id"], "title": d["title"], "channel": e["channel"],
                        "caught": where is not None, "where": where or "MISSED"})

    caught = sum(1 for d in defects if d["caught"])
    return {
        "case": gt["case"],
        "total": len(defects),
        "caught": caught,
        "recall": round(caught / len(defects), 3) if defects else 0.0,
        "defects": defects,
    }


if __name__ == "__main__":
    import sys

    run_file = sys.argv[1] if len(sys.argv) > 1 else str(DATA_DIR / "runs" / "demo-andigi.json")
    report = score_run(json.loads(Path(run_file).read_text()))
    print(f'{report["case"]}: {report["caught"]}/{report["total"]} planted defects caught '
          f'(recall {report["recall"]:.0%})')
    for d in report["defects"]:
        mark = "✓" if d["caught"] else "✗"
        print(f'  {mark} {d["id"]} [{d["channel"]}] {d["title"]} -> {d["where"]}')
