# App-only auth + Developer Console notes

## Why

`mcp__xapi__search_posts_all` with user OAuth2 returns:

```text
403 Unsupported Authentication
Authenticating with OAuth 2.0 User Context is forbidden for this endpoint.
Supported authentication types are [OAuth 2.0 Application-Only].
```

This is expected product auth split, not a broken Hermes MCP wiring.

## Working split (this host pattern)

- **User context:** `xurl` app profile `hermes-x`, OAuth2 user `nickvasiles`, MCP server `xapi` via `xurl --app hermes-x mcp https://api.x.com/mcp`
- **Docs:** HTTP MCP `x-docs` → `https://docs.x.com/mcp` (no auth)
- **App-only:** `xurl auth app-only --app hermes-x` + requests with `--auth app`, and/or MCP `xapi-app-only` with bearer from env (`X_APP_ONLY_BEARER_TOKEN`)

Do not merge user-context and app-only assumptions into one server.

## Recent search without app-only

```bash
xurl --app hermes-x search 'QUERY -is:retweet lang:en' -n 20
```

Filter metrics client-side; avoid unsupported operators like `min_faves:` when packaging rejects them.

## console.x.com navigation (headed, Dewey)

| Step | Detail |
|------|--------|
| Entry | `https://console.x.com/accounts/<accountId>/apps` |
| Load | After navigation, page may sit on Loading then skeleton cards for 2–6s. Wait until Production app text is white/readable. |
| Windows | Focus window titled **Developer Console** if another Chrome has X login. |
| Open app | **Double-click** production app name (single click often no-ops or opens Create modal). |
| Deep link | Once known: `.../apps/<numericAppId>` lands on Keys & Tokens. |
| Tabs | Keys & Tokens · Subscriptions · Webhooks · Connections |
| App-only block | Bearer: date generated + **Revoke** / **Regenerate** only. **No Show** for existing bearer. |
| OAuth1 | Consumer Key/Secret have Show; Access Token may show user handle + scopes. |
| OAuth2 | Client ID may be visible; Client Secret has Show; user Access Token may say refresh active. |

### Bearer store (no chat leak)

1. Confirm with user before **Regenerate** (destroys previous app-only token).
2. User copies the new bearer in the portal.
3. Run:

```bash
bash ~/.hermes/skills/social-media/x-mcp-integration/scripts/store_app_only_from_clipboard.sh hermes-x
```

Script: clipboard → `xurl auth app-only --app hermes-x -` → clear clipboard → redacted smoke.

4. Optional: set `X_APP_ONLY_BEARER_TOKEN` in Hermes `.env` (user-owned; agent must not echo).
5. Add MCP `xapi-app-only` HTTP server with `Authorization: Bearer ${X_APP_ONLY_BEARER_TOKEN}` when full-archive MCP search is required.
6. `/reload-mcp` or new session; probe `search_posts_all`.

### Verify without dumping secrets

```bash
xurl auth status   # hermes-x bearer non-empty; do not print ~/.xurl
xurl --app hermes-x --auth app '/2/tweets/search/recent?query=from:XDevelopers&max_results=10'
```

## Incomplete mid-session resume

If a prior session stopped mid-portal (login wall, black framebuffer, max_turns / tool_choice errors):

- Check doctor green + whether Chrome is already on Keys & Tokens vs login.
- Do not re-walk the whole UI if the production app Keys page is already open.
- Finish only: bearer store → status → one app-only read probe → optional MCP wire.
- Prefer `xurl search` for urgent live grounding while app-only remains unwired.
- Portal pixel crawls + research in one turn easily hit `agent.max_turns` (60). Split: portal secrets first, research next session.

## Related

- Skill `grounded-research` for multi-source grounding workflow
- Skill `xurl` for CLI surface and secret safety
- Skill `orgo-desktop-local` for headed same-box control (double_click via Python client)
