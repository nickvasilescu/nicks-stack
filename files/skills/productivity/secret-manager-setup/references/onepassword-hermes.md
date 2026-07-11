# 1Password + Hermes setup notes

This reference captures the reusable setup pattern for enabling Hermes to resolve secrets from 1Password on a headless Linux VM.

## What to check first

```bash
hermes secrets --help
hermes secrets 1password --help
hermes secrets 1password status
command -v op && op --version
```

If `op` is missing on Ubuntu/Debian amd64, install the 1Password CLI:

```bash
install -d -m 0755 /etc/apt/keyrings
curl -fsS https://downloads.1password.com/linux/keys/1password.asc \
  | gpg --dearmor -o /etc/apt/keyrings/1password-archive-keyring.gpg
printf '%s\n' 'deb [arch=amd64 signed-by=/etc/apt/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/amd64 stable main' \
  > /etc/apt/sources.list.d/1password.list
apt-get update
apt-get install -y 1password-cli
op --version
```

Then enable Hermes integration:

```bash
hermes secrets 1password setup --binary-path "$(command -v op)"
hermes secrets 1password status
```

## Authentication choice

For long-running Hermes on a server, ask for a 1Password service-account token and use:

```bash
hermes secrets 1password setup --token '<OP_SERVICE_ACCOUNT_TOKEN>'
```

If passing a token through shell commands, disable xtrace (`set +x`) and avoid echoing it. The Hermes setup command stores it in `.env` as `OP_SERVICE_ACCOUNT_TOKEN`; verify file permissions remain restrictive, e.g. `stat -c '%a %U:%G %n' ~/.hermes/.env` should usually show `600`.

Interactive `op signin` is weaker for this class because sessions expire after inactivity. Use it for quick local testing or when the user explicitly chooses it.

Verify the service-account token actually works and inspect accessible vaults:

```bash
set -a; . ~/.hermes/.env; set +a
op whoami --format json
op vault list --format json
```

Service accounts cannot access 1Password Personal/Private vaults. If no usable vault appears, ask the user to create a shared/custom vault and grant the service account at least `read_items`. To let the agent create a new Hermes item from existing `.env` secrets, grant `read_items,write_items` during setup.

## Safe reads (never dump full items)

**Do not** run `op item get … --format=json` for verification when the item holds many secrets — the full JSON prints every field value into the transcript.

Prefer single-field reads and **metadata only** (length, prefix class, never the secret):

```bash
python3 - <<'PY'
import json, subprocess, urllib.request
t = subprocess.check_output(
    ["op", "read", "op://Hermes/Hermes Agent Secrets/GITHUB_PAT"],
    text=True,
).strip()
print("len", len(t))
print("prefix", "ghp_" if t.startswith("ghp_") else "github_pat_" if t.startswith("github_pat_") else "other")
req = urllib.request.Request(
    "https://api.github.com/user",
    headers={
        "Authorization": f"Bearer {t}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "hermes-pat-check",
    },
)
with urllib.request.urlopen(req, timeout=20) as r:
    body = json.loads(r.read().decode())
    print("http", r.status, "login", body.get("login"))
PY
```

## Validating new secrets before mapping

Field presence ≠ correct value. Common failure: user adds `GITHUB_PAT` but pastes a UUID / Latitude key / wrong secret (len 36, no `ghp_` / `github_pat_` prefix) → GitHub 401.

**Before** `hermes secrets 1password set`:

1. `op read` the reference successfully.
2. Check shape metadata (prefix + length), not the secret text.
3. Call the vendor API with the secret and require success (GitHub: `GET /user` → 200).
4. Only then map + `hermes secrets 1password sync`.

Do **not** map a secret that fails the vendor auth test.

## GitHub PAT (Dewey / Hermes Agent Secrets)

| Env var | Reference |
|---|---|
| `GITHUB_TOKEN` | `op://Hermes/Hermes Agent Secrets/GITHUB_PAT` |
| `GH_TOKEN` | same (for `gh` CLI if installed later) |

