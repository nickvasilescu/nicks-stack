---
name: agentmail-setup
description: Set up AgentMail direct and through Composio; diagnose send blocks, bounce suppression, and inbound vs outbound delivery failures.
version: 0.3.2
author: Hermes
metadata:
  hermes:
    tags: [AgentMail, Email, Composio, MCP, Outbound, Slack]
---

# AgentMail Setup

Set up AgentMail as an API-first email inbox provider for agents, either directly with AgentMail credentials/CLI/MCP or indirectly through Composio when a Composio-connected toolkit is available. This skill does not assume AgentMail is already connected in Composio; it verifies the available Composio surface first and uses exact tool slugs discovered at runtime. Dependency stance: use `terminal` for CLI/API checks and Hermes MCP configuration, and prefer environment variables over pasted secrets.

Also covers **operational delivery failures**: outbound 403 bounce suppression (`send/block`) and how that differs from missing **inbound** OTP/notices.

Also covers **Dewey outbound send policy** (always CC Nick, approval rules) and dual-channel notify (email + Slack) when the user asks to alert someone.

## When to Use

- The user says “set up AgentMail,” “agentmail.to,” or “give the agent an email inbox.”
- The user wants agent-controlled inboxes for signups, OTP/2FA, support, scheduling, or email workflows.
- The user mentions Composio access to AgentMail or asks whether AgentMail can be routed through Composio.
- You need to add AgentMail as a hosted MCP connector for Hermes or another MCP client.
- Outbound send fails with `MessageRejectedError` / 403 / `Recipient(s) blocked … bounced` (auto send-block suppression).
- User asks why AgentMail bounced, how to unblock a recipient, or whether a missing inbound OTP is the same bounce issue.
- User asks to **send email**, **CC Nick**, or dual-notify (email + Slack DM) about a ship/publish/heads-up.

**Nick personal inbox triage — DUAL-SOURCE (+ Granola when asked) mandatory.** If the user asks “what emails have I missed / should I get back to / catch up,” you MUST check BOTH mail sources, and Granola when they also mention meetings/follow-ups:

1. **Composio Gmail FIRST** — `${OWNER_EMAIL}` via Composio `gmail` toolkit (`COMPOSIO_SEARCH_TOOLS` → `GMAIL_LIST_THREADS` / `GMAIL_FETCH_EMAILS` paginated with `page_token` + hydrate in parallel via `COMPOSIO_REMOTE_WORKBENCH` ThreadPoolExecutor). Primary human mail. 200+ unread is normal; filter noisy senders (openrouter receipts, Mia watchdog alerts, Latitude, otter/fireflies/riverside, xfinity, slacks, linkedin). See `references/personal-gmail-triage-via-composio.md`.
2. **AgentMail SECOND** — `dewey@`, `orgo@`, `org@`, `momentum-amp@`, `ideabrowser@`, `alex_stbl@` via MCP `list_threads`. OTP/card noise usually; surface real human leads and vendor support. AgentMail alone is NEVER sufficient.
3. **Granola MCP (when meetings / follow-ups mentioned)** — Composio toolkit `granola_mcp`. Prefer `GRANOLA_MCP_QUERY_GRANOLA_MEETINGS` for Nick-owned action items. List ranges **serially** (`this_week` / `last_week` / `last_30_days`) — parallel triple list often returns `Rate limit exceeded`.

User correction “why not check composio” = first-class skill signal. Next session must start with both mail sources.

**One-by-one action loop (Nick preference):** When Nick says work through items “one by one,” do **not** batch-send after the triage board. For each item: (1) state what is known, (2) **ask questions** before proposing (slot, agenda, reply-only vs reply+calendar), (3) propose exact reply and/or calendar change, (4) execute only on explicit go, confirm ids, then advance.

## Prerequisites

- Direct AgentMail path:
  - AgentMail account/API key from `https://console.agentmail.to`, or use first-time agent signup.
  - Environment variable: `AGENTMAIL_API_KEY=am_...`.
  - Optional CLI install: `npm install -g agentmail-cli`.
- AgentMail hosted MCP path:
  - MCP URL: `https://mcp.agentmail.to/mcp`.
  - OAuth-capable clients can authenticate via AgentMail Console.
  - API-key clients can pass the key as `?apiKey=YOUR_API_KEY` or `x-api-key` header.
- Composio path:
  - Composio CLI installed and authenticated: `curl -fsSL https://composio.dev/install | bash`, then `composio login`.
  - Environment variable for SDK work: `COMPOSIO_API_KEY=...`.
  - Use a stable Composio `user_id`; avoid `default` in production.
  - Composio's AgentMail toolkit slug is `agent_mail`; its auth type is API key.
  - Known Composio AgentMail tools: `AGENT_MAIL_CREATE_INBOX`, `AGENT_MAIL_GET_MESSAGE`, `AGENT_MAIL_LIST_INBOXES`, `AGENT_MAIL_LIST_MESSAGES`, `AGENT_MAIL_SEND_EMAIL`.

