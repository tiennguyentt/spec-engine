"""Streamlit Community Cloud entrypoint.

Delegates to app.py via runpy so the real script re-executes on every
Streamlit rerun (a plain `import app` would be cached after the first run).

IMPORTANT: re-executing app.py is not enough on its own. app.py does
`import theme`, `import intro`, `from engine import ...`; those land in
sys.modules and are NOT re-imported on rerun. Across a Cloud redeploy that
changes one of them, a fresh app.py can call into a STALE cached module
(e.g. `theme.telemetry` missing) and crash with AttributeError. So we drop
the project's own modules from sys.modules first, forcing every rerun to
import the current files. Third-party packages stay cached.
"""

import sys
from pathlib import Path
import runpy

for _name in list(sys.modules):
    if _name in {"app", "theme", "intro"} or _name == "engine" or _name.startswith("engine."):
        del sys.modules[_name]

runpy.run_path(str(Path(__file__).parent / "app.py"), run_name="__main__")
