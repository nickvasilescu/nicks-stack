---
name: agentphone-setup
description: Set up AgentPhone numbers and MCP access.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [AgentPhone, Phone, MCP, Messaging]
---

# AgentPhone Setup

Set up AgentPhone as a phone-number provider for AI agents: SMS, MMS, iMessage, voice calls, webhooks, SDKs, and MCP access. This skill does not assume exact OpenClaw config paths or undocumented endpoints; it grounds changes in AgentPhone docs first, then uses Hermes tools to edit local config and verify. Dependency stance: use the hosted docs index and `.md` pages as source of truth, `terminal` for CLI/API checks, and `patch`/`write_file` for config edits.

## When to Use

- The user says “AgentPhone,” “agentphone.ai,” or “give the agent a phone number.”
- The user wants Hermes, OpenClaw, Claude Code, Cursor, Windsurf, or another MCP client to send texts or make calls.
- The user asks for SMS, MMS, iMessage, voice-call, transcript, webhook, or phone-identity setup for an agent.
- The user wants to compare AgentPhone MCP, SDK, REST API, or Claude Code skill setup.

## Prerequisites

- AgentPhone account/API key from `https://agentphone.ai`.
- Environment variable: `AGENTPHONE_API_KEY=...`.
- Optional base URL for MCP/server configs: `AGENTPHONE_BASE_URL=https://api.agentphone.ai`.
- Node.js with `npx` for MCP: package `agentphone-mcp`.
- Optional Python SDK: `pip install agentphone`.
- Optional TypeScript/JavaScript SDK: `npm install agentphone`.
- For Hermes MCP setup, Hermes config must support stdio MCP servers.

## How to Run

Start by grounding the current docs with `browser_navigate` or Composio search/fetch tools against `https://docs.agentphone.ai/llms.txt`, then use `terminal` for installation/API checks. Use `patch` or `write_file` for Hermes/OpenClaw MCP config edits; do not guess undocumented config paths. For outward communications like SMS, iMessage, or calls, ask before sending or calling unless the user explicitly authorizes the action.

## Quick Reference

| Surface | Command / endpoint |
|---|---|
| Docs index | `https://docs.agentphone.ai/llms.txt` |
| Welcome docs | `https://docs.agentphone.ai/welcome.md` |
| MCP docs | `https://docs.agentphone.ai/mcp.md` |
| Agent integration docs | `https://docs.agentphone.ai/integrations/connect-your-ai.md` |
| Base URL | `https://api.agentphone.ai/v1` |
| Auth header | `Authorization: Bearer YOUR_API_KEY` |
| MCP package | `npx -y agentphone-mcp` |
| MCP env | `AGENTPHONE_API_KEY`, `AGENTPHONE_BASE_URL` |
| Claude Code MCP | `claude mcp add agentphone -- npx -y agentphone-mcp` |
| Claude Code skill | `npx skills add AgentPhone-AI/skills` |
| Python SDK | `pip install agentphone` |
| TypeScript SDK | `npm install agentphone` |
| Create agent | `POST /v1/agents` |
| Create number | `POST /v1/numbers` |
| Attach number | `POST /v1/agents/{agent_id}/numbers` |
| Configure project webhook | `POST /v1/webhooks` |
| Configure agent webhook | `POST /v1/agents/{agent_id}/webhook` |
| Send message | `POST /v1/messages` |

## Procedure

For inbound AgentPhone-to-Hermes bridges, see `references/inbound-webhook-bridge.md` before implementing. It captures the webhook signature scheme, agent-scoped webhook endpoint, bridge checklist, cloudflared quick-tunnel DNS pitfall, and supervisor verification pattern.

For Poke-style iMessage UX on a Hermes bridge, see `references/poke-style-imessage-bridge.md`. It captures smart acks (generic only, no keyword extraction), typing keepalive, interruption, per-bridge model override via CLI flags, inherited reasoning/service-tier defaults with effective-runtime verification, progress updates, reaction handling, reply chunking, and the critical legibility rule: never split copyable drafts/artifacts.

For iMessage/MMS images and other media, see `references/inbound-media-imessage.md` (inbound image-only empties) and `references/outbound-media-imessage.md` (Hermes `MEDIA:` paths must become AgentPhone `media_url`/`media_urls` public HTTPS attachments; never send both fields).

When the user gets a canned iMessage like “Hermes hit an internal error while generating a reply,” diagnose with `references/hermes-bridge-false-failure.md` before blaming webhooks, allowlists, or models. Often Hermes already finished a good reply and aborted during CLI/memory cleanup; the bridge discarded stdout.