## How to Run

Use the `terminal` tool for all shell commands. Use `search_files` or `read_file` to inspect local `.env` files before changing configuration, and use `patch` or `write_file` rather than shell redirection when editing files. For Hermes MCP setup, first run `hermes mcp add --help` through `terminal` and then add the AgentMail server with a URL/auth form supported by the current Hermes build.

## Quick Reference

| Surface | Command / endpoint |
|---|---|
| Agent signup | `agentmail agent sign-up --human-email you@example.com --username my-agent` |
| Signup API | `POST https://api.agentmail.to/agent/sign-up` |
| Verify OTP | `agentmail agent verify --otp-code 123456` |
| Verify API | `POST https://api.agentmail.to/agent/verify` |
| API key env | `export AGENTMAIL_API_KEY=am_...` |
| Create inbox | `agentmail inboxes create` |
| List inboxes | `agentmail inboxes list` |
| Send email | `agentmail inboxes:messages send --inbox-id inb_xxx --to user@example.com --subject "Hello" --text "Hi there"` |
| Reply | `agentmail inboxes:messages reply --inbox-id <inbox_id> --message-id <message_id> --text "..."` |
| List threads | `agentmail inboxes:threads list --inbox-id inb_xxx` |
| Webhook | `agentmail webhooks create --event-type message.received --url https://example.com/webhook` |
| AgentMail MCP | `https://mcp.agentmail.to/mcp` |
| Send block GET | `GET /v0/lists/send/block/{email}` |
| Send block DELETE | `DELETE /v0/lists/send/block/{email}` |
| Composio install | `curl -fsSL https://composio.dev/install | bash` |
| Composio login | `composio login` |
| Composio search | `composio search "agentmail email inbox"` |
| Composio link | `composio link <toolkit>` |
| Composio schema | `composio execute <TOOL_SLUG> --get-schema` |

## Procedure

1. **Determine the requested access path.**
   - If the user wants fastest setup, use direct AgentMail CLI/API.
   - If they specifically want MCP, use AgentMail hosted MCP.
   - If they say “via Composio too,” verify Composio has a relevant toolkit/tool first; do not invent tool slugs.

2. **Check local prerequisites.** Invoke through `terminal`:
   ```bash
   command -v node || true
   command -v npm || true
   command -v agentmail || true
   command -v composio || true
   printenv AGENTMAIL_API_KEY >/dev/null && echo AGENTMAIL_API_KEY=set || echo AGENTMAIL_API_KEY=missing
   printenv COMPOSIO_API_KEY >/dev/null && echo COMPOSIO_API_KEY=set || echo COMPOSIO_API_KEY=missing
   ```
   Completion criterion: you know which CLIs and keys are present without printing secret values.

3. **Install the direct AgentMail CLI when needed.** Invoke through `terminal`:
   ```bash
   npm install -g agentmail-cli
   agentmail --version
   ```
   Completion criterion: `agentmail --version` exits successfully.

4. **Obtain AgentMail credentials.**
   - Existing user path: get an API key from `https://console.agentmail.to` and store it as `AGENTMAIL_API_KEY`.
   - First-time agent path, if the user provides the human email:
     ```bash
     agentmail agent sign-up \
       --human-email you@example.com \
       --username my-agent
     ```
     Then set `AGENTMAIL_API_KEY` from the response and verify the OTP:
     ```bash
     agentmail agent verify --otp-code 123456
     ```
   Completion criterion: API key is available and verified if using first-time agent signup.

5. **Smoke-test direct AgentMail.** Invoke through `terminal`:
   ```bash
   agentmail inboxes list --format json
   agentmail inboxes create --display-name "Hermes AgentMail Smoke Test" --format json
   ```
   Completion criterion: list succeeds and create returns an inbox identifier or email address.

6. **Send only with explicit recipient approval** (user-directed “send email to X” counts). Prefer both `text` and `html`. **Always include `cc: ["${OWNER_EMAIL}"]`** on every real outbound send so Nick can see it (standing Dewey rule). Default from-inbox for Dewey: `${AGENTMAIL_INBOX}` (`inboxId` is that email string on the MCP `send_message` tool).

   MCP example shape:
   ```json
   {
     "inboxId": "${AGENTMAIL_INBOX}",
     "to": ["recipient@example.com"],
     "cc": ["${OWNER_EMAIL}"],
     "subject": "...",
     "text": "...",
     "html": "..."
   }
   ```
   CLI (if installed): pass whatever CC flag the current CLI exposes; if none, send via MCP/API with `cc`.

   If a send already left without Nick on CC, do **not** re-spam the primary recipient. Send Nick a separate **copy** (to `${OWNER_EMAIL}` only) with the same body and a subject like `Copy: <original subject>`.

   Completion criterion: send returns `messageId`/`threadId` and Nick is on the thread (CC or explicit copy).

