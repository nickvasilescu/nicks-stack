# Context7 via Composio

Toolkit slug: `context7_mcp` (often ACTIVE on this Hermes Composio account).

## Tools

1. `CONTEXT7_MCP_RESOLVE_LIBRARY_ID` — required: `libraryName`, `query`
2. `CONTEXT7_MCP_QUERY_DOCS` — required: `libraryId`, `query`

## Flow

```
COMPOSIO_SEARCH_TOOLS query must mention Context7 (query-matched discovery)
→ MULTI_EXECUTE resolve
→ pick best libraryId (snippets, High reputation, benchmark score)
→ MULTI_EXECUTE query-docs
```

## Smoke-tested IDs (examples)

| Intent | libraryId | notes |
|--------|-----------|-------|
| Node X client + media tweet | `/plhery/node-twitter-api-v2` | high snippets |
| Next App Router metadata/OG | `/vercel/next.js` | prefer over weaker mirrors |

## Pitfalls

- If you only search Exa/Firecrawl/X marketing, Context7 may not appear in COMPOSIO_SEARCH_TOOLS results even when connected. Name it explicitly.
- Response text is often free-form under `data.data[].text`; parse for `Context7-compatible library ID: /...`
- Cap ~3 resolve + ~3 query per question
- Fallback: `deepwiki_mcp` for GitHub repo docs

## Not for

Live X timeline content, algorithm ranking, or "what posts are performing now" (use xurl/xapi).
