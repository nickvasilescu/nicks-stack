---
name: latitude-agent-review
description: "Review Hermes Latitude traces, multi-tenant Orgo fleet coverage (project-per-customer, OTEL), and telemetry insights."
version: 0.3.8
author: Hermes
metadata:
  hermes:
    tags: [Latitude, Observability, Telemetry, Analysis, Orgo, MultiTenant]
---

# Latitude Agent Review

Use this skill to review Hermes Agent activity through Latitude telemetry and turn raw traces into operational insight. It does not replace source-of-truth inspection of files, apps, or live systems; Latitude tells you what happened in observed runs, not whether the outside world is currently correct. Prefer the Latitude MCP server when available; fall back to the `terminal` tool with the `latitude` CLI only when MCP tools are missing.

Also use for **multi-tenant fleet coverage**: "are Momentum VMs in Latitude?", "should we add everything?", project-per-customer layout, OTEL resource conventions, Orgo computer × Latitude service audits. Full procedure: `references/orgo-fleet-coverage.md`. For **new customer project + install** (including thin pilots when Nick asks): `references/hermes-otel-backfill.md` (plugin path preferred for Telegram pilots).

## When to Use

- "Based on Latitude, do you have insights?"
- "Review the last Hermes run / session / trace."
- "Why was that agent workflow slow or expensive?"
- "Find tool errors, model retries, or runaway context in Latitude."
- "Turn the workflow we just did into a reusable skill using Latitude evidence."
- "Are customer / Momentum / fleet VMs in Latitude?" / "should we add everything to Latitude?"
- "Are customers/agencies actually using these agents?" / "is this adoption or only provisioning?" Follow `references/customer-adoption-analysis.md`; report strict confirmed-use and broader telemetry counts separately.
- Multi-tenant layout: dewey vs customer projects, OTEL service naming, coverage gaps.
- Create monitors or triage escalating flagger signals on a customer project.
- "Set up Latitude for Brennan / Budgetdog / customer X" (project create + backfill).
- Latitude UI stuck on "Waiting for your first trace" after wiring.

## Prerequisites

- Latitude MCP server authenticated and exposing `mcp__latitude__listProjects`, `mcp__latitude__listTraces`, `mcp__latitude__listTraceSpans`, `mcp__latitude__getTraceSpan`, `mcp__latitude__queryAnalytics`, and `mcp__latitude__querySpans`.
- A Latitude project slug, usually discovered with `mcp__latitude__listProjects`.
- Optional CLI fallback: `LATITUDE_API_KEY` in `.env` or environment; `LATITUDE_BASE_URL` only for a self-hosted Latitude API.
- For current time windows, use the `terminal` tool with `date -u +%Y-%m-%dT%H:%M:%SZ` before constructing explicit `fromIso` / `toIso` ranges.

## How to Run

Canonical path: use `mcp__latitude__listProjects` to get the project slug, then use Latitude MCP analytics and trace tools to collect evidence, and synthesize a short findings list with trace IDs, span IDs, metric values, and confidence labels. If the user referred to "what we just did," also use `session_search` for conversation history when available; if history is absent, state the scope you inferred and proceed from recent Latitude traces.

Fleet coverage path: follow `references/orgo-fleet-coverage.md` (Orgo inventory + service aggregation + gap report). Do not answer "is the fleet on Latitude?" from memory.

New-customer / pilot setup path: follow `references/hermes-otel-backfill.md` (`latitude projects create` + **plugin or** OTEL bootstrap + verify `traces list`). Never put customers into `dewey`. Files alone often leave the UI on "Waiting for first trace."

## Quick Reference

