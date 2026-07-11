# Latitude implementation patterns learned from Dewey rollout

Use this reference when moving from Latitude review into implementation: signals, monitors, saved searches, capture/instrumentation, and validation.

## Auth and API surface

- Latitude API-key auth can create and read user-authored signals and monitors in the Dewey setup.
- Saved-search creation may require OAuth user auth even when list/read and project analytics work with an API key. If `createSavedSearch` returns OAuth-required/403, do not loop on argument shape. Use inline monitor targets with `type: savedSearch`, `id: null`, `stream: traces`, `filterSet`, and optional semantic `query` as the fallback.
- `signals monitor` (attach evaluation) can also return 400 under API-key; leave flagger signals active.
- When using the `latitude` CLI for API operations, ensure `LATITUDE_BASE_URL` is not pointed at the ingest endpoint. Load `.env` but remove/override `LATITUDE_BASE_URL` if it is an OTLP ingest URL; the CLI should call the Latitude API, not `https://ingest.latitude.so`.

## Monitor create vs list (shape mismatch)

**List response** nests configuration under `rule`. **Create body is flat** (`name`, `target`, `severity`, `trigger`, `metric`, optional `condition`). Replaying list JSON into create → 400 Invalid input.

Full examples and fleet pack: `references/monitors-and-signal-triage.md`.

`--dry-run` is **not** a schema guarantee: it can accept nested-rule bodies that still fail live create. Always verify with a real create + `monitors list` read-back.

High-volume fleets: use `errorRate` for error spikes, not Dewey-style absolute count of 5 on all traces.

If a project already has dozens of auto-flagger signals and **zero** monitors: create the five ops monitors and triage escalating signals. Do not invent more signals first.

## Resource design

Best default split:

- Signals: recurring behavior failures.
  - premature completion without verification
  - tool loop / avoidable detour
  - avoidable user handoff
  - real tool failure blocks task
  - poor observability capture
  - unsafe confidence after weak evidence
- Monitors: operational metric thresholds and semantic matches.
  - high cost
  - slow trace
  - runaway context
  - errored trace spike
  - poor observability capture match
- Saved searches: useful when OAuth is available; otherwise implement their logic as inline monitor targets.

## Metric units and field names

Latitude has two related surfaces:

- Trace rows expose raw fields such as `durationNs`, `tokensTotal`, and `costTotalMicrocents`.
- Analytics/monitor metrics use abstract fields `duration`, `tokens`, and `cost`.

Do not blindly copy row-field units into metric thresholds. Validate with `queryAnalytics` before finalizing monitor thresholds. In the Dewey rollout, `metric: {kind: "max", field: "cost"}` returned dollar-denominated values, so high-cost thresholds are dollars (`0.25`), not microcents (`250000`). `metric: {kind: "max", field: "duration"}` returned second-denominated values, so slow-run thresholds are seconds (`120`), not nanoseconds (`120000000000`). `metric: {kind: "max", field: "tokens"}` returns token counts, so `1000000` is the right 1M-token threshold.

## Capture/instrumentation pattern

For Hermes-to-Latitude traces, prefer safe structured summaries over raw content by default:

- `hermes.capture.level`
- `hermes.profile`
- `hermes.platform`
- `hermes.approval_mode`
- `user_prompt_summary`
- `gen_ai.input.messages_summary`
- `gen_ai.output.messages_summary`
- `gen_ai.tool.call.arguments_summary`
- `gen_ai.tool.call.result_summary`

The summary should include type, size, selected keys, and stable redacted hashes, not raw secrets or full tool payloads. Validation should include a synthetic secret and assert the raw secret string is absent from no-content-mode OTLP output.

## Validation checklist

A full implementation pass should prove all of these:

1. Project is readable.
2. Each expected signal is readable by slug and has at least one evaluation.
3. Each expected monitor is readable by slug with expected trigger, severity, stream, and metric.
4. Any saved-search fallback is explicitly documented if OAuth blocks saved-search creation.
5. Inline monitor filters or equivalent analytics queries execute against recent traces.
6. Instrumentation code compiles.
7. Synthetic capture test proves summary attributes exist and raw test secrets are absent.
8. Metric unit sanity checks pass for cost, duration, and tokens.
9. A fresh live Hermes trace after the patch contains the new metadata/summary attributes.
10. Monitor create used flat body (not nested `rule`); live create + list read-back succeeded.

Do not report complete success until metric units and a fresh trace are verified.