```bash
hermes secrets 1password set GITHUB_TOKEN 'op://Hermes/Hermes Agent Secrets/GITHUB_PAT'
hermes secrets 1password set GH_TOKEN 'op://Hermes/Hermes Agent Secrets/GITHUB_PAT'
hermes secrets 1password sync
hermes secrets 1password status
```

Expected shapes: classic PAT `ghp_…` (~40 chars); fine-grained `github_pat_…` (much longer). Prefer field type **Concealed**.

If `gh` is not installed, Composio `github` may still be connected (API actions only; not a full substitute for local `git push`).

## Creating a 1Password item from existing `.env` secrets

If the user chooses “create item from current Hermes `.env`”, avoid putting secret values in shell argv. Generate a JSON item template on stdin and pipe it into `op item create`:

```bash
set -euo pipefail
set -a; . ~/.hermes/.env; set +a

python3 - <<'PY' | op item create --vault Dewey - --format json > /tmp/hermes_1p_item.json
import json
from pathlib import Path
keys = ['LATITUDE_API_KEY','ORGO_API_KEY','TELEGRAM_BOT_TOKEN','AGENTMAIL_API_KEY','AGENTPHONE_API_KEY']
vals = {}
for line in Path.home().joinpath('.hermes/.env').read_text(errors='ignore').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        if k in keys and v:
            vals[k] = v
item = {
    'title': 'Hermes Agent Secrets',
    'category': 'SECURE_NOTE',
    'fields': [
        {'id':'notesPlain','type':'STRING','purpose':'NOTES','label':'notesPlain','value':'Hermes Agent API keys migrated from ~/.hermes/.env.'}
    ],
}
for k in keys:
    if k in vals:
        item['fields'].append({'id': k, 'type': 'CONCEALED', 'label': k, 'value': vals[k]})
print(json.dumps(item))
PY
```

Then map and verify each field:

```bash
for k in LATITUDE_API_KEY ORGO_API_KEY TELEGRAM_BOT_TOKEN AGENTMAIL_API_KEY AGENTPHONE_API_KEY; do
  ref="op://Hermes/Hermes Agent Secrets/${k}"
  op read "$ref" >/dev/null
  hermes secrets 1password set "$k" "$ref"
done
hermes secrets 1password sync
hermes secrets 1password status
```

Keep raw `.env` copies until you verify every non-Hermes service that may source `.env` directly.

## Mapping references

1Password secret reference format:

```text
op://Vault Name/Item Name/Field Name
```

```bash
hermes secrets 1password set ORGO_API_KEY 'op://Automation/Hermes Agent/ORGO_API_KEY'
hermes secrets 1password set AGENTMAIL_API_KEY 'op://Automation/Hermes Agent/AGENTMAIL_API_KEY'
hermes secrets 1password set AGENTPHONE_API_KEY 'op://Automation/Hermes Agent/AGENTPHONE_API_KEY'
hermes secrets 1password set LATITUDE_API_KEY 'op://Automation/Hermes Agent/LATITUDE_API_KEY'
hermes secrets 1password set TELEGRAM_BOT_TOKEN 'op://Automation/Hermes Agent/TELEGRAM_BOT_TOKEN'
```

Verify before removing local `.env` copies:

```bash
op read 'op://Automation/Hermes Agent/ORGO_API_KEY'
hermes secrets 1password sync
hermes secrets 1password status
```

Use `sync --apply` only when you need to export resolved values into the current shell.

## User-facing clarification

If the user provides a snippet like this:

```sshconfig
Host *
  IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
```

Explain directly that this is the 1Password SSH agent for local SSH private keys. It does not authenticate the Linux VM or give Hermes access to API-key secrets. For Hermes secrets, request a service-account token and `op://...` references.

## Completion criteria

Setup is complete only when all are true:

- `op --version` works.
- `hermes secrets 1password status` shows enabled.
- A valid authentication path exists, preferably `OP_SERVICE_ACCOUNT_TOKEN` for headless use.
- At least one required env var is mapped to an `op://...` reference.
- `hermes secrets 1password sync` or `op read` proves the mapped reference resolves.
- For newly added secrets: **vendor API auth test passed** before mapping.
- If raw `.env` secrets were removed, a fresh Hermes process still starts and resolves them.
