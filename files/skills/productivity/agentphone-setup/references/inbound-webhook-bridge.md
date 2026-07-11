# AgentPhone inbound webhook bridge notes

Session-derived reference for building a production-ish inbound SMS/iMessage bridge from AgentPhone to Hermes.

## Target architecture

```text
Inbound text
  -> AgentPhone webhook
  -> cloudflared tunnel
  -> local Python bridge on 127.0.0.1:8787
  -> POST /hooks/agentphone
  -> one-shot `hermes chat -Q -q ...`
  -> POST https://api.agentphone.ai/v1/messages
```

Use this when MCP/outbound AgentPhone is already configured but inbound texts do not reach the VM.

## Authoritative docs confirmed

Start from:

```text
https://docs.agentphone.ai/llms.txt
https://docs.agentphone.ai/documentation/guides/webhooks.md
https://docs.agentphone.ai/documentation/guides/messages.md
https://docs.agentphone.ai/api-reference/messages/send-message-v-1-messages-post.md
https://docs.agentphone.ai/api-reference/webhooks/create-or-update-webhook-v-1-webhooks-post.md
```

Important: do not guess webhook signatures. AgentPhone docs define:

```text
X-Webhook-Signature: sha256=<hex_digest>
X-Webhook-Timestamp: <unix timestamp>
X-Webhook-ID: <delivery id>
X-Webhook-Event: <event type>

signed_string = "{timestamp}.{raw_body}"
expected = HMAC-SHA256(webhook_secret, signed_string)
accepted signature = "sha256=" + expected_hex_digest
reject if timestamp is outside a 5-minute replay window
```

Inbound message events use one envelope:

```json
{
  "event": "agent.message",
  "channel": "sms | mms | imessage",
  "timestamp": "...",
  "agentId": "...",
  "data": {
    "conversationId": "...",
    "numberId": "...",
    "from": "+155...",
    "to": "+155...",
    "message": "...",
    "direction": "inbound",
    "receivedAt": "..."
  },
  "recentHistory": []
}
```

Group iMessage events may have `data.group` and `data.senderIdentifier`; reply to the group using the `groupId`, not `data.from`.

## Endpoint shapes

Send a reply:

```http
POST https://api.agentphone.ai/v1/messages
Authorization: Bearer <api-key>
Content-Type: application/json
```

Minimum request shape:

```json
{
  "to_number": "+155... or grp_...",
  "body": "reply text"
}
```

Useful optional fields:

```json
{
  "agent_id": "...",
  "number_id": "...",
  "from_number": "+155...",
  "media_urls": ["https://..."],
  "reply_to_message_id": "...",
  "send_style": "confetti"
}
```

Send iMessage typing indicator before long work:

```http
POST https://api.agentphone.ai/v1/conversations/{conversation_id}/typing
Authorization: Bearer <api-key>
```

The request body is empty. Docs describe it as iMessage-only/best-effort; stale or SMS conversations may fail or be ignored. Treat failures as non-fatal.

Create/update project webhook:

```http
POST /v1/webhooks
```

Create/update agent-specific webhook, preferred for one Hermes/one AgentPhone agent:

```http
POST /v1/agents/{agent_id}/webhook
```

Body:

```json
{
  "url": "https://public.example/hooks/agentphone",
  "contextLimit": 10,
  "timeout": 30
}
```

Agent-specific webhooks override the project default for that agent only; events are not duplicated to both.

## Bridge implementation checklist

