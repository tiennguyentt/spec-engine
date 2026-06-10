# 📐 Spec Engine

**Not AI-assisted. Agent-operated.**

A public, fully synthetic rebuild of the PM intelligence system I operate in my
day-to-day product work. Raw meeting transcripts go in; a graded, source-backed
spec comes out; a human reads the diff and signs off.

## The pipeline

```
transcripts ──▶ 1 source-traced wiki      every claim carries a verbatim quote
            ──▶ 2 conflict check          truth hierarchy resolves contradictions, never hides them
            ──▶ 3 spec draft              requirements trace to wiki claim ids
            ──▶ 4 automated grading       adversarial grader: clarity / sources / testability
            ──▶ 5 human sign-off          deliberately NOT automated
```

The demo project is **FlowBook**, a fictional salon booking app. Two
contradictions are planted in the transcripts (deposit policy vs floor
practice, 24h vs 48h cancellation) — stage 2 catches and resolves both by
authority, and flags them for a human.

> All data here is synthetic. No employer or client material is included.

## Run it

```sh
pip install -r requirements.txt
streamlit run app.py
```

- **Replay mode** needs no API key — it plays a recorded run from `data/runs/`.
- **Live mode** runs the real pipeline through any OpenAI-compatible endpoint.
  Default is [OpenRouter](https://openrouter.ai) so cheap models work out of
  the box; paste your key (`sk-or-...`), pick or type any model id, press run.

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
- **The grader is adversarial.** It is prompted to find problems (invented
  numbers, untraced assertions, vague quantities), report everything, and let
  the human filter — verdicts, not vibes.
- **Run logs are plain JSON** (`data/runs/`), so any run can be replayed,
  downloaded, and diffed without the engine installed.

## Roadmap

- **V2 — autonomous scrum team.** PO / dev / QA agent roles running a sprint
  end-to-end on the same knowledge base, watchable as an event stream.
