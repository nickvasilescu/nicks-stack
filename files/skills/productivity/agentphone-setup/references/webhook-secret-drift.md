# Webhook secret drift after AgentPhone or MCP reload

Use when AgentPhone MCP can list numbers/messages but the Hermes iMessage bridge does not reply.

## Distinguish outbound connectivity from inbound health

A working MCP read proves only API access. It does not prove that inbound iMessages reach the local bridge. Verify both planes:

1. MCP/API: `list_numbers`, `list_conversations`, or `get_messages` works.
2. Bridge process: supervisor reports running and `127.0.0.1:8787` is listening.
3. Inbound events: inspect `~/.hermes_agentphone_bridge/events.log` for the newest `webhook_received`, `signature_rejected`, `hermes_start`, `hermes_done`, and `reply_sent` events.

If a recent inbound message exists in AgentPhone but the bridge log shows:

```text
signature_rejected reason="signature mismatch"
POST /hooks/agentphone ... 401
```

then the bridge's stored webhook secret is stale. This can happen while the webhook ID and URL remain unchanged.

## Repair

1. Call AgentPhone `get_webhook(agent_id=...)` and obtain the current `secret`.
2. Update only the bridge state/config field holding `webhook_secret`; never print the secret or paste it into chat.
3. Preserve restrictive permissions (`0600`) and use an atomic replace.
4. Restart the supervised bridge.
5. Confirm the listener and `bridge_ready` / `webhook_registered` events.
6. Call `test_webhook(agent_id=...)`.
7. Verify the bridge log records `webhook_received` and HTTP 200, not merely that the MCP tool says success.
8. With the user's authorization, send a short direct iMessage acknowledging the repair, then ask for a fresh inbound test.

Do not delete and recreate the webhook unless secret refresh plus restart fails. Recreating is a larger side effect and may change delivery configuration.

## Important diagnostic lesson

Do not claim “connected to iMessage” solely because the MCP server is present, a number is active, or messages can be read. State the narrower truth unless you have verified a signed inbound webhook and an outbound reply. The complete success condition is:

```text
active iMessage number
+ MCP read works
+ signed inbound webhook returns 200
+ bridge starts Hermes
+ outbound reply status=sent
```
