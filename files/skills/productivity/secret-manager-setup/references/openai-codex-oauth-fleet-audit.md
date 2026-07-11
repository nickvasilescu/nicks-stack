# OpenAI Codex OAuth fleet audit and scrub

Use when Nick reports ChatGPT/Codex plan credits draining, suspects a customer Orgo VM is using operator OAuth (`nickv@testkey.com` / prolite), or asks to find where `openai-codex` credentials live.

## Fingerprint (no full tokens in chat)

From local `~/.hermes/auth.json` (or `~/.codex/auth.json`):

1. Decode JWT payload of `access_token` (middle segment, base64url).
2. Record only:
   - `https://api.openai.com/profile.email` (e.g. `nickv@testkey.com`)
   - `https://api.openai.com/auth.chatgpt_account_id`
   - `chatgpt_plan_type` (e.g. `prolite`)
   - `exp` / expired?

Search needles on remote boxes (presence only):

- email string
- account id UUID
- `user-MRMZ…` style chatgpt_user_id if known
- `openai-codex` + `chatgpt.com/backend-api/codex`

## Local usage first (often the real drain)

Before blaming customers, query Dewey `~/.hermes/state.db`:

```sql
-- billing_provider = 'openai-codex'
-- group by source: cli | telegram | agentphone-bridge
-- windows: 24h / 3d / 7d
-- top sessions by input+output tokens
```

Session finding (2026-07): Dewey burned ~11.7M openai-codex tokens in 7d (cli + telegram + agentphone-bridge on `gpt-5.5`). Customer MAGNUS had ~70.8M historical (Jun 15–24) then 0 for 14d after status `exhausted`.

Also check:

- default `config.yaml` model/provider
- `image_gen.provider: openai-codex` (image gens hit the same plan)
- agentphone bridge env: if `AGENTPHONE_HERMES_MODEL` / `PROVIDER` unset, bridge inherits global model (can be Codex)

## Fleet scan (Orgo)

```bash
orgo computers list --json > /tmp/orgo_computers.json
# prefer REST POST /computers/{id}/exec with Python code
# Hermes terminal rejects foreground nohup/& — remote scripts must use start_new_session=True / no shell &
```

Priority targets: names containing Hermes / known customers (Budgetdog, ORG, Jordan, Gus/MAGNUS, Mia, STBL, IdeaBrowser) + Dewey. Full 170-box scan is slow; start priority set.

Remote probe (presence + JWT email only):

1. Exists `~/.hermes/auth.json` / `~/.codex/auth.json`?
2. `credential_pool.openai-codex` / `providers.openai-codex` present?
3. Decode access JWT → email/plan/acct/expired
4. `state.db` last 7d tokens for `billing_provider='openai-codex'`
5. `last_status` (e.g. `exhausted`) and `last_refresh`

**Do not print access/refresh tokens.**

## Scrub customer box (operator OAuth only)

Goal: leave customer on their intended stack (usually OpenRouter) with zero operator Codex OAuth.

1. Backup: `~/.hermes/backups/auth.json.pre-codex-scrub-<ts>`
2. Delete `providers.openai-codex` and `credential_pool.openai-codex` if present
3. If `active_provider == "openai-codex"`, set to the real stack (`openrouter` when that is the only pool + config default)
4. Scrub `~/.codex/auth.json` only if it contains operator email/account id
5. Confirm strings gone: email, account id, `openai-codex` (except historical session DB — do not wipe state.db)
6. Restart Hermes gateway so in-memory pool drops (`kill` gateway PIDs, `Popen` `hermes gateway run --accept-hooks --replace` with start_new_session)

Remote exec reliability:

- Prefer base64-write script to `/tmp/…py` then `subprocess.run([python, script])` — long inline `exec` code can return empty stdout with success=true
- Avoid `&` / `nohup` in any string that passes through Dewey Hermes `terminal` tool

## Containment order

1. OpenAI account: revoke ChatGPT sessions / disconnect Codex OAuth (kills all refresh paths)
2. Scrub every fleet hit with operator fingerprint
3. Dewey: decide keep vs remove openai-codex; pin agentphone model override; move image_gen off openai-codex if not intentional
4. Templates/pilots: never bake `~/.hermes/auth.json` with operator OAuth into customer images (see `managed-hermes-on-orgo`)

## Related

- `managed-hermes-on-orgo` — customer deploy must not inherit Dewey auth
- `agentphone-setup` / poke-style bridge — always set model/provider CLI overrides
- `orgo-cloud-computers` — fleet list + remote exec
