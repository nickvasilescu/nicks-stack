---
name: agent-observability
description: Instrument AI agents/apps with observability and tracing systems such as Latitude or OpenTelemetry, verify first traces, and record non-secret setup state.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [observability, tracing, opentelemetry, latitude, agents]
---

# Agent Observability

Use this skill when the user wants an AI agent, Hermes-adjacent workflow, or application instrumented so traces appear in an observability system. The default pattern is source-grounded setup, secret-safe configuration, one real first trace, and durable non-secret documentation.

## When to Use

- The user says a dashboard is "waiting for your first trace".
- The user provides a project slug, API key location, OTLP endpoint, tracing dashboard, or observability vendor.
- The task involves Latitude, OpenTelemetry, OTLP, traces, spans, sessions, tool calls, LLM observability, or agent telemetry.
- You need to verify that telemetry actually arrived rather than merely writing config.

## Procedure

1. Identify the product and authoritative docs.
   - Use external grounding for current vendor docs when the user asks about a third-party observability product.
   - Prefer official docs over summaries. For Latitude, read the Markdown docs where available, e.g. `/telemetry/otel-exporter.md`, `/telemetry/python.md`, and `/telemetry/typescript.md`.
   - Record package names and endpoints from docs, not guesses.

2. Separate three levels of setup.
   - Config present: env vars or config files exist.
   - Instrumentation active: app/agent creates spans around real work.
   - Trace verified: the remote dashboard or ingest endpoint accepted a real payload.
   Do not claim the system is "set up" until at least the level the user requested is verified.

3. Handle secrets safely.
   - Store API keys only in the intended secret location such as `.env`, a secret manager, or vendor CLI auth store.
   - Do not write keys into vault notes, skills, memory, final answers, logs, or support files.
   - In reports, show `LATITUDE_API_KEY=<set>` or equivalent, never the value.

4. Create a dependency-minimal first-trace path when native instrumentation is absent.
   - If the app has no OTEL SDK and the user only needs to unblock "first trace", create a small deterministic OTLP test sender.
   - Validate it fails safely without the API key before sending a real trace.
   - When the key is available, send one real trace and record HTTP status, response shape, trace ID, span ID, and project slug.

5. Prefer OpenTelemetry-compatible env helpers for future apps.
   - Export endpoint and headers in a reusable script rather than hardcoding them into every app.
   - Typical OTLP env shape:

```bash
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=<vendor-traces-endpoint>
OTEL_EXPORTER_OTLP_TRACES_HEADERS="Authorization=Bearer ${API_KEY},X-Latitude-Project=${PROJECT_SLUG}"
OTEL_SERVICE_NAME=<service-name>
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

6. For full automatic traces, instrument the actual runtime.
   - Python apps: install the vendor SDK or OpenTelemetry SDK in the app venv, initialize before LLM calls, and wrap request/agent turns in capture/context spans.
   - TypeScript apps: install the vendor SDK, initialize before LLM clients, and flush before short-lived CLIs/tests exit.
   - Generic runtimes: configure OTLP HTTP exporter with endpoint + auth/project headers.
   - A manual test trace proves ingest works; it does not prove the agent/app is fully instrumented.

7. Record non-secret state in the project knowledgebase when one exists.
   - Include project slug, endpoint, helper script paths, verification timestamp, trace ID, and next instrumentation steps.
   - Exclude API keys and sensitive payload contents.
   - If the knowledgebase is synced, verify the note itself is synced after writing it.

8. For Latitude Users, attach a stable user identity to traces.
   - Latitude does not need a separate user creation step; the Users page is populated from trace metadata.
   - If traces exist but Users says "No users yet", check `listTraces`/trace details for `userId: null` and `getUsersOverview` for `identifiedTraces: 0`.
   - In SDK integrations, pass `userId`/`userEmail` (TypeScript) or `user_id`/`user_email` (Python) at the request/agent-turn boundary.
   - In raw OTLP or Hermes-plugin integrations, attach `user.id` and, when known, `user.email`/`user.name` to the root interaction span; keep `session.id` separate for conversation grouping.
   - For multi-user gateways, derive user id from platform/user context; do not hardcode the operator's email for every trace.

## Latitude Quick Reference

See `references/latitude-otel.md` for the session-grounded Latitude OTLP details, `references/latitude-mcp.md` for Hermes MCP configuration using header auth, and `references/latitude-users.md` for attaching user identity so the Latitude Users page populates. Use `scripts/send_latitude_test_trace.py` when you need a reusable dependency-free first-trace probe.

Core Latitude OTLP path:

```text
Endpoint: https://ingest.latitude.so/v1/traces
Authorization: Bearer <LATITUDE_API_KEY>
X-Latitude-Project: <project-slug>
```

Official SDKs/connectors found during setup:

```text
Python apps: latitude-telemetry
TypeScript/JavaScript apps: @latitude-data/telemetry
Hermes native plugin: latitude-telemetry-hermes
```

For Hermes Agent specifically:

- Install the native package into the Hermes venv, not system Python: `/usr/local/lib/hermes-agent/venv/bin/python -m pip install latitude-telemetry-hermes`.
- Enable plugin `latitude` in `~/.hermes/config.yaml` under `plugins.enabled` if the CLI plugin enable command does not surface the entry-point plugin.
- Validate with Hermes' `PluginManager`, not just `hermes plugins list`; entry-point plugins may be discoverable by the manager even when the list output omits them.
- For short-lived `hermes chat -q` runs, verify the connector flushes before process exit. If traces disappear from one-shot runs but appear from long-lived sessions, inspect the connector transport for daemon-thread shipping.

A successful first-trace sender should produce a 2xx status with `{}` and a trace/span ID generated locally.

## Pitfalls

- Do not confuse a stored API key with working telemetry.
- Do not confuse a manual OTLP test trace with full app instrumentation.
- Do not install instrumentation into the wrong Python venv or Node project; resolve the app runtime first.
- Do not print the API key while proving it is present.
- Do not persist a user-provided one-off API key in skills or memory.
- If a vendor docs page is rendered as noisy HTML, look for `.md` or `llms.txt` versions before scraping the page.
- Some docs may say HTTP `202` is the expected success code, but live endpoints may return another 2xx with `{}`; treat any 2xx plus empty/success body as accepted, while recording the exact status.
- For hosted Latitude, do not set `LATITUDE_BASE_URL` globally to the ingest origin. The Latitude CLI interprets `LATITUDE_BASE_URL` as the API base URL, so `LATITUDE_BASE_URL=https://ingest.latitude.so` makes API reads hit ingest and return 404s. Leave it unset unless using a private/self-hosted API URL.
- Latitude MCP does not have to use OAuth. In non-interactive/headless Hermes sessions, prefer header auth with the existing API key: `headers.Authorization: Bearer ${LATITUDE_API_KEY}`. `hermes mcp login latitude` starts a browser OAuth flow and only works when the user can authenticate and return the redirect/callback. See `references/latitude-mcp.md`.
- Do not claim saved searches, monitors, datasets, evaluations, signals, Slack/PostHog, or dispatch are configured merely because their read/list APIs work. Creation can be blocked by API-key permissions or require user policy choices; record those as gates unless create/update calls actually succeed.

## Verification

- Secret presence: print only booleans or `<set>` markers for required env keys.
- Syntax: compile or lint any helper scripts.
- Negative path: run without the API key and verify a clear non-zero failure.
- Positive path: send a trace with the real key and record status, response shape, trace ID, and span ID.
- If a synced vault or docs repo was updated, verify sync/commit state separately.
