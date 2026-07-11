# Hermes Latitude OTEL backfill (existing Orgo VMs)

Use when eng/agency Hermes boxes have **no Latitude service** (or config is stale) and product provision already knows how to instrument new VMs (MomentumClaw `provision.ts` pattern). Prefer this over copying Dewey’s full `LATITUDE_*` env pack.

Also use when Nick says **set up Latitude for customer X** (including thin pilots like Budgetdog) — create a **dedicated project** + wire emission on the flagship computer.

## New customer project (CLI)

Never put customer agents into `dewey`.

```bash
set -a; . /root/.hermes/scripts/latitude/env.sh; set +a   # or LATITUDE_API_KEY from secrets
latitude projects create --name "Budgetdog" --format json
# → name, slug (e.g. budgetdog), id
latitude projects list --format json
```

| Customer | Project slug | Service pattern |
|---|---|---|
| Nick / internal | `dewey` | Dewey only |
| Momentum fleet | `momentumclaw` | `hermes-<id8>` |
| Brennan / Budgetdog | `budgetdog` | `hermes-e3741a9a` |

Vault: `projects/<slug>/latitude.md` with project id, service name, computer id (no keys).

## Two emission paths (pick the right one)

### A) Hermes session plugin (preferred for pilots / Telegram CoS)

Config files alone + OpenAI/Anthropic instrumentors often leave the Latitude UI on **“Waiting for your first trace”** until Hermes actually exports session spans.

**Preferred path for Budgetdog-class Hermes boxes:**

1. Create project slug (above).
2. Install package on the **gateway venv**:
   - Copy Dewey’s `~/.hermes/local-packages/latitude-telemetry-hermes` to the VM (tar/base64 via Orgo exec).
   - `pip install -e` into `/usr/local/lib/hermes-agent/venv`.
3. Patch `~/.hermes/.env` (quote values with spaces):
   ```bash
   LATITUDE_API_KEY=…          # from secrets; never print
   LATITUDE_PROJECT=budgetdog
   LATITUDE_PROJECT_SLUG=budgetdog
   LATITUDE_BASE_URL=https://ingest.latitude.so
   LATITUDE_HERMES_TELEMETRY_ENABLED=true
   LATITUDE_TELEMETRY_ENABLED=true
   LATITUDE_NO_CONTENT=true    # metadata-first for customer pilots
   LATITUDE_USER_ID=brennan-budgetdog
   LATITUDE_USER_NAME="Brennan Schlagbaum"   # MUST be quoted
   OTEL_SERVICE_NAME=hermes-<id8>
   ```
4. `hermes plugins enable latitude` (takes effect next session). Confirm `hermes plugins list` shows **enabled**.
5. Restart gateway **on the VM only** (see Safe gateway restart + Host terminal guard).
6. Force a first real span if UI still empty:
   ```bash
   set -a; source ~/.hermes/.env; set +a
   hermes chat -Q --accept-hooks --max-turns 1 -q 'Reply with exactly: latitude-ok'
   ```
7. Verify from Dewey:
   ```bash
   latitude traces list --project-slug budgetdog --format json
   # expect rootSpanName interaction (and optional smoke test)
   ```

Also keep `~/.hermes/.latitude.json` + bootstrap as belt-and-suspenders for raw OTLP/instrumentors.

### B) OTel `.pth` bootstrap only (fleet / provision-style)

All of:

```text
~/.hermes/.latitude.json
  endpoint, key, project=<customer-slug>, computer_id=<uuid>,
  service_name=hermes-<id8>, account=<optional>
$HERMES_VENV/site-packages/latitude_bootstrap.py
$HERMES_VENV/site-packages/latitude_bootstrap.pth   # contents: import latitude_bootstrap
/tmp/latitude_bootstrap.log
  # ok instrumentors... OR ok headers...
gateway / hermes process running (Telegram pilots may not use :8642)
```

Typical Hermes venv on Orgo images: `/usr/local/lib/hermes-agent/venv/bin/python3`

**OTLP headers must include the project** (same as `send_test_trace.py`):

```text
Authorization=Bearer <key>
X-Latitude-Project=<slug>
```

Resource attrs: `latitude.project=<slug>,computer.id=<uuid>,account=<label>`.

### Incomplete-config trap

`.latitude.json` **can exist** while UI still says waiting because:

- OTel packages missing from the **gateway venv**
- `.pth` / bootstrap not installed
- gateway never restarted after install
- only instrumentors installed, **no Hermes session traffic / no latitude plugin**
- missing `X-Latitude-Project` on OTLP posts

Always verify **import + env in running process + `traces list` non-empty**, not file presence alone.

## UI still empty?

| Check | Action |
|---|---|
| Project exists, 0 traces | Smoke test from Dewey (below), then plugin path + `hermes chat -Q` |
| Smoke OK, no `interaction` | Plugin not enabled / gateway without `LATITUDE_*` env / no LLM turn yet |
| Traces list has rows, UI empty | Hard-refresh browser; confirm project slug matches |
| Tokens > 0, cost $0 | Normal for some OpenRouter/Grok routes until Latitude pricing maps; report tokens + cost separately |

