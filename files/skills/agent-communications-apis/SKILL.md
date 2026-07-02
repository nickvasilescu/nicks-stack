---
name: agent-communications-apis
description: "Workflows for programmable agent communication APIs such as AgentMail and AgentPhone: docs discovery, safe credential handling, inbox and number selection, hosted agents, messaging, calls, and verification."
---

# Agent Communications APIs

Use this skill when the user asks to set up, configure, use, or troubleshoot API-backed communication accounts for an AI agent: AgentMail inboxes, AgentPhone numbers, SMS/MMS/iMessage, voice calls, webhooks, hosted agents, or similar services.

## Core principles

1. Treat API keys as secrets.
   - Do not echo full keys back to the user.
   - Do not save keys in memory or skill files.
   - If a script needs the key, keep it local to the tool call and redact it in outputs when possible.

2. Start from agent-friendly docs.
   - Look for `/llms.txt` at the docs root.
   - Use `.md` versions of docs pages where available.
   - Prefer OpenAPI/AsyncAPI specs when endpoint details are unclear.

3. Verify with real API output.
   - List existing resources before creating new ones.
   - Prefer reusing already-paid or available resources the user names.
   - After every create/update/attach step, fetch the resource again and confirm the resulting state.

4. Save durable defaults in memory, not in the skill.
   - Examples: the user’s default AgentMail inbox, default AgentPhone agent id, default number id.
   - The skill should describe the reusable workflow; session-specific ids belong in `references/` if useful for audit, and current operational defaults belong in memory.

## AgentMail workflow

1. Read `https://docs.agentmail.to/llms.txt` first.
2. Use the user’s remembered default AgentMail inbox if present.
3. For API work, consult:
   - `https://docs.agentmail.to/llms-full.txt`
   - `https://docs.agentmail.to/openapi.json`
4. Common operations:
   - List/create inboxes.
   - Send messages.
   - Read recent messages/threads, especially magic-link verification emails for third-party CLI setup.
   - Configure webhooks or WebSockets.
5. Verify by reading the created/updated inbox/message/thread after mutation.

### AgentMail via Composio pitfalls

- `AGENT_MAIL_LIST_MESSAGES` requires `inbox_id` to be the full email address (for example `agent@agentmail.to`), not an internal id and not omitted. Before retrying after a 400, inspect the actual tool arguments you are sending; repeated identical retries can temporarily trip Composio's MCP unreachable/backoff state.
- If a message-list call unexpectedly reports missing `inbox_id`, switch to `AGENT_MAIL_LIST_INBOXES` to confirm the mailbox value, then retry once with explicit `{"inbox_id": "...", "limit": 10}`. Do not keep retrying the same empty argument payload.
- For magic-link login flows, keep the CLI/browser verification process alive, read the newest email in the inbox, open/click the verification URL if permitted, then verify with the service's `whoami`/status command before proceeding to payment or MCP setup.

## AgentPhone workflow

1. Read `https://docs.agentphone.ai/llms.txt` first.
2. Base API URL: `https://api.agentphone.ai/v1`.
3. Include bearer auth and a normal User-Agent header:
   - `Authorization: Bearer <token>`
   - `User-Agent: Hermes-Agent/1.0`

   Pitfall: AgentPhone may return Cloudflare-style `403 error code: 1010` to bare Python `urllib` requests without a User-Agent. Retry with an explicit User-Agent before assuming the key or endpoint is wrong.

4. Discover current resources before changing anything:
   - `GET /numbers?limit=100&offset=0`
   - `GET /agents`
   - optionally `GET /agents/voices`

5. Choose the right phone number:
   - Prefer an active, unattached number if the user says there is already an available/paid number.
   - If the UI/API masks numbers, prefix matching can be ambiguous: a user saying “415 or something” may correspond to a masked `+141...` number, not necessarily `+1415...` visible in API output.
   - Do not release/delete numbers unless explicitly asked; releasing is irreversible.

6. Create or reuse a dedicated assistant agent:
   - Use hosted mode when the user wants the number to behave as the assistant’s own phone and no webhook backend is specified.
   - Use webhook mode only when the user has/provides a backend URL and wants custom server-side handling.
   - Good hosted defaults:
     - `voiceMode: "hosted"`
     - `enableMessaging: true`
     - `modelTier: "balanced"`
     - `sttMode: "fast"`
     - `ambientSound: "none"`
     - `denoisingMode: "noise-cancellation"`
     - `language: "en-US"`
     - concise system prompt stating the agent is an AI assistant and should not claim to be human.

7. Attach the number:
   - `POST /agents/{agent_id}/numbers` with `{ "numberId": "..." }`.
   - Verify with `GET /agents/{agent_id}` and `GET /numbers?limit=100&offset=0`.
   - Confirm `number.agentId` equals the selected agent id and `voiceRouting.method` is `agent` when available.

8. Sending messages:
   - `POST /messages`
   - Provide at least one of `from_number`, `number_id`, or `agent_id`.
   - Prefer `number_id` or the remembered default agent id to avoid ambiguity.

## References

- `references/agentphone-setup-notes.md` — condensed notes from a successful AgentPhone setup, including endpoints, masked-number pitfall, and verification shape.
- `references/agentmail-notes.md` — AgentMail docs entry points and common resource areas.

## Verification checklist

Before telling the user setup is complete:

- Authentication succeeded with a real API call.
- Existing resources were listed.
- The selected inbox/number/agent matches the user’s requested resource as closely as API visibility allows.
- Mutations returned success status.
- A follow-up GET confirms the final state.
- Any persistent operational defaults were saved to memory, without secrets.