- `references/openrouter-cost-attribution.md`: reconcile OpenRouter key-level billed usage with estimated Latitude trace costs; reprice token categories from the live model catalog; detect shared keys, provider double-attribution, and runaway cached context.
- `references/orgo-fleet-coverage.md`: multi-tenant project-per-customer model, OTEL resource convention, Orgo×Latitude coverage audit, sampling, rollout order (Momentum 2026-07 snapshot).
- `references/customer-adoption-analysis.md`: distinguish provisioned, emitting, user-active, operationally used, and production adoption; validate service filters; decompose flagship/cron concentration; attribute signals by service.
- `references/hermes-otel-backfill.md`: project create; **plugin path vs OTel-only**; empty UI; smoke test + `hermes chat -Q`; OTel pins (anthropic **0.61.0**); `X-Latitude-Project`; env quoting; host terminal gateway-kill guard; Budgetdog example.
- `references/monitors-and-signal-triage.md`: flat CreateMonitorBody, **dry-run false positive**, fleet monitor pack, escalating signal triage, shallow-span fallback to conversation.
- `references/latitude-signals-best-practices.md`: official-doc-grounded guidance for signals, saved searches, monitors, annotations, capture, and default thresholds.
- `references/implementation-patterns.md`: API auth, **flat monitor create** (not nested rule), inline monitor fallbacks, metric units, capture summaries, validation.
- `references/dewey-telemetry-durability.md`: durable editable-package patches, metric units, API-key vs OAuth saved-search behavior.
- `mcp__latitude__listProjects`: list project slugs.
- `mcp__latitude__listTraces`: newest trace rows, session IDs, cost, tokens, errors.
- `mcp__latitude__getTrace`: trace metadata and captured conversation, if stored.
- `mcp__latitude__listTraceSpans`: span timeline and tool/model sequence.
- `mcp__latitude__getTraceSpan`: full span payload when captured.
- `mcp__latitude__queryAnalytics`: aggregate metrics by model, provider, tool, status.
- `mcp__latitude__querySpans`: drill into individual error or slow spans.
- `mcp__latitude__listSignals`: existing signal definitions and occurrences.
- `session_search`: recover prior chat context when the user references it.
- `terminal`: current UTC time or CLI fallback.

## Procedure

0. **If the question is fleet coverage / multi-tenant setup**, follow `references/orgo-fleet-coverage.md` first.
   - Completion: matrix summary with coverage %, emitters, P0 gaps, recommendation (not "add everything").

0b. **If Nick wants Latitude set up for a customer**, follow `references/hermes-otel-backfill.md`.
   - Completion: project exists; plugin and/or bootstrap on box; **at least one row in `traces list`** (smoke or `hermes chat -Q`); Nick told spend starts at $0 until traffic (tokens may still count).

1. Resolve scope.
   - If the user names a project, use that slug.
   - Customer fleets: use that customer's project (`momentumclaw`, `budgetdog`, etc.), never default customer traffic into `dewey`.
   - If they say "just now" or "this conversation," inspect recent traces first and use `session_search` only for missing conversational context.
   - Completion: you have a project slug, a time range, and any stated focus such as cost, errors, latency, skill authoring, fleet coverage, or tool use.

2. Establish the recent trace set.
   ```json
   {"projectSlug":"<slug>","limit":10,"sortBy":"startTime","sortDirection":"desc"}
   ```
   Call `mcp__latitude__listTraces` with those parameters. Record trace IDs, session IDs, models, providers, token totals, costs, duration, and error counts.
   - Completion: you can name the 2-3 traces most likely relevant.

3. Read the run shape, not just the headline row.
   ```json
   {"projectSlug":"<slug>","traceId":"<traceId>"}
   ```
   Call `mcp__latitude__listTraceSpans` for the relevant trace IDs. Build a timeline: LLM request, tool call, LLM request, tool call, final response. Use `mcp__latitude__getTraceSpan` only when span content is needed and `latitude.captured.content` is true.
   - Completion: you can explain the workflow sequence and where time, retries, or tools entered.

4. Run targeted aggregates.
   - **OpenRouter spend questions:** before trusting Latitude cost, follow `references/openrouter-cost-attribution.md`. Separate key-level billed usage, Latitude's estimated trace cost, and a repriced trace estimate. Check `costIsEstimated`, successful provider spans, current model-catalog rates, and shared-key reuse. Do not sum trace-level provider rows when abandoned fallback spans cause full-trace double attribution.
   ```json
   {
     "projectSlug":"<slug>",
     "body":{
       "stream":"traces",
       "breakdown":"model",
       "metric":{"kind":"count"},
       "range":{"fromIso":"<start>Z","toIso":"<end>Z"},
       "limit":20
     }
   }
   ```
   Repeat with `metric:{"kind":"errorRate"}`, `metric:{"kind":"sum","field":"cost"}`, and for spans use `stream:"spans"`, `breakdown:"status"` or `breakdown:"operation"`.
   - Completion: each conclusion has either a trace/span citation or an aggregate number.

