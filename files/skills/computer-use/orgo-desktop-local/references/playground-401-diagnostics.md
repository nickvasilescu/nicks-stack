# Playground / agent 401 when controlling an Orgo VM

## Symptom

Orgo sandboxed playground (or any computer-use agent) returns **401** while trying to
screenshot/click/bash a computer spun from a Hermes template.

## First principle

**Do not assume the template broke desktop auth.** Measure which HTTP path fails.
Also separate **playground 401** from **blank terminal UI** (different subsystems).

## Paths and expected auth (2026-07 evidence)

### Path A — Computer actions (playground should use these)

```text
GET  /api/computers/{computer_id}/screenshot
POST /api/computers/{computer_id}/bash
POST /api/computers/{computer_id}/click
Authorization: Bearer <account ORGO_API_KEY or session with computer scope>
```

Observed **200** on agentmail, hermes-orgo-desktop-local (`@0.1.x`–`@0.3.x`), and base VMs.

### Path B — Official computer-use loop

```text
POST /api/v1/chat/completions
  model: claude-sonnet-4.6 | claude-opus-4.6
  computer_id: <uuid>
  messages: […]
Authorization: Bearer <account key>
```

Observed **200** on `hermes-orgo-desktop-local` (agent completed click + "acted").

Wrong model names → **400** `invalid_model`, not 401.

### Path C — Desktop proxy (edge → VM :8080)

```text
GET/POST /api/desktops/{instance_id}/proxy/{health|screenshot|bash}
```

Auth accepted (varies by desktop-api build):

- `Authorization: Bearer <vnc_password>`
- Sometimes account API key
- Local loopback: `VNC_PASSWORD` / `ORGO_DESKTOP_API_TOKEN`

Pitfall: create/`instance_details` may show

```text
desktop_api_token: "template-build"   # placeholder, not a real secret
```

On some images (desktop-api `a186397-dirty`, including **agentmail** VMs), proxy
screenshot/bash return **401 invalid token** even with VNC password, while Path A still **200**.

On `v0.0.5` hdl VMs, proxy usually **200** with VNC password or account key.
Local loopback: `Bearer template-build` → 401; `Bearer $VNC_PASSWORD` → 200.

**401 on Path C is not unique to hermes-orgo-desktop-local.**

### Path D — Terminal WebSocket

```text
wss://www.orgo.ai/desktops/{instance_id}/ws/terminal?token={vnc_password}
```

Separate from playground action 401s. Token rotates every restart.
If WS works and Path A is 200 but UI panel is black → not a 401 issue; see `template-terminal-blank-ui.md`.

## Diagnostic script (operator)

```bash
# 1) Computer actions (must work for "playground can act")
curl -sS -H "Authorization: Bearer $ORGO_API_KEY" \
  "https://www.orgo.ai/api/computers/$CID/screenshot" | head -c 200

curl -sS -X POST -H "Authorization: Bearer $ORGO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command":"echo OK"}' \
  "https://www.orgo.ai/api/computers/$CID/bash"

# 2) VNC token + proxy
curl -sS -H "Authorization: Bearer $ORGO_API_KEY" \
  "https://www.orgo.ai/api/computers/$CID/vnc-password"
# note password + desktop_api_token

# 3) If playground 401s, inspect browser Network for:
#    - exact URL path (computers vs desktops/proxy)
#    - Authorization header class (session JWT vs API key vs VNC)
#    - response body (invalid token vs Authentication required)
```

## How to report honestly

| Observation | Conclusion |
|-------------|------------|
| Path A/B 200, UI still 401 | Frontend/session token bug, not Hermes install |
| Path A 401 with valid account key | Workspace-scoped key / wrong computer / account issue |
| Path C 401, Path A 200 | Proxy/token plumbing; agentmail can fail the same way |
| Local `orgo-desktop doctor` ready | Same-box control is fine; cloud playground path is separate |
| Path A 200 + WS prompt + black side panel | Blank-terminal class, not 401 (`template-terminal-blank-ui.md`) |

## Template authoring notes (do not "fix" 401 by)

- Adding random secrets named desktop_api_token
- Dumping doctor into terminal wake hooks
- Multiple terminal tabs

Auth for cloud control is Orgo edge + VNC password rotation, not plugin enable.

## Related

- `references/template-terminal-blank-ui.md`
- `orgo-cloud-computers` → `references/template-metal-authoring.md`
- Local auth: `VNC_PASSWORD` for `:8080` (`references/desktop-api.md`)
