# Orgo fleet ↔ Latitude coverage audit

Use when Nick asks whether customer VMs are "in Latitude," whether to add a fleet, or how multi-tenant telemetry should be structured for managed Hermes on Orgo.

## Multi-tenant model (locked)

| Layer | Rule |
|---|---|
| **Latitude project** | One project per customer account (or strict tenant). Isolation unit. |
| **Internal** | `dewey` = Nick/Dewey only. Never dump customer fleets here. |
| **Momentum example** | slug `momentumclaw` (project id `urlmfpzfitsq8a7hqea2w96x`) |
| **service.name** | `hermes-<first-8-chars-of-orgo-computer-uuid>` |
| **Resource attributes** | `latitude.project=<slug>,computer.id=<full-uuid>,account=<customer-slug>` |
| **Optional** | `deployment.environment=prod\|stage\|lab`, `hermes.role=executive\|agency\|eng\|rd` |
| **Capture** | Metadata / no-content by default for customer boxes. No AMS payloads, tokens, PII in attributes. |
| **Injection preference** | Orgo/platform **OTEL env** on the runtime (Mia pattern), not hand-copying Dewey's full `LATITUDE_*` pack onto 50 VMs. |

Example (Mia-class, process env observed):

```text
OTEL_SERVICE_NAME=hermes-978b687d
OTEL_RESOURCE_ATTRIBUTES=latitude.project=momentumclaw,computer.id=978b687d-2b54-458e-804a-41f5f6951333
```

## Do / don't

**Do**

- List Latitude projects first (`latitude projects list` or MCP `listProjects`).
- Audit coverage as a **matrix**: Orgo computers × Latitude `serviceNames` × optional process OTEL probe.
- Treat **Latitude service presence** as ground truth for "is this box emitting?"
- Prioritize flagship + eng + active agency; leave idle/unused off until needed.
- Create a new project when a **strategic** customer needs review (Budgetdog, Saddles, etc.).
- Vault a short `projects/<account>/latitude.md` with slug + convention + last audit summary when material.

**Don't**

- Put all Orgo VMs into one Latitude project.
- Assume "project exists" means fleet coverage is complete.
- Expect Hermes Latitude services from **OpenClaw-only** boxes (no Hermes process).
- Claim OTEL is absent globally because the gateway PID lacks `OTEL_*` — child/SDK paths can still emit; re-check Latitude services after a real interaction.
- Route customer traffic into `dewey`.

## Audit procedure

1. **Inventory Orgo**  
   `orgo_list_workspaces` / list computers for the customer workspace. Record `id`, `name`, status.

2. **List Latitude projects**  
   Confirm customer slug exists (or recommend creating it). Keep internal vs customer separate.

3. **Sample traces for service set**  
   Paginate `traces list --project-slug <slug> --limit 200` with cursor until enough rows (or cap ~5–10k). Aggregate `serviceNames` counts and top `userId` values.

4. **Join**  
   Map `hermes-XXXXXXXX` → computer where `computer.id.startswith(XXXXXXXX)`.  
   Coverage = computers with ≥1 hit / total workspace computers (state scan window).

5. **Probe gaps (P0 only, not every idle box)**  
   On flagship/eng/active gateways, check process environ for `OTEL_*` / `LATITUDE_*` (redact secrets). Also note stack: Hermes vs OpenClaw-only vs idle.

```bash
export PATH=/usr/local/bin:$HOME/.local/bin:$PATH
which hermes openclaw 2>/dev/null
hermes --version 2>&1 | head -1
found=0
for pid in $(pgrep -f 'hermes|openclaw' 2>/dev/null | head -20); do
  e=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -E '^(OTEL_|LATITUDE_)' \
    | sed -E 's/(KEY|TOKEN|SECRET|PASSWORD)=.*/\1=REDACTED/')
  if [ -n "$e" ]; then echo "pid $pid"; echo "$e"; found=1; fi
done
[ $found -eq 0 ] && echo OTEL_PROCESS=absent
pgrep -af 'hermes|openclaw' 2>/dev/null | head -8
```

6. **Report**  
   Summary table: computers, emitters, %, dominant service/user. P0 gaps. Explicit recommendation: instrument eng first, then active agencies; do not "add everything."

7. **Optional vault**  
   Write/update `projects/<slug>/latitude.md` (convention + matrix summary). Link from overview/tasks/registry observability section. validate + commit.

## Sampling policy

| Class | Policy |
|---|---|
| Flagship executive agent | Always on; richer metadata OK |
| Eng / stage | Always on |
| Active agency | On; prefer tool-error fidelity over full prompt capture |
| Idle / unused | Off until activated |

## Rollout order

1. Freeze convention (table above).
2. Confirm platform OTEL injection used on a known-good box (Mia).
3. Enable eng Hermes missing OTEL.
4. Skip pure OpenClaw until Hermes+OTEL or separate OpenClaw telemetry decision.
5. Active agency non-emitters.
6. Monitors (cost/latency/tool errors) only after coverage is real — validate metric units (`cost` dollars, `duration` seconds).

## Success criteria

- Active Hermes gateways appear as distinct services after one real interaction.
- Service count roughly tracks **active** fleet size (not flagship-only).
- Zero customer traces in `dewey`.
- No secrets in resource attributes or captured content.
- Audit cites Orgo inventory + Latitude service counts (not opinion).

## Session snapshot

Momentum AMP (2026-07-08): workspace 53 computers; ~32 services in 10k-trace scan (~60%); Mia `hermes-978b687d` dominated volume; Sanket-Prod / Kayden Hermes up without process OTEL; Alex/Peter OpenClaw-only. Vault: `Dewey-Agent-Vault/projects/momentum-amp/latitude.md`.
