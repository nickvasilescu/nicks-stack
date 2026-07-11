---
name: agentcard-hermes-setup
description: Set up AgentCard MCP for Hermes.
version: 0.1.2
author: Hermes
metadata:
  hermes:
    tags: [AgentCard, Hermes, MCP, Payments]
---

# AgentCard Hermes Setup

Use this skill to connect AgentCard to Hermes through the Streamable HTTP MCP server and verify that the card, wallet, merchant, and buy tools are usable. It does not replace the hub-installed `agent-card` skill's operational rules for card creation, PAN/CVV, KYC, shopping, or safety. It is a Hermes-specific setup and troubleshooting layer for OAuth, MCP config, reload verification, merchant linking, and post-KYC wallet funding.

See `references/agentcard-doordash-setup-2026-07.md` for a condensed session transcript pattern covering OAuth with AgentMail and DoorDash linking.
See `references/agentcard-kyc-troubleshooting.md` for KYC document/face-scan blockers, expired verification links, direct document upload, and face-scan minting.
See `references/agentcard-wallet-funding.md` for fund_wallet flow, submit_user_info vs KYC gates, sandbox/TEST vs live cards, and support when onramp stays blocked after KYC approved.

When the user asks for **the AgentCard ID / KYC / face / verification link** (resume setup): do not dig old chat tokens first. Call `get_kyc_status`, then `start_kyc(terms_accepted=true)`, return the fresh `verificationUrl`. Open in Safari/Chrome (not in-app browser). Poll after they finish.

When the user asks to **fund the wallet / add money / Apple Pay or Google Pay**: follow `references/agentcard-wallet-funding.md`. Ask amount first. Do not probe with `create_card`.

## When to Use

- The user asks for the AgentCard identity verification / face-scan / ID setup link.
- The user asks to fund the AgentCard wallet or unblock `fund_wallet`.
- The user asks to enable AgentCard, AgentCards, Agent Card, or agentcard.sh in Hermes.
- The AgentCard skill is installed but `mcp__agent_cards__*` tools are not available yet.
- The user wants DoorDash, Good Eggs, Locale, or Agentcard Flights available through Hermes.
- `hermes mcp add ... --auth oauth` fails in a non-interactive session or does not save config.
- The user asks whether AgentCard checkout uses DoorDash's card-on-file or one-time cards.
- The user asks whether cards are live vs sandbox/TEST.

## Prerequisites

- Hermes is installed and can run `hermes mcp list` through the `terminal` tool.
- AgentCard docs source of truth: `https://docs.agentcard.sh`.
- AgentCard MCP endpoint: `https://mcp.agentcard.sh/mcp`.
- MCP transport: Streamable HTTP.
- Authentication: OAuth 2.0 / OAuth 2.1 PKCE, no API key.
- A reachable email inbox or phone number for AgentCard magic-code login.
- If using the Dewey setup, AgentMail inbox `${AGENTMAIL_INBOX}` can receive WorkOS AgentCard sign-in codes.

## How to Run

Use `terminal` for Hermes CLI setup and tests. Use AgentMail tools, when available, to read magic-code emails. Use `browser_navigate`, `browser_type`, and `browser_click` for the AgentCard OAuth page when a browser flow is required.

Canonical config in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  agent-cards:
    url: https://mcp.agentcard.sh/mcp
    auth: oauth
    enabled: true
```

After config and OAuth, verify with:

```bash
hermes mcp test agent-cards
hermes mcp list
```

## Quick Reference

```text
https://docs.agentcard.sh/llms.txt
https://docs.agentcard.sh/personal/mcp/overview.md
https://docs.agentcard.sh/personal/quickstart.md
https://docs.agentcard.sh/companies/mcp/overview.md
https://docs.agentcard.sh/companies/examples/hermes.md
https://mcp.agentcard.sh/mcp
hermes mcp test agent-cards
hermes mcp login agent-cards
hermes mcp list
script -q /tmp/agentcards-oauth.typescript -c 'hermes mcp login agent-cards'
```

## Procedure

1. **Ground the setup in official docs.**
   - Check `https://docs.agentcard.sh/llms.txt` and the Personal MCP overview.
   - Confirm the endpoint is `https://mcp.agentcard.sh/mcp`, transport is Streamable HTTP, and auth is OAuth.

2. **Install or verify the AgentCard skill.**
   - If the user provided a skill package, install it through the approved skills path.
   - Load the hub-installed `agent-card` skill with `skill_view` before doing card or shopping operations.
   - Do not edit the hub-installed skill; create or update this local setup skill for Hermes-specific lessons.

3. **Add the MCP config.**
   - Prefer `hermes mcp add` when a fully interactive CLI is available.
   - If non-interactive OAuth prevents config from being saved, patch `~/.hermes/config.yaml` with the canonical `agent-cards` entry above.

4. **Run OAuth in an interactive pseudo-terminal.**
   - Invoke through the `terminal` tool with a PTY or `script` wrapper:

```bash
script -q /tmp/agentcards-oauth.typescript -c 'hermes mcp login agent-cards'
```

   - Open the printed authorization URL in the browser.
   - Sign in with the selected AgentCard email or phone number.
   - Retrieve the WorkOS code from the user's chosen inbox if you have read permission.
   - Authorize Hermes Agent when AgentCard shows the scopes.

