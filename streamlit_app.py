"""Streamlit Community Cloud entrypoint.

Delegates to app.py via runpy so the real script re-executes on every
Streamlit rerun (a plain `import app` would be cached after the first run).
"""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).parent / "app.py"), run_name="__main__")
