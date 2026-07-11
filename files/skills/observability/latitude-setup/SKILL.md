---
name: latitude-setup
description: Zero-account onboarding orchestrator for Latitude. Bootstrap a temporary Latitude account from the terminal (no signup), instrument the app for tracing, verify real traces, clean up, and hand back a browser link to claim ownership. Use when someone wants to set up Latitude from scratch with no existing account or API key — the landing-page "try it with your agent" flow.
---

# Latitude Setup (zero-account onboarding)

Orchestrates the **from-scratch** path: the user has **no Latitude account and no API key**. This skill provisions a temporary account via the CLI, instruments the app, verifies real traces, and returns a claim link the user opens in a browser to take ownership.

**When NOT to use this skill:** if the user already has a Latitude account/API key (e.g. they're signed in and want to instrument another app), skip bootstrap/claim entirely and go straight to `latitude-telemetry` + `latitude-cli`.

This skill depends on two others — **`latitude-cli`** (install + auth + command primitives) and **`latitude-telemetry`** (instrumentation). Read both; this skill only adds the orchestration between them.

## Ground rules

- **Plan, then wait.** Instrumentation goes through `latitude-telemetry`'s "present a plan, wait for explicit approval" contract. Do not edit app code before approval.
- **Never print raw secrets.** The bootstrap API key must never appear in chat, logs, or commits. The claim link is safe to show (it's the whole point) — the API key is not.
- **One project, named once.** Bootstrap creates exactly one project. There is no throwaway "testing" project; cleanup is delete + recreate with the same name (see step 7).

## The flow

### 1. Install dependencies

Ensure the `latitude-telemetry` and `latitude-cli` skills are available, and install the `latitude` binary as described in **`latitude-cli` → Install** (OS/ARCH detection, download the matching release asset, place on `PATH`, `chmod +x`). **Only `cli-5.0.0` and later are the real Latitude CLI** — `latitude-cli` explains why earlier `cli-*` tags must be ignored. Confirm with `latitude --version` (expect ≥ 5.0.0).

### 2. Bootstrap a temporary account

This is unauthenticated — no key needed yet. Infer a sensible project name from the app (and optionally an org name); ask the user for an email only if you want the claim link mailed to them.

**First, discover the command's exact flags and response fields** — don't assume the shape; it can change across versions:

```bash
latitude account bootstrap --schema
```

**Keep the API key out of your own conversation.** `--format json` prints the API key to stdout, which lands in the transcript. On a best-effort basis, capture the response to a scratch file instead of letting it print, then display everything *except* the secret:

```bash
latitude account bootstrap \
  --project-name "<inferred project name>" \
  --organization-name "<inferred org name>" \
  --format json > ~/.latitude-bootstrap.json
# optional: --user-email <address>  (also emails the claim link)

# Show the non-secret fields; drop the API key (and any other sensitive field --schema flags):
jq 'del(.apiKey)' ~/.latitude-bootstrap.json
```

The flow relies on a few of the response fields, by role (confirm their exact names in `--schema`):

- the **API key** — an org-scoped secret; never print it. It flows straight into `.env` in step 3, then the scratch file is deleted.
- the **project slug** — the single created project; your telemetry target and the cleanup handle (step 7).
- the **claim link** (plus its expiry, and the email it was sent to if you passed one) — handed back to the user in step 8.

### 3. Configure auth via `.env`

Write the key and project slug into the app's `.env` **straight from the scratch file, so the value never prints**. Make sure `.env` is gitignored. Replace any existing `LATITUDE_*` lines rather than duplicating them, then delete the scratch file:

```bash
touch .env
# Drop any prior LATITUDE_API_KEY / LATITUDE_PROJECT_SLUG lines (avoids duplicates). BSD+GNU sed:
sed -i.bak '/^LATITUDE_API_KEY=/d;/^LATITUDE_PROJECT_SLUG=/d' .env && rm -f .env.bak
# Append the real values from the file — never echoed (field names .apiKey/.projectSlug per --schema):
printf 'LATITUDE_API_KEY=%s\n'     "$(jq -r .apiKey      ~/.latitude-bootstrap.json)" >> .env
printf 'LATITUDE_PROJECT_SLUG=%s\n' "$(jq -r .projectSlug ~/.latitude-bootstrap.json)" >> .env
# Remove the scratch file so the key isn't left on disk:
rm -f ~/.latitude-bootstrap.json
```

If any value you later add to `.env` contains spaces (not the key/slug — e.g. a header/token value), wrap it in double quotes: the CLI's `.env` parser rejects unquoted spaced values and stops, after which it won't read `LATITUDE_API_KEY` (see `latitude-cli` → Authentication).

`LATITUDE_API_KEY` authenticates **both** the `latitude` CLI (it auto-loads `.env` from the working directory and its parents) **and** the telemetry SDK — one entry, both consumers. **Do not** run `latitude auth login`; it invokes the OS keychain and can block on a prompt. Run subsequent `latitude` commands from the app root so `.env` is picked up. Do not echo the key back to the user.

**Verify auth before going further** (this catches the most common failure early):

```bash
latitude auth status     # expect:  ✓ active   LATITUDE_API_KEY env var
```

If it shows `missing`, `.env` isn't being applied — you're either not running from the app root (or a subdirectory), or an empty/stale `LATITUDE_API_KEY` in the shell is shadowing it (the `.env` load never overrides an already-set var). Fix the directory or `unset` the shadowing var, then re-check. See `latitude-cli` → Authentication.

### 4. Instrument the app (delegate to `latitude-telemetry`)

Hand off to `latitude-telemetry` to add instrumentation, pointing it at `LATITUDE_PROJECT_SLUG=<projectSlug>`. The key/slug are already provisioned and in `.env`, so **skip that skill's MCP-config discovery detour** — you have the values. Follow its audit → group → clarify → **plan → wait for approval** → implement steps. Do not edit code before the user approves the plan.

### 5. Run the user's real LLM flow

After instrumentation, run the user's **actual** code so real spans are emitted — not a synthetic span. Spans typically export on a batch interval, so they may take a short while to arrive — poll rather than expecting them instantly (step 6). Let the process finish or shut down **gracefully** so buffered spans flush; a hard kill can drop them. For short-lived scripts, ensure the SDK flushes before exit (see `latitude-telemetry`).

### 6. Inspect real traces and iterate

Poll the project's traces until the expected spans arrive, then verify quality:

```bash
latitude traces list --project-slug <projectSlug> --format json
```

Confirm model, token counts, message capture, and span boundaries look right. If instrumentation is wrong (missing spans, no token data, wrong boundaries), fix it and re-run the user's code. **Loop until the traces are correct.**

### 7. Clean the messy iteration traces — without touching app config

The verification loop leaves noisy traces. Wipe them by deleting and recreating the project **with the same name**, which yields the **same slug** — so `LATITUDE_PROJECT_SLUG` and all instrumentation stay valid and **no config is re-edited**:

```bash
latitude projects delete --project-slug <projectSlug>
latitude projects create --name "<the exact same project name from step 2>"
```

A successful `projects delete` returns HTTP 204 (no body), which the CLI renders as a placeholder like `{ bytes: 0, mimeType: text/plain, saved_file: download.txt, status: success }` — **that `status: success` is the delete succeeding**, not an error or a file download. Then run the user's code **once more** to produce a single clean set of real traces. Confirm with `latitude traces list` again.

### 8. Hand back the claim link

Present the claim link to the user (safe to show) and tell them to open it in a browser to claim ownership of the temporary account — that makes them the owner and stops it from expiring. Mention its expiry (unclaimed temp accounts are deleted then). If you passed an email, note the link was also sent there.

Do **not** print the API key. The final state: instrumented app, one clean project of verified real traces, and a working claim link — with the user never having touched the Latitude UI first.
