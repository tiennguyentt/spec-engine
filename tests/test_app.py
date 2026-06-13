"""UI smoke tests via Streamlit AppTest — no model calls, no browser.

The app must render every workspace from the committed demo run, show the
measured surfaces (recall scorecard, standards drawer), and populate the
chat feed from the recorded sequence.
"""

import pytest
from streamlit.testing.v1 import AppTest

WORKSPACES = ["Overview", "Debate", "Verify", "Sign-off"]


@pytest.fixture()
def at() -> AppTest:
    app = AppTest.from_file("app.py", default_timeout=60)
    app.run()
    assert not app.exception, app.exception
    return app


def _body(app: AppTest) -> str:
    return " ".join(getattr(md, "value", "") or "" for md in app.markdown)


def test_default_view_is_the_overview(at):
    body = _body(at)
    # A cold viewer lands on the verdict + receipts, not a chat frame.
    assert at.radio[0].options == WORKSPACES
    assert at.radio[0].value == "Overview"
    assert "se-countup" in body  # the readiness delta animates in the hero
    assert "spec readiness" in body


def test_every_workspace_renders(at):
    for ws in WORKSPACES:
        at.radio[0].set_value(ws)
        at.run()
        assert not at.exception, f"{ws}: {at.exception}"


def test_report_shows_measured_surfaces(at):
    at.radio[0].set_value("Overview")
    at.run()
    body = _body(at)
    assert "Detection recall" in body
    assert "10/10 caught" in body
    assert "INCOSE QUALITY CHARACTERISTICS" in body
    assert "se-countup" in body  # score animates from the real grade delta


def test_transcript_populates_chat_feed(at):
    at.radio[0].set_value("Debate")  # the debate workspace holds the transcript
    at.run()
    buttons = {b.label: b for b in at.button}
    buttons["Show transcript"].click()
    at.run()
    assert not at.exception, at.exception
    feed = at.session_state["chat_feed"]
    kinds = {item["kind"] for item in feed}
    assert "turn" in kinds and "system" in kinds
    assert any("RECORDED REPLAY" in i["text"] for i in feed if i["kind"] == "system")


def test_intro_lists_the_problems(at):
    at.session_state["view"] = "intro"
    at.run()
    assert not at.exception, at.exception
    body = _body(at)
    assert "Knowledge Engine" in body
    assert "What this system solves" in body
