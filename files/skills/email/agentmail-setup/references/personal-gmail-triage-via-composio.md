# Personal Gmail triage via Composio (${OWNER_EMAIL})

Class procedure for Nick reply-queue questions. AgentMail remains for agent inboxes only. Granola is for meeting follow-ups when asked.

## Default mailbox

- **Primary:** `${OWNER_EMAIL}` via Composio `gmail` toolkit.
- **Secondary:** AgentMail MCP only if named or after personal triage for exceptions.
- **Meetings:** Composio `granola_mcp` when user asks about meetings / follow-ups.
- **Not required:** local google-workspace OAuth when Composio Gmail works.

## Pull mail

Always Gmail first. Paginate `GMAIL_FETCH_EMAILS` / `GMAIL_LIST_THREADS` with `page_token`. Parallel hydrate via ThreadPoolExecutor in COMPOSIO_REMOTE_WORKBENCH.

If `/mnt/files/mex/*.json` missing, re-fetch with `run_composio_tool` inside workbench (do not stall).

Noise denylist: OpenRouter receipts, Mia watchdog (MEMORY cap, cron fail, gateway), Latitude noise, Otter/Fireflies, Xfinity, pure Cal RSVP, Slack notify.

## Granola

Prefer `GRANOLA_MCP_QUERY_GRANOLA_MEETINGS` for Nick action items. List `this_week` / `last_week` / `last_30_days` **serially** (parallel hits rate limit). Merge into same P0–P2 board.

## Priority

| Rank | Meaning |
|---|---|
| P0 | Billing/legal, stuck customer, time-critical |
| P1 | Clear human ask (reschedule, phone, commercial) |
| P2 | Soft loops / promised deliverables |
| FYI | Receipts, agent diagnostics (act, don't email-reply) |

## One-by-one loop (Nick preference)

Ask questions (slot, agenda, Meet vs phone, reply-only vs reply+calendar) → propose exact draft/calendar → wait for go → execute one item → next. Never batch-send the triage board.

Gus-style: reply on thread + move Calendar event; keep Meet link unless told otherwise.

## Deliverable

Mailbox+Granola scanned · table · Reply now / Ops / Meeting follow-ups / Ignore · drafts only until explicit send.

## Session notes (Jul 2026)

- Roman: stop billing / free account
- Drew: phone after flaky Meet (+15555550123 when approved)
- Gus: 10–12am EST window; agenda Grok+Cursor+Obsidian then Magnus; reply+calendar
- Nate Menkin: Orgo spine interest
- Michael: Mia MEMORY 92% needs ops + reply
- Granola overdue: Glen rev-share, Marc Revo/ACH/Loom, Neal template, BrandRocket, Latitude Scale