5. **Handle callback quirks.**
   - If the browser lands on `127.0.0.1 refused to connect`, inspect the page URL. The URL may still contain the OAuth `code` and `state`.
   - If the running `hermes mcp login` process is still prompting for a pasted redirect URL, paste the full callback URL or the `?code=...&state=...` portion.
   - If the process already timed out, rerun login and complete the flow promptly with the fresh URL and state.

6. **Verify the setup.**
   - Run:

```bash
hermes mcp test agent-cards
hermes mcp list
```

   - Success looks like connection to `https://mcp.agentcard.sh/mcp` with OAuth and a discovered AgentCard tool count.
   - Confirm token files under `~/.hermes/mcp-tokens/` are mode `0600` if inspecting credentials.

7. **Reload Hermes tools if needed.**
   - Hermes may reload MCP servers automatically after config changes.
   - If the conversation reports that MCP servers reloaded and `agent-cards` was added, AgentCard tools are now available in the current session.
   - Otherwise restart or reload the Hermes session before expecting `mcp__agent_cards__*` tools to appear.

8. **Link DoorDash only when the user wants shopping.**
   - Call `buy_list_merchants` to inspect merchant state.
   - For DoorDash, call `buy_connect` with merchant `doordash` and send the hosted login URL to the user.
   - After the user says they completed login, call `buy_connect_status` with the returned `pending_id`.

9. **Orient merchant address and payment behavior.**
   - For linked DoorDash accounts, list saved addresses through the buy flow before asking for a raw address.
   - DoorDash and Good Eggs do not use a stored DoorDash card-on-file through AgentCard. Checkout mints a one-time AgentCard virtual card funded from the AgentCard wallet.
   - Before shopping, check wallet status with `get_wallet`; use `fund_wallet` to generate Apple Pay or Google Pay funding links if the balance is short.

10. **Handle KYC blockers before wallet funding.**
   - If identity is incomplete, use `get_kyc_status` / `start_kyc` and follow `references/agentcard-kyc-troubleshooting.md`.
   - **Mint face link on demand:** `get_kyc_status` then `start_kyc(terms_accepted=true)` → `verificationUrl` (`api.agentcard.sh/kyc/verify?token=...`, ~48h). Prefer this over reusing AgentMail or old transcript links. Confirm account with `whoami` (Dewey: typically `${AGENTMAIL_INBOX}`).
   - If browser upload links expire immediately but the user sent ID images in chat, prefer direct document upload using the upload token rather than repeatedly giving failing links.
   - Do not save SSN, raw ID values, or document numbers in memory or support messages.

11. **Fund the wallet for live spend (after KYC).**
   - Full path: `references/agentcard-wallet-funding.md`.
   - Confirm amount (and Apple vs Google Pay if needed). Call `fund_wallet(amount_cents)`; success returns a checkout URL the user must open.
   - Before funding, ensure `submit_user_info` has phone (E.164) + `terms_accepted=true` with explicit user confirmation.
   - Orient with `get_wallet` / `list_cards`: `[TEST]` / `sandbox: true` cards are not live.
   - If KYC is already approved and phone/terms are saved but `fund_wallet` still returns verification required, treat as backend onramp bug: escalate via `start_support_chat` (template in the wallet-funding reference). Do not spam retries or probe with `create_card`.

## Pitfalls

- Do not use raw AgentCard API calls. The hub skill says API routes are internal; use MCP tools or the `agent-cards` CLI only.
- `hermes mcp add ... --auth oauth` can fail in non-interactive contexts and offer to save config only after a failed unauthenticated probe. If config is not saved, add the `auth: oauth` MCP entry directly and authenticate separately.
- Background OAuth attempts can complete after a later successful retry and produce stale failure notifications. Treat the latest verified `hermes mcp test agent-cards` result as authoritative.
- OAuth callback URLs are single-run stateful URLs. Do not reuse old authorization URLs after timeout; rerun `hermes mcp login agent-cards`.
- A visible browser `127.0.0.1 refused to connect` page can still be useful if the address bar has `code` and `state` and the login process is still waiting for a pasted redirect.
- DoorDash linking is separate from AgentCard wallet funding. A linked DoorDash account can still fail checkout if the AgentCard wallet has insufficient funds.
- AgentCard saved Stripe payment methods are for flight bookings only, not DoorDash or Good Eggs.
- **KYC approved ≠ onramp unlocked.** `fund_wallet` can still return "Verification is required" after approved KYC + saved phone/terms; that is a backend/onramp state issue, not a cue to re-run full KYC.
- **Do not use `create_card` to diagnose funding.** Sandbox/TEST cards can be created with $0 wallet while live funding stays blocked; each create emails the user and leaves a card entry.
- Always confirm dollar amount before `create_card` or `fund_wallet`. Confirm phone + cardholder terms before `submit_user_info`.
- Docs may mention `get_mode` / `set_mode` (test vs prod). If those tools are absent from the live MCP tool list, rely on `list_cards` sandbox flags and support rather than inventing mode APIs.

## Verification

Run this through the `terminal` tool:

```bash
hermes mcp test agent-cards && hermes mcp list
```

The setup is ready when the test connects to `https://mcp.agentcard.sh/mcp`, reports OAuth authentication, discovers AgentCard tools, and the current session reloads with `agent-cards` available.