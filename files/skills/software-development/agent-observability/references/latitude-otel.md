# Latitude OTLP Setup Notes

Condensed from official Latitude docs and this session's verified setup. Do not store API keys here.

## Official docs checked

- `https://docs.latitude.so/llms.txt`
- `https://docs.latitude.so/telemetry/otel-exporter.md`
- `https://docs.latitude.so/telemetry/python.md`
- `https://docs.latitude.so/telemetry/typescript.md`
- `https://docs.latitude.so/telemetry/claude-code.md`
- `https://docs.latitude.so/getting-started/skills.md`

## Latitude OTLP endpoint

Latitude accepts standard OTLP over HTTP:

```text
POST https://ingest.latitude.so/v1/traces
Authorization: Bearer <LATITUDE_API_KEY>
X-Latitude-Project: <project-slug>
Content-Type: application/json
```

Docs say HTTP `202` with `{}` means accepted. A live run in this session returned HTTP `200` with `{}`, also accepted.

## SDK package names

```text
Python: latitude-telemetry
TypeScript/JavaScript: @latitude-data/telemetry
```

Python docs import:

```python
from latitude_telemetry import Latitude, capture
```

TypeScript docs import:

```ts
import { Latitude, capture } from "@latitude-data/telemetry"
```

## Generic OTEL env helper shape

```bash
export LATITUDE_PROJECT_SLUG=dewey
export LATITUDE_INGEST_URL=https://ingest.latitude.so/v1/traces
export LATITUDE_SERVICE_NAME=hermes-agent
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="$LATITUDE_INGEST_URL"
export OTEL_EXPORTER_OTLP_TRACES_HEADERS="Authorization=Bearer ${LATITUDE_API_KEY},X-Latitude-Project=${LATITUDE_PROJECT_SLUG}"
export OTEL_SERVICE_NAME="$LATITUDE_SERVICE_NAME"
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

## Verified first-trace pattern

A dependency-free script can send an OTLP JSON `ExportTraceServiceRequest` with:

- `resourceSpans[].resource.attributes`: include `service.name`, environment, host.
- `scopeSpans[].scope.name`: e.g. `hermes-latitude-setup`.
- `spans[].traceId`: 16 random bytes / 32 hex chars.
- `spans[].spanId`: 8 random bytes / 16 hex chars.
- `spans[].name`: e.g. `hermes-latitude-test-trace`.
- `startTimeUnixNano` and `endTimeUnixNano`: strings.
- useful attributes such as `gen_ai.system`, project slug, and setup source.

Verification should record only non-secret values: HTTP status, response body shape, trace ID, span ID, project slug, and trace name.

## Session-specific paths from this setup

These paths are useful examples, not universal requirements:

```text
/root/.hermes/scripts/latitude/send_test_trace.py
/root/.hermes/scripts/latitude/env.sh
/root/.hermes/scripts/latitude/README.md
/root/dewey-vault-migration/staging/Dewey-Agent-Vault.v3-clean/AI/knowledge/latitude-observability-setup.md
```

## Lessons

- If the user's dashboard says "Waiting for your first trace", the fastest safe proof is a manual OTLP test trace after grounding the endpoint/headers in docs.
- A manual test trace proves credentials/project/ingest work. It does not mean the target app is automatically instrumented.
- For Hermes itself, do not claim native Latitude tracing exists unless the installed Hermes tree has explicit OTEL/Latitude hooks. Use a wrapper or code change for full automatic session/tool/LLM spans.
- If the user provides the API key in chat, write it to `.env` without echoing it back, then redact tool/final output to `<set>`.
