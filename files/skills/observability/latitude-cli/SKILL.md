---
name: latitude-cli
description: Install, authenticate, and drive the Latitude CLI (the `latitude` binary) to run Latitude API operations from a terminal — projects, traces, analytics, datasets, and more. Use for the `latitude` command-line tool, installing the CLI binary, CLI authentication with an API key, or scripting the Latitude API from an agent or shell.
---

# Latitude CLI

The `latitude` CLI is a single self-contained binary that exposes the Latitude API as typed subcommands. It is **auto-generated from the Latitude OpenAPI spec**, so its command set tracks the API and grows over time.

**Do not memorize or hardcode the command list.** Discover commands at runtime with `--help` and `--schema` (below). Instructions that enumerate every entity command go stale on the next release; the discovery flow does not.

## Install

Skip this if `latitude --version` already works. Otherwise install the binary for the current platform. There is no one-line installer URL — resolve the latest release and download the matching asset.

### 1. Detect OS and architecture

```bash
uname -s   # Darwin → macos, Linux → linux (Windows: use windows)
uname -m   # x86_64/amd64 → amd64, arm64/aarch64 → arm64
```

Asset names follow `latitude-<os>-<arch>`:

| OS      | arm64                              | amd64                              |
| ------- | ---------------------------------- | ---------------------------------- |
| macOS   | `latitude-macos-arm64.tar.gz`      | `latitude-macos-amd64.tar.gz`      |
| Linux   | `latitude-linux-arm64.tar.gz`      | `latitude-linux-amd64.tar.gz`      |
| Windows | —                                  | `latitude-windows-amd64.zip`       |

### 2. Find the latest CLI release and download the asset

Releases live in `latitude-dev/latitude-llm`. **CLI releases are tagged `cli-<version>`** (titled "Latitude CLI vX.Y.Z") and are interleaved with the main app's `vX.Y.Z` tags — filter for the `cli-` prefix.

> **Only `cli-5.0.0` and later are the real Latitude CLI.** A retired, unrelated 2025 tool published `cli-*` tags up to `cli-4.0.0` under the same name; those releases carry **no binaries**. Never pick a `cli-*` tag below `v5` — filter to major version ≥ 5, then take the highest. "Newest tag" or "highest tag overall" logic will grab a stale, asset-less release and the download will fail.

Set the asset name for your platform once (from the table above):

```bash
ASSET=latitude-macos-arm64.tar.gz   # ← set to YOUR platform's asset from the table (e.g. latitude-linux-amd64.tar.gz)
```

**With the GitHub CLI (`gh`), if installed and authenticated (preferred):**

```bash
# Highest cli-* release with major version >= 5.
# NOTE: use --slurp. Under --paginate, a per-page --jq runs once PER PAGE and emits
# multiple values instead of one, which breaks tag selection.
TAG=$(gh api repos/latitude-dev/latitude-llm/releases --paginate --slurp \
  | jq -r '[ .[][].tag_name | select(startswith("cli-"))
             | select((ltrimstr("cli-") | split(".")[0] | tonumber) >= 5) ]
           | sort_by(ltrimstr("cli-") | split(".") | map(tonumber)) | last')

gh release download "$TAG" --repo latitude-dev/latitude-llm --pattern "$ASSET"
```

**Without `gh` (curl + the public API):**

```bash
# GitHub returns releases newest-first. The retired pre-v5 cli-* tags have NO assets,
# so matching the asset filename inherently skips them; head -1 takes the newest release
# that actually ships it.
URL=$(curl -fsSL "https://api.github.com/repos/latitude-dev/latitude-llm/releases?per_page=100" \
  | grep -oE "https://[^\"]*${ASSET}" | head -1)
curl -fsSL -o "$ASSET" "$URL"
```

If neither works, open <https://github.com/latitude-dev/latitude-llm/releases>, find the latest **Latitude CLI vX.Y.Z** entry (**v5.0.0 or higher**), and download the asset for this platform.

