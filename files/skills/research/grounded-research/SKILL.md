---
name: grounded-research
description: "When the user says grounding or asks to ground reasoning/context/search, use live X tools and Composio specialized search (Exa, Firecrawl, Perplexity, Context7) instead of only generic web_search. Also covers IdeaBrowser-backed startup/idea grounding when IB MCP is available."
version: 1.2.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, grounding, composio, x, context7, exa, firecrawl, perplexity, ideabrowser, startups]
    category: research
    related_skills: [x-mcp-integration, xurl, vendor-tool-evaluation, secret-manager-setup, claude-design]
    created_by: agent
---

# Grounded Research

## Triggers (load this skill)

- User says **grounding**, **ground this**, **ground your reasoning**, or **use xmcp / composio to ground**
- User wants claims backed by live platform data or specialized search, not only general web_search
- Multi-source research on X/social, current algorithms, docs-backed library APIs, or deep web synthesis

User preference (explicit): **grounding means X MCP + Composio search stack**, not a generic web_search-only pass.

### First-turn discipline (hard)

- When the user says **grounding / ground this / ground your reasoning**, load this skill and **run the stack before any final answer**. Do not ship a web_search-only synthesis first and offer to re-ground later.
- When the task is **X/social performance, algorithm claims, launch-post playbooks, or live discussion on X**, treat it as grounding by default even if the word is absent: start with xurl/x-docs (and Composio) in the first tool batch.
- After a grounded pass, always include a brief **tools used / failed** table. User previously called out ungrounded answers explicitly.

## Default stack

| Job | Tools (prefer in this order) |
|-----|------------------------------|
| Live X posts / metrics / discussion | `xurl search` (app `hermes-x`), xapi MCP reads, `x_search` if credits allow |
| Official X product/API docs | x-docs MCP: `mcp__x_docs__search_x`, then filesystem/query tools for full pages |
| Web discovery + ranked sources | Composio **EXA_SEARCH** (highlights/summary; `deep` when needed) |
| Full article / page text | Composio **FIRECRAWL_SCRAPE** or **FIRECRAWL_SEARCH** |
| Multi-source synthesis with citations | Composio **PERPLEXITYAI_EXECUTE_AGENT** (`pro-search`) or PERPLEXITYAI_SEARCH |
| Library/framework/SDK docs | Composio **Context7**: resolve then query (see below) |
| Generic fallback only | Hermes `web_search` / `web_extract` after or beside the above, not instead |

Composio workflow always:

1. `COMPOSIO_SEARCH_TOOLS` with a query that **names the toolkits you need** (Exa, Firecrawl, Perplexity, Context7). Search is query-matched; a marketing-only query may omit Context7.
2. Pass `session_id` from the search response on subsequent Composio calls.
3. `COMPOSIO_MULTI_EXECUTE_TOOL` for parallel independent calls.
4. If response is large, use `COMPOSIO_REMOTE_WORKBENCH` / bash on the saved sandbox file; do not re-fetch blindly.

## Context7 (Composio toolkit `context7_mcp`)

Connection is typically ACTIVE. Do not skip because it was missing from a prior unrelated search.

```
CONTEXT7_MCP_RESOLVE_LIBRARY_ID  { libraryName, query }  → pick libraryId
CONTEXT7_MCP_QUERY_DOCS          { libraryId, query }   → docs + snippets
```

Rules:

- Always resolve first unless user already gave `/org/project` library ID.
- Prefer higher snippet count + High reputation + higher benchmark score when matches compete.
- Max ~3 resolve and ~3 query calls per question; narrow the query if truncated.
- Results often arrive as free-text under `data.data[].text`; parse for `library ID: /...`.
- Use for SDKs/frameworks (Next.js, twitter-api-v2, React, etc.). Not for live X feed content.

Fallback if Context7 coverage is thin: `deepwiki_mcp` (GitHub repo wiki) via Composio.

## Operational commerce/payment failure grounding

When a shopping or payment agent fails after cart confirmation, do not stop at generic web research or repeat the checkout blindly. First localize the failure from live account, wallet, card, transaction, merchant-link, and order-history evidence; then compare it with the provider's documented lifecycle and incident history.

