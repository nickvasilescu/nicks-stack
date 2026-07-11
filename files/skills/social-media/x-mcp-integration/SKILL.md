---
name: x-mcp-integration
description: "Configure and probe X API MCP and X Docs MCP from Hermes, including xurl OAuth bridge setup, app-only split, Developer Portal settings, and safe read/write boundaries."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [x, twitter, mcp, xurl, oauth, hermes, social-media]
    related_skills: [xurl, hermes-agent, grounded-research, orgo-desktop-local]
---

# X MCP Integration

Use this skill when setting up, validating, or troubleshooting X/Twitter MCP access in Hermes, especially when connecting both:

- X Docs MCP at `https://docs.x.com/mcp`
- X API MCP at `https://api.x.com/mcp` through `xurl mcp`

This skill complements the protected `xurl` and `hermes-agent` skills. Load those too for general CLI and Hermes MCP behavior.

## Non-negotiable secret safety

- Do not read, print, summarize, upload, or inspect `~/.xurl`.
- Do not use `xurl --verbose` in an agent session.
- Do not ask the user to paste secrets unless the user is deliberately configuring credentials in the current session. If a secret appears in chat, avoid reprinting it.
- Prefer recording only non-secret durable facts: app profile name, authorized handle, server names, and setup pattern.

## Server topology

Use separate MCP servers for separate auth modes:

1. `x-docs`, unauthenticated HTTP MCP:
   ```yaml
   mcp_servers:
     x-docs:
       url: https://docs.x.com/mcp
       enabled: true
       connect_timeout: 60
   ```

2. `xapi`, user-context X API MCP via xurl bridge:
   ```yaml
   mcp_servers:
     xapi:
       command: xurl
       args: ["--app", "<app-name>", "mcp", "https://api.x.com/mcp"]
       connect_timeout: 300
       enabled: true
   ```

3. Optional `xapi-app-only`, app-only HTTP MCP for endpoints that reject OAuth2 User Context:
   ```yaml
   mcp_servers:
     xapi-app-only:
       url: https://api.x.com/mcp
       headers:
         Authorization: Bearer ${X_APP_ONLY_BEARER_TOKEN}
       enabled: true
   ```

Do not merge user-context and app-only assumptions. Some search/count endpoints may demand app-only auth while user/timeline/bookmark endpoints need user context.

## Setup workflow

1. Install and verify xurl:
   ```bash
   xurl --version
   xurl auth status
   ```

2. Register the app profile only when authorized to handle the supplied credentials:
   ```bash
   xurl auth apps add <app-name> --client-id '...' --client-secret '...' --redirect-uri 'http://localhost:8080/callback'
   ```

3. For remote/headless machines, start OAuth in an interactive PTY so stdin stays open:
   ```bash
   xurl auth oauth2 --app <app-name> --headless
   ```

4. Give the user the generated URL. They authorize in a browser and paste back the full callback URL or the `code` value.

5. Submit the callback/code to the waiting process. Verify:
   ```bash
   xurl --app <app-name> whoami
   xurl auth default <app-name>
   ```

6. Add MCP through Hermes:
   ```bash
   hermes mcp add xapi --command xurl --connect-timeout 300 --args --app <app-name> mcp https://api.x.com/mcp
   hermes mcp test xapi
   ```

7. Reload tools:
   - In-session: `/reload-mcp`
   - Or start a fresh Hermes session.

## X Developer Portal checklist

When an authorization URL fails, check the portal before debugging Hermes:

- User authentication / OAuth2 enabled.
- App type: `Web app, automated app or bot`, not Native App or SPA.
- Permissions: `Read and write and Direct Message` when full user-context coverage is desired.
- Callback URI exactly: `http://localhost:8080/callback`.
- Optional extra callback: `http://127.0.0.1:8080/callback`.
- Website URL is a valid public HTTPS URL, not localhost.
- App/project is in Production and Pay-per-use if `client-not-enrolled` appears.
- Do not rotate keys unless the user explicitly asks.

## Pitfalls

- A non-PTY background `xurl auth oauth2 --headless` can fail with EOF because it expects pasted input. Use PTY/background with `process.submit`, or have the user run it interactively.
- OAuth authorization URLs are stateful. If portal settings changed after a failed attempt, kill the stale process and generate a fresh URL.
- If `xurl auth status` shows the built-in `default` app selected with no OAuth token, set the named app as default.
- `search_posts_all` can reject OAuth2 User Context with `Unsupported Authentication`. Add app-only MCP instead of treating the tool as broken.
- X News fields are strict. Observed valid fields include `id,name,summary,category,hook,keywords,disclaimer,updated_at,cluster_posts_results,contexts`; `title` is invalid.
- Trends/count endpoints may return 503 transiently. Retry later or try the app-only server before concluding anything durable.

