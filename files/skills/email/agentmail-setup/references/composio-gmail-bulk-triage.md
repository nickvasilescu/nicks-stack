# Composio Gmail Bulk Triage — 200+ Unread Pattern (Jul 10 2026)

Session recovered 219 unread `newer_than:7d`, 52 after human filter. Key technique: pagination + parallel hydration via remote workbench.

## Why simple list fails

- `GMAIL_LIST_THREADS max_results 50` returns only first page, `nextPageToken` needed. `resultSizeEstimate: 201` means 4+ pages.
- Inline `COMPOSIO_MULTI_EXECUTE_TOOL` saves large output to `/mnt/files/mex/*.json` — must parse `structure_info` + remote file, not inline preview.
- Hydrating one thread at a time is too slow (>3min timeout). Use ThreadPoolExecutor.

## Code — Pagination

```python
all_threads = []
page_token = None
for i in range(5):
  args = {"max_results": 50, "query": "is:unread newer_than:14d", "verbose": False}
  if page_token: args["page_token"] = page_token
  result, error = run_composio_tool("GMAIL_LIST_THREADS", args)
  data = result.get('data',{})
  all_threads.extend(data.get('threads',[]))
  page_token = data.get('nextPageToken')
  if not page_token: break
```

## Code — Human filter + Parallel hydration

```python
def is_likely_human(snippet):
  s = snippet.lower()
  bad = ['receipt from openrouter','■','cron job','latitude discovered','resolved: escalation','escalating:','your bill','weekly digest','your edit is ready','loop engineering','venture summit','polite debt','document center','alert openrouter']
  return not any(b in s for b in bad)

candidates = [t for t in all_threads if is_likely_human(t.get('snippet',''))]

def fetch_thread(tid):
  res,_ = run_composio_tool("GMAIL_FETCH_MESSAGE_BY_THREAD_ID", {"thread_id": tid})
  return res.get('data',{})

with ThreadPoolExecutor(max_workers=10) as ex:
  hydrated = list(ex.map(fetch_thread, candidate_ids[:20]))
```

## Queries — 3 in parallel then dedupe

1. `is:unread newer_than:14d in:inbox -from:noreply -from:no-reply -from:openrouter -from:otter.ai -from:fireflies -from:riverside.fm -from:slack-mail -from:linkedin.com -from:newsletter.agentmail.to -category:promotions -category:updates`
2. `is:unread from:momentumamp.com OR from:tanishq OR from:apoyo OR from:karen OR from:agentcard.sh`
3. `is:unread newer_than:30d (from:gmail.com OR from:outlook.com)`

Dedupe by `thread.id`.

## What counts as human needing reply (Jul 10 2026)

- Apoyo demo invite today at Bravado — unread calendar invite 2026-07-09
- Glen Collins brandlord — "Position me in the best way..." waiting on rev share proposal
- Karen Serfaty Agentcard — co-founder check-in + Slack invite #dp-agentcard-orgo
- Prajakta Joglekar — Hermes-Claude bridge sync request IST
- Mia diagnostic forwarded for Michael Lebor — Fireflies auto-join 429 + is_calendar_in_sync conflict, cron 8fa3c8b9ff40
- Tracer lead in orgo@agentmail.to — churned user wanting rebuild + 50% off, 17 days stale

## Noise to skip

Mia Health Watchdog (MEMORY.md 92%, openrouter pools EXHAUSTED, gateway crashed), Latitude signals, OpenRouter $26.38 receipts, Xfinity, Expedia, Skool, Riverside.fm export ready, Skoolers noreply@skool.com, Best Western, PG&E, calendar Accepted/Declined without question, Google security alert, Composio unrecognized device.

## Verification

- After fetch, confirm `From:` not in `['noreply','no-reply','notifications@','newsletter']`
- Always surface TODAY meetings (check `messageTimestamp` within 24h)
- Always include AgentCard bug context when relevant (test cards Jul 2-9)
