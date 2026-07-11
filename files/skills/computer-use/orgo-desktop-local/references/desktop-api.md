# Orgo in-VM Desktop API (loopback)

Grounded on live `GET http://127.0.0.1:8080/schema` (OpenAPI 3.0.1) and
https://docs.orgo.ai/introduction (cloud computers + agent loop). Cloud
lifecycle/MCP is separate from this loopback control plane.

## Topology

```
Hermes on Dewey
  → http://127.0.0.1:8080   (orgo-desktop-api)   AUTH: VNC password
  → Xvnc DISPLAY=:99

Cloud Orgo MCP / www.orgo.ai/api/computers/{id}/…
  → metal port → same desktop-api class of control (plus lifecycle)
```

When co-located, skip the cloud hop for GUI/bash/screenshot.

## Auth

```http
Authorization: Bearer <vnc_password>
```

Sources (in order used by client): `ORGO_DESKTOP_API_TOKEN`, `VNC_PASSWORD`,
`~/.hermes/.env` same keys. Not `ORGO_API_KEY`.

Open without auth: `GET /health`, `GET /schema`, `GET /metrics`.

## Verbs (typical body)

| Method | Path | Body notes |
|---|---|---|
| GET | `/health` | `{status, service: orgo-desktop-api, version}` |
| GET | `/` | endpoint catalog + events types |
| GET | `/status` | needs auth |
| GET | `/screenshot` | `{image: base64 png}` |
| POST | `/click` | `{x,y,button?,double?}` |
| POST | `/double_click` | `{x,y}` |
| POST | `/drag` | `{start_x,start_y,end_x,end_y}` |
| POST | `/type` | `{text, delay_ms?}` |
| POST | `/key` | `{key}` e.g. `Return`, `Escape`, `ctrl+l` |
| POST | `/scroll` | `{direction, amount?, x?, y?}` |
| POST | `/mouse_move` | `{x,y}` |
| POST | `/wait` | `{seconds}` max 60 |
| POST | `/bash` | `{command, timeout?}` |
| POST | `/exec` | Python exec payload per schema |

WS: `/events`, `/terminal`, `/audio` (token query param).

Event types (useful waits): `window_focus`, `window_open/close`, `clipboard`,
`file_change`, `process_start/stop`, `idle`/`active`, screen change.

## Client additions (local stack)

- `frame_fingerprint` / `click(verify=…)` / `drag(verify=…)` / `click_path`
- Doctor fields: `prefer`, `control_plane`, `avoid_when_ready`, `guidance`
- Fingerprint default crops top ~28px so panel clock does not force false diffs

## Coords

Full desktop pixels. Dewey default **1280×720**. Window-local vs desktop
offsets matter if mixing CUA window crops with Desktop API clicks — prefer
full-desktop screenshots from this API for click planning.

## Client locations

- Python: `~/.hermes/scripts/orgo_desktop/client.py`
- CLI: `orgo-desktop` → `~/.local/bin/orgo-desktop`
- Smoke: `orgo-desktop smoke` → `/tmp/orgo-desktop-smoke/`
