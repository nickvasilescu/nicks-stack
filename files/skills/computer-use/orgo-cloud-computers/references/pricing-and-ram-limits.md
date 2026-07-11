# Orgo plan pricing and RAM limits (source of truth)

Use this for support answers: “how much RAM on Scale?”, “anything between $99 and $399?”, upgrade-for-memory cases.

## Source of truth (prefer code over marketing docs)

| Priority | Location |
|---|---|
| 1 | Private repo **`OrgoAI/orgo-web`** → `lib/subscription-tiers.ts` (enforcement) |
| 1 | Same repo → `public/pricing.md` (machine-readable plan matrix, served at `/pricing.md`) |
| 2 | Live pricing UI bundle / `app/(public)/pricing/` (prices + plan IDs only) |
| 3 | `docs.orgo.ai/guides/instance-types` — **often stale** on plan RAM caps |

Do **not** trust docs-only lines like “Hacker 4 / Team 8 / Scale 16” without checking `subscription-tiers.ts`. That table was true for older keys; go-forward `*_v2` differs.

## Auth for private clone (Dewey)

1. If `GITHUB_TOKEN` / `GH_TOKEN` missing or **commented** in `~/.hermes/.env`, still try **1Password**:
   - `op read 'op://Hermes/Hermes Agent Secrets/GITHUB_PAT'`
   - Expect `ghp_…` (~40) or `github_pat_…`; validate `GET /user` → 200
2. Shallow clone (never print token):

```bash
git clone --depth 1 \
  "https://x-access-token:${GITHUB_TOKEN}@github.com/OrgoAI/orgo-web.git" \
  /root/Desktop/repos/orgo-web
```

Nick may have push on `OrgoAI/orgo-web`. Related private product trees: `OrgoAI/orgo-metal`, `orgo-cli`, `orgo-shared`, etc.

## Self-serve prices (go-forward checkout)

Hardcoded in pricing client (and `public/pricing.md`):

| Plan | Stripe key (new signups) | Monthly |
|---|---|---|
| Hacker | `hacker_v2` | **$29** |
| Startup | `startup_v2` | **$99** |
| Scale | `scale_v2` | **$399** |
| Enterprise | custom | email `spencer@orgo.ai` / cal |

**No self-serve SKU between $99 and $399.** Legacy aliases still map: `developer→hacker`, `team→startup`, `max→scale`.

## Go-forward v2 limits (`*_v2` in subscription-tiers.ts)

SKU unit concept: ~8 GB RAM baseline per computer; **pool = count × 8**; **per-desktop cap is higher** so users can concentrate RAM.

| Key | Computers | RAM pool (`maxRamPerUser`) | Max RAM / computer | Default vCPU (display) | Disk / computer |
|---|---|---|---|---|---|
| `hacker_v2` | 1 | 8 GB | **8 GB** | 0.5 | 20 GB |
| `startup_v2` | 4 | 32 GB | **16 GB** | 0.5 | 20 GB |
| `scale_v2` | 16 | 128 GB | **32 GB** | 0.5 | 20 GB |

Marketing cards list computer/seat counts; they often omit RAM. Use this table + `public/pricing.md` for memory answers.

**Scale answer:** up to **32 GB per computer**, **128 GB account pool**, 16 computers.

## Legacy / grandfathered keys (still in code)

| Key | maxRamPerDesktop | Notes |
|---|---|---|
| `hacker` | 4 GB | older paid Hacker |
| `team` | 8 GB | maps to Startup marketing historically |
| `scale` | 16 GB | older Scale (not 32) |
| `startup` | 16 GB | legacy Startup (larger desktop caps) |
| `max` | 32 GB | legacy Max |
| `enterprise` | 64 GB | custom |

**Always resolve the user’s actual Stripe/profile tier key** before telling them to upgrade. Someone on `startup_v2` who only needs 12–16 GB may **not** need Scale; someone on legacy `team` is stuck at 8 GB/desktop until upgrade/remapping.

## Support reply pattern

1. Confirm need: more **per-box** RAM vs more **computers/pool**.
2. If on current Startup and need ≤16 GB/box → try resize/create with `ram=16` (pool permitting) before Scale.
3. Scale only if they need **>16 GB/box**, large fleet, Windows, custom templates, or enterprise-ish capacity.
4. Between $99 and $399: honest “no self-serve middle; custom/enterprise only.”
5. If docs contradict `subscription-tiers.ts`, **code wins**; note docs may lag.

## Related product gaps (for internal notes)

- Price cliff $99 → $399 with RAM ladder 8 → 16 → 32 (per-desktop) is a common complaint.
- `public/pricing.md` must be updated when `subscription-tiers.ts` or PricingPageClient changes (repo CLAUDE.md rule).