Key rule: a live card minted and then closed with **no pending, settled, or declined transaction** strongly localizes the failure to the merchant-shopping path before issuer authorization. Repeated attempts may still consume card quota, so inspect quota before retrying and escalate with every card/conversation ID.

Detailed workflow and support payload: `references/agent-commerce-checkout-failure-localization.md`.

## X grounding specifics

Load `x-mcp-integration` + `xurl` for setup and safety. Research pattern:

```bash
xurl --app hermes-x auth status
xurl --app hermes-x whoami
xurl --app hermes-x search 'QUERY -is:retweet lang:en' -n 20
```

Score posts with `public_metrics` (likes, replies weighted higher, retweets, bookmarks, impressions). Prefer original posts with media when studying what performs.

### Pitfalls

- **`search_posts_all` (xapi) + OAuth2 User Context → 403** Unsupported Authentication. Needs app-only bearer MCP (`xapi-app-only`), not "API is broken". Use `xurl search` for user-context recent search.
- **`min_faves:` / some premium operators** may be invalid for current product packaging. Drop them; filter client-side on `public_metrics`.
- **`x_search` (xAI plugin)** can fail with spending-limit/credits. Fall back to xurl/xapi; do not claim X search is permanently unavailable.
- **x-docs** is strong for API/media/ads/metrics docs, weak for organic For You ranking. Combine with Buffer/Sprout-style studies via Firecrawl/Exa and live post samples via xurl.
- Do not treat one recent-search sample as global "what always goes viral." Label confidence.

## Output contract when user asked for grounding

1. State which tools ran and which failed (brief table).
2. Lead with evidence-backed claims; cite sources (Buffer study, live post IDs/metrics, docs).
3. Explicit confidence: high / moderate / low / unknown.
4. Separate durable platform mechanics from one session's live sample.
5. Do not re-answer from prior ungrounded memory as if it were re-verified.

## YouTube / video-idea grounding (vidIQ + X)

When the user wants **video ideas, outliers, packaging, or niche content strategy** (not a transcript summary):

1. **vidIQ MCP** — `https://mcp.vidiq.com/mcp` with Bearer `VIDIQ_MCP_API_KEY` (`.env` + 1Password). Config:
   ```yaml
   mcp_servers:
     vidiq:
       url: https://mcp.vidiq.com/mcp
       headers:
         Authorization: Bearer ${VIDIQ_MCP_API_KEY}
       enabled: true
   ```
   Verify: `hermes mcp test vidiq`.
2. **Key tool args (session-proven):**
   - `vidiq_outliers`: use **`keyword`** (not `query`). Prefer `publishedWithin`, `contentType` long|short|all, `minOutlierScore`, `maxSubscribers`, `sort: breakoutScore`.
   - `vidiq_keyword_research`: `mode: research`, optional `country: US`.
   - `vidiq_score_title`: **requires** `type: long|short` and `title`.
   - `vidiq_trending_videos`: requires `videoFormat`; `titleQuery` is often off-niche noise — prefer outliers for targeted niches.
3. **Plan gating:** support docs say MCP on **all plans during launch** (Free/Boost/Max). Marketing “Max only” is stale. Boost credits (~2k/mo) are enough for research; most calls ~5 credits. Confirm with `vidiq_balance`.
4. **X layer:** `xurl --app hermes-x search 'from:HANDLE -is:reply'`; rank by bookmarks/likes/impressions. Bookmarks often flag how-to demand. Avoid broken `min_faves:` operators; filter metrics client-side.
5. **Output shape:** ranked ideas with (a) title, (b) outlier format being stolen, (c) X proof, (d) packaging, (e) confidence. Separate keyword *estimates* from measured breakout scores.
6. Transcript-only work stays with skill `youtube-content`.

## Film → cloud → multi-platform publish (architecture, not product pitch)

When user asks how to store filmed video then have the agent publish everywhere:

