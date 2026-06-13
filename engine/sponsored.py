"""Sponsored live inference — capped, queued, honest (round-7 consensus).

A server-side key (SPONSORED_DEMO_KEY in env or .env) lets any visitor watch
real tokens stream without bringing a key. Guards: one concurrent run via a
stale-checked lockfile, a daily run/token ledger, a per-run budget, and a
provider-side spending limit as the ultimate kill switch. When the slot is
busy or the cap is hit, the UI falls back to the latest real recorded run
with an honest freshness label.
"""

import json
import os
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USAGE_FILE = DATA_DIR / "runs" / ".sponsored-usage.json"
LOCK_FILE = Path(os.getenv("TMPDIR", "/tmp")) / "knowledge-engine-sponsored.lock"
LOCK_STALE_SECONDS = 15 * 60

DAILY_RUN_CAP = int(os.getenv("SPONSORED_DAILY_CAP", "10"))
# a full AnDigi run (11-role debate) lands around ~60k tokens; give headroom so a
# sponsored run completes instead of hitting the budget mid-debate (still pennies
# on a cheap model). Override with SPONSORED_RUN_BUDGET.
PER_RUN_TOKEN_BUDGET = int(os.getenv("SPONSORED_RUN_BUDGET", "90000"))
SPONSORED_MODEL = os.getenv("SPONSORED_MODEL", "deepseek/deepseek-chat")


def key() -> str:
    return os.getenv("SPONSORED_DEMO_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")


def available() -> bool:
    return bool(key())


def _usage() -> dict:
    today = time.strftime("%Y-%m-%d")
    if USAGE_FILE.exists():
        u = json.loads(USAGE_FILE.read_text())
        if u.get("day") == today:
            return u
    return {"day": today, "runs": 0, "tokens": 0}


def remaining_runs() -> int:
    return max(0, DAILY_RUN_CAP - _usage()["runs"])


def record_run(tokens: int) -> None:
    u = _usage()
    u["runs"] += 1
    u["tokens"] += tokens
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(u))


def acquire_slot() -> bool:
    if LOCK_FILE.exists():
        if time.time() - LOCK_FILE.stat().st_mtime < LOCK_STALE_SECONDS:
            return False
        LOCK_FILE.unlink(missing_ok=True)
    try:
        LOCK_FILE.touch(exist_ok=False)
        return True
    except FileExistsError:
        return False


def release_slot() -> None:
    LOCK_FILE.unlink(missing_ok=True)
