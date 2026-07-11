# vidIQ MCP + content ideas (Dewey)

## Wire-up (verified)

- URL: `https://mcp.vidiq.com/mcp`
- Key UI: `https://app.vidiq.com/account/settings/mcp`
- Env: `VIDIQ_MCP_API_KEY` in `~/.hermes/.env` + 1Password `op://Hermes/Hermes Agent Secrets/VIDIQ_MCP_API_KEY`
- Config:

```yaml
mcp_servers:
  vidiq:
    url: https://mcp.vidiq.com/mcp
    headers:
      Authorization: Bearer ${VIDIQ_MCP_API_KEY}
    enabled: true
    connect_timeout: 60.0
```

- Test: `hermes mcp test vidiq` (expect ~40+ tools including `vidiq_outliers`, `vidiq_balance`)
- Plan: Boost OK during launch; MCP uses shared AI credits (~5/call typical; Video/Reel Watch ~10)

## Tool arg pitfalls

| Tool | Required / correct args | Do not use |
|---|---|---|
| `vidiq_outliers` | `keyword` and/or `channelIds` | `query` (wrong; returns garbage) |
| `vidiq_score_title` | `title` + **`type`: `long`\|`short`** | omitting `type` → -32602 |
| `vidiq_trending_videos` | `videoFormat` long\|short; optional `titleQuery` | trusting broad titleQuery alone |
| `vidiq_keyword_research` | `mode` research\|country_*; `keyword` for research | treating volumes as exact |

Useful outlier filters: `publishedWithin` (thisWeek…oneYear), `contentType`, `minOutlierScore`, `maxSubscribers`, `sort: breakoutScore`.

Direct JSON-RPC (when MCP tools not in-session): POST SSE to MCP URL with `Authorization: Bearer …`, methods `initialize`, `tools/call`.

## Nick content niche (for idea ranking)

Orgo (computers for AI agents), Hermes / OpenClaw / Claude Code, agent fleets, AI employees, Grok-as-brain, business-owner self-implementation, personalized production agents (Dewey).

High-signal X themes: config/setup (bookmarks), model swaps (Grok speed), fleet/templates, “stop building until…”, comparisons.

## Wave play (example)

Grok release wave → title pattern “Grok X Made My Hermes Agent Feel Brand New” + timed computer-use demo on Orgo; score titles with `vidiq_score_title` type=long before publishing.

## Related

- Skill `grounded-research` body sections: YouTube/video-idea grounding; film→publish; voice/Realtime
- Skill `youtube-content`: transcripts only
