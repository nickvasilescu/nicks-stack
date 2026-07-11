---
name: secret-manager-setup
description: "Set up external secret managers for headless agent/Hermes environments, especially 1Password CLI service-account flows and op:// secret references; Dewey vendor key probes; Composio-vs-Hermes boundary; related OAuth status (Anthropic headless PKCE, Spotify, Codex)."
version: 1.4.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [secrets, 1password, bitwarden, op-cli, hermes, setup]
---

# Secret Manager Setup

Use this skill when configuring an agent or Hermes installation to load API keys and tokens from an external secret manager instead of storing raw secrets directly in `.env` files. It is especially relevant for headless Linux VMs, Orgo computers, gateway agents, cron jobs, and long-running Hermes profiles.

Authoritative product docs still win over this skill. For Hermes-specific commands, verify against `hermes secrets --help` and the official Hermes secrets docs when available.

## Core workflow

1. Identify the secret manager and runtime shape.
   - Headless server or Orgo VM: prefer a service-account token or machine credential.
   - Personal laptop with GUI unlock: interactive desktop-app integration may be acceptable.
   - Long-running Hermes gateway or cron: avoid short-lived interactive sessions unless only testing.

2. Install and verify the vendor CLI.
   - 1Password CLI command: `op`.
   - Check: `command -v op && op --version`.

3. Enable the Hermes secret source.
   - Inspect support: `hermes secrets --help`.
   - 1Password help: `hermes secrets 1password --help`.
   - Setup: `hermes secrets 1password setup --binary-path "$(command -v op)"`.

4. Authenticate the CLI in a way appropriate to the runtime.
   - Recommended for headless Hermes: `OP_SERVICE_ACCOUNT_TOKEN`.
   - Less durable: `op signin` interactive session, which can expire.

5. Map Hermes env vars to secret references.
   - 1Password reference shape: `op://Vault Name/Item Name/Field Name`.
   - Example: `hermes secrets 1password set OPENROUTER_API_KEY 'op://Automation/Hermes Agent/OPENROUTER_API_KEY'`.

6. **Validate before trusting a new field.**
   - Field exists ≠ correct secret. Users often paste the wrong value (UUID, other product key).
   - `op read` the reference; print only metadata (length, prefix class), never the secret.
   - Call the vendor auth API (e.g. GitHub `GET /user`) and require HTTP 200.
   - **Only then** run `hermes secrets 1password set` + sync.

7. Verify resolution before removing local secrets.
   - Dry run: `hermes secrets 1password sync`.
   - Apply/export if needed by current shell: `hermes secrets 1password sync --apply`.
   - Status: `hermes secrets 1password status`.
   - Vendor-level test: `op read 'op://Vault/Item/Field'` (do not echo the value into chat).

8. Only after successful resolution, consider cleaning raw duplicated secrets from `.env`.
   - Keep non-secret config values in `.env`.
   - Do not delete raw secrets until the agent can restart and resolve references successfully.

## 1Password on headless VMs

For a long-running agent VM, ask for or create a 1Password service account with read access to the vault/items containing the agent secrets. The user usually needs to provide the service account token, commonly resembling `ops_...`, and the vault/item/field names or exact `op://...` references.

If the user wants the agent to create the 1Password item from an existing `.env`, the service account needs `read_items,write_items` on a non-personal vault. 1Password service accounts cannot access Personal/Private vaults, so ask the user to create or name a shared/custom vault such as `Dewey`, `Automation`, or `Agent Secrets`.

Manual account login is possible but inferior for a server because `op signin` sessions are short-lived. Use it for temporary testing only unless the user explicitly wants that trade-off.

When a service-account token is pasted into chat or logs, finish the setup, verify it, then recommend rotating that token and replacing `OP_SERVICE_ACCOUNT_TOKEN`. The token is the bootstrap secret and must remain protected even after other API keys move into 1Password.

## Pitfalls

