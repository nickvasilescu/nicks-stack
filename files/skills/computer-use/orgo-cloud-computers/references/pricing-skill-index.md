# Pricing skill index (pointers)

Canonical detail: **`references/pricing-and-ram-limits.md`**.

When to load:

- “How much RAM on Scale?”
- “Anything between $99 and $399?”
- Customer told they must upgrade for memory
- Nick: answer from orgo-web

Quick go-forward (`*_v2`):

| Plan | Price | Pool | Max RAM / computer |
|---|---|---|---|
| Hacker | $29 | 8 GB | 8 GB |
| Startup | $99 | 32 GB | 16 GB |
| Scale | $399 | 128 GB | 32 GB |

No mid-tier. Docs instance-types 4/8/16 are often **stale**. Code: `OrgoAI/orgo-web` `lib/subscription-tiers.ts` + `public/pricing.md`.

Auth for private clone: 1Password PAT — `secret-manager-setup` → `references/github-pat-from-1password.md`.