7. **Add AgentMail hosted MCP when the user wants MCP access.** First inspect the active Hermes syntax:
   ```bash
   hermes mcp add --help
   ```
   Then add the hosted server using the current Hermes-supported URL flow. AgentMail’s hosted MCP server is:
   ```text
   https://mcp.agentmail.to/mcp
   ```
   If the MCP client cannot do OAuth, AgentMail supports API key auth via:
   ```text
   https://mcp.agentmail.to/mcp?apiKey=YOUR_API_KEY
   x-api-key: YOUR_API_KEY
   ```
   Completion criterion: `hermes mcp test agentmail` or the equivalent current Hermes MCP test command succeeds.

8. **Verify Composio AgentMail access.** Install/login if needed, then invoke through `terminal`:
   ```bash
   curl -fsSL https://composio.dev/install | bash
   composio login
   composio whoami
   composio search "agentmail email inbox"
   ```
   Expected toolkit slug from Composio's public toolkit page: `agent_mail`. Expected tools: `AGENT_MAIL_CREATE_INBOX`, `AGENT_MAIL_GET_MESSAGE`, `AGENT_MAIL_LIST_INBOXES`, `AGENT_MAIL_LIST_MESSAGES`, `AGENT_MAIL_SEND_EMAIL`. Completion criterion: Composio login succeeds and search or schemas confirm the `agent_mail` toolkit/tools for the active account.

9. **Connect and execute through Composio only after discovering exact names.** Use the exact toolkit and tool slug returned by `composio search`:
   ```bash
   composio link <toolkit>
   composio execute <TOOL_SLUG> --get-schema
   composio execute <TOOL_SLUG> -d '{ /* schema-valid input */ }'
   ```
   Completion criterion: schema retrieval succeeds and a low-risk read/list tool executes successfully.

10. **For Composio SDK/MCP projects, use current v3 session patterns.** Do not use old `ComposioToolSet` or app/action terminology. Python native-tools pattern:
    ```python
    from composio import Composio

    composio = Composio()
    session = composio.create(user_id="user_123")
    tools = session.tools()
    ```
    MCP pattern:
    ```python
    from composio import Composio

    composio = Composio()
    session = composio.create(user_id="user_123", mcp=True)

    mcp_url = session.mcp.url
    mcp_headers = session.mcp.headers
    ```
    Completion criterion: the project stores the Composio session ID for reuse or can recreate a scoped session intentionally.

## Outbound bounce suppression (send block)

When MCP `send_message` or `POST .../messages/send` returns:

```text
MessageRejectedError 403
Recipient(s) blocked: user@domain.com (bounced)
```

AgentMail is **refusing the send before mail leaves**. A previous delivery attempt bounced/rejected/complained, and AgentMail auto-added an **org-level send block**. Known-good customer addresses can still sit here after a one-off historical bounce.

### Diagnose and fix

```bash
# Never print AGENTMAIL_API_KEY
curl -sS -H "Authorization: Bearer $AGENTMAIL_API_KEY" \
  "https://api.agentmail.to/v0/lists/send/block/user@domain.com"
# 200 + reason "bounced" or "Unsubscribed via List-Unsubscribe" → suppressed; 404 → not blocked
# If JSON has read_only:true, DELETE returns 409 — do not loop; fall back to Nick Gmail Composio
# Known: opticalresourcesgroup@gmail.com (Mark/ORG) is read-only List-Unsubscribe; use ${OWNER_EMAIL} Gmail for Mark approval packs
# 413 on send: compress attachments to email JPEG or Drive-link large packs

# Only if address is known-good AND not read_only:
curl -sS -X DELETE -H "Authorization: Bearer $AGENTMAIL_API_KEY" \
  "https://api.agentmail.to/v0/lists/send/block/user@domain.com"
# expect 204; re-GET → 404; then resend (text + html)
```

Also: `GET /v0/lists/send/block` (paginated), `GET /v0/lists/receive/block`, `GET /v0/metrics` (`message.bounced` / `rejected` / `complained`).

### Outbound vs inbound (do not conflate)

| Pattern | Direction | Where to look |
|---|---|---|
| 403 `blocked … bounced` on **send** | Outbound | `send/block` auto-suppression |
| Third-party OTP never appears | Inbound | Inbox list + `receive/block` (often empty) — product/gate, not send-block |
| Other mail from same vendor **does** land | Inbound OK | Missing type is product-side |