- Load `/root/.hermes/.env`, then bridge-local env; local bridge env wins.
- Never print API keys, bearer tokens, webhook secrets, `whsec_...`, or `sk_live_...`; redact in JSONL logs.
- HTTP server binds to `127.0.0.1`, not `0.0.0.0`, when fronted by `cloudflared`.
- Expose `POST /hooks/agentphone`; return 401 on missing/bad signature and 405/404 for unsigned junk.
- Verify HMAC over raw body bytes before JSON parsing.
- Dedupe retries/restarts with a stable key such as: event type + conversation ID + sender + timestamp + text.
- Sender-gate before invoking Hermes. Keep allowlist and full-access list in env.
- Extract inbound media fields before invoking Hermes: AgentPhone image/file-only messages may have empty `data.message`/body and a populated `data.mediaUrl`; also handle `media_url`, `mediaUrls`, and `media_urls` variants. Include media URLs or downloaded local cache paths in the Hermes prompt so it can use vision tools. Log only media count and URL hashes, not signed/private media URLs.
- For Poke-style SMS/iMessage UX, use a conservative delivery layer: **generic static acks only** (no keyword extraction), typing keepalive during long runs, then split final replies into at most 2-3 back-to-back bubbles at ~120-160 char thresholds. Code blocks, tables, and draft-like replies (matching patterns like `i'd send:`, `draft:`, `Subject:`) must stay as single unsplit bubbles. Lowercase sentence boundaries and comma-conjunction splits are supported for texting style. See `references/poke-style-imessage-bridge.md` (acks section is authoritative; keyword “contextual” acks are rejected).
- For per-bridge model override (different model for iMessage than global Hermes), set env vars `AGENTPHONE_HERMES_MODEL` and `AGENTPHONE_HERMES_PROVIDER` in the bridge env file. **CRITICAL:** the bridge must pass these as `-m` and `--provider` CLI flags to `hermes chat`, NOT as `HERMES_INFERENCE_MODEL` env vars. The env var approach only works for `hermes -z` (oneshot) and `hermes --tui` — `hermes chat` silently ignores it and falls back to the global config model. This was a real production bug. See `references/poke-style-imessage-bridge.md` for the correct implementation and verification steps.
- For reasoning effort and service tier, set globally via `hermes config set agent.reasoning_effort low` and `hermes config set agent.service_tier fast`. These apply to all Hermes surfaces (CLI, gateway, bridge). There is no per-bridge reasoning override; the bridge subprocess inherits the global config.
- Ack implementation: static generic pool only (`on it`, `checking now`, `digging in`, …). Keyword extraction was tried and rejected (word salad on real messages). Keep acks enabled unless the user asks to disable. See `references/poke-style-imessage-bridge.md`.
- Full-access senders may get `--toolsets all`; other allowed senders should get constrained toolsets such as `web,vision`.
- After allowlist/dedupe passes and before starting the Hermes subprocess, call `POST /v1/conversations/{conversation_id}/typing` with an 8-second timeout. This gives iMessage users the typing bubble while Hermes works. Log failures as `typing_skipped` and continue; SMS and stale iMessage conversations can return 400 or silently ignore it.
- For Poke-style UX, add a smart acknowledgement path before long-horizon work. Use bridge env such as `AGENTPHONE_ACK_ENABLED=1`, `AGENTPHONE_ACK_MODE=smart`, `AGENTPHONE_ACK_DELAY_SECONDS=1.25`, `AGENTPHONE_TYPING_REFRESH_SECONDS=25`. In smart mode, send a short **generic** text ack only for task-ish requests (email/calendar/research/debug/build/search/etc.), not casual chatter like "you up", "nice", or "what's your name". Log `ack_sent` with the classifier reason and `ack_skipped` for non-taskish texts.
- Add conservative progress updates for long jobs: after one ack, keep typing alive and send at most one extra **generic** progress text after roughly 45 seconds. Gate with `AGENTPHONE_PROGRESS_ENABLED` and avoid repeated updates. See `references/poke-style-imessage-bridge.md`.
- Add per-conversation interruption. Maintain a `RUNNING_JOBS` registry keyed by conversation ID or reply target. Register the job synchronously before spawning the Hermes thread; when a new inbound event arrives for the same key, set the old cancellation event, terminate its subprocess if running, suppress its final reply, and optionally send one "got it, switching" acknowledgment. Verify with a fake subprocess test before restart.
- For iMessage-native UX, add smart reactions before Hermes. Use `AGENTPHONE_REACTIONS_ENABLED=1`, `AGENTPHONE_REACTION_MODE=smart`. For trivial closers such as "nice", "thanks", "lol", "ok", "sounds good", resolve the inbound `message_id` and call `POST /v1/messages/{message_id}/reactions`, then suppress the Hermes run. Classic tapbacks are `love`, `like`, `dislike`, `laugh`, `emphasize`, and `question`; SMS returns 400. If the webhook omits message id, resolve it from `GET /v1/conversations/{conversation_id}/messages` by matching newest inbound sender/body/timestamp. Log `reaction_sent`, `reaction_only_handled`, `reaction_failed`, or `reaction_skipped`.
- Invoke Hermes one-shot quiet mode: `hermes chat -Q --source agentphone-bridge --max-turns N -t <toolsets> -q <prompt>`.
- Prompt Hermes not to call AgentPhone send tools itself; the bridge sends the final text via `/v1/messages`.
- Cap Hermes runtime with a subprocess timeout; send a short failure reply on timeout/error only if the sender is allowlisted.
- **Stdout recovery on non-zero exit:** if Hermes exits non-zero (including SIGABRT `-6` during memory/Honcho cleanup) but printed a clean final answer, send the cleaned stdout. Do not discard good replies solely because `returncode != 0`. See `references/hermes-bridge-false-failure.md`.

