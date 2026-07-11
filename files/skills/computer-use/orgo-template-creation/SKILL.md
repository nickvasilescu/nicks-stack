---
name: orgo-template-creation
description: Create and publish Orgo computer templates via REST.
version: 0.1.0
author: Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [Orgo, Templates, Metal, Publish, Hermes]
    related_skills: [orgo-cloud-computers, orgo-desktop-local]
---

# Orgo Template Creation

Author, validate, publish, build, launch, and prune Orgo account templates (`default/<name>@<semver>`) over REST. Does not install Hermes on an already-running VM (use the desktop-local plugin path for that) and does not replace cloud computer lifecycle (`orgo-cloud-computers`).

Source of truth for product Hermes templates: package layout plus `build_template.py` under `/root/Desktop/orgo-hermes-desktop-local` (GitHub publishes as `default/hermes-orgo-desktop-local@…`). Gold structural pattern: agentmail-agent (single terminal, no `run`; Hermes in `apps[].install`; lean hooks).

## When to Use

- User asks to create, publish, bump, or rebuild an Orgo template
- Bake Hermes into a new Orgo computer / template_ref / golden image
- Validate a template JSON or YAML before publish
- List account templates and delete old versions or probes
- Diagnose `not_built`, black web Terminal, or TEMPLATE_NOT_READY

Do not use for same-box GUI control (`orgo-desktop-local`) or fleet MCP GUI against other VMs.

## Prerequisites

- `ORGO_API_KEY` in the environment or Hermes `.env` (Bearer auth)
- Scale plan (or plan that allows `POST /templates` plus metal build) for publish/build
- Workspace UUID for launch (`workspace_id`)
- Optional local package with `build_template.py` for Hermes desktop-local product templates

Schema (public): `GET https://www.orgo.ai/api/template-schema`  
Docs: `https://docs.orgo.ai/guides/templates/schema`

## How to Run

Invoke through the `terminal` tool with `ORGO_API_KEY` set. Prefer a package `build_template.py --build` when one exists; otherwise assemble JSON and call REST with `scripts/orgo_template_ops.py`.

Never print the API key. Prefer `default/<name>@x.y.z` refs; do not overwrite system templates.

## Quick Reference

```text
Base:  https://www.orgo.ai/api
Auth:  Authorization: Bearer $ORGO_API_KEY

GET    /template-schema
GET    /templates
GET    /templates/global
GET    /templates/{ns}/{name}
GET    /templates/{ns}/{name}/{version}
POST   /templates/validate
POST   /templates?auto_build=true
POST   /templates/{ns}/{name}/{version}/build
GET    /templates/{ns}/{name}/{version}/build
DELETE /templates/{ns}/{name}/{version}
POST   /computers   body: workspace_id, name, template_ref, cpu?, ram?

Ref form:  default/my-template@1.0.0
MCP launch field: image = same ref string
CLI: no template commands (REST only)

Gold package:
  VERSION=0.3.5 python3 build_template.py --build
  python3 build_template.py --launch <WORKSPACE_ID>
```

## Procedure

### 1) Inventory (optional cleanup first)

```bash
python3 ~/.hermes/skills/computer-use/orgo-template-creation/scripts/orgo_template_ops.py list
```

Keep only latest built-out product versions. Delete probes (`hdl-*`, `zz-*`, isolation stubs) and older semvers after user confirmation. System refs stay: `system/hermes-agent@1.0.0`, `system/claude-code@1.0.0`, `system/openclaw@1.0.0`.

Completion: `list` shows intended keep set only, or an explicit delete plan is approved.

### 2) Author the document

Canonical top-level keys: `api_version` (`orgo.ai/v1`), `template` (name, version, description), `hardware`, `secrets`, `build`, `files`, `apps`, `terminal`, `hooks`.

Agentmail / Hermes product rules (copy, do not invent):

1. Hermes install in `apps[].install`, not long `build.run`:
   `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --non-interactive --skip-setup --skip-browser`