- Do not confuse the 1Password SSH agent with 1Password secret resolution. A config like `IdentityAgent "~/Library/Group Containers/.../agent.sock"` is for SSH private keys on the user's local Mac, not for resolving API keys on a Linux VM.
- Do not claim setup is complete just because the integration is enabled. Complete setup requires an authenticated CLI plus at least one mapped reference and a successful sync/read test.
- Missing `op` is a setup state, not a durable tool limitation. Install the CLI, then retry.
- Service-account permissions matter. A token may authenticate but still fail to read a vault/item/field if the account lacks access.
- Do not pass migrated secret values as `op item create` assignment arguments. Assignment arguments can be visible in process listings or shell history. Use a JSON template through stdin for secret-valued fields.
- Do not remove raw `.env` secrets immediately after a successful Hermes sync if external scripts or services source `.env` directly. First verify those services either run under Hermes secret resolution or can read the replacement source.
- If a user pasted a service-account token into a chat transcript, treat setup as provisional. After verification, recommend token rotation and replace only `OP_SERVICE_ACCOUNT_TOKEN` with the new token.
- **Never dump full `op item get --format=json` into the transcript** when the item holds multiple API keys; use single-field `op read` and print metadata only.
- **Do not map a secret that fails its vendor auth test** (e.g. GitHub 401 with a UUID-shaped "PAT").
- Discovery endpoints are not always authentication checks. Vercel AI Gateway `GET /v1/models` may return HTTP 200 with an invalid credential; require a minimal authenticated `POST /v1/chat/completions` before trusting the key.
- Vercel AI Gateway keys are one-time `vck_…` secrets. A 36-character UUID is the key ID, not the bearer token (`apiKeyString`); create a new key because the plaintext cannot be retrieved later.
- Replacing a 1Password field does not refresh secrets already injected into a running Hermes process. Clear `~/.hermes/cache/op_cache.json`, then fully quit and restart the CLI or restart the gateway. `/reload` only rereads `.env`; it does not rerun external secret sources such as 1Password.
- **Query-string MCP credentials can leak in CLI diagnostics.** A config such as `url: https://example/mcp?key=${API_KEY}` safely keeps the raw key out of `config.yaml`, but `hermes mcp test <name>` currently prints the fully resolved URL. Do not run that command in shared logs/transcripts for query-key MCPs. Prefer a minimal vendor/MCP initialize probe whose output reports only HTTP status and protocol markers, or use header auth when the vendor supports it. If a resolved URL is printed into a transcript, treat the key as exposed and recommend rotation.
- GitHub PATs: expect `ghp_…` or `github_pat_…`. Len-36 UUID values are wrong even if the field is named `GITHUB_PAT` (common paste = Latitude-style UUID).
- Map **both** `GITHUB_TOKEN` and `GH_TOKEN` to the same PAT field so curl, git `x-access-token`, and future `gh` all resolve.
- After GitHub mapping: Composio `github` toolkit is fine for lightweight API recon; use the PAT for private shallow clones when reading source trees.
- Bundled `github-auth` / `github-repo-management` may be unpatchable in curator mode; keep durable GitHub+1Password procedure **here** and in `vault-managed-customer-agents/references/product-code-repo-recon.md` + `github-collaborator-invites.md` (username API accept vs email Gmail invites).
- Collaborator invites sent to an **email** may not appear on `GET /user/repository_invitations` for the PAT login — check Gmail before telling the user to re-invite.

## Dewey field catalog (Hermes Agent Secrets)

Canonical item: `op://Hermes/Hermes Agent Secrets/<FIELD>`.