## Read-only probe pattern

After `/reload-mcp`, probe without writes:

- `get_users_me`
- `get_users_posts`
- `get_users_mentions`
- `get_users_timeline`
- `get_users_bookmark_folders`
- `search_news` with valid `news.fields`
- relevant docs lookups via `x-docs`

Summarize both capability and limitations. Separate observed MCP tool surface from broader docs claims.

**Durable use case: product and model release research**  
Use targeted `xurl search` (directly or via xapi MCP) for official accounts when checking new model availability:

```bash
xurl search "grok 4.5" -n 5 --app hermes-x
xurl search "from:elonmusk Grok 4.5" -n 3 --app hermes-x
xurl search "from:SpaceXAI Grok 4.5" -n 3 --app hermes-x
```

This pattern was used successfully to capture announcement timing, pricing, "Grok Build" availability notes, and links to the official blog before cross-checking Hermes config, provider cache, and the live `https://api.x.ai/v1/models` endpoint. Combine X signals with Hermes `hermes status`, `provider_models_cache.json`, and direct API calls for full configuration verification.

## Write-action boundary

Before any post, reply, like, repost, bookmark, follow, block, mute, delete, media upload, or DM, confirm the exact target and text/action with the user unless they already gave explicit unambiguous instruction in the current turn.

## Headed Developer Portal (Orgo desktop)

When wiring **app-only bearer** or fixing portal settings on Dewey:

1. Prefer local `orgo-desktop` / `orgo_desktop_*` (doctor green) over cloud Orgo GUI.
2. Open `https://console.x.com` (modern) or `https://developer.x.com` headed so the user can watch. Classic dashboard often redirects into `console.x.com`.
3. **Login wall:** type only the known public handle if empty; **never** type password, 2FA, recovery codes, or paste secrets into chat. Stop and wait; poll screenshots until portal appears.
4. Focus the **Developer Console** Chrome window by name when multiple Chrome windows exist (X.com login vs console).
5. Navigate: left nav **Apps** → wait until skeleton rows resolve (Loading / gray placeholders for several seconds after URL change).
6. **Production app card:** single click often no-ops or hits adjacent Create / + New app. Prefer:
   - **double-click** the production app name via Python `OrgoDesktopClient.double_click` (CLI has no `double_click` subcommand yet), **or**
   - direct URL once known: `https://console.x.com/accounts/<accountId>/apps/<appId>`
   - Re-measure name text with PIL white-pixel centroid from the **latest** screenshot.
7. App detail opens on **Keys & Tokens**: App-Only Bearer, OAuth 1.0 Keys, OAuth 2.0 Keys.
8. **Bearer cannot be re-shown** after first generation (Revoke / Regenerate only). Do **not** Regenerate without explicit user consent.
9. Store app-only without leaking to chat:
   - User regenerates (if needed) → **Copy** in portal → run `scripts/store_app_only_from_clipboard.sh` which pipes clipboard into `xurl auth app-only --app hermes-x -`, clears clipboard, redacts smoke.
   - Alternate: user runs `xurl auth app-only --app hermes-x -` themselves and says **stored**.
10. Wire Hermes MCP `xapi-app-only` with `Authorization: Bearer ${X_APP_ONLY_BEARER_TOKEN}` only after xurl status shows bearer present (value never printed).
11. Re-probe `search_posts_all` only after app-only is live. Until then use `xurl search` and report the auth split honestly.

Long portal sessions burn `agent.max_turns` (often 60) and can end with provider `tool_choice` errors at the cap. Prefer a short checklist + user completes secrets over a 50-step pixel crawl.

### Dewey host facts (non-secret)

- xurl app profile: **`hermes-x`** (default)
- OAuth2 user: **`nickvasiles`**
- MCP: `x-docs` + `xapi` (user-context); `xapi-app-only` is the usual missing piece when full-archive search 403s

## References

- `references/x-mcp-hermes-setup.md`: OAuth headless flow, probe notes, app-only split.
- `references/app-only-and-console.md`: 403 split, console.x.com navigation, bearer store, mid-session resume.
- `references/announcement-research.md`: release/announcement search patterns.
- `scripts/store_app_only_from_clipboard.sh`: clipboard → `xurl auth app-only` without printing the token.
