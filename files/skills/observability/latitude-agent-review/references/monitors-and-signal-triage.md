# Latitude monitors + escalating signal triage

Use after a fleet coverage audit or when Nick asks what to do **in Latitude product** (not OTEL injection).

## Product state diagnosis

| Pattern | Meaning | Action |
|---|---|---|
| Many **flagger** signals, **0 monitors** | Behavior noise without ops thresholds | Create operational monitors; do **not** invent more signals |
| Many monitors, few signals | Dewey-style ops posture | Leave signals for real behaviors after annotation |
| Project empty of both | Nothing instrumented | Fix OTEL first (`orgo-fleet-coverage.md`) |

**Default for high-volume fleets (Momentum-class):** monitors + triage escalating signals. Do not create dozens of manual signals.

## CreateMonitorBody (CLI/API) — critical shape

`latitude monitors list` returns nested `rule: { trigger, severity, config }`.  
**Create does not accept that shape.** Nested `rule` → HTTP 400 `"Invalid input"`.

OpenAPI `CreateMonitorBody` is **flat** (oneOf: match | threshold | escalating):

```json
{
  "name": "MomentumClaw: High-cost trace over $0.25",
  "description": "…",
  "target": {
    "type": "savedSearch",
    "id": null,
    "stream": "traces",
    "query": null
  },
  "severity": "high",
  "trigger": "threshold",
  "metric": { "kind": "max", "field": "cost" },
  "condition": {
    "trigger": "threshold",
    "direction": "above",
    "metric": { "kind": "max", "field": "cost" },
    "threshold": { "mode": "absolute", "value": 0.25 }
  }
}
```

Match monitor (semantic):

```json
{
  "name": "… Poor observability capture match",
  "target": {
    "type": "savedSearch",
    "id": null,
    "stream": "traces",
    "query": "missing content capture, empty tool arguments, …"
  },
  "severity": "medium",
  "trigger": "match",
  "metric": { "kind": "count" }
}
```

CLI:

```bash
latitude monitors create --project-slug <slug> --format json --json '<body>'
# Verify with live create + list (see dry-run pitfall below):
latitude monitors list --project-slug <slug> --format json
```

Do **not** put `slug` in the body; name derives slug.

### Dry-run pitfall

`--dry-run` can return success for a body that still fails live create with 400 Invalid input (e.g. nested `rule` from list payloads). **Dry-run is not proof of schema validity.** Prefer the flat examples above, or `latitude monitors create --spec` → `CreateMonitorBody`. Confirm with a real create + `monitors list` read-back.

## Standard five monitors (clone Dewey, retune fleet)

Validate units with analytics **before** thresholds:

```bash
# cost → dollars; duration → seconds; tokens → count
latitude analytics query --project-slug <slug> --format json --json \
  '{"stream":"traces","metric":{"kind":"max","field":"cost"},"range":{"fromIso":"…","toIso":"…"}}'
```

| Monitor theme | Metric | Starting threshold | Notes |
|---|---|---|---|
| High cost | max cost | $0.25 | Safety net; may rarely fire if fleet is cheap |
| Slow | max duration | 120s | Noisy if max duration is thousands of seconds — retune |
| Runaway context | max tokens | 1_000_000 | |
| Errored spike | **errorRate** (fleet) or count (single agent) | 5% errorRate | **Do not** use Dewey's count>5 on high-volume fleets |
| Poor capture | match + semantic query | — | Inline savedSearch target, id null |

## Escalating signal triage

1. `latitude signals list --project-slug <slug>` → sort by `states` containing `escalating`, then by `occurrences`.
2. For each escalating slug:  
   `latitude signals listTraces --project-slug <slug> --signal-slug <slug> --limit 8`
3. Aggregate sample rows: `serviceNames` → computer, `userId`, `sessionId`, `models`.
4. Deepen:
   - `latitude traces listSpans --trace-id <id>` (may be **shallow**: single `openai.chat` on some fleets)
   - If spans empty of tools: `latitude traces get` and walk **conversation** for tool names / skill_view failures
5. Verdict labels: real user-visible | config/skill inventory | flagger noise | unknown.
6. Next actions outside Latitude when real (skill pack fix, agent loop on box). Inside Latitude: annotate true positives; mute only after review.

### `signals monitor` (attach eval)

`latitude signals monitor --project-slug <slug> --signal-slug <slug>` may return **400** under API-key auth. Do not spin. Leave flagger signal active; note OAuth/eval path as optional follow-up (same class as saved-search OAuth limits).

## Shallow spans pitfall

Fleet traces often report `spanCount` high on list rows but `listSpans` returns only root `openai.chat`. **Conversation payload** still has tool names. Always fall back to `traces get` before declaring "no tools."

## Session snapshot (MomentumClaw 2026-07-08)

- Created 5 flat monitors on `momentumclaw` (cost/slow/tokens/errorRate/poor-capture).
- Escalating: redundant tools → Jack's Computer (`hermes-22cb6336`) Telegram; skill lookup → the-haring-agency (`hermes-a9ebc778`) api_server missing skills like `hermes-agent` / `hermes-platform-operations`.
- Vault: `projects/momentum-amp/latitude.md`.