| Env var | 1P field | Shape check | Vendor smoke (require 200) | Notes |
|---|---|---|---|---|
| `GITHUB_TOKEN` + `GH_TOKEN` | `GITHUB_PAT` | `ghp_` / `github_pat_` | `GET https://api.github.com/user` Bearer | Map both env names |
| `LATITUDE_API_KEY` | same | often UUID-like 36 | Latitude API / telemetry path | Historical map |
| `ORGO_API_KEY` | same | long opaque | Orgo API | Historical map |
| `TELEGRAM_BOT_TOKEN` | same | bot token shape | Telegram getMe | Historical map |
| `AGENTMAIL_API_KEY` | same | long opaque | AgentMail | Historical map |
| `AGENTPHONE_API_KEY` | same | long opaque | AgentPhone | Historical map |
| `EXA_API_KEY` | same | often UUID-like 36 | `POST https://api.exa.ai/search` Bearer | Native web-exa |
| `FIRECRAWL_API_KEY` | same | often `fc-…` | `GET https://api.firecrawl.dev/v1/team/credit-usage` Bearer | Enable `web-firecrawl` after map |
| `BROWSER_USE_API_KEY` | same | often `bu_…` | `GET https://api.browser-use.com/api/v2/tasks` header `X-Browser-Use-API-Key` | Not Bearer |
| `OPENROUTER_API_KEY` | same | `sk-or-…` | `GET https://openrouter.ai/api/v1/auth/key` Bearer | 1P override wins when enabled |
| `XAI_API_KEY` | same | `xai-…` | `GET https://api.x.ai/v1/models` Bearer | Parallel to xAI OAuth |
| `AI_GATEWAY_API_KEY` | `VERCEL_AI_GATEWAY_API_KEY` | `vck_…`; UUID is only the key ID | Authenticated `POST https://ai-gateway.vercel.sh/v1/chat/completions` | `/v1/models` alone is not an auth test; named Hermes provider `custom:vercel-ai-gateway` |
| `MODEL_API_KEY` | `META_API_KEY` | `LLM|…` (secret redaction may alter the displayed separator) | Authenticated `POST https://api.meta.ai/v1/responses` | Meta Model API; model `muse-spark-1.1`; named Hermes provider `custom:meta-model-api` with `codex_responses` transport |
| `HONCHO_API_KEY` | same | `hch-…` (often `hch-at-…`) | `hermes memory status` → provider honcho available | Also keep `~/.hermes/honcho.json` hosts.hermes.apiKey; optional non-secret 1P text fields for base URL / workspace |
| `IDEABROWSER_KEY` | same | `ib_…` (~50 chars) | MCP initialize HTTP 200 + `protocolVersion` (do not print full URL with key) | Hosted MCP uses `?key=${IDEABROWSER_KEY}`; procedure `references/ideabrowser-mcp-hermes.md` |

### Meta Model API / Muse Spark on Dewey

Map the official runtime variable to the existing 1Password field, then register a named Responses-API provider:

```bash
hermes secrets 1password set MODEL_API_KEY \
  'op://Hermes/Hermes Agent Secrets/META_API_KEY'
rm -f ~/.hermes/cache/op_cache.json

hermes config set providers.meta-model-api.name 'Meta Model API'
hermes config set providers.meta-model-api.api 'https://api.meta.ai/v1'
hermes config set providers.meta-model-api.key_env 'MODEL_API_KEY'
hermes config set providers.meta-model-api.transport 'codex_responses'
hermes config set providers.meta-model-api.default_model 'muse-spark-1.1'
hermes config set providers.meta-model-api.context_length '1048576'
```

Use `--provider custom:meta-model-api --model muse-spark-1.1` for an isolated smoke. After a basic response and a real Hermes tool-call loop both pass, make it the default with `model.provider`, `model.default`, and `model.api_mode=codex_responses`, then restart a running gateway.

Direct API pitfall verified 2026-07-09: Meta Responses accepts only `tool_choice: "auto"`; `"required"`, `"none"`, and named choices return HTTP 400. Force tool-use smokes through the prompt rather than `tool_choice: "required"`. Do not add `providers.meta-model-api.max_output_tokens` on Hermes v0.18.2; runtime may lift it, but config normalization warns that it is an unknown provider key.

### Adding a field to an existing 1P item (Dewey)