5. Separate telemetry artifacts from real failures.
   - Treat `llm_request abandoned before post_llm_call` and `llm_request superseded by retry` as retry/fallback telemetry until proved otherwise.
   - Treat tool spans with `statusCode:"error"` or nonzero tool failure clusters as stronger evidence of real agent failure.
   - Use Latitude's product model deliberately: signals are recurring behavior patterns, while metric thresholds such as cost, latency, token count, and capture gaps usually belong in saved searches plus monitors until review reveals a repeated behavioral cause.
   - Completion: every "error" insight says whether it is a user-visible failure, a retry artifact, a monitorable metric threshold, or unknown.

6. If implementing resources, follow the implementation checklist.
   - **Monitors create = flat body** (`name`, `target`, `severity`, `trigger`, `metric`, `condition`). Nested `rule` from list responses → 400 Invalid input. See `references/monitors-and-signal-triage.md`.
   - **`--dry-run` is not schema-safe:** nested-rule bodies can dry-run OK and still 400 on live create. Confirm with live create + `monitors list`.
   - High-volume fleets: prefer **errorRate** for error spikes, not Dewey-style raw count of 5.
   - If project has many flagger signals and **zero** monitors: create the five ops monitors + triage escalating; do not invent more signals.
   - Escalating triage: `signals listTraces` → map service to computer → `traces get` conversation when `listSpans` is shallow.
   - Prefer saved searches when OAuth is available. If create returns OAuth/403 under API-key, use inline savedSearch targets (`id:null`). `signals monitor` may also 400 under API-key — leave flagger active.
   - Before setting monitor thresholds, validate metric units with `queryAnalytics` (`cost` dollars, `duration` seconds, `tokens` count).
   - Capture: safe summaries/redacted hashes by default. See `references/implementation-patterns.md`.
   - Completion: monitors list by slug; units validated; escalating verdicts labeled real vs noise.

7. Convert observations into actionable insights.
   Use this order: user-visible failures, runaway cost/context, slow spans, brittle tool routing, missing observability. Include confidence labels: high when supported by repeated aggregates, moderate when supported by a few traces, low when inferred from sparse data.
   - Completion: the final answer contains no naked metric dump; every metric has an implication.

8. If creating or updating a skill, distill the observed workflow.
   Use `skill_view` for relevant existing skills, then save the new procedure with `skill_manage`. Do not include private trace IDs in the skill body unless they are necessary examples; keep trace IDs in the final report instead.
   - Completion: `skill_manage` reports success and the skill has a short frontmatter description under 60 characters.

## Pitfalls

