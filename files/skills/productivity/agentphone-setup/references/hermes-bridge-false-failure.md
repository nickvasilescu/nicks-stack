# Hermes bridge false failure (canned internal error)

Use when the user receives on iMessage/SMS:

```text
I received your text, but Hermes hit an internal error while generating a reply.
```

Or the sibling timeouts / empty-output strings from the same bridge.

## What the message is

Not model prose. Dewey bridge hardcodes it when the Hermes subprocess is treated as failed:

```python
# ~/.hermes_agentphone_bridge/agentphone_bridge.py  (run_hermes_and_reply)
if returncode != 0:
    log_event("hermes_failed", returncode=returncode, stderr=stderr[-4000:], ...)
    body = "I received your text, but Hermes hit an internal error while generating a reply."
else:
    body = clean_hermes_output(stdout)
send_agentphone_reply(...)
```

Sibling canned strings in the same function:

| Condition | Body |
|---|---|
| subprocess returncode != 0 | Hermes hit an internal error while generating a reply |
| wall-clock timeout | the agent run timed out before I could finish |
| empty cleaned stdout (success path) | I could not generate a reply |

Critical: on non-zero exit the bridge **does not** fall back to stdout even if Hermes already printed a full good answer.

## Observed production pattern (2026-07-09)

Two back-to-back Nick iMessages (`can i do google pay`, `hello?`):

1. `events.log`: `hermes_start` → tools run → **`hermes_failed` returncode=-6**
2. `agent.log` for the same session_id:
   - full conversation loop with successful tool calls
   - `Turn ended: reason=text_response(finish_reason=stop) ... response_len=N`
   - `cli: CLI cleanup calling memory shutdown for session ... with N message(s)`
   - then process dies
3. Session DB (`session_search`): final assistant message is a complete, sendable reply (e.g. Google Pay fund link)
4. User only sees the canned error; the good answer is discarded

**returncode -6 = SIGABRT** (Python `subprocess` negative codes are signals). Crash lands after successful generation, during CLI/memory (Honcho) shutdown, not during model generation.

Earlier failures on this bridge were mostly returncode `1` (also often thin stderr: 1Password applied secrets + session_id only). Aggregate on Dewey events.log at diagnosis time: far more `hermes_done` than `hermes_failed` (e.g. ~148 done / 7 failed), so this is intermittent, not total bridge death.

## Diagnostic checklist (order matters)

1. **Bridge events** (do not start by re-auth or restarting blindly):

```bash
rg 'hermes_failed|hermes_done|hermes_timeout|hermes_cancelled|reply_send_failed' \
  /root/.hermes_agentphone_bridge/events.log | tail -30
```

2. **If `hermes_failed`**: note `returncode`, `job_id`, `stderr` tail, `ts`.
   - `-6` → SIGABRT during/after process exit
   - `1` → soft failure or unclean exit; still check whether a session completed
   - positive large codes → shell/hermes error; read stderr fully

3. **Correlate session_id from stderr** (often present) or timestamps with:

```bash
rg 'session=YYYYMMDD_...|Turn ended|CLI cleanup calling memory' /root/.hermes/logs/agent.log | tail -40
```

4. **Read the session** with `session_search(session_id=...)`. If final assistant content is good, the bug is bridge exit handling (or Hermes teardown), not “Hermes failed to think.”

5. **Separate true delivery failures**: `reply_send_failed` with AgentPhone/Cloudflare 5xx (e.g. HTTP 502 on `api.agentphone.ai`) means Hermes/bridge answer existed but outbound POST failed. Different class from `hermes_failed`.

6. **Do not misattribute to**:
   - allowlist (webhook would not start Hermes)
   - missing API key (1Password line in stderr usually shows secrets applied)
   - wrong model refusal
   - AgentCard tool failure (tools often completed successfully in the aborted sessions)

## Correct remediation priorities

1. **Bridge resilience (user-facing, do first):** when `returncode != 0`, still run `clean_hermes_output(stdout)`; if non-empty and not an obvious traceback, **send that body**, log `hermes_failed_but_stdout_recovered` (or keep `hermes_failed` + send recovered body). Only send the canned error when stdout is empty/useless.
2. **Root cause (secondary):** Hermes CLI abort during memory/Honcho shutdown after tool-heavy one-shots. Track in Hermes core/cleanup; do not block user-visible fix on that.
3. **Optional recovery:** if job failed but session_id known and final assistant message exists, bridge could rehydrate body from session DB (heavier; stdout recovery is enough for most cases).

## Verification after a bridge patch

- Synthetic: mock subprocess that prints a good reply then exits with code `-6` or `1`; bridge must text the good reply, not the canned error.
- Live: short allowlisted iMessage; confirm `hermes_done` or recovered path in `events.log` and that the phone receives real content.
- Regression: empty stdout + non-zero still gets a clear failure string.

## Related paths

- Bridge code: `/root/.hermes_agentphone_bridge/agentphone_bridge.py` (`run_hermes_and_reply`, `clean_hermes_output`)
- Events: `/root/.hermes_agentphone_bridge/events.log`
- Hermes agent log: `~/.hermes/logs/agent.log`
- Poke UX (acks, typing, chunking): `references/poke-style-imessage-bridge.md`
- Webhook architecture: `references/inbound-webhook-bridge.md`
