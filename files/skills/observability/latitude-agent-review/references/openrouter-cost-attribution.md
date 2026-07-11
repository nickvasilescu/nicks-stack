# OpenRouter cost attribution from Latitude

Use this reference when a user asks why OpenRouter spend is high, especially when Latitude totals disagree with the OpenRouter dashboard.

## Core rule

Treat three numbers as different evidence:

1. **OpenRouter key usage** from `GET https://openrouter.ai/api/v1/key`: account/key-level billed usage. Never print the key or a key-derived label that could contain key material.
2. **Latitude trace cost**: often estimated. Check span/trace `costIsEstimated` before treating it as billing truth.
3. **Repriced trace estimate**: recompute token categories using the current OpenRouter model catalog. Label this an estimate, not a ledger value.

Never claim the account total belongs to one agent when the key is shared.

## Investigation workflow

1. Establish an explicit UTC window with `date -u`.
2. Query Latitude by **model** and inspect individual `chat` spans. Record:
   - `tokensInput`
   - `tokensOutput`
   - `tokensReasoning`
   - `tokensCacheRead`
   - `tokensCacheCreate`
   - `costTotalMicrocents`
   - `costIsEstimated`
3. Convert Latitude raw cost only after validating the unit against analytics `sum(cost)`. In the observed CLI schema, dollars matched `costTotalMicrocents / 1e8`, despite ambiguous naming/documentation. Do not assume this constant across API versions without checking.
4. Fetch the current public model catalog from `https://openrouter.ai/api/v1/models`. Pricing fields are per token. Convert each to dollars per million tokens for reporting.
5. Reprice each trace:

   ```text
   estimated_cost =
       tokensInput       * prompt_rate
     + tokensCacheRead   * cache_read_rate
     + tokensCacheCreate * cache_write_rate
     + (tokensOutput + tokensReasoning) * completion_rate
   ```

   Confirm whether the provider counts reasoning separately before publishing exact-looking figures.
6. Query `GET /api/v1/key` and retain only safe usage/limit fields such as daily, weekly, monthly, total, limit, and remaining limit.
7. Compute:
   - traced-agent estimate;
   - key-level billed usage;
   - unattributed remainder;
   - traced share and remainder share.
8. Search deployment history and live fleet configuration for key reuse. Compare one-way hashes remotely and print only `MATCH`, `DIFFERENT`, or `NO_KEY`. Do not emit full hashes or credentials.
9. If a regular inference key cannot access `/api/v1/analytics/query`, report the 403 boundary plainly. Exact per-model account attribution requires an OpenRouter management key.
10. Verify the current agent provider with a fresh trace after any model switch. Historic OpenRouter spend does not prove the current turn still uses OpenRouter.

## Provider-breakdown trap

Trace-level provider breakdowns can double-attribute full trace cost when a trace contains the real provider plus an abandoned fallback/instrumentation span. A common example is an `anthropic` span with `llm_request abandoned before post_llm_call` alongside a successful OpenRouter or Codex span.

Therefore:

- do not sum provider rows blindly;
- use successful `chat` spans for actual request routing;
- use model breakdowns for aggregate cost sanity checks;
- classify abandoned spans as telemetry artifacts until proven billable.

## Runaway context diagnosis

For expensive tool-driven sessions, report both model calls and tool calls. Aggregate token totals can be dominated by repeated context reads, not final-answer output. Compute:

```text
cache_share = total_cache_read / total_token_units
```

A high cache share is still expensive because cache reads are discounted, not free. Long sessions with dozens of model/tool iterations repeatedly reread a growing context. Break the result down by session/task so the user can see what actually consumed money.

## Shared-key conclusion language

Use precise language:

- **High confidence:** direct key usage, trace counts, successful provider/model spans, current provider from a fresh trace.
- **Moderate confidence:** repriced agent allocation and unattributed remainder, because pricing can change and uninstrumented calls may exist.
- Never say the remainder definitely came from one fleet unless OpenRouter management analytics or distinct per-service keys prove it.

## Remediation pattern

Recommend, but do not rotate without authorization:

- one OpenRouter key per agent/fleet/customer;
- a hard budget/limit per key;
- management-key analytics for exact attribution;
- explicit auxiliary/fallback routing instead of `auto` where surprise OpenRouter usage is unacceptable;
- current pricing metadata in Latitude;
- a fresh post-change trace proving the desired provider.

Key rotation or credential removal can interrupt active agents, so require explicit scope before changing it.