- `getTrace` may return `conversation: []`; use spans and session history instead of inventing missing content.
- `getTraceSpan` may show empty `toolInput` / `toolOutput` when `latitude.captured.content` is false. That is a capture policy limit, not proof the tool had no arguments.
- Trace-level `errorRate` can be misleading when every run includes an abandoned fallback span. Inspect span `statusMessage` before calling a run failed.
- `listTools` can be very large and truncated. Prefer `queryAnalytics` for bounded summaries.
- Model and provider attribution can include fallback or routing providers. Check successful `chat` spans before making claims about the final answering model. Abandoned fallback spans can make trace-level provider analytics assign the same full trace cost to multiple providers; never sum those provider rows without span-level reconciliation.
- `costIsEstimated:true` means Latitude is not billing truth. For OpenRouter, compare direct key usage and reprice token categories using the current public model catalog; cached reads and writes are discounted, not free.
- A shared OpenRouter key destroys per-agent attribution. Separate agent/fleet/customer keys are the durable fix; use one-way equality checks without printing credentials when auditing reuse.
- `timeToFirstTokenNs: 0` often means not captured, not instant streaming.
- Latitude is historical telemetry. If the user asks whether an external system is currently correct, inspect that system directly before using Latitude as context.
- **Project exists ≠ fleet covered.** Count distinct `serviceNames` vs Orgo computer inventory.
- **Fleet covered ≠ customer adoption.** Separate provisioned, emitting, user-active, operationally used, and production-adopted agents. Sparse one-off telemetry is not sustained usage.
- **Service filters can fail open.** For trace listing use `filters.serviceNames` and verify every returned row's `serviceNames`; unknown singular keys may be silently ignored and return unrelated traces.
- **Count grain can differ.** Reconcile `queryAnalytics count` with `getTraceAnalytics` raw traces and `getUsersOverview` sessions/users before publishing totals.
- **Flagship volume can hide gaps** (Mia-class can dominate ~90% of traces while eng boxes emit nothing).
- **OpenClaw-only boxes** will not appear as `hermes-*` services; say so explicitly.
- **Gateway PID without `OTEL_*` is not definitive** if Latitude already shows that service; confirm with a fresh interaction after instrumentation changes.
- Never mix customer fleets into `dewey` or other customers' projects.
- Do not recommend full-fidelity prompt capture on insurance/legal customer fleets by default.
- **List≠create for monitors:** replaying nested `rule` JSON into create fails; use flat CreateMonitorBody.
- **Dry-run false positive:** dry-run can accept invalid nested create bodies; only live create + list proves success.
- **Shallow spans:** single `openai.chat` span does not mean no tools — read conversation from `traces get`.
- **Flagger flood ≠ done:** dozens of signals with zero monitors still need an ops monitor pack.
- **Fleet OTEL may be product-provisioned:** customer workbench provision (e.g. MomentumClaw `provision.ts`) can install Latitude via OTel `.pth` + `~/.hermes/.latitude.json` (project default `momentumclaw`) fail-open. Prefer that over hand-copying Dewey `LATITUDE_*` packs onto large fleets. OpenClaw-only product APIs will not emit `hermes-*` services.
- **Coverage work ≠ monitor work:** after an Orgo×Latitude matrix, still check `monitors list` on the customer project; zero monitors is a separate action pack.
- **`.latitude.json` present ≠ instrumented:** still need gateway-venv OTel packages, `latitude_bootstrap.pth`, and a live gateway; see `references/hermes-otel-backfill.md`.
- **Gateway kill inside Orgo exec:** naive kill of hermes gateway can SIGTERM the exec (−15) after files write; respawn supervisor with `start_new_session` and re-check port.
- **User said Hermes-only:** skip OpenClaw API dual-path work; instrument and operate `hermes-*` services only.
- **OTel pin clash:** openai 0.61.0 + anthropic 0.53.0 fails pip — use anthropic **0.61.0**.
- **Pilot Latitude when asked:** Budgetdog-class single-box still gets own project + backfill if Nick asks.
- **Spend before setup is not recoverable** — $0 in Latitude until post-setup traffic.
- **Never put API keys in remote exec source** that surfaces in `pgrep`/logs.
- **"Waiting for first trace" after wiring** — project/files alone are not enough. Smoke-test OTLP (`send_test_trace.py`), enable `latitude-telemetry-hermes` + `LATITUDE_PROJECT` in gateway env, restart on the VM, force one `hermes chat -Q` turn, then `traces list`. Hard-refresh the UI.
- **Tokens without cost** — OpenRouter/Grok may show tokens with Latitude cost still $0; report both.
- **Host blocks gateway restart strings** — Dewey terminal may refuse commands containing gateway kill/restart even when intended for a remote VM; use Orgo bash/API only.
- **Unquoted `.env` values with spaces** break `source` (e.g. user names) and can leave gateway without Latitude env.

## Verification

For review-only work, run one bounded `mcp__latitude__queryAnalytics` count over the chosen project and time range, then cite at least one returned trace ID or span status in the final insight. The review worked only if the final answer contains evidence-backed implications, not just raw telemetry.

For implementation work, also verify resource read-back and unit correctness:

- every created signal/monitor reads back by slug;
- any saved-search OAuth/API-key blocker is documented with the fallback used;
- monitor metric thresholds use analytics metric units, not blindly copied row-field units;
- capture/instrumentation changes compile;
- a synthetic no-content-mode test proves summary attributes are present and raw test secrets are absent;
- a fresh live trace is inspected when possible before claiming end-to-end success.
- customer pilot setup: `latitude traces list --project-slug <slug>` returns ≥1 item before telling Nick "it's live".