### 3. Extract, place on `PATH`, make executable

The archive extracts to a `latitude-<os>-<arch>/` folder holding the `latitude` binary.

```bash
tar -xzf "$ASSET"          # Windows (.zip asset): unzip "$ASSET"
```

Move the binary somewhere on `$PATH` so it runs from anywhere. Try a user-writable, already-on-`PATH` location first; use `sudo` only if the user has it and consents:

```bash
# Prefer a user dir already on PATH (no sudo). ~/.local/bin or ~/bin are common.
mkdir -p ~/.local/bin
mv latitude-*/latitude ~/.local/bin/latitude   # the glob matches the extracted latitude-<os>-<arch>/ folder
chmod +x ~/.local/bin/latitude          # downloaded binaries often need the exec bit
# If ~/.local/bin isn't on PATH, add it (e.g. append to the shell rc) or fall back below.
```

macOS only — the binary is unsigned, so Gatekeeper may quarantine it. If it refuses to run, clear the flag:

```bash
xattr -d com.apple.quarantine ~/.local/bin/latitude 2>/dev/null || true
```

**If no `PATH` location is writable and `sudo` isn't available**, leave the binary in place and invoke it by explicit path (still `chmod +x` it first):

```bash
chmod +x latitude-*/latitude
latitude-*/latitude --version
```

Verify: `latitude --version` (or the explicit path).

## Authentication

The credential is an **organization-scoped API key**, sent as `Authorization: Bearer <key>`. Two sources:

- **`LATITUDE_API_KEY` environment variable** — the CLI also **auto-loads a `.env` file** (searching the current directory and its parents) on startup, so a `LATITUDE_API_KEY=...` line in `.env` authenticates it. It's the same variable the telemetry SDK reads, so one `.env` entry covers both.
- **OS keyring** via `latitude auth login` (interactive).

**For agents and non-interactive use, put the key in `.env` (or export `LATITUDE_API_KEY`). Do not run `latitude auth login` / `auth logout`** — they touch the OS keychain and can block on a user prompt. A `.env` entry means you never have to prefix commands with `LATITUDE_API_KEY=… latitude …`.

Three footguns make `.env` silently *not* apply — all surface as `auth status` reporting `LATITUDE_API_KEY: missing` even though `.env` contains it:

- **Wrong directory.** `.env` is resolved from the current directory upward — run `latitude` from the app root or a subdirectory of it, never from `/tmp`, `$HOME`, or an unrelated path.
- **A shadowing process var.** The `.env` load does **not** override a variable already set in the environment, *including an empty one*. If the harness/shell exports `LATITUDE_API_KEY` (or `LATITUDE_BASE_URL`) as empty or stale, `.env` won't win. `unset` it first, or pass the value inline (`LATITUDE_API_KEY=… latitude …`).
- **An unquoted value with spaces, anywhere earlier in the file.** The CLI's `.env` parser (`dotenvy`) is **stricter than Node's `--env-file`**: **any** value containing spaces (or other special characters) **must be wrapped in quotes**, or the parser errors and **stops — silently dropping every variable defined *after* that line**, including `LATITUDE_API_KEY`. This is about the value, not the variable's name. A common culprit is a header/token value with a `Bearer ` space — whatever the app names it:

  ```dotenv
  # any spaced value must be quoted:
  EXAMPLE_HEADERS="Authorization=Bearer <token>, X-Other=value"
  ```

  The quotes are stripped by Node's `--env-file` and other loaders too, so one quoted `.env` works for both the app and the CLI. A `.env` the app tolerates can still break the CLI this way.

**Always verify auth right after configuring it** (neither command prints the key):

```bash
latitude auth status     # expect:  ✓ active   LATITUDE_API_KEY env var
latitude projects list   # any cheap authenticated read confirms the key actually works
```

If `auth status` shows `missing` for `LATITUDE_API_KEY`, you've hit one of the footguns above — fix the working directory, the shadowing var, or the unquoted line, then re-check before continuing.

## Self-hosted / on-premise