Fallback: operator Gmail (Composio) if AgentMail still blocked or policy forbids unblocking.

Full cheatsheet: `references/bounce-suppression-send-block.md`.

## Pitfalls

- Do not assume a Composio AgentMail toolkit exists in the user’s account. Run `composio search "agentmail email inbox"` and use only returned toolkits/tool slugs.
- Do not print API keys. Check secret presence with `printenv NAME >/dev/null` style commands.
- The AgentMail agent signup flow is for first-time users; human email addresses already signed up with AgentMail will not work there.
- The AgentMail signup endpoint is idempotent; calling it again with the same email rotates the API key and resends the OTP if expired.
- For AgentMail MCP, OAuth and API-key auth are different paths. Use OAuth for clients that support it; use `?apiKey=` or `x-api-key` for clients that do not.
- AgentMail send/reply has a recipient limit of 50 total across `to`, `cc`, and `bcc`.
- For outbound email, provide both `text` and `html` when possible; AgentMail docs call this a deliverability best practice.
- In Composio v3, use `composio.create(user_id)` and `session.tools()` or `session.mcp.url`; do not use old “entity ID,” “actions,” “apps,” or `ComposioToolSet` patterns.
- **403 blocked/bounced is not “mailbox invalid.”** Inspect `send/block` first; often a one-line DELETE, not a domain investigation.
- **Do not treat missing inbound fund/OTP mail as send-block.** If other vendor messages land, it is a product/gate issue.
- **Send block is org-wide** across all inboxes until the entry is removed.
- Do not mass-delete the entire send/block list; clear known-good addresses only.
- Dewey policy: read/search/list + drafts OK; **explicit user approval before send** (a direct “send this to X” is approval).
- **Always CC `${OWNER_EMAIL}`** on outbound AgentMail sends. Never omit because the message is “informal” or “internal.” Nick asked for visibility on every agent-sent email.
- Do not double-email a primary recipient just to fix a missing CC; send Nick a one-off copy instead.
- Dual-channel heads-up (email + Slack): see `references/outbound-cc-and-dual-notify.md`. Slack workspace for Orgo is via Composio (`SLACK_FIND_USERS` → `SLACK_OPEN_DM` → `SLACK_SEND_MESSAGE`). Work emails can differ from Slack profile emails (e.g. Tiger: vault `tiger@orgo.ai`, Slack profile may be personal Gmail; name search works when email lookup returns empty).
- **Customer multi-touch marketing drips** (e.g. `org@agentmail.to` Jobber/Revo sequences): load `customer-outbound-campaigns`. Always-CC-Nick applies to **one-off / operator-style** sends, not every row of a 200+ drip — use campaign labels + Google Sheet tracking for bulk; still CC Nick when emailing Mark/Richard personally or sending approval links.
- Ground drip voice from **prior messages on that inbox** (`AGENT_MAIL_LIST_MESSAGES` / `GET_MESSAGE`) before writing new subjects.
- Check custom-domain DNS status on the customer inbox before volume; PENDING domains degrade deliverability.

## Verification

A setup is verified when this `terminal` check succeeds without exposing secrets:

```bash
agentmail inboxes list --format json >/tmp/agentmail-inboxes.json && \
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('/tmp/agentmail-inboxes.json')
print('agentmail_direct_ok=', p.exists() and p.stat().st_size > 0)
PY
```

For Composio, additionally verify:

```bash
composio whoami && composio search "agentmail email inbox"
```

If the Composio search does not return AgentMail-specific tools, report direct AgentMail as working and Composio AgentMail access as unverified/unavailable in the current Composio surface.

Bounce fix is verified when: `GET send/block/{email}` is 404 after DELETE, and a subsequent send returns a real `messageId`/`threadId`.

Outbound policy is verified when every real send includes `cc` containing `${OWNER_EMAIL}` (or a deliberate Nick-only copy if fixing a missed CC).

## References

- `references/bounce-suppression-send-block.md` — outbound 403 send/block diagnosis
- `references/inbound-otp-vs-send-block.md` — do not conflate inbound OTP miss with send-block
- `references/outbound-cc-and-dual-notify.md` — always CC `${OWNER_EMAIL}`; dual-channel email + Slack DM; Tiger lookup notes
- `references/personal-gmail-triage-via-composio.md` — personal Gmail triage via Composio (${OWNER_EMAIL}), priority rubric, deliverable shape
- `references/composio-gmail-bulk-triage.md` — bulk 200+ unread pattern, pagination, ThreadPoolExecutor hydration, noise denylist expansion (Jul 10 2026 session)

