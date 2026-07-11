---
name: agent-context-management
description: "Use when diagnosing, comparing, or tuning an AI agent's context window, token budget, output reserve, automatic compaction threshold, or provider-specific context cap. Separates model capability from route limits and client bookkeeping, verifies live metadata before editing config, and prevents unsafe fake context-length overrides."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [context-window, token-budget, compaction, providers, agents]
    related_skills: [hermes-agent, serving-llms-vllm, llama-cpp]
---

# Agent Context Management

## Overview

Context-window questions are usually accounting questions disguised as a single number. A UI may display total context, input capacity, an effective window after safety margin, current remaining tokens, or the threshold at which the client compacts history. Treat those as separate quantities.

The central rule is route-first diagnosis: the same model slug can expose different windows through a direct API, a subscription-backed coding product, a cloud intermediary, or a local server. A client setting cannot expand a server-enforced limit.

## When to Use

Use this skill when the user asks:

- whether a context window can be increased;
- why a displayed token count differs from advertised model capacity;
- whether a window such as 128K, 372K, or 1M is "low";
- when or why Hermes, Codex, or another agent compacts conversation history;
- whether to change `context_length`, `max_tokens`, or a compression threshold;
- why a long session fails despite a larger locally configured window;
- how to compare context capacity across providers or routes;
- fleet agent MEMORY.md at 80–92% of char cap / writes failing / watchdog memory alert (distinct from token context).

Do not use it merely to summarize an ordinary conversation. Use it for context accounting, configuration, and failure diagnosis.

## Context Accounting Model

Always identify these quantities independently:

| Quantity | Meaning | Controlled by |
|---|---|---|
| Model maximum | Largest combined token budget the model family can support | Model/provider |
| Route maximum | Maximum exposed by the selected API/product route | Provider/product tier |
| Raw input budget | Tokens available for system prompt, tools, history, and current input | Route minus output reservation |
| Effective input window | Raw input budget after provider/client safety margin | Provider/client |
| Compaction threshold | Point where history is summarized or pruned | Client configuration |
| Remaining context | Effective budget minus tokens already present | Runtime state |
| Displayed denominator | Whichever of the above the UI chose to label as context | UI implementation |

A common decomposition is:

```text
total context = maximum input + reserved maximum output

effective input = raw input × safety percentage

compaction trigger = (context length - explicit output reservation) × client threshold
```

Do not assume every provider uses the same convention. Verify the model page and active route metadata.

## Workflow

### 1. Identify the active route

Collect the exact model slug, provider, transport/API mode, product tier, and relevant client. For Hermes, inspect only the non-secret fields needed to establish:

```yaml
model:
  default: <slug>
  provider: <provider>
  api_mode: <transport>
```

Completion criterion: the answer names both the model and route. A model slug alone is insufficient.

### 2. Classify the displayed number

Determine whether the value is:

- a fixed denominator in `/usage` or `/status`;
- a shrinking remaining-token count;
- an input-only budget;
- a total input-plus-output capacity;
- an effective window after a percentage buffer;
- or an automatic compaction threshold.

If the UI is ambiguous, inspect source or runtime metadata rather than guessing from the number.

Completion criterion: state exactly what the displayed value measures, or label the interpretation as unresolved.

### 3. Verify authoritative limits

Use sources in this order:

1. provider model documentation for the direct API;
2. provider-owned live model catalog or model-list endpoint for the active product route;
3. client source code showing how it transforms metadata;
4. current local configuration;
5. issue trackers only for implementation details, maintainer clarifications, or rollout anomalies.

Record retrieval date for volatile model metadata. Product windows can change without the model slug changing.

Completion criterion: distinguish the provider's direct-model capacity from the active route's actual cap.

### 4. Inspect client compaction separately

Read the client's active compression configuration and source semantics. For Hermes, distinguish:

```yaml
compression:
  threshold: 0.85
```

from:

```yaml
model:
  context_length: 1000000
```

The first changes when Hermes summarizes history. The second changes Hermes's bookkeeping and is safe only when it matches a window the active backend really accepts.

Calculate concrete trigger values for the current window. Present tokens, not just percentages.

Completion criterion: report both the hard route limit and approximate compaction trigger.

### 5. Choose the correct intervention

Use the least misleading intervention:

- **Need more raw history before compaction:** raise the client compression threshold while leaving safety headroom.
- **Need a genuinely larger hard window:** switch to a route that officially exposes it, often a separately billed direct API.
- **Metadata is stale or wrong:** refresh the provider catalog/client, then verify with a new session.
- **Displayed value is only remaining capacity:** do not edit model limits; compact, fork, or start a fresh session.
- **Provider reserves large output capacity:** reduce output reservation only if the route supports that tradeoff and the user accepts shorter maximum outputs.

Completion criterion: proposed settings do not exceed verified backend capability.

### 6. Verify after changing configuration

Start a fresh session if initialization caches model metadata or compressor state. Verify:

- reported context denominator;
- effective compaction trigger;
- provider and model route;
- behavior near the old threshold;
- absence of context-overflow or premature-compaction errors.

Do not call a config edit successful merely because the file contains the requested number.

## Safe Threshold Selection

Compression is lossy, but delaying it too far can make the summary turn itself exceed the remaining budget. Use these defaults as starting points, not universal laws:

- `0.75`: conservative for uncertain providers or large tool schemas;
- `0.80` to `0.85`: balanced for well-understood large-context routes;
- `0.90`: aggressive, requires reliable token accounting and summary behavior;
- `0.95`: usually provider-style safety-buffer territory, not a default recommendation for a separate client-side compressor.

Leave enough room for the protected tail, summary prompt, tool definitions, current user turn, model reasoning, and response. Recalculate if `max_tokens` is explicitly reserved from the same window.

## Reporting Format

Answer context questions in this order:

1. Direct conclusion: whether the hard limit can actually be raised.
2. What the displayed number means.
3. Current route cap versus direct model/API cap.
4. Current compaction threshold and token trigger.
5. Safe adjustment, if any.
6. Risks and verification method.
7. Confidence label.

When the user asks whether a number is "low," answer against two baselines:

- absolute comparison with common agent windows;
- relative comparison with the same model through other routes.

This avoids both empty reassurance and misleading alarm.

## Common Pitfalls

1. **Treating a route cap as a model cap.** The direct API and subscription product may expose different windows for the same slug.

2. **Calling an input budget the total context window.** Check for a separately reserved maximum output allowance.

3. **Increasing `context_length` locally without backend support.** This only delays compaction and can turn a manageable session into a provider rejection.

4. **Confusing compaction with context expansion.** Raising a threshold preserves raw history longer; it does not enlarge the model's hard limit.

5. **Ignoring system and tool overhead.** Tool-heavy agents may begin each turn with substantial fixed input before conversation history.

6. **Using advertised marketing numbers without route metadata.** Verify the active product catalog, especially during staged rollouts.

7. **Changing a global threshold for one model without checking other routes.** A safe value for a 372K model may be unsafe for a smaller fallback model.

8. **Claiming success from the display alone.** A local override can alter the UI while the backend still enforces a smaller limit.

9. **Starting too close to 100%.** Summary generation and output need headroom. Prefer an evidence-backed incremental increase.

## Hermes MEMORY.md store consolidation (fleet agents)

Distinct from **token** context: Hermes also has a durable **MEMORY.md char cap** (often ~16k on managed boxes; alert fires near 80–92%). When writes fail or watchdog emails fire, follow `references/hermes-memory-md-consolidation.md`:

1. Probe remote MEMORY.md char count (Orgo bash/REST).
2. Backup under `~/.hermes/memories/backups/` before rewrite.
3. Archive full dump to the agent Obsidian/vault path.
4. Rewrite hot MEMORY to well under 80% (target ≤50%): keep cardinals, merge dupes, move long-form out, **strip plaintext secrets**.
5. Report before/after % of cap to the operator.

Do not raise model `context_length` to fix MEMORY.md write failures — different layer.

## Linked Reference

Read `references/provider-route-accounting.md` for a dated GPT/Codex/Hermes example, authoritative-source locations, and the specific distinction between a 372K input route and a larger direct API window.

Also: `references/hermes-memory-md-consolidation.md` for the MEMORY.md char-cap procedure.

## Verification Checklist

- [ ] Exact model slug identified
- [ ] Active provider and transport identified
- [ ] Displayed number classified
- [ ] Direct API capacity verified from provider documentation
- [ ] Active route capacity verified from route metadata
- [ ] Input/output split checked
- [ ] Safety percentage checked
- [ ] Client compaction threshold read from active config
- [ ] Trigger converted from percentage to tokens
- [ ] Proposed override remains within backend capability
- [ ] Fresh-session/runtime verification specified
- [ ] Uncertainty and confidence stated
