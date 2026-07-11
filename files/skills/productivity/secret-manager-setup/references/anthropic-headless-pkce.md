# Anthropic headless PKCE (Claude Pro/Max) for Hermes

## Why not only `hermes auth add anthropic`

On non-TTY / agent-driven shells, `input("Authorization code: ")` gets EOF and exits with "Anthropic OAuth login did not return credentials." Generate PKCE yourself, keep verifier+state on disk, ask the user for the code, exchange, then write pool + oauth file.

## Constants (Hermes-aligned)

- Client ID: `9d1c250a-e61b-44d9-88ed-5944d1962f5e`
- Redirect: `https://console.anthropic.com/oauth/code/callback`
- Scopes: `org:create_api_key user:profile user:inference`
- Authorize host: `https://claude.ai/oauth/authorize`
- Token endpoints (try in order):
  1. `https://platform.claude.com/v1/oauth/token`
  2. `https://console.anthropic.com/v1/oauth/token`
- User-Agent for token exchange: non-claude-code UA (e.g. `hermes-agent`)

## Flow

1. Generate PKCE S256 verifier/challenge + random `state`.
2. Save pending JSON to `$HERMES_HOME/.anthropic_oauth_pending.json` mode 0600:
   `{verifier, oauth_state, client_id, redirect_uri, created_at}`.
3. Print full authorize URL (do not claim browser opened on headless).
4. User pastes `code#state` (state must match pending).
5. POST JSON grant with `grant_type=authorization_code`, `client_id`, `code`, `state`, `redirect_uri`, `code_verifier`.
6. Write `$HERMES_HOME/.anthropic_oauth.json`:
   `{access_token, refresh_token, expires_at_ms}` mode 0600.
7. Add credential pool entry:

```python
from agent.credential_pool import PooledCredential, load_pool
from hermes_cli.auth_commands import AUTH_TYPE_OAUTH, SOURCE_MANUAL
import uuid
pool = load_pool("anthropic")
pool.add_entry(PooledCredential(
    provider="anthropic",
    id=uuid.uuid4().hex[:6],
    label="claude-oauth",
    auth_type=AUTH_TYPE_OAUTH,
    priority=0,
    source=f"{SOURCE_MANUAL}:hermes_pkce",
    access_token=access,
    refresh_token=refresh,
    expires_at_ms=expires_at_ms,
    base_url="https://api.anthropic.com",
))
```

8. Unlink pending file. Verify `hermes auth status anthropic` → logged in.
9. Smoke Messages API:
   - Authorization Bearer token
   - anthropic-version: 2023-06-01
   - anthropic-beta: oauth-2025-04-20
   - Probe model e.g. claude-haiku-4-5-20251001
   - Auth OK if not 401 (404 model name still means token works)

## Pitfalls

- Regenerating a new URL after the user has a code invalidates verifier/state.
- State mismatch is a hard abort.
- `resolve_anthropic_token()` may also surface a `claude_code` pool entry from `~/.claude`; both can coexist.
- Prefer OAuth over inventing ANTHROPIC_API_KEY when user wants Pro/Max subscription auth.
- OpenAI Codex is separate: `hermes auth status openai-codex` (ChatGPT OAuth), not OPENAI_API_KEY.
