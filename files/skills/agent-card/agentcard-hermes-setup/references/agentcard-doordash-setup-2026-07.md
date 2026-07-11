# AgentCard DoorDash Setup Session, 2026-07

## What happened

- Installed the hub skill from `tiny-agent-company/agent-card-skill` and verified it as `agent-card` version `1.2.0`.
- Grounded AgentCard MCP setup in official docs:
  - `https://docs.agentcard.sh/llms.txt`
  - `https://docs.agentcard.sh/personal/mcp/overview.md`
  - `https://docs.agentcard.sh/personal/quickstart.md`
  - `https://docs.agentcard.sh/companies/mcp/overview.md`
  - `https://docs.agentcard.sh/companies/examples/hermes.md`
- Confirmed endpoint `https://mcp.agentcard.sh/mcp`, Streamable HTTP transport, OAuth auth.
- Added local Hermes MCP config:

```yaml
mcp_servers:
  agent-cards:
    url: https://mcp.agentcard.sh/mcp
    auth: oauth
    enabled: true
```

## OAuth pattern that worked

The first non-interactive login attempt timed out around callback binding. The successful pattern was:

```bash
script -q /tmp/agentcards-oauth2.typescript -c 'hermes mcp login agent-cards'
```

Then:

1. Open the authorization URL in the browser.
2. Sign in with `${AGENTMAIL_INBOX}`.
3. Read the WorkOS code from AgentMail.
4. Enter the code into AgentCard.
5. Authorize Hermes Agent.
6. If the browser redirects to `http://127.0.0.1:<port>/callback?...`, the running login process should complete automatically if the callback listener is still alive. If not, paste that callback URL into the waiting PTY prompt.

Verified after success:

```text
hermes mcp test agent-cards
Transport: HTTP → https://mcp.agentcard.sh/mcp
Auth: OAuth 2.1 PKCE
✓ Connected
✓ Tools discovered: 46
```

Token files were present under `~/.hermes/mcp-tokens/` and mode `0600`.

## DoorDash linking pattern

1. Call `buy_list_merchants`.
2. DoorDash initially showed `unlinked`.
3. Call `buy_connect` with merchant `doordash`.
4. Send the hosted login URL to the user.
5. After the user says done, call `buy_connect_status` with the returned `pending_id`.
6. Success message: `Linked doordash. The user can now search and shop this merchant.`

## Address and payment observations

Saved DoorDash addresses were available after linking. The buy flow reported no default, but one address marked last used.

Payment behavior: DoorDash does not use a separate saved DoorDash card-on-file through AgentCard. DoorDash checkout uses a one-time AgentCard virtual card funded from the AgentCard wallet. AgentCard saved Stripe payment methods are for flight bookings only, not DoorDash.

Wallet status can be checked with `get_wallet`. If the wallet balance is short, call `fund_wallet` with an amount in cents and `apple_pay` or `google_pay`; it returns a secure funding URL.