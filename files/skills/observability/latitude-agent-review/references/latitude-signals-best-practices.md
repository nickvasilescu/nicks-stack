# Latitude signals and monitors best practices

Session-grounded notes from official Latitude docs and OpenTelemetry GenAI conventions for improving Dewey/Hermes observability.

## Source URLs

- https://docs.latitude.so/getting-started/how-to-use-latitude
- https://docs.latitude.so/getting-started/concepts
- https://docs.latitude.so/signals/overview
- https://docs.latitude.so/signals/create.md
- https://docs.latitude.so/signals/management.md
- https://docs.latitude.so/monitors/overview.md
- https://docs.latitude.so/search/overview
- https://docs.latitude.so/search/guides/search-and-review-effectively.md
- https://docs.latitude.so/annotations/flaggers
- https://docs.latitude.so/annotations/guides/annotate-effectively.md
- https://docs.latitude.so/evaluations/overview
- https://docs.latitude.so/evaluations/alignment
- https://docs.latitude.so/observability/features/metadata.md
- https://docs.latitude.so/observability/tool-calls.md
- https://docs.latitude.so/observability/tools.md
- https://docs.latitude.so/observability/features/token-cost-tracking.md
- https://docs.latitude.so/observability/features/user-tracking.md
- https://docs.latitude.so/observability/features/sampling.md
- https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md

## Product model

Latitude works best as a continuous improvement loop:

1. Send real traces from production traffic.
2. Use search to find behaviors and cohorts.
3. Annotate representative traces with specific feedback.
4. Let failed annotations, flaggers, evaluations, and custom checks produce scores.
5. Let failed scores cluster into signals.
6. Generate evaluations for important signals.
7. Monitor regressions, fix the agent, and repeat.

Do not define every possible failure upfront. Use manual signals only for known behaviors you already care about. Use search and annotation for exploratory discovery.

## Signals vs saved searches vs monitors

| Need | Latitude primitive | Rationale |
| --- | --- | --- |
| Recurring behavior failure | Signal | Signals are recurring behavior patterns, usually failures. |
| Known behavior to track from day one | Manual signal | Create manually when the behavior is known and important. |
| Metric threshold such as high cost or high latency | Saved search plus monitor | Cost and latency are symptoms unless tied to a behavior. |
| Alert on signal lifecycle | System monitor | Latitude provides signal discovered, regressed, and escalating monitors. |
| Alert on custom cohort | Saved-search monitor | User monitors currently watch saved searches. |
| Human-grounded detector quality | Evaluation alignment | Compare automated evaluations against human annotations. |

## Recommended Dewey taxonomy

Prefer signals for behavioral failures:

- Premature completion without verification.
- Tool loop without progress.
- Avoidable user handoff or agent laziness.
- Requirements dropped during skill authoring.
- Real tool failure that blocks the task.
- User frustration caused by agent behavior.

Prefer saved searches and monitors for operational symptoms:

- High-cost Hermes traces.
- Slow Hermes interactions.
- High-token interactions.
- Poor capture or metadata-only traces.
- Retry or fallback artifacts.

Only promote an operational symptom to a signal when review shows a repeated behavioral cause, such as repeatedly reloading large context or looping between the same tools.

## Annotation practices

Latitude's docs emphasize that consistency and specificity matter more than volume.

- Review through saved searches instead of random spot checks.
- Keep saved-search cohorts small enough to finish.
- Diversity beats volume: 20 varied traces are often better than 200 near-duplicates.
- On thumbs-down annotations, write specific feedback: what went wrong, what triggered it, and what should have happened.
- Use conversation-level annotations for whole-run failures such as tool loops or requirement drift.
- Use message-level or text-range annotations for isolated hallucinations, refusal phrasing, or specific bad output.
- Tune noisy flagger sampling instead of ignoring flaggers entirely.

## Capture and metadata

Latitude's trace, tool, and search features need structured metadata and tool payload visibility.

Recommended root-span metadata:

- `user.id`, `user.email`, `user.name` when known.
- `session.id` for conversation grouping.
- `hermes.profile` for Hermes profile separation.
- `hermes.platform` for Telegram, iMessage, CLI, cron, etc.
- `hermes.channel` or equivalent channel context.
- `hermes.task.kind` such as setup, coding, email, research, skill-authoring.
- `hermes.approval_mode` for yolo vs confirmation-heavy sessions.
- `hermes.skill.loaded` or a compact list of loaded skills.
- `hermes.capture.level` such as metadata, summary, full-safe.
- `hermes.capture.redacted` as a boolean.

OpenTelemetry GenAI conventions support standard attributes such as `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.model`, token usage fields, `gen_ai.tool.name`, and `gen_ai.tool.call.id`. Prompt, output, system instruction, and tool definition content is opt-in, so default to safe metadata and redacted summaries rather than raw content.

## Default thresholds to propose, not hard-code

These are useful starting points for Dewey but should be tuned after observing traffic:

- High-cost warn: trace cost over $0.10.
- High-cost alert: trace cost over $0.25.
- Slow warn: duration over 60 seconds.
- Slow alert: duration over 120 seconds.
- Token warn: total tokens over 500k.
- Token alert: total tokens over 1M.
- LLM judge signal sampling: 10 to 25 percent unless low volume.
- Cheap structural/rule signals: 100 percent when cost is negligible.

## Implementation order

1. Improve metadata and capture summaries first.
2. Create saved searches for cost, latency, token bloat, tool failures, poor capture, tool loops, premature completion, and user frustration.
3. Annotate 10 to 25 varied traces per cohort with specific feedback.
4. Enable and tune relevant flaggers: tool errors, tool loops, frustration, laziness, forgetting, empty responses, refusal if relevant.
5. Create manual signals only for known behavior failures.
6. Generate or realign evaluations for important signals.
7. Add monitors for saved searches and rely on system monitors for signal lifecycle.

## Pitfalls

- Do not make every metric threshold a signal. Use saved-search monitors for thresholds.
- Do not call retry/fallback spans user-visible failures unless trace review proves user impact.
- Do not rely on trace-level error rate when abandoned fallback spans inflate errors.
- Do not over-annotate duplicates. Broaden the cohort or move on.
- Do not claim Latitude can explain a trace when content capture is disabled and tool inputs/outputs are empty.
- Do not capture raw sensitive tool payloads by default. Use summaries and allowlists.
