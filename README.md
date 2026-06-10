# 📐 Knowledge Engine

**Not AI-assisted. Agent-operated.**

An **evidence-backed spec red team** for regulated product work: it audits a
plausible-looking draft spec against transcripts, policy documents, production
code and the database; exposes the defects that cause rework or regulatory
exposure — with verbatim receipts; and returns a **dev-ready corrected diff**
for human approval.

Open the app and you land on the catch: the defects the agent team found in an
approved-looking insurance spec, the corrected diff, the readiness delta
(61 → 92), and the one decision only a human can make. The full machinery —
deterministic code gate, D1–D5 adversarial grading, an 11-role enterprise team
debating through a bounded router, the append-only eval-log — is inspectable
depth behind one click.

The output is not documentation. It is buildable work.

This is a public, fully synthetic rebuild of the PM intelligence system I
operate in my day-to-day product work.

## What it solves

| # | The problem | The answer |
|---|------------|------------|
| 01 | **Stakeholders contradict each other — and specs silently pick a side.** The CEO decides one thing, written policy says another, ops does a third. | A truth hierarchy resolves every contradiction by authority and never hides one: conflicts are surfaced, resolved, and flagged for a human ruling. |
| 02 | **AI writes confident specs with invented facts.** Hallucinated SLAs, imaginary regulatory caveats. | Claims without sources don't exist. Every statement traces to a verbatim quote, a document, code, or a tagged assumption — an adversarial grader hunts the ones that don't. |
| 03 | **Quality depends on who wrote the doc.** Standards live in people's heads. | A deterministic quality gate enforces standards as code — hedge words, vague quantities, missing scope. Models cannot sweet-talk it. |
| 04 | **Documentation ships weeks after the feature.** Docs are downstream cleanup, so they drift. | Documentation is a release gate: nothing advances to sign-off until it passes grading — max three revision rounds, then it blocks loudly. |
| 05 | **The spec says one thing, the code does another.** The gap between intended and actual systems is where incidents live. | Evidence comes from every source — transcripts, documents, code, schemas. Spoken decisions argue by authority; code and data are artifact-state facts no one can out-talk. Gaps become explicit migration requirements. |
| 06 | **Corrections die in chat threads.** The same mistake gets fixed for the tenth time. | Every human edit at sign-off distills into a persistent rule applied on the next run — corrections become institutional memory. |

## The loop

```
evidence ────▶ source-traced wiki      every claim: verbatim quote + locator + claim class
             ▶ conflict check          truth hierarchy; code/DB are artifact-state facts
             ▶ deterministic gate      pure code — models cannot override it
             ▶ D1–D5 grading           adversarial; typed findings P0/P1/P2
             ▶ phase-gated debate      bounded router; full 11-role roster, streamed as CHAT
             ▶ corrected diff          amendments + migration requirements, re-graded
             ▶ Decision Console        your rulings rewrite the baseline; edits re-run the gate
             ▶ Judgment Ledger         rulings distill into scoped, versioned, revocable rules
             ▶ compiled behavior       the signed baseline compiles to a decision table +
                                       acceptance vectors — flip a ruling, behavior + tests flip
             ▶ drift watch             changed evidence surfaces in chat, naming moved claims
```

**Four workspaces behind one run bar:** 💬 Chat (the debate as a streaming
conversation — your message is the 12th seat, top authority), 📋 Report
(catches with receipts), 🧪 Test (the compiled FNOL slice + acceptance board
+ Executable Time Machine), ✍ Decide (rulings → baseline → rules).

The default view needs no API key (it replays a recorded run through the real
engine). Live mode runs the whole red team on any OpenAI-compatible endpoint
with your own key, streaming real tokens — agents type as they work.

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
  and watch the agents argue.

Configuration (optional, env vars): `LLM_BASE_URL`, `KNOWLEDGE_ENGINE_MODEL`.

## Design notes

- **Provider-agnostic by construction.** Structured output is enforced
  client-side: each stage asks for JSON against a pydantic schema, validates,
  and feeds validation errors back for bounded retries (`engine/llm.py`).
  Works on any model, no provider-specific JSON features required.
- **Claims without sources don't exist.** The wiki stage must attach a source
  and verbatim quote to every claim; downstream stages may only reference
  claim ids (`engine/stages.py`).
- **Conflicts resolve up the hierarchy, but never silently.** Decision-maker >
  written policy > ops statement > anecdote. Anything where practice diverges
  from policy is flagged `needs_human_confirmation`.
- **The debate is adversarial by role, not by chance** (`engine/debate.py`).
  Each role has a single job and is told to concede resolved points — the
  arbiter synthesizes amendments from what survives.
- **Run logs are plain JSON** (`data/runs/`), so any run can be replayed,
  downloaded, and diffed without the engine installed.
- **Detection is measured, not claimed.** The benchmark case ships with a
  ground-truth file of planted defects (`data/evals/`); `engine/evals.py`
  scores any run — scripted or live — for detection recall per channel
  (gate, conflict, finding). The scorecard renders in the Report workspace.
- **The theme is reusable** (`theme.py` + `.streamlit/config.toml`): the
  design language of [tiennguyentt.github.io](https://tiennguyentt.github.io),
  packaged as a drop-in for every app in this series.

## Data & trust

- **All demo data is synthetic.** The AnDigi case, transcripts, policy, code
  and schema are fictional; no employer or client material is included.
- **Your API key is never stored.** Live mode uses it for that session's
  calls only; the app keeps no server-side copy.
- **The simulator runs no model.** Compiled behavior, acceptance vectors,
  the gate, drift checks and the Time Machine are pure code.
- **Honest labels everywhere.** Recorded replays are labeled recorded;
  scripted content is labeled scripted; nothing pretends to be live inference.
- **Not legal or compliance advice.** The regulatory content in the demo is
  illustrative.

## Roadmap

| # | Milestone | Status |
|---|-----------|--------|
| M1 | AnDigi case, 11-role debate, code gate, D1–D5, chat terminal, Decision Console, Judgment Ledger (rules fire across runs), Executable Baseline Compiler (rulings → running behavior + tests), drift watch, handoff exports, Time Machine | **shipped** |
| M1.5 | First fully model-generated run (BYO/sponsored key), capped sponsored live mode | plumbing ready, awaiting key |
| M2 | Public product: FastAPI + Next.js + SSE broadcast, shareable run URLs, branded PDF exports | committed |
| M3 | Workflow 02: spec → sprint plan · outcome re-ingestion (decision_events → evidence) | planned |