```bash
export OP_SERVICE_ACCOUNT_TOKEN=...   # from env, never print
op item edit "Hermes Agent Secrets" --vault Dewey \
  "HONCHO_API_KEY[password]=${HONCHO_API_KEY}"
# optional non-secret metadata as text fields
op item edit "Hermes Agent Secrets" --vault Dewey \
  "HONCHO_BASE_URL[text]=https://api.honcho.dev"
```

Wire Hermes injection under `secrets.onepassword.env` in `config.yaml`:

```yaml
HONCHO_API_KEY: op://Hermes/Hermes Agent Secrets/HONCHO_API_KEY
```

`hermes config set secrets.onepassword.env.HONCHO_API_KEY 'op://…'` may fail (nested path treated as env name). Prefer a surgical YAML edit next to the other maps, then:

```bash
rm -f ~/.hermes/cache/op_cache.json
hermes memory status   # should log: 1Password: applied N secrets (... HONCHO_API_KEY ...)
```

Verify with `op read 'op://Hermes/Hermes Agent Secrets/HONCHO_API_KEY'` (metadata only in chat: len/prefix/suffix).

After mapping web/browser keys, enable matching plugins if needed and start a new session so injection + plugin load apply.

Do not invent API-key 1P fields for OAuth-preferred providers on Dewey:
- OpenAI Codex → `hermes auth` / openai-codex OAuth
- Anthropic Claude Pro/Max → Anthropic OAuth (not ANTHROPIC_API_KEY by default)
- Spotify → `hermes auth spotify` + HERMES_SPOTIFY_CLIENT_ID

## Composio vs Hermes secrets

Composio connections do not export raw credentials for Hermes `secrets.onepassword` maps, `.env`, or `auth.json`. Treat Composio as a parallel tool proxy. Native Hermes plugins need 1Password maps or Hermes OAuth.

## Operator OpenAI Codex OAuth (subscription drain)

When ChatGPT/Codex credits drain mysteriously:

1. Fingerprint local JWT email + account id (never print tokens).
2. Measure **local** Hermes `state.db` usage by `billing_provider=openai-codex` and `source` (cli/telegram/agentphone-bridge) before blaming customers.
3. Fleet-scan Orgo Hermes boxes for the same email/account id; scrub customer hits; leave them on OpenRouter/API keys.
4. Revoke OpenAI sessions if refresh tokens may still exist anywhere.

Full procedure: `references/openai-codex-oauth-fleet-audit.md`.
Customer isolation: `managed-hermes-on-orgo` → `references/operator-oauth-isolation.md`.

## Useful references

- `references/onepassword-hermes.md` — command sequence, safe reads, GitHub PAT, full setup
- `references/vercel-ai-gateway-hermes.md` — 1Password mapping, named custom-provider config, `vck_` versus UUID key IDs, and authenticated smoke tests
- `references/dewey-vendor-key-probes.md` — vendor validation probes (metadata only, never print secrets)
- `references/composio-vs-hermes-auth.md` — Composio does not export Hermes credentials
- `references/composio-discordbot-auth.md` — Discordbot BYO OAuth2 props (client_id, client_secret, bot bearer_token); Managed App unavailable
- `references/anthropic-headless-pkce.md` — Claude Pro/Max OAuth when CLI input EOF-fails
- `references/spotify-and-oauth-status.md` — Spotify check_fn + Codex/Anthropic status
- `references/openai-codex-oauth-fleet-audit.md` — JWT fingerprint, fleet scan, scrub, containment
- `references/ideabrowser-mcp-hermes.md` — IdeaBrowser 1P field, `${IDEABROWSER_KEY}` MCP URL, non-interactive `hermes mcp add`, avoid `mcp test` in transcripts
- Dewey GitHub field: `op://Hermes/Hermes Agent Secrets/GITHUB_PAT` → `GITHUB_TOKEN` + `GH_TOKEN` only after `GET /user` returns 200
