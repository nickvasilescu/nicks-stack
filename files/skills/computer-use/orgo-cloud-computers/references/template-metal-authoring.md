# Orgo template metal authoring (Hermes + desktop-local)

Lessons through `default/hermes-orgo-desktop-local@0.3.4` (2026-07).

## Gold references (study these first)

| Repo / template | Why |
|-----------------|-----|
| **[nickvasilescu/agentmail-agent](https://github.com/nickvasilescu/agentmail-agent)** / `default/agentmail-agent@0.2.4` | Best Hermes-on-Orgo product template: single `hermes` terminal **no run**, `apps[].install`, gateway waits for `auth.json`, lean first_boot, on_resume secret bridge |
| **[nickvasilescu/nicks-stack](https://github.com/nickvasilescu/nicks-stack)** | Same builder REST flow + staging pattern |
| Package | `/root/Desktop/orgo-hermes-desktop-local` → `build_template.py` |

Do not invent multi-tab bootstrap/validate terminals. Copy agentmail shape.

## API sequence (works)

```text
GET  /template-schema
POST /templates/validate          → ok: true
POST /templates?auto_build=true   → 201 + digest
POST /templates/{ns}/{name}/{ver}/build  → 202 building
GET  same path until status=ready (+ golden_dir)
POST /computers  template_ref=default/name@semver
```

`auto_build: building` alone is not enough; poll GET until `ready`.
`TEMPLATE_NOT_READY` on create means golden not ready yet.

## Product ref (current)

```text
default/hermes-orgo-desktop-local@0.3.4
```

## What metal will build vs hang at not_built

| Pattern | Result |
|---------|--------|
| Small files + short `build.run` (chmod, echo) | **ready** quickly |
| Many inline files (~100KB) + short run | **ready** |
| Hermes `curl\|bash` in **`build.run`** | often stays **`not_built`** (silent) |
| **agentmail/nicks-stack `apps[].install`** with `hermes install --non-interactive --skip-setup --skip-browser` + minimal `build.apt` (`git`, `xz-utils`, `python3-yaml`, `ripgrep`) | **ready** |
| Heavy `apps[].install` with nodesource + interactive prompts | often **`not_built`** or hung boot |
| Stage under `/opt/...` only + first-boot bootstrap | **ready**; software after boot |

**Rules:**

1. Prefer **agentmail**: Hermes + stack in `apps[].install` with non-interactive flags; lean hooks.
2. Never put long Hermes install in **`build.run`**.
3. `build.apt`: include **`xz-utils`**. Avoid apt that upgrades libssl and kills supervisord (skip ca-certificates/openssl/curl in apt if they upgrade libssl3t64).
4. Secrets: declare optional vault names; bridge in `on_resume` into `~/.hermes/.env`. Do not use `env:{secret}` / `files:secret://` if they crash compile.
5. Gateway service: wait for `config.yaml` **and** `auth.json` before `hermes gateway run` (flock lock recommended).

## Terminal tabs (browser UI attach) — critical

Docs: terminal = pre-staged **tmux** sessions; browser attaches **by name**.

WS: `wss://www.orgo.ai/desktops/{instance}/ws/terminal?token={vnc_password}&session={name}`  
VNC password **rotates every restart** — soft reload is not enough; user must **hard refresh**.

Orgo generates `/usr/local/bin/orgo-tmux-startup.sh` from `terminal[]`. Agentmail gold:

```bash
tmux new-session -d -s 'hermes' -c '/root'
# only that — no send-keys
```

| Anti-pattern | Symptom |
|--------------|---------|
| `run: bootstrap.sh` bare `hermes plugins enable` | Tab hung on "Grant it?" |
| `run: validate.sh` one-shot | Tab exits → empty |
| **`run: bash -l`** (or any run) | Generated `send-keys bash -l` → nested shell → **black tab** |
| Supervisord heal kill-server + recreate | Socket **0660** vs agentmail **0770**; wrong tmux owner |
| Large `send-keys` doctor JSON | Garbled/blank-looking UI |
| Complex multi-tab `run` strings | Metal flaky; UI confuses |

| Working pattern (agentmail) | |
|-----------------------------|--|
| Single tab | `{ name: hermes, title, description, cwd: /root }` — **no `run` field at all** |
| Noninteractive enable | in `apps.install` / install script: `--no-allow-tool-override` |
| Hooks | lean stamp first_boot; **do not** pre-create tmux; **no** doctor dump |
| Soft heal only | wait + chmod 0770 + optional one-line paint; never kill under supervisord |

**User-verified UI recovery (2026-07-09):** restart computer → agentmail-clean session → **hard refresh** browser. Full write-up: `orgo-desktop-local` → `references/template-terminal-blank-ui.md`.

Create response must include `instance_details.templateTerminals` matching session names.

## Plugin enable (never interactive in templates)

```bash
hermes plugins enable orgo-desktop-local --no-allow-tool-override
# WRONG — hangs forever
hermes plugins enable orgo-desktop-local
```

## Playground 401 vs template bugs

Computer actions (`/api/computers/{id}/screenshot|bash|click`) and  
`POST /api/v1/chat/completions` with `computer_id` return **200** on agentmail and
hermes-orgo-desktop-local when the account key is valid.

Proxy path `/api/desktops/{instance}/proxy/*` can 401 when `desktop_api_token` is the
placeholder `"template-build"` (also seen on agentmail). Edge WS with `token=template-build`
closes immediately; use the real VNC password. Measure before blaming the template.

Full procedure: `orgo-desktop-local` → `references/playground-401-diagnostics.md`.

## Dual product path (same package)

1. **Template** `default/hermes-orgo-desktop-local@x.y.z` — new VMs
2. **Individual** `install/install-on-existing-hermes.sh` — existing Hermes-on-Orgo

## E2E gate before claiming "template works"

1. Create computer from ref
2. Confirm `templateTerminals` on create payload
3. Computer API screenshot/bash **200**
4. `orgo-tmux-startup.sh` is agentmail-only; socket prefer 0770; clean shell
5. MCP/orgo_bash `validate.sh` exit 0
6. MCP screenshot non-black
7. If UI terminal blank: **restart → hard refresh**, not re-publish first
8. WS green ≠ browser green — require hard refresh after token rotate

`orgo_wait` parameter is **`duration`**, not `seconds`.

## Prefer order

On the VM after doctor green: local Desktop API first. Operator outside uses cloud Orgo MCP / computer API against that computer_id.

## See also

- `orgo-desktop-local` → `references/e2e-template-validation.md`, `template-terminal-blank-ui.md`, `playground-401-diagnostics.md`
- https://docs.orgo.ai/guides/templates/schema#terminal
- https://github.com/nickvasilescu/agentmail-agent
- https://github.com/nickvasilescu/nicks-stack
