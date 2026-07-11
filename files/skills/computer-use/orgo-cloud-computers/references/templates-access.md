# Orgo templates access matrix

Observed 2026-07 on operator account with Orgo MCP + CLI + REST.

## Capability matrix

| Surface | List templates | Get body/schema | Validate/publish/build | Launch computer from template |
| --- | --- | --- | --- | --- |
| Orgo CLI | No | No | No | No (`computers create` has no template flag) |
| Orgo MCP | No dedicated tools | No | No | Yes via `orgo_create_computer.image` |
| REST `https://www.orgo.ai/api` | Yes | Yes | Yes (publish/build often needs Scale) | Yes via `POST /computers` `template_ref` |

## REST endpoints

```text
GET  /templates/global
GET  /templates
GET  /templates/{namespace}/{name}/{version}
GET  /template-schema
POST /templates/validate
POST /templates?auto_build=true
GET  /templates/{namespace}/{name}/{version}/build
```

Auth: `Authorization: Bearer $ORGO_API_KEY`. Never print the key.

## Launch forms

MCP:

```text
image: "system/hermes-agent@1.0.0"
# also: default/<name>@<semver>
```

REST create body field:

```text
template_ref: "system/hermes-agent@1.0.0"
```

## System refs (global)

- `system/hermes-agent@1.0.0`
- `system/claude-code@1.0.0`
- `system/openclaw@1.0.0`

## Pitfall: image launch without software

Creating with `image: system/hermes-agent@1.0.0` via MCP can return a running desktop **without** Hermes installed (`which hermes` empty, no `~/.hermes`). Always verify and install if needed:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --skip-browser
```

## Files upload interaction

When staging secrets onto a computer, multipart upload requires `projectId` (workspace UUID) + `desktopId` (computer UUID). `workspaceId` alone returned `Missing projectId` (2026-07).
