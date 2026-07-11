# Researching model and product releases / announcements via X

This captures durable read-only patterns that worked for checking a major AI model release (Grok 4.5 on 2026-07-08) using the authenticated xurl bridge.

## Core commands that succeeded

Always use the named app profile for user context:

```bash
xurl auth status
xurl search "grok 4.5" -n 5 --app hermes-x
xurl search "grok 4.5 (release OR launch OR available OR public)" -n 5 --app hermes-x
xurl search "from:elonmusk Grok 4.5" -n 3 --app hermes-x
xurl search "from:SpaceXAI Grok 4.5" -n 3 --app hermes-x
xurl posts xai -n 5 --app hermes-x   # fallback; some user lookups fail with auth errors — prefer search
```

## Cross-reference with local Hermes model state

After gathering X signals, verify what is actually configured and available:

- `hermes status` (look for "Model:" and "Provider:" lines)
- `hermes config get model` or read `~/.hermes/config.yaml` (model.default + provider + base_url)
- Parse provider cache:
  ```python
  python3 -c '
  import json
  with open("~/.hermes/provider_models_cache.json") as f: data = json.load(f)
  for p in ["xai-oauth", "xai"]:
      if p in data: print(p, "has grok-4.5?", "grok-4.5" in data[p].get("models", []))
  '
  ```
- Direct API list (sanitized):
  ```bash
  curl -s -H "Authorization: Bearer $(grep -o 'xai-[^ ]*' ~/.hermes/.env | head -1)" \
    https://api.x.ai/v1/models | python3 -c '... filter grok* ids ...'
  ```

## Lessons

- `grok-build-0.1` and `grok-4.5` appeared as distinct IDs in the xAI endpoint.
- Some models (e.g. grok-4.5) were present under plain "xai" provider list but not (at the time) under the active "xai-oauth".
- Official announcement used "grok-4.5" in the API example and positioned it as default in "Grok Build".
- Always cross-check X signals against live Hermes config + provider cache + direct /models before assuming the configured model is the newly released one.

Use these patterns for any timely model, CLI, or product announcement research. Combine with `xurl search "from:officialaccount keyword"` for precision.

Update the local model when confirmed:
`hermes config set model.default grok-4.5`
