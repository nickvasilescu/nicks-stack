---
name: hermes-latitude-observability
description: Set up and validate Hermes Agent observability in Latitude via the bundled observability/latitude plugin.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, latitude, observability, opentelemetry, plugins]
    created_by: agent
---

# Hermes Latitude Observability

Use when setting up or troubleshooting Latitude traces for Hermes Agent.

## What exists

The default Hermes install has a bundled plugin at:

`/usr/local/lib/hermes-agent/plugins/observability/latitude`

It emits OTLP/HTTP JSON directly to Latitude; no `latitude-telemetry` or OpenTelemetry Python dependency is required.

## Configuration

Secrets belong in `/root/.hermes/.env`:

```bash
HERMES_LATITUDE_API_KEY=<Latitude API key>
HERMES_LATITUDE_PROJECT=<Latitude project slug>
HERMES_LATITUDE_ENDPOINT=https://ingest.latitude.so/v1/traces
HERMES_LATITUDE_SERVICE=hermes-agent
HERMES_LATITUDE_ENV=local
```

Enable the plugin:

```bash
hermes plugins enable observability/latitude
```

Changes take effect in new Hermes sessions; restart CLI/gateway for already-running processes.

## Validation checklist

1. Confirm plugin is enabled:

```bash
hermes plugins list | grep -A2 -B1 -i latitude
```

2. Confirm config contains the plugin:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('/root/.hermes/config.yaml').read_text()) or {}
print('observability/latitude' in (cfg.get('plugins', {}).get('enabled') or []))
PY
```

3. Run plugin tests from the Hermes repo. If pytest-timeout is missing, disable that plugin flag:

```bash
cd /usr/local/lib/hermes-agent
python3 -m pytest tests/plugins/test_latitude_plugin.py -q -o 'addopts=' -p no:timeout
```

4. Validate real HTTP export using the plugin itself, not a hand-written curl payload. A successful result prints `plugin_real_http_statuses=200` or another 2xx:

```bash
cd /usr/local/lib/hermes-agent
python3 - <<'PY'
import os, sys, importlib.util, urllib.request
from pathlib import Path
for line in Path('/root/.hermes/.env').read_text().splitlines():
    if not line or line.lstrip().startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    os.environ[k.strip()] = v.strip().strip('"').strip("'")
plugin = Path('plugins/observability/latitude/__init__.py').resolve()
spec = importlib.util.spec_from_file_location('latitude_validation_real_http', plugin)
mod = importlib.util.module_from_spec(spec)
sys.modules['latitude_validation_real_http'] = mod
spec.loader.exec_module(mod)
mod.reset_for_tests()
orig_urlopen = urllib.request.urlopen
statuses = []
def wrapped_urlopen(*args, **kwargs):
    resp = orig_urlopen(*args, **kwargs)
    statuses.append(getattr(resp, 'status', None))
    return resp
urllib.request.urlopen = wrapped_urlopen
mod.on_pre_api_request(task_id='validation-task', turn_id='validation-turn', api_request_id='validation-turn:api:1', session_id='validation-session', platform='cli', model='validation-model', provider='hermes-validation', api_mode='chat_completions', started_at=1700000000.0, message_count=1, tool_count=0)
mod.on_post_api_request(task_id='validation-task', turn_id='validation-turn', api_request_id='validation-turn:api:1', session_id='validation-session', platform='cli', model='validation-model', provider='hermes-validation', api_mode='chat_completions', api_call_count=1, started_at=1700000000.0, ended_at=1700000001.0, api_duration=1.0, finish_reason='stop', response_model='validation-model', assistant_content_chars=2, assistant_tool_call_count=0, usage={'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2})
print('plugin_real_http_statuses=' + ','.join(str(s) for s in statuses))
PY
```

5. Smoke test a real Hermes turn:

```bash
hermes chat -Q -q 'Reply exactly: latitude smoke ok' --source latitude-smoke
```

## Success criteria

- Plugin list shows `latitude` enabled.
- `/root/.hermes/.env` permissions are `600`.
- Tests pass: `5 passed` for `tests/plugins/test_latitude_plugin.py`.
- Plugin validation export returns a 2xx status from Latitude ingest.
- Real Hermes smoke run returns the exact expected response.
- Latitude dashboard receives traces named `hermes.agent.turn` with child spans `hermes.llm.call` and, when tools are used, `hermes.tool.call`.

## Notes

The plugin exports one root span per agent turn and child spans for LLM calls, tool calls, and API errors. It intentionally avoids raw prompt/result capture by default; it records metadata such as provider, model, token usage, finish reason, tool name, duration, and status.