When MCP reads work but inbound iMessages receive no reply, use `references/webhook-secret-drift.md`. An AgentPhone/MCP reload can leave the same webhook ID and URL active while its secret changes; the local bridge then logs `signature_rejected` and returns 401 until its stored secret is refreshed and the supervised process is restarted.

When replies start, cancel, or act on old follow-ups in the wrong order, use `references/out-of-order-webhook-delivery.md`. AgentPhone can deliver queued iMessage webhooks late. A per-conversation message-time watermark must reject stale events before they interrupt the current Hermes job; envelope delivery time is not a safe ordering key.

1. **Ground current AgentPhone docs.** Use `browser_navigate` or Composio fetch/search tools for:
   ```text
   https://docs.agentphone.ai/llms.txt
   https://docs.agentphone.ai/welcome.md
   https://docs.agentphone.ai/mcp.md
   https://docs.agentphone.ai/integrations/connect-your-ai.md
   https://docs.agentphone.ai/documentation/guides/messages.md
   ```
   Completion criterion: you have confirmed the current base URL, auth header, MCP command, and relevant docs pages before editing anything.

2. **Check local prerequisites without printing secrets.** Invoke through the `terminal` tool:
   ```bash
   command -v node || true
   command -v npx || true
   command -v npm || true
   command -v python3 || true
   printenv AGENTPHONE_API_KEY >/dev/null && echo AGENTPHONE_API_KEY=set || echo AGENTPHONE_API_KEY=missing
   ```
   Completion criterion: you know whether Node/npx and the API key are available.

3. **Store credentials only when supplied by the user.** If the user provides an API key, write it to the active env file without exposing it. Prefer existing Hermes env conventions, e.g. `/root/.hermes/.env`, and preserve `0600` permissions. Completion criterion: `printenv AGENTPHONE_API_KEY >/dev/null` succeeds in a shell that sources the env file.

4. **Add AgentPhone MCP to Hermes.** Convert the AgentPhone docs’ MCP block into Hermes YAML and edit with `patch` or `write_file`:
   ```yaml
   mcp_servers:
     agentphone:
       command: npx
       args:
         - -y
         - agentphone-mcp
       env:
         AGENTPHONE_API_KEY: ${AGENTPHONE_API_KEY}
         AGENTPHONE_BASE_URL: https://api.agentphone.ai
       enabled: true
   ```
   Completion criterion: Hermes config contains `agentphone` as a stdio MCP server with env indirection, not a pasted secret.

5. **Verify the MCP server.** Invoke through the `terminal` tool:
   ```bash
   hermes mcp test agentphone
   ```
   Completion criterion: Hermes connects and discovers AgentPhone tools. If it fails, run `npx -y agentphone-mcp` through `terminal` to separate npm/package errors from Hermes config errors.

6. **For OpenClaw or other MCP clients, use the same server block.** AgentPhone docs say OpenClaw supports MCP servers natively, but they do not specify a universal path. Add this block to the client’s MCP configuration location, not an invented path:
   ```json
   {
     "mcpServers": {
       "agentphone": {
         "command": "npx",
         "args": ["-y", "agentphone-mcp"],
         "env": {
           "AGENTPHONE_API_KEY": "your_api_key_here",
           "AGENTPHONE_BASE_URL": "https://api.agentphone.ai"
         }
       }
     }
   }
   ```
   Completion criterion: the target MCP client lists AgentPhone tools or its MCP test command succeeds.

7. **Use the official Claude Code skill only when that is the target client.** Invoke through `terminal`:
   ```bash
   npx skills add AgentPhone-AI/skills
   export AGENTPHONE_API_KEY=your_key_here
   ```
   Example skill commands from docs:
   ```text
   /agentphone create an agent called Support Bot
   /agentphone buy a US phone number with area code 415
   /agentphone call +14155551234 and ask about their return policy
   /agentphone show me recent calls and transcripts
   /agentphone check my SMS conversations
   /agentphone set up a webhook at https://my-server.com/hook
   ```
   Completion criterion: Claude Code has the skill installed and the API key is in its runtime environment.

8. **Smoke-test direct API only with safe read/list calls first.** Use API endpoints from `https://docs.agentphone.ai/llms.txt` or the OpenAPI files. For write actions, create a tiny test only with user approval because numbers, calls, and messages have billing and external side effects. Completion criterion: a read/list call succeeds, or a controlled user-approved write returns an AgentPhone resource ID.

