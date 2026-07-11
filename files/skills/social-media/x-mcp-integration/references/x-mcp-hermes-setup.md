# X MCP Hermes setup and probe notes

These notes condense a successful Hermes setup session for X MCP and are safe to reuse. They intentionally omit secrets.

## Successful sequence

- Installed/verified xurl 1.2.x.
- Added X Docs MCP as `x-docs` with URL `https://docs.x.com/mcp`; Hermes discovered docs search/read tools.
- Registered a local xurl app profile.
- Fixed X Developer Portal settings before OAuth:
  - app type `Web app, automated app or bot`
  - callback `http://localhost:8080/callback`
  - permissions `Read and write and Direct Message`
  - valid public Website URL
  - Production / Pay-per-use when needed
- Ran `xurl auth oauth2 --app <app> --headless` in a PTY/background process.
- User opened the generated URL and pasted the localhost callback URL containing `state` and `code`.
- Submitted callback to the waiting process. xurl printed `OAuth2 authentication successful!`.
- Verified with `xurl --app <app> whoami`.
- Set default app: `xurl auth default <app>`.
- Added X API MCP:
  `hermes mcp add xapi --command xurl --connect-timeout 300 --args --app <app> mcp https://api.x.com/mcp`
- Ran `hermes mcp test xapi`; Hermes discovered 24 tools in that session.
- Used `/reload-mcp` before calling the new MCP tools in the same conversation.

## Observed probe results and lessons

Read-only calls that worked:

- `get_users_me`
- `get_users_posts`
- `get_users_mentions`
- `get_users_timeline`
- `search_news` with valid `news.fields`

Observed MCP tool surface was read-heavy: news, trends, post lookup, counts/search, user lookup/search, bookmarks, mentions, timeline, user posts. The current exposed MCP tools may be narrower than broad documentation claims, so probe `hermes mcp test xapi` and report observed tools rather than assuming the full API surface.

Failures that produced durable setup lessons:

- Non-PTY/background headless OAuth can exit with EOF. Use PTY or a real interactive shell.
- OAuth URL failure was resolved by giving the user a Developer Portal checklist, then generating a fresh OAuth URL.
- `search_posts_all` returned `Unsupported Authentication` under OAuth2 User Context; it wanted OAuth2 Application-Only. Add a separate app-only MCP server for that endpoint class.
- `get_trends_by_woeid` and `get_posts_counts_recent` returned 503 during probing. Treat as transient or auth-mode-specific until retried; do not hard-code a permanent limitation.
- `search_news` rejected `news.fields=title`; use fields such as `id,name,summary,category,hook,keywords,disclaimer,updated_at,cluster_posts_results,contexts`.

## Suggested final topology

- `x-docs`: docs search/read, no auth.
- `xapi`: user-context xurl bridge for account/timeline/mentions/bookmarks/user-context endpoints.
- `xapi-app-only`: optional direct HTTP server with app-only Bearer for full archive search and count endpoints that reject user-context OAuth.

## Reporting pattern

When the user asks to “probe around,” produce:

1. What identity/auth is active.
2. Which tool categories are actually exposed.
3. A few representative successful reads with metrics or IDs.
4. Endpoint failures with exact error class.
5. Concrete next setup improvement, usually app-only MCP if search/count endpoints reject user context.
