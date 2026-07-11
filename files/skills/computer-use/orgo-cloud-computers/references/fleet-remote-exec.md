# Fleet remote exec patterns (REST)

## List computers

```bash
orgo computers list --json > /tmp/orgo_computers.json
# fields: id, name, status, project_id, …
# GET /api/computers may 405; CLI list works
```

## Exec Python on a computer

```text
POST https://www.orgo.ai/api/computers/{computer_id}/exec
Authorization: Bearer $ORGO_API_KEY
Content-Type: application/json

{"code": "<python source>", "timeout": 90}
```

Response often: `{success, output, error, …}`.

## Reliability pitfalls

1. **Hermes `terminal` rejects foreground shell `&` / nohup.** If the remote code string contains `&` (even inside a comment or dead branch), the local runner can refuse the whole call. Use `subprocess.Popen(..., start_new_session=True)` on the remote side instead.
2. **Long inline remote code can return empty `output` with `success: true`.** Prefer base64-encode a script, write `/tmp/job.py` on the remote, `subprocess.run([sys.executable, path], capture_output=True)`.
3. **Flush prints** on long jobs (`print(..., flush=True)` or line-buffered stdout).
4. **Do not retarget `ORGO_DEFAULT_COMPUTER_ID`** to a customer box during fleet audits; pass explicit computer IDs.

## Credential / presence probes

When auditing secrets, print only booleans, emails from JWT claims, statuses, token lengths — never access/refresh token values. See `secret-manager-setup/references/openai-codex-oauth-fleet-audit.md`.
