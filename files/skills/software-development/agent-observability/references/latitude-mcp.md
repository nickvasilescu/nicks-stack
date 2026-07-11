# Latitude MCP in Hermes

Session-grounded pattern from configuring Latitude MCP for Hermes Agent.

## Working non-interactive configuration

Latitude's MCP endpoint can be used from Hermes with the existing Latitude API key via HTTP header auth. This avoids the interactive OAuth flow when the VM/browser session cannot log in to Latitude.

```yaml
mcp_servers:
  latitude:
    url: https://api.latitude.so/v1/mcp
    enabled: true
    headers:
      Authorization: Bearer ${LATITUDE_API_KEY}
```

Prerequisites:

- `LATITUDE_API_KEY` is set in the Hermes `.env` loaded by the session.
- For hosted Latitude CLI/API reads, leave `LATITUDE_BASE_URL` unset unless intentionally targeting a self-hosted API.

## Validation commands

```bash
hermes mcp list
hermes mcp test latitude
```

Expected result:

- `hermes mcp list` shows `latitude` as enabled.
- `hermes mcp test latitude` connects to `https://api.latitude.so/v1/mcp` and discovers Latitude tools.

A direct protocol smoke test can verify header auth before changing Hermes config:

```bash
set -a
. /root/.hermes/.env
set +a
unset LATITUDE_BASE_URL
curl -sS -i -X POST https://api.latitude.so/v1/mcp \
  -H "Authorization: Bearer $LATITUDE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"hermes-test","version":"0.0.1"}}}'
```

A successful response is HTTP 200 `text/event-stream` containing an MCP `initialize` result with serverInfo for `Latitude`.

## OAuth fallback

`hermes mcp login latitude` starts a browser OAuth flow and may print a URL plus a local callback port. Use it only when the user can authenticate in the browser or can paste the redirect URL back into the terminal. In non-interactive/headless sessions without cached tokens, OAuth fails with a `no cached tokens found` style message.

## Pitfalls

- Do not assume Latitude MCP requires OAuth just because Hermes offers `--auth oauth`; API-key header auth works for the endpoint.
- If `hermes config set mcp_servers.latitude.auth null` writes the literal string `"null"`, remove the key with a config-aware edit or save through `hermes_cli.config`; otherwise the config is untidy even if header auth still works.
- After changing MCP config, existing Hermes sessions may need `/reload-mcp`, `/reset`, or a fresh session before the MCP tools appear in the model tool list.
- Treat MCP write tools separately from read/list tools. Tool discovery and `listProjects` prove auth/connectivity, not that create/update/delete operations are authorized or policy-approved.