9. **Use SDKs when building application code.** For Python:
   ```bash
   pip install agentphone
   ```
   Example from AgentPhone docs/home page:
   ```python
   from agentphone import AgentPhone

   client = AgentPhone(api_key="YOUR_API_KEY")
   agent = client.agents.create(
       name="Support Bot",
       voice_mode="hosted",
       system_prompt="You are a helpful assistant."
   )
   number = client.numbers.buy(agent_id=agent.id)
   ```
   For TypeScript:
   ```bash
   npm install agentphone
   ```
   Example from docs:
   ```typescript
   import { AgentPhoneClient } from "agentphone";

   const client = new AgentPhoneClient({ token: "YOUR_API_KEY" });
   const agent = await client.agents.createAgent({ name: "Support Bot" });
   const number = await client.numbers.createNumber();
   await client.agents.attachNumberToAgent({
     agent_id: agent.id,
     numberId: number.id,
   });
   ```
   Completion criterion: the project can authenticate and perform a low-risk list/get operation before provisioning numbers or sending communications.

## Pitfalls

- `https://docs.agentphone.ai/_mcp/server` appears in docs-page banners for AI client integration with docs; the phone-capability MCP server documented for agents is the local stdio package `npx -y agentphone-mcp` with `AGENTPHONE_API_KEY`.
- Do not paste `AGENTPHONE_API_KEY` into committed config. Use environment indirection like `${AGENTPHONE_API_KEY}`.
- Phone numbers, SMS/iMessage, and calls can incur cost and contact third parties. Ask before buying numbers, sending messages, or placing calls unless the user explicitly authorizes it.
- AgentPhone messages use one endpoint for SMS, MMS, and iMessage; platform delivery may fall back to SMS/MMS when iMessage-only features cannot apply.
- Image-only iMessage/MMS messages may arrive with an empty `message`/body and the attachment in `data.mediaUrl`; bridges must extract media fields and pass them to Hermes, not treat empty text as “nothing received.” See `references/inbound-media-imessage.md`.
- **False “Hermes hit an internal error” on iMessage:** that string is a **bridge canned fallback**, not model output. Dewey bridge (`~/.hermes_agentphone_bridge/agentphone_bridge.py`) sends it whenever the `hermes chat` subprocess exits non-zero and **discards stdout**. Observed pattern: Hermes fully finishes (`Turn ended: reason=text_response`), writes a good final reply + session, then aborts during CLI cleanup (`CLI cleanup calling memory shutdown` / Honcho) with **returncode -6 (SIGABRT)**. Session DB and `agent.log` show success; `events.log` shows `hermes_failed`. Do not treat this as webhook, allowlist, API key, or model refusal until you check those. Preferred bridge fix: if returncode != 0 but cleaned stdout still has a real reply, send the reply and log the bad exit. Recipe: `references/hermes-bridge-false-failure.md`.
- Acks on the Dewey bridge are **generic only** (static pool). Keyword-extracted “contextual” acks were rejected in production for word salad. Older checklist lines that still recommend keyword acks are stale; authority is `references/poke-style-imessage-bridge.md`.
- Source docs can move. Start from `https://docs.agentphone.ai/llms.txt`; it lists the current `.md` pages and OpenAPI links.
- Context7 may not have an AgentPhone library entry; if resolution fails, use AgentPhone’s docs index, OpenAPI, Composio web search, Perplexity, and Firecrawl instead.
- Do not invent OpenClaw config file paths. Use the client’s MCP configuration location or inspect its docs/config first.
- SDK method names differ by language: TypeScript docs show `AgentPhoneClient`, while the website/Python examples show `AgentPhone`.
- Direct REST calls from generic Python/HTTP clients may hit Cloudflare Error 1010 even with a valid key; verify through `hermes mcp test agentphone` or the `agentphone-mcp` stdio server before blaming credentials.
- Inbound texting is a separate class of setup from outbound MCP: outbound tools can work while inbound texts go nowhere until an AgentPhone webhook reaches a local/cloud bridge. Agent-scoped webhooks (`POST /v1/agents/{agent_id}/webhook`) are safer than project-level webhooks when configuring one Hermes agent among several.
- `cloudflared` quick-tunnel URLs can be emitted before AgentPhone's webhook safety validator can resolve them. If registration fails with `VALIDATION_ERROR_URL` / “DNS resolution failed — cannot verify webhook URL safety,” wait for public DNS readiness before registering or use a stable named tunnel; do not misdiagnose this as credential failure.

## Verification

For Hermes MCP setup, invoke through the `terminal` tool:

```bash
hermes mcp test agentphone
```

The skill worked when Hermes connects to `agentphone`, discovers tools, and no secret value is printed in the command output.
