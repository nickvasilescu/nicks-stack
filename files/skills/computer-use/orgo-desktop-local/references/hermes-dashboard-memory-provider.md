# Hermes dashboard: memory provider + API key (Orgo headed)

## Layout trap

On `http://127.0.0.1:9119/plugins` under **Runtime Provider Plugins**:

1. MEMORY PROVIDER dropdown (honcho, hindsight, mem0, …)
2. API KEY field (password; may show green **set** when env/provider file already has the key)
3. BASEURL optional (self-hosted only)
4. SAVE MEMORY PROVIDER

The dropdown sits **above** the key field. On 1280×720 pixel clicks aimed at the key often open the dropdown. SAVE with the wrong selection can switch `memory.provider` (observed: honcho → hindsight).

## Durable path (prefer)

1. Write secret to the provider's own store (e.g. `~/.hermes/honcho.json` `hosts.hermes.apiKey` and/or `HONCHO_API_KEY` in `~/.hermes/.env`).
2. `hermes config set memory.provider honcho` (or target provider).
3. Optionally map `secrets.onepassword.env.HONCHO_API_KEY` → `op://Hermes/Hermes Agent Secrets/HONCHO_API_KEY` (see skill `secret-manager-setup`).
4. Reload dashboard (F5). Expect badges **ready** + **active** and API KEY green **set**.
5. If the field still says “Leave blank to keep existing value”, leave blank and SAVE only when the selected provider is correct.

## When you must type in the UI

1. Escape until the dropdown is closed.
2. Measure the API KEY field y from the latest screenshot (horizontal dark input band), not memory.
3. Click field center → type → click SAVE MEMORY PROVIDER only (not the dropdown chevron).
4. Immediately re-check `hermes memory status` and `config.yaml` `memory.provider`.

## Honcho specifics

- Cloud default API: `https://api.honcho.dev` (leave BASEURL empty).
- App: `https://app.honcho.dev`.
- Host peer config lives in `~/.hermes/honcho.json` (workspace / aiPeer / peerName), not the dashboard form alone.
