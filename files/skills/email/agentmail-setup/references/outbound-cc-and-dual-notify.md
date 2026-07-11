# Outbound CC + dual-channel notify (Dewey)

## Standing email rule

On **every** outbound AgentMail send from Dewey:

| Field | Value |
|---|---|
| From inbox | Prefer `${AGENTMAIL_INBOX}` unless user names another managed inbox |
| `to` | Recipient(s) the user named |
| `cc` | **Always** include `${OWNER_EMAIL}` |
| Body | Prefer both `text` and `html` |

User phrases like “send an email to Tiger about X” = approval to send. Still do not invent recipients or extra To/BCC.

### Missed CC recovery

If mail already sent without Nick:

1. Do **not** resend the same note to the primary recipient.
2. Email `${OWNER_EMAIL}` alone: subject `Copy: <original subject>`, body = original content + one line that it was already delivered to `<recipient>`.

## Dual-channel: email + Slack DM

When the user asks for both email and Slack DM:

1. **Email first or in parallel** with `cc: ["${OWNER_EMAIL}"]`.
2. **Slack** via Composio (active Orgo workspace connection as Nick):
   - `COMPOSIO_SEARCH_TOOLS` for find user + open DM + send message (session id required).
   - Resolve user: try `SLACK_FIND_USER_BY_EMAIL_ADDRESS` / `SLACK_FIND_USERS` with email; if empty, search by display name (`Tiger`, `Tiger Wang`).
   - Filter: one active human (`deleted`/`is_bot`/`is_app_user` false). Capture `id` (`U…`).
   - `SLACK_OPEN_DM` with `users: "<U…>"` → channel id `D…` (reuse even if `already_open`).
   - `SLACK_SEND_MESSAGE` with `channel: "D…"` and `markdown_text` (not a user id / email as channel).
3. Report both delivery handles (AgentMail `messageId`/`threadId`, Slack `channel` + `ts`).

### Orgo contact note (Tiger Wang)

| Surface | Identifier |
|---|---|
| Work email (vault) | `tiger@orgo.ai` |
| Slack display | Tiger Wang / Tiger Yun Wang |
| Slack user id (Orgo workspace) | `U0B43603BCL` (re-resolve if stale) |
| Slack profile email (may differ) | personal Gmail on profile; do not assume equals work email |

Email lookup by `tiger@orgo.ai` can return empty while name search finds the user. Prefer work email for AgentMail; use name search for Slack when needed.

## What not to put here

- Do not hardcode “Slack is broken” if a lookup fails once; re-search by name/email and report miss honestly.
- Do not send Slack as the Composio bot without a clear “from Nick” framing when the connected account posts as Nick’s identity (Composio Slack often posts as the connected user).