2. Stage package under `/opt/<pkg>/` via `files[]` (`to`, `inline`, `mode`, `when: build`), then install after Hermes so staged files win.
3. Minimal `build.apt`: include `xz-utils` (Node unpack). Avoid apt that upgrades libssl and kills supervisord mid-build when possible.
4. Terminal: single session `{ name, title, description, cwd }` with no `run` field. Any `run` (including `bash -l`) becomes nested send-keys and a black Web Terminal.
5. Hooks lean: stamp-only `on_first_boot`; do not pre-create tmux; bridge vault secrets into `~/.hermes/.env` in `on_resume`.
6. Plugin enable must be noninteractive: `hermes plugins enable <name> --no-allow-tool-override`.
7. Gateway service should wait for `auth.json` before `hermes gateway run` (avoid crash loops).
8. Secrets optional in template; never bake personal API keys into golden images.

If packaging hermes-orgo-desktop-local, start from `/root/Desktop/orgo-hermes-desktop-local/build_template.py` and bump `VERSION`.

Completion: JSON/YAML assembles; file count and description look product-grade (not "probe").

### 3) Validate

```bash
python3 build_template.py --remote-validate
# or
python3 ~/.hermes/skills/computer-use/orgo-template-creation/scripts/orgo_template_ops.py validate path/to/template.json
```

Completion: `POST /templates/validate` returns `{ "ok": true }`.

### 4) Publish and build golden

```bash
VERSION=x.y.z python3 build_template.py --build
# equals: validate → POST /templates?auto_build=true → POST .../build → poll GET until status=ready
```

Statuses: `not_built` | `building` | `ready` | `failed`.  
`auto_build: building` alone is not enough; poll until ready.

Completion: `GET .../build` shows `status=ready` and ref appears on `GET /templates`.

### 5) Launch smoke computer

```bash
python3 build_template.py --launch <WORKSPACE_ID>
# or POST /computers with template_ref, workspace_id, name, cpu, ram
```

Then remote bash: package `validate.sh` / `orgo-desktop-local-validate` if applicable; `which hermes`; optional `orgo-desktop doctor` on desktop-local images.

Completion: computer `running`; create payload `instance_details.templateTerminals` matches terminal names; validate exit 0 when the package defines it.

### 6) Version discipline

- Semver is immutable once published; bump version for each publish, or use `?force=true` only while iterating.
- Prefer one live version per product name in the account (delete older after promote).

## Pitfalls

- Orgo CLI has no templates surface; inventing `orgo templates` fails; use REST.
- Hermes install in `build.run` often sticks at `not_built`; use `apps[].install` instead.
- Terminal `run` causes black Web Terminal; fix by republishing without `run`, restart computer, hard-refresh browser (VNC password rotates).
- Interactive `hermes plugins enable` hangs golden/boot forever.
- Keys in golden images must not be published or curated; use vault plus `on_resume` bridge.
- TEMPLATE_NOT_READY on create means golden is not ready yet; poll build.
- Template launch is not software verified; always run validate / `which hermes` on the new VM.
- Probes and stack churn fill the account with mid-iteration semvers; prune regularly.

## Verification

```bash
python3 ~/.hermes/skills/computer-use/orgo-template-creation/scripts/orgo_template_ops.py list
python3 ~/.hermes/skills/computer-use/orgo-template-creation/scripts/orgo_template_ops.py build-status default NAME VERSION
# expect status == ready for a just-built version
```

Optional: launch one computer from `template_ref` and confirm package validate / Hermes on PATH.

## References

- Package gold: `/root/Desktop/orgo-hermes-desktop-local/` (`build_template.py`, `SUCCESS_CRITERIA.md`)
- GitHub patterns: `nickvasilescu/agentmail-agent`, `nickvasilescu/nicks-stack`, `nickvasilescu/orgo-hermes-desktop-local`
- Schema: https://docs.orgo.ai/guides/templates/schema
- Metal notes: `orgo-cloud-computers` → `references/template-metal-authoring.md`
- Helper: `scripts/orgo_template_ops.py`
