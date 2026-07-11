# Dewey Orgo Session Notes

Session-specific detail from configuring the user's Orgo setup. This reference supplements the class-level Orgo skill; do not paste secrets from this file into chat or config.

## Target Computer

```text
name: Dewey
workspace: Minions
computer_id: ef2f6e29-3864-494b-a82c-15280c5d9f9e
os: linux
cpu: 8
ram_gb: 32
expected status: running
```

## CLI Setup Observed

```bash
curl -fsSL https://orgo.ai/install.sh | bash
export PATH="$HOME/.local/bin:$HOME/.orgo/node/bin:$PATH"
orgo --version
orgo computers list
```

Observed installed CLI:

```text
/root/.local/bin/orgo
orgo 2.0.3
```

The installer may also place Node/npx under:

```text
/root/.orgo/node/bin/npx
```

Persist PATH for the CLI with:

```bash
line='export PATH="$HOME/.local/bin:$PATH"'
grep -Fqx "$line" /root/.bashrc 2>/dev/null || printf '\n# Orgo CLI\n%s\n' "$line" >> /root/.bashrc
```

## Secret-Safe Hermes Env Pattern

Save the API key and default target in `/root/.hermes/.env` without printing the key:

```text
ORGO_API_KEY=***
ORGO_DEFAULT_COMPUTER_ID=ef2f6e29-3864-494b-a82c-15280c5d9f9e
```

## MCP Setup Used

Local stdio MCP command:

```bash
hermes mcp add orgo \
  --command npx \
  --env 'ORGO_API_KEY=${ORGO_API_KEY}' ORGO_DEFAULT_COMPUTER_ID='${ORGO_DEFAULT_COMPUTER_ID}' \
  --args -y github:nickvasilescu/orgo-mcp
```

Result observed:

```text
Connected! Found 28 tool(s) from 'orgo'
Saved 'orgo' to ~/.hermes/config.yaml
```

Config shape:

```yaml
mcp_servers:
  orgo:
    command: npx
    args:
      - -y
      - github:nickvasilescu/orgo-mcp
    env:
      ORGO_API_KEY: ${ORGO_API_KEY}
      ORGO_DEFAULT_COMPUTER_ID: ${ORGO_DEFAULT_COMPUTER_ID}
    enabled: true
```

Hosted alternative provided by user:

```text
https://orgo-mcp.onrender.com/mcp
```

Prefer local stdio when available because it tested cleanly and uses local env interpolation.

## Verification Outputs To Reproduce

CLI verification:

```text
orgo path: /root/.local/bin/orgo
orgo version: 2.0.3
Dewey    Minions    running    8 vCPU    32 GB
```

MCP verification:

```text
orgo_doctor ok: true
auth source: env:ORGO_API_KEY
api reachable: true
status_code: 200
```

Computer readback:

```text
id: ef2f6e29-3864-494b-a82c-15280c5d9f9e
name: Dewey
os: linux
cpu: 8
ram: 32
status: running
```

## Practical Rule

Before taking action on Dewey, first list/read the computer and confirm the target is the Minions workspace Dewey, not another similarly named Orgo machine.
