# IdeaBrowser-backed startup ideation (grounded)

Use when the user wants buildable startup / micro-SaaS / AI-agent business ideas and expects multi-tool grounding (IdeaBrowser, X, market sources). Setup and secret safety: `secret-manager-setup` → `references/ideabrowser-mcp-hermes.md`.

## When to run

- "10 startup ideas", "what should we build", "use IdeaBrowser MCP", "ground this in market/X"
- Follow-up: pick a top option and ship a landing or pilot path

## Multi-source recipe

1. **IdeaBrowser browse** (multiple queries, not one vague search):
   - Themes: vertical agents, voice receptionist, MCP security, local business AI, agency automation, creator ops, collections/invoicing
   - Sorts that matter: `highest_opportunity`, `highest_pain`, `easiest_build`, `most_saved`
   - Capture per idea: `id`, `title`, `slug`, `scores` (O/P/B/T), `engagement` (views/saves), short summary, hub path
2. **Optional IB enrich:** `browse_platform_trends`, `browse_platform_insights`, `get_founder_profile`, `get_idea_research` with **string** `idea_id`
3. **X demand:** `xurl --app hermes-x search` on category phrases (narrow queries; broad ones are noisy). Prefer original posts; score with `public_metrics`. Use `x_search` for synthesis when available.
4. **Market:** Composio EXA / PERPLEXITY / FIRECRAWL or Hermes `web_extract` on 2026 vertical-agent / micro-SaaS writeups. Filter for "own the workflow", not horizontal chatbot wrappers.
5. **Rank 8–12 unique ideas** then cut to ~10 with: IB scores + engagement, X/market corroboration, founder-fit, "build this week" path.

## Output shape

For each idea: name, one-liner, IB id/slug if any, why-now (evidence), build-this-week stack, pricing wedge, Nick/founder fit, **confidence** (high/moderate/low).

Include:
- Tools used / failed table
- Explicit "start this weekend" order (cash + demo + stack leverage)
- What **not** to build (horizontal agent platforms, thin wrappers)

## After ranking (default next step)

1. User picks **one** top wedge. Do not open 10 IB projects.
2. **Create IB project** for that wedge (`create_project`) + `submit_idea` + optional `start_idea_research` / `research_market_insight` (no auto-poll).
3. **Lock ONE employee role** if the wedge is managed AI workers: sell one **weekly artifact**, not "AI employees in general". See skill `managed-ai-employee-pilot`.
4. Ship a **demoable landing** (Linear-dark or brand-matched single HTML): outcome hero, product mock of the worker, compare-vs-chatbot, how-it-works, pricing pilot, form → mailto/CRM. Craft: `claude-design` + `popular-web-designs`.
5. **Parallel, required:** headed Orgo demo of the real weekly artifact (`orgo-desktop-local`). Landing mock is not the product.
6. Wire form later (AgentMail/CRM); localStorage + mailto is fine for v0.
7. Design-partner outreach drafts (skill `impressive-cold-outreach` for high-signal targets; productized pilot drafts may live next to the demo pack).

## Pitfalls

- IdeaBrowser MCP tools may be **enabled in config but absent from mid-session tool surface** until reload/new process. Use HTTP MCP client with env key (see ideabrowser-mcp-hermes.md); do not claim "no IdeaBrowser tools" without that fallback.
- `get_idea_research.idea_id` is a **string**; numbers fail schema validation.
- `hermes mcp test ideabrowser` **prints the resolved API key URL**. Never run in shared transcripts.
- X recent-search is noisy; label confidence and do not overfit one viral post.
- IB scores are research priors, not guarantees.
- Do not open 10 IdeaBrowser projects or start 10 research jobs unless the user asks; rank first, then project on the winner.
- `get_quickstart` suggested_actions may target a **stale** project; if user locked a new wedge, ignore and use the new `project_id`.
- Full idea research takes 15–30 min; **do not poll in a loop**. Tell the user it is running; check on their ask; attach with `rough_idea_id` when complete.
- `run_skill` returns expert **prompts** for Hermes to execute, not finished IB writeups. Still produce the analysis and `save_to_project`.

## Nick-specific fit (Dewey operator, when profile matches)

Unfair wedges often beat generic micro-SaaS: managed digital employees on Orgo desktops, Hermes multi-agent fleets, MCP security/gateway for agent teams, agency reporting/follow-up seats. Budget/time from founder profile: prefer pilot ($1.5k) + monthly seat over multi-year pure-infra unless MCP security is the explicit product bet.

Default first managed-employee pilot role (when stack is Orgo+Hermes+marketing): **client reporting employee for agencies** — weekly multi-client pack, live-demoable, human approve gate. Full playbook: `managed-ai-employee-pilot`.