## cloudflared quick tunnel pitfall

`cloudflared tunnel --url http://127.0.0.1:8787` can print a `*.trycloudflare.com` URL before AgentPhone's webhook safety validator can resolve it. Observed AgentPhone response:

```json
{
  "error": {
    "message": "DNS resolution failed — cannot verify webhook URL safety",
    "code": "VALIDATION_ERROR_URL",
    "type": "validation_error"
  }
}
```

Do not treat this as a bad API key. The durable fix is to wait for public DNS readiness before registering the webhook, or use a stable named Cloudflare tunnel/hostname. If a user gives a strict "fail twice then stop" guardrail, stop after two registration failures and report the exact AgentPhone error.

## Production named-tunnel pattern

For production, prefer a stable named Cloudflare tunnel and hostname over quick tunnels:

```text
public hostname -> named cloudflared tunnel -> localhost:8787 -> /hooks/agentphone
```

A working Dewey deployment uses:

```text
https://<random>.trycloudflare.com/hooks/agentphone
```

Implementation notes:

- The VM may not hold Cloudflare zone credentials; creating/routing the named tunnel can require another host/account with the zone cert.
- Move only the per-tunnel credential to the agent VM; keep it revocable by deleting the tunnel.
- Put `~/.cloudflared/config.yml` on the VM with ingress from the stable hostname to `http://localhost:8787`.
- Set `AGENTPHONE_PUBLIC_URL=https://<stable-hostname>` in the bridge env. When present, the bridge should skip internal quick-tunnel startup and register the AgentPhone webhook against the stable hostname.
- Supervise cloudflared and the bridge as separate programs when using a named tunnel.
- If `cloudflared tunnel route dns` accidentally routes the CNAME to a local default tunnel, rerun with the explicit tunnel UUID and `--overwrite-dns`.

## Supervisor pattern

When registration succeeds, add a supervisor program roughly like:

```ini
[program:agentphone-bridge]
command=/root/.hermes_agentphone_bridge/agentphone_bridge.py
directory=/root/.hermes_agentphone_bridge
autostart=true
autorestart=true
startretries=999
stdout_logfile=/root/.hermes_agentphone_bridge/supervisor.out.log
stderr_logfile=/root/.hermes_agentphone_bridge/supervisor.err.log
```

Then:

```bash
supervisorctl reread
supervisorctl update
supervisorctl status
```

Verify public endpoint connectivity, AgentPhone `test_webhook`, delivery logs, and survival across `supervisorctl restart agentphone-bridge` before declaring inbound ready.