### Smoke test (proves key + project routing)

```bash
set -a; . /root/.hermes/scripts/latitude/env.sh; set +a
export LATITUDE_PROJECT_SLUG=budgetdog
export LATITUDE_SERVICE_NAME=hermes-e3741a9a
export LATITUDE_TRACE_NAME=budgetdog-setup-smoke
python3 /root/.hermes/scripts/latitude/send_test_trace.py
# uses Authorization + X-Latitude-Project; never prints the key
latitude traces list --project-slug budgetdog --format json | head
```

## OTel package pins (do not mix)

**Working set** (gateway venv, Jul 2026):

```text
opentelemetry-sdk==1.43.0
opentelemetry-exporter-otlp-proto-http==1.43.0
opentelemetry-instrumentation-openai==0.61.0
opentelemetry-instrumentation-anthropic==0.61.0
```

**Broken combo** (pip ResolutionImpossible): `...-openai==0.61.0` + `...-anthropic==0.53.0`

Older Momentum backfill scripts used anthropic **0.53.0** — always use **0.61.0** with openai 0.61.0. Install into the **same** python that runs `hermes`.

## Orgo remote exec (API)

```text
POST https://www.orgo.ai/api/computers/{computer_id}/exec
Authorization: Bearer $ORGO_API_KEY
Content-Type: application/json

{"code": "<python>", "timeout": 300}
```

**Secrets hygiene:** do **not** embed `LATITUDE_API_KEY` as a string literal inside the remote `code=` payload if that process can appear in `pgrep -af` / exec logs. Prefer env → short-lived on-box script → write only into `~/.hermes/.latitude.json` / `.env` (mode 0600), never print the key.

Working wrapper: stage base64 installer on the VM → `subprocess.run([py, path], env={...})` → print stdout/stderr/exit only.

### Host terminal guard (Dewey)

Running Hermes on Dewey may **block host terminal** commands whose source contains gateway kill/restart phrases (even when the kill is only in remote payload strings). Prefer:

- Orgo MCP `orgo_bash` / REST exec for **all** remote gateway process management
- Avoid putting `pkill … hermes gateway` / `hermes gateway restart` in the **local** tool command text

## Safe gateway restart (critical)

**Do not** kill the gateway from inside the same Orgo exec that is a child of the supervisor tree without detaching — remote shell can exit **-15 (SIGTERM)** after writing files.

**Do:**

1. Write config + plugin/env + OTel pins.
2. Verify env sources: `set -a; source ~/.hermes/.env; set +a` (unquoted spaces break source — e.g. `LATITUDE_USER_NAME=Brennan Schlagbaum` → command not found).
3. Stop only `hermes … gateway … run` PIDs via `/proc` scan; spawn with `start_new_session=True` or Budgetdog’s `start_telegram_gateway.sh` **on the VM**.
4. **Telegram-first pilots**: may have no listener on `:8642`. Success signals:
   - `pgrep` shows `hermes gateway run`
   - `ss` ESTAB to Telegram (`149.154.*:443`) even if log stuck on “Connecting attempt 1/8”
   - `getMe` OK for the bot
5. Confirm process environ has `LATITUDE_PROJECT` / `LATITUDE_API_KEY` set (print key names only).

## Spend / analytics

- Latitude **cost can stay $0** while `tokensTotal` is nonzero (provider pricing not mapped yet). Report both.
- Pre-setup usage **does not backfill**.
- After setup: `latitude traces analytics --project-slug <slug>` + `traces list`.

## Backfill / first-time order

1. Create or confirm customer Latitude project slug.
2. Load `LATITUDE_API_KEY` from secret manager (never vault/print).
3. Target **Hermes-running** boxes only.
4. Prefer **plugin path (A)** for single-box pilots; fleet may use provision/bootstrap (B).
5. Tell Nick: spend starts after post-setup traffic; empty UI ≠ no project.
6. Smoke test + force `hermes chat -Q` if needed; re-check `traces list`.

## Dewey helpers

- `~/.hermes/scripts/momentum/backfill-latitude-otel.sh` — Momentum default project; override `LATITUDE_PROJECT`. Pins must match the **working set** (no anthropic 0.53.0).
- `~/.hermes/scripts/latitude/send_test_trace.py` — OTLP smoke with `X-Latitude-Project`.
- `~/.hermes/local-packages/latitude-telemetry-hermes` — copy to customer VMs for plugin path.

Vault examples: `projects/momentum-amp/hermes-fleet.md`, `projects/budgetdog-ops/latitude.md`.

## Product source of truth for *new* VMs

Customer workbench provision (e.g. `nickvasilescu/momentumclaw` `src/lib/provision.ts` → `configure-gateway`) installs Latitude fail-open for **new** provisions (project default often `momentumclaw`). Backfill is for pre-provision boxes, incomplete installs, or **non-Momentum customers** (Budgetdog, etc.).
