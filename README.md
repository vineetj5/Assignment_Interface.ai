# Bank Mock Automation

This project is a working vertical slice of an Interface.ai-style computer-use agent for a deliberately old-fashioned credit-union servicing application. The core workflow is:

```text
lookup_balance(member_id: str, account_type: savings|checking) -> BalanceResult
```

The system starts with an LLM-driven discovery run, compiles the observed behavior into a typed capability artifact, then replays that artifact deterministically without LLM UI decisions. The local app also includes a natural-language chat surface and an operator handoff console for exceptional replay states.

## Demo Video

Short app demos are included in the repository:

[video1761494673.mp4](video1761494673.mp4)

[video1540829306.mp4](video1540829306.mp4)

These recordings show the local app experience and the balance-lookup automation flow from the user-facing demo surface.

## What Is Included

- A mock legacy banking target with nested iframes, server-rendered pages, dense tables, synthetic members, and injectable runtime conditions.
- A discovery agent that observes the UI, asks an LLM or mock LLM for the next action, validates that action, executes it through Playwright, and records evidence.
- A capability artifact compiler that converts a successful discovery trace into a reusable JSON artifact under `artifacts/`.
- A deterministic replay engine that executes approved artifacts with parameter binding, typed output extraction, checkpoints, error detection, and redacted evidence.
- A natural-language router that uses an LLM only to map the user's request into an approved capability call; replay remains deterministic after routing.
- A Phase 7 human handoff layer with run ownership, intervention state, same-session browser preservation, and an operator console.

## Setup

Use Python 3.12+.

```bash
cd interface_ai_legacy_demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
```

Start the local target and chat app:

```bash
uvicorn app:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

The operator handoff console is available at:

```text
http://127.0.0.1:8000/operator
```

## Keys And Configuration

Live LLM mode uses Groq.

Create `.env` from `.env.example` and fill in your own key:

```bash
cp .env.example .env
```

Expected variables:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
TARGET_URL=http://127.0.0.1:8000
```

To run without live services, use the mock discovery mode:

```bash
python3 scripts/phase3_discovery_demo.py --mock --member 12345 --account-type checking
```

Deterministic replay and tests do not require a live LLM key.

## Demo Path: Discover, Compile, Replay

Run the agent on a goal. This records observations, screenshots, decisions, actions, and a final discovery result under `evidence/demo_phase3_*`.

```bash
python3 scripts/phase3_discovery_demo.py \
  --mock \
  --member 12345 \
  --account-type checking \
  --max-steps 15
```

Compile the latest successful discovery run into a reusable artifact:

```bash
python3 scripts/phase4_compile_artifact.py \
  --capability lookup_balance \
  --version 1.0.0
```

Replay the resulting artifact with new runtime inputs and zero LLM UI-decision calls:

```bash
python3 scripts/phase5_replay_demo.py \
  --capability lookup_balance \
  --version 1.0.0 \
  --member 76821 \
  --account-type checking
```

Replay a business-outcome path:

```bash
python3 scripts/phase5_replay_demo.py \
  --capability lookup_balance \
  --version 1.0.0 \
  --member 99999 \
  --account-type checking
```

## Natural-Language Chat Demo

This path calls the LLM for routing only. Once the router chooses `lookup_balance` and validates arguments, deterministic replay runs with no further LLM involvement.

```bash
python3 scripts/phase6_chat_demo.py \
  --message "What is member 76821's checking balance?"
```

The browser UI also supports multi-turn clarification. For example:

```text
User: What is member 76821's balance?
Assistant: Would you like the savings or checking balance?
User: savings
Assistant: Member 76821's current savings balance is ...
```

## Human Handoff Demo

The handoff implementation is exposed through the operator API and console:

```bash
curl http://127.0.0.1:8000/api/operator/interventions
```

Operator lifecycle endpoints:

```text
GET  /api/operator/interventions
GET  /api/operator/interventions/{intervention_id}
POST /api/operator/interventions/{intervention_id}/claim
POST /api/operator/interventions/{intervention_id}/resume
POST /api/operator/interventions/{intervention_id}/cancel
GET  /api/runs/{run_id}
POST /api/runs
POST /api/runs/{run_id}/claim
POST /api/runs/{run_id}/resume
POST /api/runs/{run_id}/cancel
```

The automated Phase 7 tests exercise escalation creation, claim, automation blocking while human owns control, and cancellation/resume behavior.

## Evidence

Representative submission evidence is indexed in `evidence/README.md`.

Key examples:

- `evidence/example_artifact_lookup_balance_1.0.0.json` - saved example artifact.
- `evidence/demo_phase3_1786831501/` - successful discovery run.
- `evidence/replay_1786898220/` - successful deterministic replay run.
- `evidence/replay_1786842930/` - deterministic replay that reports `MEMBER_NOT_FOUND`.

Key result locations:

- Discovery results: `/Users/vineetjujjavarapu/Downloads/interface_ai_legacy_demo/evidence/demo_phase3_1786831501/result.json`
- Successful replay result: `/Users/vineetjujjavarapu/Downloads/interface_ai_legacy_demo/evidence/replay_1786898220/result.json`
- Error / exceptional replay result: `/Users/vineetjujjavarapu/Downloads/interface_ai_legacy_demo/evidence/replay_1786842930/result.json`

## Tests

Run the full suite:

```bash
PYTHONPATH=. pytest -q
```

The unit and integration-style tests cover the main risk areas of the project: target app behavior, observation/action execution, LLM discovery validation, artifact compilation and schema validation, parameter binding, deterministic replay, runtime condition detection, output extraction, natural-language routing, multi-turn chat memory, LLM isolation after routing, operator handoff state transitions, and final safety guardrails. The suite also includes happy-path replay, business outcomes such as `MEMBER_NOT_FOUND`, hard failures, routing validation errors, and human-control blocking while an intervention is claimed.

At the time of this submission, the full suite passes:

```text
130 passed
```

## Repository Notes

All member records are synthetic and live in `data/customers.json`. The developer-only endpoint `/api/mock/customers` is intentionally not used by automation; the agent and replay engine drive the legacy UI surface itself.