- **Two layers:** (1) asset store with HTTPS URL (Drive/Dropbox inbox → optional R2/S3), (2) publish fabric MCP/API.
- **Agent-ready publish options:** Upload-Post (MCP + Hermes skill marketing, free tier), Blotato (`mcp.blotato.com/mcp`, flat ~$29), Ayrshare (video last-mile, `mediaUrls`, action MCP; higher price). Ayrshare does not host/transcode.
- **Do not** use YouTube unlisted as master storage. Prefer approval-gated first posts.
- See also `vendor-tool-evaluation` for product verdicts from official pages.

## Hermes voice vs OpenAI Realtime (attach to Dewey)

- **Native Hermes voice** = STT → agent loop → TTS (not Realtime-as-brain). Config: `stt.*`, `tts.*`, `/voice on`. OpenAI ears/mouth: `VOICE_TOOLS_OPENAI_KEY` (Whisper + OpenAI TTS). Edge TTS works with no key.
- **OpenAI Realtime / gpt-realtime** = duplex speech-to-speech. Hermes core does **not** replace the agent loop with Realtime. Existing Realtime use: Google Meet plugin `mode=realtime` (`OPENAI_API_KEY` / `HERMES_MEET_REALTIME_KEY` + virtual audio).
- **Recommended product path for Nick:** Path1 Telegram voice notes + OpenAI STT/TTS (keep Grok as brain); Path2 Realtime **orchestrator** tool-calling into Hermes/Grok/Orgo executor. Do not fork Realtime as sole tool host if MCP/computer-use/Honcho must stay.
- Orgo cloud desktop usually has no real mic — prefer Telegram/AgentPhone audio over CLI mic on the VM.

## Startup / idea grounding (IdeaBrowser + market + X)

When the user wants **startup ideas, micro-SaaS wedges, AI agent business concepts, or "what should we build"** and grounding is requested (or implied: "use IdeaBrowser / xmcp / search tools"):

1. **Do not invent a top-10 list from model priors alone.** Run multi-source grounding first.
2. **Stack (Dewey):** IdeaBrowser MCP (validated idea DB) + xurl/x_search (demand chatter) + Composio Exa/Perplexity/Firecrawl (market writeups) + Hermes `web_extract` on shortlisted URLs.
3. **IdeaBrowser ops** live in `secret-manager-setup` → `references/ideabrowser-mcp-hermes.md` (setup, key safety, HTTP fallback when tools not mid-session). Research playbook + output shape: `references/ideabrowser-startup-ideation.md` (this skill).
4. **Founder-fit filter:** pull `get_founder_profile` when available; prefer ideas that match skills, budget, time, and unfair stack (for Nick: Orgo computers, Hermes fleets, marketing, agency/AI-employee demos).
5. **Default next deliverable after ranking:** one wedge + a demoable landing/pilot CTA (not a full product). Landing craft: `claude-design` + `popular-web-designs`.
6. If the wedge is a **managed AI employee**, lock one role + weekly artifact and follow skill `managed-ai-employee-pilot` (headed Orgo demo pack required; do not stop at landing mock).
7. Always emit the **tools used / failed** table and per-idea **confidence** labels.

## Related skills

- `x-mcp-integration` — MCP/xurl auth, app-only split, headed Developer Portal setup, probes
- `xurl` — CLI surface + secret safety
- `secret-manager-setup` / `references/ideabrowser-mcp-hermes.md` — IdeaBrowser key + MCP wire-up (not idea research method)
- `references/ideabrowser-startup-ideation.md` — browse/sort/filter recipe, ranking, landing-first next step
- `managed-ai-employee-pilot` — role lock, weekly artifact, headed demo pack, design partners after wedge pick
- `references/website-landing-launch-on-x.md` — launch/post format ladder (this skill; no separate x-organic-content skill)
- `claude-design` + `popular-web-designs` — one-off HTML landing after wedge selection
- `vendor-tool-evaluation` — product verdicts from official sources
- `youtube-content` — transcripts/summaries only (not outlier discovery)
- `agentphone-setup` — phone/SMS/iMessage bridge (voice calls separate from Hermes CLI voice)
