---
name: hermes-gateway-onboarding
description: Class-level workflow for configuring Hermes Agent messaging gateway platforms, especially QR/managed onboarding flows such as Telegram.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, gateway, messaging, telegram, onboarding, qr, bot]
    related_skills: [hermes-agent]
created_by: agent
---

# Hermes Gateway Onboarding

Use this skill when setting up, repairing, or validating Hermes Agent messaging gateway integrations: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Teams, or similar gateway-backed surfaces. It is especially relevant when the user wants a scannable/phone-friendly onboarding flow rather than manual token copy-paste.

Authoritative source: official Hermes docs and the installed Hermes CLI/source for the current machine. The `hermes-agent` skill remains the broad protected reference; this skill captures operational patterns learned from real gateway setup work.

## Success criteria

A gateway setup is not complete when config is written. It is complete only when:

1. The platform credential exists in `~/.hermes/.env` or the active profile env file.
2. The platform is enabled by config/env and visible to `hermes gateway status` or the running gateway logs.
3. Access control is explicit: allowlist, DM pairing, or deliberate open access.
4. A home channel is configured when the user expects cron/job/notification delivery.
5. The gateway process is actually running, or a durable start mechanism is installed.
6. A real inbound or outbound platform message has been tested when credentials are available.

## General workflow

1. Load current Hermes context first.
   - Use official docs as source of truth.
   - Check installed CLI/source because gateway features often evolve faster than docs.
   - Prefer Hermes-native commands/config helpers over hand-editing where possible.

2. Identify the active profile.
   - Default profile uses `~/.hermes/config.yaml` and `~/.hermes/.env`.
   - Named profiles use `~/.hermes/profiles/<name>/`.
   - Do not write another profile unless the user explicitly asked for it.

3. Determine whether the user wants automatic or manual onboarding.
   - Automatic/QR: use managed onboarding if the platform supports it.
   - Manual: collect token/IDs from the user or from a provider-specific setup flow.

4. Configure secrets in `.env`, not `config.yaml`.
   - Tokens go in `.env`.
   - Non-secret platform behavior can go in `config.yaml` under the platform's supported section.

5. Configure access control.
   - Telegram specifically is fail-closed unless `TELEGRAM_ALLOWED_USERS`, platform/group allowlists, pairing, or `GATEWAY_ALLOW_ALL_USERS=true` is configured.
   - Prefer allowlisting the detected owner ID when managed onboarding returns it.
   - Set `TELEGRAM_HOME_CHANNEL` to the owner DM chat/user ID if the user wants cron and notifications routed to Telegram.

6. Start or restart the gateway.
   - If service management exists, prefer `hermes gateway install` / `hermes gateway start` / `hermes gateway restart`.
   - If no service manager is available, run `hermes gateway run --accept-hooks` under a tracked background process or a deliberate detached process with logs.
   - Do not claim the bot is live until logs or a process check confirms the gateway is running.

7. Validate.
   - Check gateway status/logs.
   - Confirm platform API connectivity where possible.
   - Send or receive a real message when feasible.

## Telegram managed QR onboarding pattern

Hermes includes a managed Telegram onboarding client in `hermes_cli.telegram_managed_bot`. It can create a user-owned bot via Telegram's managed bot flow without manual BotFather token copy-paste.

Operational sequence:

