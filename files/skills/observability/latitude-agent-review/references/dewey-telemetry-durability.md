# Dewey Latitude telemetry durability and saved-search caveats

## Context

During the Dewey Latitude observability rollout, the connector changes were first applied directly under Hermes' venv `site-packages`. That validated quickly, but it was not durable: a package reinstall or Hermes venv rebuild could replace those files.

## Durable patch pattern

When a Hermes plugin or connector must be patched locally and upstreaming is not immediate:

1. Copy the patched package into a local editable package directory, for example:
   `~/.hermes/local-packages/<package-name>/`.
2. Add a minimal `pyproject.toml` preserving the original entry point group.
   For the Latitude connector, the key entry point is:
   ```toml
   [project.entry-points."hermes_agent.plugins"]
   latitude = "latitude_telemetry_hermes"
   ```
3. Install into the Hermes venv in editable mode:
   ```bash
   /usr/local/lib/hermes-agent/venv/bin/python -m pip install -e ~/.hermes/local-packages/latitude-telemetry-hermes
   ```
4. Verify import location, package version, and entry point:
   ```bash
   /usr/local/lib/hermes-agent/venv/bin/python - <<'PY'
   import importlib.metadata as md, pathlib
   import latitude_telemetry_hermes
   print(md.version('latitude-telemetry-hermes'))
   print(pathlib.Path(latitude_telemetry_hermes.__file__).resolve())
   print([str(ep) for ep in md.entry_points().select(group='hermes_agent.plugins') if ep.name == 'latitude'])
   PY
   ```
5. Keep a repair script under `~/.hermes/scripts/latitude/` so a venv rebuild can restore the editable package quickly.

## Per-call reasoning-effort observability

Do not label reasoning from the global config alone. Hermes can change the live setting with `/reasoning`, providers can clamp it, and models such as Grok 4.5 can reason natively while rejecting an explicit effort dial.

For Dewey, the durable Latitude plugin records these attributes on every `llm_request` span:

- `hermes.reasoning_effort`: easy-filter alias for the live configured value.
- `hermes.reasoning_effort.configured`: live Hermes value for that API call.
- `hermes.reasoning_effort.effective`: final provider-request value, or `provider_default` when no effort dial was sent.
- `hermes.reasoning_effort.explicit`: whether an effort/toggle was actually present in the final request.
- `hermes.reasoning_effort.source`: `explicit_effort`, `explicit_toggle`, or `provider_default`.
- `gen_ai.request.reasoning_effort`: emitted only when the final request carries an explicit effort.
- `gen_ai.usage.reasoning_tokens`: actual returned reasoning-token usage when the provider reports it.

The plugin compares two sources:

1. `reasoning_config` passed by Hermes' `pre_api_request` hook after session overrides.
2. The sanitized final request body after provider mapping and LLM request middleware.

Hermes core currently needs this hook kwarg in `agent/conversation_loop.py`:

```python
reasoning_config=agent.reasoning_config,
```

Keep that one-line hook addition in `~/.hermes/scripts/latitude/install_local_telemetry_patch.sh`; Hermes upgrades can replace the core file even though the editable plugin itself survives. Validation must assert both that the hook line exists and that synthetic request cases cover explicit effort, provider clamp, explicit disable, and provider-default/native reasoning.

A verified Grok 4.5 Dewey span showed the intended distinction: configured `xhigh`, effective `provider_default`, explicit `false`, and nonzero reasoning tokens. This means Grok reasoned, but the request did not send an xhigh dial. Never report xhigh as the effective Grok 4.5 effort in that case.

## Validation script pitfall

Validation scripts should locate the package dynamically from Python import metadata rather than hardcoding `site-packages`. Editable installs move the import path. Use:

```python
import pathlib, latitude_telemetry_hermes
plugin_dir = pathlib.Path(latitude_telemetry_hermes.__file__).resolve().parent
```

Then run `py_compile` against that directory.

## Latitude metric unit pitfall

Latitude trace rows expose fields such as `costTotalMicrocents` and `durationNs`, but monitor/analytics metric fields use normalized units:

- `cost` is dollars.
- `duration` is seconds.
- `tokens` is token count.

Before setting monitor thresholds, query `queryAnalytics` for max values over a recent window and confirm the unit scale. Do not copy row-field units into metric thresholds.

## Saved-search auth caveat

The Latitude MCP can be configured with API-key/header auth and still create/read signals and monitors. Persisted saved-search endpoints may require OAuth user auth. If saved-search creation is blocked under API-key auth, use inline monitor targets for functional alerting. Only add a separate OAuth MCP connection when literal saved-search objects are required in the UI.

Avoid replacing a working API-key MCP with OAuth during an observability rollout. If OAuth is needed, add a separate server name such as `latitude-oauth`, authenticate it interactively, and leave the stable API-key MCP in place until the OAuth path is verified.
