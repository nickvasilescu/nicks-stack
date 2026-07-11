# Packaging and sharing

## Surfaces

| Surface | Role |
|---------|------|
| Orgo template `default/hermes-orgo-desktop-local@x.y.z` | New VMs with stack baked in |
| GitHub `nickvasilescu/orgo-hermes-desktop-local` | Template + monorepo package |
| GitHub `nickvasilescu/orgo-desktop-local` | Plugin + skills + CLI for existing Hermes |
| Hermes plugin `orgo-desktop-local` | Model tools `orgo_desktop_*` |
| Skills `orgo-desktop-local` + `orgo-cloud-computers` | Prefer-order / recovery / fleet routing |
| Public MCP `nickvasilescu/orgo-mcp` | Cloud fleet only (not same-box GUI) |

## Prefer order

Orgo local Desktop API → Hermes `browser_*` (DOM) → cloud Orgo MCP (other VMs) → CUA last.

## Install existing Hermes

```bash
curl -fsSL https://raw.githubusercontent.com/nickvasilescu/orgo-desktop-local/main/install/bootstrap.sh | bash
```

## Validation

`install/validate.sh` and `SUCCESS_CRITERIA.md`.