By default the CLI targets **Latitude Cloud** (`https://api.latitude.so`). If the user runs a **private / self-hosted** Latitude instance, point the CLI at that instance's API URL instead — preferably by setting `LATITUDE_BASE_URL` in `.env` alongside `LATITUDE_API_KEY`, so both load together and every command uses it. `--base-url <URL>` overrides it per-command if needed. Leave it unset for the hosted service.

## Discovering commands

Command **groups map 1:1 to API resources**; the exact set is generated from the spec. Discover it live:

```bash
latitude --help                       # list all command groups
latitude <group> --help               # list a group's methods (e.g. `latitude projects --help`)
latitude <group> <method> --schema    # machine-readable inputs/outputs for one command
```

**Agents: prefer `--schema` over `--help`.** `--schema` returns JSON (params, types, `location`, required set, output shape); `--help` returns human prose. Read the `--schema` of a command before calling it rather than guessing flags.

> The CLI ships a `latitude generate-skills` command that writes per-entity SKILL.md files. **Don't depend on its output** — it hardcodes whatever commands exist in that binary version and drifts as the API evolves. Use live `--schema`/`--help` discovery instead.

## Global flags (stable, not entity-specific)

These apply across commands and don't change as entities are added:

| Flag | Purpose |
| --- | --- |
| `--format <fmt>` | `json`, `table`, `yaml`, `csv`, `raw`, `jsonl`, `http`. Default: `table` on a TTY, `json` when piped. Use `--format json` for parsing. |
| `--query <JMESPath>` | Project/filter the response before formatting (e.g. `--query 'projects[].slug'`). |
| `--json <BODY\|->` | Request body for create/update ops (`-` reads stdin). |
| `--params <JSON>` | Path/query/body params as one JSON object (overrides individual flags). |
| `--page-all` / `--page-limit <N>` / `--page-delay <MS>` | Auto-paginate list endpoints (emits NDJSON). |
| `--dry-run` | Validate and print the request without sending it. |
| `--base-url <URL>` | Override the API base URL (also via `LATITUDE_BASE_URL`). |
| `--debug` | Dump the HTTP request/response to stderr. |
| `-q, --quiet` | Suppress stdout on success. |

## Common operations

Exact flags may differ by version — confirm with `<group> <method> --schema`. Representative:

```bash
latitude projects list                                   # list projects
latitude projects create --name "My Project"             # create (name → stable slug)
latitude projects delete --project-slug my-project       # delete by slug
latitude traces list --project-slug my-project --limit 50   # inspect incoming traces
```

Commands scoped to a project take the **project slug** (`--project-slug`), not the display name. Get slugs from `latitude projects list --format json`.

Endpoints that return **HTTP 204 No Content** (e.g. `projects delete`) have no body, so the CLI prints a placeholder like `{ bytes: 0, mimeType: text/plain, saved_file: download.txt, status: success }`. That `status: success` means the call succeeded — it is not an error or an actual file download.

To watch for traces after running instrumented code, poll `latitude traces list --project-slug <slug>` until the expected spans appear — there is no dedicated "tail" command; polling the list is the pattern.

## Secret handling

- **Never print the API key** in chat, logs, or committed files. Treat any `apiKey` value as a secret.
- **Best-effort transcript hygiene: keep keys out of your own conversation.** A key printed to stdout enters the transcript. For any command whose response contains a key (e.g. `account bootstrap --format json`), redirect it to a scratch file and extract only non-secret fields with `jq` — don't let the raw response print. Write the key into `.env` from the file (`printf 'LATITUDE_API_KEY=%s\n' "$(jq -r .apiKey file)" >> .env`), then delete the scratch file.
- Store the key in `.env` (ensure `.env` is gitignored) or the project's secret manager — never inline it into source or commit it.
- Don't `cat`/echo `.env` or paste raw command output that may contain the key; confirm auth with `latitude auth status` (which redacts it).
- If a command's output could include secrets, redact them before showing the user.
