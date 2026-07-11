# Provider Route Accounting: GPT-5.6 Sol on Hermes/Codex

Last verified: 2026-07-10

This reference records a concrete example of why model, route, input budget, output reserve, and compaction threshold must be separated. Treat all model numbers as volatile and re-check the linked sources before applying them later.

## Observed route

```yaml
model:
  default: gpt-5.6-sol
  provider: openai-codex
  api_mode: codex_responses

compression:
  enabled: true
  threshold: 0.5
  target_ratio: 0.2
```

No explicit `model.context_length` override was configured.

## Verified accounting

At verification time, OpenAI's Codex-owned model catalog exposed `gpt-5.6-sol` with a raw input `context_window` of 372,000 tokens and the same route maximum. The direct OpenAI API model page advertised a 1,050,000-token context window and 128,000 maximum output tokens.

For the Codex product route, the useful interpretation was:

```text
372,000 input + 128,000 maximum output = 500,000 total
```

Therefore, the 372K denominator displayed by Hermes was not evidence of a broken local cap. It was the input side exposed by the subscription-backed Codex route. The larger direct-API capacity did not imply that the Codex route would accept a local 1M override.

## Hermes compaction consequence

Hermes's active global threshold was 0.50. With no explicit output reservation subtracted by Hermes:

```text
372,000 × 0.50 = 186,000 tokens
```

So Hermes could compact raw history near 186K even though the route accepted 372K input. This was a separate, safely adjustable client behavior.

Candidate trigger values:

```text
0.75 -> 279,000
0.80 -> 297,600
0.85 -> 316,200
0.90 -> 334,800
0.95 -> 353,400
```

A threshold of 0.85 was the balanced recommendation because it preserved roughly 316K raw tokens while leaving about 56K for summary generation, fixed prompt/tool overhead, and continued work. This was a recommendation, not a change performed in the session.

## Hermes implementation detail

The inspected Hermes version automatically raised the compression threshold to 0.85 for OpenAI Codex GPT-5.4/GPT-5.5 families, but its matcher did not yet include GPT-5.6. Consequently, GPT-5.6 Sol inherited the user's global 0.50 threshold. Future versions may change this behavior, so inspect the current matcher and effective initialization logs before recommending a manual adjustment.

Relevant local source concepts:

- `agent/model_metadata.py`: provider/model context resolution and config override precedence.
- `agent/context_compressor.py`: effective input budget and threshold arithmetic.
- `agent/agent_init.py`: active compression config and per-model threshold overrides.
- `agent/auxiliary_client.py`: route-specific model threshold matching.

## What not to do

Do not set this on the Codex route merely to make the UI show a larger number:

```yaml
model:
  context_length: 1000000
```

Unless the live Codex backend explicitly exposes and accepts that window, this changes Hermes's bookkeeping, delays compaction, and risks a context-overflow rejection. A genuine larger window requires a route that supports it, such as the separately billed direct OpenAI API where available.

## Authoritative sources

Re-check these before reuse:

- Direct API model page: https://developers.openai.com/api/docs/models/gpt-5.6-sol
- OpenAI Codex model catalog: https://raw.githubusercontent.com/openai/codex/main/codex-rs/models-manager/models.json
- Hermes documentation: https://hermes-agent.nousresearch.com/docs

OpenAI Codex issue discussions can clarify input/output splits and effective safety margins, but issue reports are secondary evidence. Prefer provider documentation, current catalog metadata, and current client source.

## Reverification checklist

1. Confirm the active model slug and provider route.
2. Fetch the current Codex model-catalog entry for that slug.
3. Read the direct API model page separately.
4. Inspect the active Hermes `compression.threshold`.
5. Confirm whether current Hermes already has a per-model autoraise for the model family.
6. Compute the exact compaction trigger from the current route window.
7. After any change, start a fresh session and verify runtime context and compaction behavior.
