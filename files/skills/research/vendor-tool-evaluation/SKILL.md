---
name: vendor-tool-evaluation
description: "Evaluate SaaS/devtools/agent-infrastructure products by researching official sources before giving opinions or recommendations."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, vendor-evaluation, tools, saas, agent-infrastructure, recommendations]
    category: research
    created_by: agent
---

# Vendor Tool Evaluation

Use this skill when the user asks for opinions, recommendations, comparisons, or a verdict on named tools, SaaS products, APIs, agent infrastructure, payment systems, communications platforms, or developer tools.

## Core rule

Do not give a generic architecture take before researching the named tools. The user's correction in a prior session was explicit: if they ask about specific tools, first verify what those tools actually are.

## Workflow

1. Identify the products and the user's intended use case.
   - Preserve the user's product names verbatim.
   - Note any assumptions separately from verified facts.

2. Research official sources first.
   - Check the product homepage.
   - Check docs, API reference, pricing, GitHub/org pages, and any `llms.txt`, `.md`, `agent.txt`, or MCP docs the site exposes.
   - Prefer official docs over search snippets or third-party summaries.

3. Extract decision-relevant facts.
   - What the tool actually is.
   - Primary use cases.
   - Integration surface: API, CLI, MCP, webhooks, SDK, OAuth, hosted service.
   - Pricing/limits when available.
   - Security and permission model.
   - Overlap with tools already available in Hermes.
   - Risks, lock-in, compliance, or operational concerns.

### Subscription, API, and BYOK compatibility check

When a user wants to carry a paid AI subscription into an IDE or third-party app, do not assume that a shared login, API-key page, or model name means the subscription funds API usage. Verify all three layers independently:

1. **Consumer entitlement:** What the subscription actually covers, such as web/app usage, CLI access, higher limits, or premium models.
2. **Developer API billing:** Whether API credits are included, separately prepaid, invoiced, or promotional. Prefer an explicit account or billing FAQ over a pricing-page omission.
3. **Destination compatibility:** Whether the receiving product supports that provider as BYOK, which key types it accepts, and whether all features work with BYOK.

Use this evidence order:

- Provider account/billing FAQ with explicit wording about shared accounts versus separate billing.
- Provider API quickstart and billing documentation showing credit purchase and key creation.
- Destination product's current supported-provider list.
- Destination staff statement for roadmap or unsupported-provider confirmation.
- Third-party summaries only as corroboration.

Practical rule: if API billing is separate, the consumer subscription cannot be treated as transferable API credit. If the destination does not list the provider, do not recommend buying API credits until compatibility is confirmed. Also distinguish the destination's built-in model integration from BYOK: built-in access normally consumes the destination's own plan or usage pool, not the upstream consumer subscription.

4. Give a verdict per tool.
   - Start each section with: "What it is", "Useful for", "Cautions", "Alternatives", and "Verdict".
   - Clearly distinguish verified facts from inference/opinion.
   - If the research changes an earlier assumption, say so directly.
   - Use explicit confidence labels for judgments: high, moderate, low, or unknown.
   - For this user, do not praise the question or validate premises before the verdict; lead with the strongest counterargument or correction when the user's implied framing is wrong.

5. Compare by role, not only by brand.
   - Map tools to jobs in the stack: compute, inbox, phone, auth/tool bridge, payments, identity, evals, monitoring, etc.
   - Identify overlap and complementary use.

6. Recommend a next step.
   - End with the order to adopt, what to configure first, and guardrails/permission boundaries.

## Useful source patterns

Many agent-oriented vendors expose model-readable docs:

- `/llms.txt`
- page `.md` endpoints
- `/agent.txt`
- MCP docs or hosted MCP endpoints
- OpenAPI/API-reference pages
- GitHub README/package pages

When available, use these before scraping JavaScript-heavy marketing pages.

## Pitfalls

- Do not assume a product's purpose from its name. Example: `AgentScore` may sound like evals but is commerce/identity/payment infrastructure; verify before opining.
- Do not treat similarly named payment products as redundant without checking rails and use cases. Visa checkout, x402/MPP, wallet identity, and KYC/compliance gates solve different problems.
- Do not present unverified recommendations as if researched.
- Do not capture transient access failures as durable facts about the product; retry with official docs, `.md`, or `llms.txt` instead.
- Do not over-index on marketing claims; separate what the docs prove from what the product promises.

## References

- `references/agent-infrastructure-stack-2026-07.md` — researched notes on Agentcard, AgentMail, AgentPhone, Orgo, Composio, and AgentScore for a Hermes-on-Orgo agent stack.
- `references/ai-subscription-api-byok-case.md` — concise evidence pattern and worked xAI SuperGrok-to-Cursor case for separating consumer subscriptions, API billing, and destination BYOK support.
