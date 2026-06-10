# 📐 Spec Engine

**Not AI-assisted. Agent-operated.**

Workflow 01 of an agent-operated product team: a public, fully synthetic
rebuild of the PM intelligence system I operate in my day-to-day product work.
Raw meeting transcripts go in; role agents compile, check, draft, grade and
**debate** the spec autonomously; a human reads the diff and signs off.

## The pipeline

```
transcripts ──▶ 1 source-traced wiki      every claim carries a verbatim quote
            ──▶ 2 conflict check          truth hierarchy resolves contradictions, never hides them
            ──▶ 3 spec draft              requirements trace to wiki claim ids
            ──▶ 4 automated grading       adversarial grader: clarity / sources / testability
            ──▶ 5 role debate             Eng Lead × QA × PO argue autonomously; arbiter rules
            ──▶ 6 human sign-off          deliberately NOT automated
```

Stage 5 is an autonomous multi-agent debate: the **Eng Lead** attacks
feasibility, **QA** attacks testability, the **PO** defends or concedes with
concrete amendments — two rounds, turn by turn, then a neutral **arbiter**
issues per-requirement rulings (accept / amend / reject).

The demo project is **FlowBook**, a fictional salon booking app. Two
contradictions are planted in the transcripts (deposit policy vs floor
practice, 24h vs 48h cancellation) — stage 2 catches both, stage 5 argues
out the rest.

> All data here is synthetic. No employer or client material is included.

## Run it

```sh
pip install -r requirements.txt
streamlit run app.py
```

- **Replay mode** needs no API key — it plays a recorded run from `data/runs/`.
- **Live mode** runs the real pipeline through any OpenAI-compatible endpoint.
  Default is [OpenRouter](https://openrouter.ai) so cheap models work out of
  the box; paste your key (`sk-or-...`), pick or type any model id, press run,
  and watch the debate turns appear as the agents argue.

Configuration (optional, env vars): `LLM_BASE_URL`, `SPEC_ENGINE_MODEL`.

## Design notes

- **Provider-agnostic by construction.** Structured output is enforced
  client-side: each stage asks for JSON against a pydantic schema, validates,
  and feeds validation errors back for bounded retries (`engine/llm.py`).
  Works on any model, no provider-specific JSON features required.
- **Claims without sources don't exist.** The wiki stage must attach a speaker
  and verbatim quote to every claim; downstream stages may only reference
  claim ids (`engine/stages.py`).
- **Conflicts resolve up the hierarchy, but never silently.** CTO decision >
  written policy > ops lead > anecdote. Anything where practice diverges from
  policy is flagged `needs_human_confirmation`.
- **The debate is adversarial by role, not by chance** (`engine/debate.py`).
  Each role has a single job and is told to concede resolved points — the
  arbiter synthesizes amendments from what survives.
- **Run logs are plain JSON** (`data/runs/`), so any run can be replayed,
  downloaded, and diffed without the engine installed.
- **The theme is reusable** (`theme.py` + `.streamlit/config.toml`): the
  design language of [tiennguyentt.github.io](https://tiennguyentt.github.io),
  packaged as a drop-in for every app in this series.

## Roadmap — the agent-operated team

Spec Engine is workflow 01. The same machinery (role agents + structured
turns + debate + human gates) scales to the full development loop:

| # | Workflow | Roles | Status |
|---|----------|-------|--------|
| 01 | Transcript → debated, graded spec | PO, Eng Lead, QA, Arbiter | **this repo** |
| 02 | Spec → sprint plan: epics, tickets, estimates, dependencies | PO, Scrum Master, Eng | next |
| 03 | Tickets → implementation + review loop | Dev pair, Reviewer | planned |
| 04 | Build → QA: test plans, bug reports, release gate | QA, Release manager | planned |
| 05 | Sprint → retro: what the team learns, fed back to 01 | whole team | planned |
