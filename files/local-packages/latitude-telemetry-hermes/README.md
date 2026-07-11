# latitude-telemetry-hermes Dewey local package

Local editable fork of `latitude-telemetry-hermes` with Dewey-safe redacted summary capture and per-call reasoning-effort observability for Hermes Agent.

Each LLM span records the live Hermes-configured effort and the effective
provider request value separately. This makes provider clamps and models that
use native/provider-default reasoning visible instead of mislabeling them as
the global configuration value.

This package is installed into `/usr/local/lib/hermes-agent/venv` in editable mode so the telemetry patch survives normal package operations better than direct edits to `site-packages`.

Validate with:

```bash
python3 /root/.hermes/scripts/latitude/dewey_observability_validate.py
```
