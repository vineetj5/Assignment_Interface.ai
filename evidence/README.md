# Evidence Manifest

This folder contains recorded evidence for the end-to-end flow: discovery, artifact creation, deterministic replay, and an exceptional replay outcome.

## Saved Example Artifact

- `example_artifact_lookup_balance_1.0.0.json`

This is a copy of the approved `lookup_balance` capability artifact from `artifacts/lookup_balance/1.0.0.json`. It contains the typed inputs, outputs, step list, locator strategies, runtime conditions, success conditions, safety policy, compatibility metadata, and provenance used by replay.

## Discovery Run

- `demo_phase3_1786831501/`

Representative files:

- `result.json` - final discovery result.
- `discovery_trace.jsonl` - step-by-step model decisions, resolved targets, actions, and extracted values.
- `decisions/` - saved model decisions.
- `observations/` - observed page states.
- `screenshots/` - visual evidence captured during the run.

Summary:

```text
Goal: Look up member 12345's checking balance.
Status: success
Steps: 5
Extracted output: member_id=12345, account_type=checking, current_balance=$1,214.87
```

## Successful Replay Run

- `replay_1786898220/`

Representative files:

- `result.json` - final deterministic replay result.
- `replay_trace.jsonl` - deterministic action trace with sensitive input redaction.
- `actions.jsonl` - action execution records.
- `observations/` - observed page states.
- `screenshots/` - replay screenshots.

Summary:

```text
Capability: lookup_balance
Version: 1.0.0
Status: success
Runtime input: member_id=[REDACTED], account_type=checking
Steps completed: 4
Output: current_balance={amount: 460.87, currency: USD}
LLM UI decision calls: 0
```

## Exceptional Replay Run

- `replay_1786842930/`

Representative files:

- `result.json` - final business-outcome result.
- `replay_trace.jsonl` - deterministic trace through the not-found condition.
- `observations/` - page states showing the detected outcome.
- `screenshots/` - visual evidence.

Summary:

```text
Capability: lookup_balance
Version: 1.0.0
Status: business_outcome
Outcome: MEMBER_NOT_FOUND
Detected at step: search_member
Steps completed: 2
```

## Chat Routing Evidence

The `chat_*/` folders contain natural-language routing records. These show the Phase 6 boundary: the router may call the LLM to choose an approved capability and arguments, then replay runs deterministically and the chat response references the replay result.

Useful example:

- `chat_20260816_163702_928480/result.json`

Summary:

```text
Status: success
Message: Member 12345's current checking balance is $460.87.
Replay run: replay_1786898220
```
