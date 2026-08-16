# Project Roadmap — Keep the Big Picture

## Phase 1 — Legacy target surface (current)

Build a controllable local proxy for a bank servicing app with synthetic data, nested frames, table layouts, multi-step member/account navigation, and explicit runtime failure states.

## Phase 2 — Surface abstraction + observability

Introduce a browser surface adapter around Playwright with:

- observe current page/frame state
- screenshot capture
- accessibility/DOM-derived concise observation
- click/fill/select/navigate primitives
- structured action logs
- stable session ownership

The target-app code must remain independent from automation code.

## Phase 3 — LLM discovery loop

Implement `observe → decide → act` against the live legacy surface. The model receives a natural-language goal and structured observation, chooses from a small typed action set, and stops on success/dead-end/max-steps.

Initial discovery goal:

```text
Look up member 12345 and read their current savings balance.
```

## Phase 4 — Capability artifact schema

Compile a successful discovery run into a typed, versioned capability, e.g.:

```text
lookup_balance(member_id: str, account_type: AccountType) -> BalanceResult
```

Artifact concepts:

- capability identity/version/status
- typed inputs/outputs
- ordered actions
- robust locator bundle per target
- waits and checkpoints
- extraction instructions
- known business outcomes/errors
- safety classification
- target/vendor compatibility metadata

## Phase 5 — Deterministic replay

Load an approved artifact, bind parameters, and execute without LLM UI decisions. Return one of:

- success + typed outputs
- known business outcome
- recoverable condition after bounded handling
- hard failure with step/evidence

## Phase 6 — Natural-language capability routing

Connect the right-side chat to a capability registry. The language model only decides **what capability to call** and extracts typed arguments. It does not decide browser actions during replay.

Example:

```text
"What is member 76821's checking balance?"
→ lookup_balance(member_id="76821", account_type="checking")
→ replay artifact
→ typed result
→ natural-language response
```

## Phase 7 — Guardrails + human handoff

Add:

- domain/route/action allowlist
- safe vs risky action classification
- redacted logs/artifacts
- pause/cede/resume ownership model
- operator takeover of the same live browser context
- intervention request with reason, current step, screenshot, and session reference

The existing `Unexpected verification dialog` state is the first handoff scenario.

## Phase 8 — Evidence + report

Produce discovery/replay logs, screenshots/traces, saved example artifact, one success replay, one business-outcome replay, and one escalation demonstration. Then write the required REPORT.md around the actual implementation decisions.
