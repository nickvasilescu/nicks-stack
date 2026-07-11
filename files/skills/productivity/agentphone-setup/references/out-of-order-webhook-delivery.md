# Out-of-order AgentPhone webhook delivery

## Symptom

Inbound iMessages appear in AgentPhone, but Hermes repeatedly starts over, sends interruption acknowledgements without a final answer, or applies an old follow-up to newer conversation context. A particularly dangerous case is a delayed confirmation such as "go for it" arriving after a newer offer and being misread as approval for the newer action.

## Diagnosis

1. Compare canonical AgentPhone conversation message times with bridge event arrival times.
2. In `events.log`, look for `webhook_received` followed by `job_interrupted` where the later-arriving webhook's original message time is older than the active job's message time.
3. Do not order on webhook envelope timestamp alone. It may represent delivery or retry time.
4. Prefer `data.receivedAt`, then `data.createdAt`, and only then the envelope timestamp.
5. Confirm `messageId` and recent AgentPhone history before treating a short delayed text as current intent.

## Required bridge behavior

- Maintain a persistent per-conversation watermark containing the latest accepted original message timestamp and message ID.
- After signature, event/channel, direction, allowlist, and dedupe checks, atomically compare the inbound original message time to the watermark.
- If the inbound time is older, return HTTP 200 with an ignored/stale result. Log `webhook_stale`. Do not start Hermes, cancel an active job, send an interruption acknowledgement, or execute tools.
- If the inbound time is newer, advance the watermark before starting work.
- Missing or malformed message times should fail open rather than blackhole messages, but log them for schema review.
- Use a lock around watermark read/compare/write. Add a second ordering check during job registration if handlers can race concurrently.

## Regression tests

Test all three levels:

1. Parser: `data.receivedAt` wins over a later envelope timestamp.
2. Watermark: a newer event is accepted and a later-delivered older event is rejected without changing the watermark.
3. Signed HTTP handler: send newer then older valid webhooks and assert only the newer message starts a job.

## Deployment and verification

1. Before restarting, inspect active bridge children. Terminate any stale action run that could cause a side effect.
2. Seed the watermark for the live conversation from AgentPhone's latest canonical inbound message if adding the feature to an active bridge.
3. Restart the supervised bridge. Confirm health and rerun tests.
4. Verify with a real new inbound message. Required evidence is: `webhook_received` -> `hermes_start` -> `hermes_done` (or recovered stdout) -> `reply_sent`, plus the outbound message visible in AgentPhone conversation history.
5. Confirm no orphan `hermes chat --source agentphone-bridge` process remains.

## Observed Dewey implementation

- Bridge: `~/.hermes_agentphone_bridge/agentphone_bridge.py`
- Tests: `~/.hermes_agentphone_bridge/test_event_ordering.py`
- Watermark: `~/.hermes_agentphone_bridge/conversation_watermarks.json`
- Relevant log event: `webhook_stale`
