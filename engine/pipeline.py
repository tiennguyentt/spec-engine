"""Pipeline orchestration + run logs.

A run log is a plain JSON dict so it can be saved, downloaded, and replayed
in the UI without the engine installed. Stage 5 (sign-off) is intentionally
NOT automated - a human reads the diff and approves.
"""

import json
import time
from collections.abc import Callable
from pathlib import Path

from engine.llm import LLM
from engine.stages import TRUTH_HIERARCHY, build_wiki, check_conflicts, draft_spec, grade_spec

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RUNS_DIR = DATA_DIR / "runs"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"

STAGE_TITLES = {
    "wiki": "1 · Transcript → source-traced wiki",
    "conflicts": "2 · Truth-hierarchy conflict check",
    "spec": "3 · Spec draft",
    "grade": "4 · Automated spec grading",
}

ProgressCb = Callable[[str, str], None]  # (stage_name, status: "start" | "done")


def load_transcripts() -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted(TRANSCRIPTS_DIR.glob("*.md"))
    }


def list_runs() -> list[Path]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(RUNS_DIR.glob("*.json"), reverse=True)


def load_run(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_pipeline(llm: LLM, transcripts: dict[str, str], on_progress: ProgressCb | None = None) -> dict:
    def progress(stage: str, status: str) -> None:
        if on_progress:
            on_progress(stage, status)

    started = time.time()

    progress("wiki", "start")
    wiki = build_wiki(llm, transcripts)
    progress("wiki", "done")

    progress("conflicts", "start")
    conflicts = check_conflicts(llm, wiki)
    progress("conflicts", "done")

    progress("spec", "start")
    spec = draft_spec(llm, wiki, conflicts)
    progress("spec", "done")

    progress("grade", "start")
    grades = grade_spec(llm, wiki, spec)
    progress("grade", "done")

    return {
        "meta": {
            "kind": "live",
            "model": llm.model,
            "base_url": llm.base_url,
            "duration_seconds": round(time.time() - started, 1),
            "usage": {
                "input_tokens": llm.usage.input_tokens,
                "output_tokens": llm.usage.output_tokens,
            },
            "truth_hierarchy": TRUTH_HIERARCHY,
            "transcript_files": list(transcripts),
        },
        "stages": {
            "wiki": wiki.model_dump(),
            "conflicts": conflicts.model_dump(),
            "spec": spec.model_dump(),
            "grade": grades.model_dump(),
        },
        "signoff": {"status": "pending", "by": None},
    }


def save_run(run: dict, name: str) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{name}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