1. Create a pairing with bot name, e.g. `Dewey`.
2. Render the returned `qr_payload` as terminal QR and provide the fallback deep link.
3. Start a poller that waits for the user to confirm bot creation in Telegram.
4. When ready, save:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_BOT_USERNAME` when returned
   - `TELEGRAM_ALLOWED_USERS` from `owner_user_id` when returned
   - `TELEGRAM_HOME_CHANNEL` from the same owner user ID when appropriate
5. Start/restart the gateway.
6. Ask the user to send the bot a test message if no inbound test was observed yet.

See `references/telegram-managed-qr-onboarding.md` for poller pattern, desktop QR poster, expiry refresh, and BotFather manual fallback.

## Live-call reliability (learned 2026-07)

Managed QR is good for desk setup, **fragile on live sales calls**:

- Pairings from `setup.hermes-agent.nousresearch.com` often expire in **~5 minutes** (API returns `410` / `status: expired`).
- Customer can create a bot on their phone after expiry and still get **no token delivered** to Hermes. Symptom: bot exists, `/start` does nothing, `.env` has no `TELEGRAM_BOT_TOKEN`, gateway logs `No messaging platforms enabled`.
- **Do not claim Telegram is connected from a scan alone.** Require: token in `.env`, `getMe` OK (username only, never print token), gateway process up, logs show `telegram connected`, and ideally one real inbound/outbound message.

**Preferred live-call path when QR stalls:** BotFather manual:

1. Customer: `@BotFather` → `/newbot` → display name + username ending in `bot`
2. Paste API token into `configure_telegram_manual.sh` or `save_env_value('TELEGRAM_BOT_TOKEN', ...)`
3. Set `TELEGRAM_ALLOWED_USERS` + `TELEGRAM_HOME_CHANNEL` (owner numeric ID from managed result or `@userinfobot`)
4. `set -a; source ~/.hermes/.env; set +a` then `hermes gateway run --accept-hooks` (or service restart)
5. Verify with redacted `getMe` + customer DM `hi`

Keep a **Refresh QR** regenerator on the desktop for call desks; always show expiry time + deep link fallback.

## Pitfalls

- A QR code alone does not configure Hermes. The process must also poll for the created bot token, write `.env`, and start/restart the gateway.
- Managed pairings expire quickly (~5 min). Refresh the pairing immediately before the customer scans; never reuse an expired `pairing_id`.
- “I set up the bot” ≠ Hermes configured. Always check token presence and gateway platform enablement.
- Never reuse the operator/Dewey Telegram bot on a customer computer.
- Telegram bot display name and username are different. Display name can be free text; username must be globally unique and end in `bot`.
- Telegram group behavior depends on BotFather privacy mode. DMs are simpler; group bots may need privacy disabled or admin status.
- Do not expose Telegram bot tokens in chat, logs, or config summaries.
- If the terminal cannot render a QR code cleanly, always provide the deep link fallback + a PNG on Desktop for phone cameras.
- In CLI-only sessions, do not emit platform-specific `MEDIA:` attachment tags; state file paths plainly.

## Verification commands

Use these as applicable:

```bash
hermes gateway status
hermes gateway run --accept-hooks
hermes gateway restart
grep -iE 'telegram|gateway|error|started|connected' ~/.hermes/logs/gateway*.log | tail -80
```

For Telegram token API verification, avoid printing the token. Use a script that reads `.env`, calls `getMe`, and prints only non-secret bot metadata.

## Live “disconnected” is often a wedged agent turn

If the customer says Telegram keeps disconnecting but:

- `getMe` returns `ok:true`
- gateway process is alive / status says connected
- `getWebhookInfo.pending_update_count > 0` (or logs have not advanced for hours)

…then transport is fine and a **single hung agent turn** is blocking the poller. Look for `Stream stale for 300s`, huge context token counts, and `skill_manage`/`memory` failure loops in `~/.hermes/logs/`.

**Do not stop at process restart.** Force-end the hung session, clear that chat’s routing in `gateway_routing` (primary) and `sessions.json` (mirror), recycle the gateway, and tighten compression / `model.context_length`. Full operator recipe: skill `managed-hermes-on-orgo` → `references/wedged-gateway-messaging-turn.md` (and `references/customer-hermes-reliability-remediation.md`).

From operator hosts that block the string `hermes gateway restart`, kill by PID on the remote box and start with `gateway run --accept-hooks --replace` via `subprocess.Popen(..., start_new_session=True)`.
