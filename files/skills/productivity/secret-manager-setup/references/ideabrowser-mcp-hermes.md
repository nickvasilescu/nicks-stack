# IdeaBrowser MCP on Dewey Hermes

Wire IdeaBrowser's hosted MCP into Hermes (operator Dewey), not customer boxes, unless Nick asks otherwise.

## Credential

| Env | 1P field | Shape |
|---|---|---|
| `IDEABROWSER_KEY` | `op://Hermes/Hermes Agent Secrets/IDEABROWSER_KEY` | `ib_…` (~50 chars) |

User may paste a key into 1Password first ("I added the API key to your 1password vault"). Discover field labels with single-item field label scan only — never dump full item JSON into the transcript.

```bash
# metadata-only resolve
ref='op://Hermes/Hermes Agent Secrets/IDEABROWSER_KEY'
key="$(op read "$ref")"
# print only: len, prefix ib_, last 4
hermes secrets 1password set IDEABROWSER_KEY "$ref"
rm -f ~/.hermes/cache/op_cache.json
```

Vendor smoke without logging the key:

```bash
# POST initialize to MCP URL with key in query; assert HTTP 200 + protocolVersion, no error
# Do not echo full URL with key into chat
```

## Hermes MCP config

IdeaBrowser "Other / MCP-compatible" docs:

```text
https://www.ideabrowser.com/api/mcp/mcp?key=YOUR_API_KEY
```

Use env substitution so the raw key never lands in `config.yaml`:

```bash
# Non-interactive: answer auth prompt "n" (key is in URL), enable all tools "y"
printf 'n\ny\n' | hermes mcp add ideabrowser \
  --url 'https://www.ideabrowser.com/api/mcp/mcp?key=${IDEABROWSER_KEY}' \
  --connect-timeout 60
```

Confirm:

```bash
hermes mcp list   # ideabrowser enabled
python3 -c "import yaml;from pathlib import Path;s=yaml.safe_load(Path.home().joinpath('.hermes/config.yaml').read_text())['mcp_servers']['ideabrowser'];assert '\${IDEABROWSER_KEY}' in s['url']"
```

Tools observed (51): `get_quickstart`, `list_projects`, `browse_ideas`, `research_trend`, `list_skills`, `run_skill`, `research_market_insight`, project/context file ops, idea research pipeline, etc.

After add: new session, `/reload-mcp`, or gateway restart before tools appear. Mid-session reload may list other MCPs first; if `ideabrowser` is missing, restart gateway / new CLI process so `${IDEABROWSER_KEY}` is injected from 1Password.

## Calling tools when not mid-session loaded

IdeaBrowser may show as **enabled** in `hermes mcp list` while `tool_search` / direct `mcp__ideabrowser__*` calls still fail in an old session ("not a deferrable tool"). Prefer:

1. New Hermes session / process after MCP add, **or**
2. **HTTP JSON-RPC client** with `IDEABROWSER_KEY` in process env (never print the key):

```python
# Pattern: initialize → optional notifications/initialized → tools/call
# Headers: Content-Type application/json, Accept application/json, text/event-stream
# Persist Mcp-Session-Id from response headers across calls
# tools/call names: browse_ideas, get_idea_research, get_founder_profile, ...
# Parse SSE "data:" lines or plain JSON; result usually under result.content[0].text as JSON string
```

Load key without echo:

```bash
# Prefer Hermes-injected env in agent tools; else:
# op read 'op://Hermes/Hermes Agent Secrets/IDEABROWSER_KEY'  (metadata only in chat)
# or single IDEABROWSER_KEY= line from ~/.hermes/.env without printing
```

### Arg quirks (session-proven)

| Tool | Quirk |
|---|---|
| `browse_ideas` | Pass `query`, optional `limit`, optional `sort` (`highest_opportunity`, `highest_pain`, `easiest_build`, `most_saved`, `newest`, …) |
| `get_idea_research` | `idea_id` must be a **string** (e.g. `"8560"`). Integer fails JSON schema. |
| `get_founder_profile` | Empty args OK when account has a profile |

Research playbook (ranking, X/market stack, landing-first next step): skill `grounded-research` → `references/ideabrowser-startup-ideation.md`.

## Security pitfalls

1. **`hermes mcp test ideabrowser` prints the fully resolved URL including `key=ib_…`.** Do not run it in shared transcripts. Prefer the metadata-only initialize probe above, or `hermes mcp list` + a real tool call after session load.
2. If a resolved key was printed, treat as exposed: rotate the IdeaBrowser key in the product UI, update the 1P field, clear `~/.hermes/cache/op_cache.json`, restart Hermes/gateway. Config URL with `${IDEABROWSER_KEY}` does not need editing.
3. Query-string auth is vendor-imposed; keep the placeholder form forever — never paste the raw key into `config.yaml`.
4. Do not map IdeaBrowser keys onto customer Orgo boxes as part of compare-fleet or pilot defaults.
5. HTTP fallback scripts must never log request URLs that include the key; log only status, tool names, and redacted idea payloads.

## Related

- Field catalog row: parent `SKILL.md` Dewey catalog
- Query-string MCP leak general rule: parent pitfalls
- Customer IdeaBrowser/Jordan vault work: skill `vault-managed-customer-agents` (product MCP on Dewey is separate from Saddles persona boxes)
- Startup ideation method: `grounded-research` / `references/ideabrowser-startup-ideation.md`
