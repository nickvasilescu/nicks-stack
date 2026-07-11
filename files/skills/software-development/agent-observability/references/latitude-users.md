# Latitude user identity for Hermes traces

Session-derived detail from configuring the Orgo `dewey` Latitude project.

## Symptom

Latitude Users page can show:

> No users yet. Attach user IDs to traces to understand each customer's activity, sessions, and errors.

This does not require creating a user record in Latitude. It means the ingested traces have `userId: null`.

Verified via Latitude MCP:

- `getUsersOverview(projectSlug="dewey")` initially returned `uniqueUsers: 0`, `identifiedTraces: 0`, `identifiedSessions: 0` while traces/sessions existed.
- `listTraces(projectSlug="dewey")` showed recent traces with `userId: null`.

## Official Latitude pattern

Latitude docs describe users as trace metadata. Send a stable user id at the request/agent-turn boundary:

- TypeScript SDK option: `userId: user.id`, optionally `userEmail: user.email`
- Python SDK option: `{"user_id": user.id, "user_email": user.email}`

For raw OTLP/Hermes plugin traces, add conventional span attributes that Latitude can lift into trace-level user fields:

```text
user.id=<stable id>
user.email=<email when known>
user.name=<display name when known>
enduser.id=<same stable id, compatibility alias>
```

## Hermes-specific implementation used

For the installed `latitude_telemetry_hermes` package, add env-driven user config and attach it to the root interaction span and child context spans.

Env vars used:

```bash
LATITUDE_USER_ID=${OWNER_EMAIL}
LATITUDE_USER_EMAIL=${OWNER_EMAIL}
LATITUDE_USER_NAME="Nick Vasilescu"
```

Code locations patched in the Hermes venv:

```text
/usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages/latitude_telemetry_hermes/config.py
/usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages/latitude_telemetry_hermes/builder.py
```

Implementation shape:

- `config.py` reads `LATITUDE_USER_ID`, `LATITUDE_USER_EMAIL`, and `LATITUDE_USER_NAME` into `_config()`.
- `builder.py` adds `_Builder._user_attrs()` returning `user.id`, `user.email`, `user.name`, and `enduser.id`.
- `_start_run()` merges `_user_attrs()` into the root `interaction` span attrs.
- `_context()` merges `_user_attrs()` into child span context attrs.

## Verification recipe

1. Compile patched files:

```bash
/usr/local/lib/hermes-agent/venv/bin/python -m py_compile \
  /usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages/latitude_telemetry_hermes/config.py \
  /usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages/latitude_telemetry_hermes/builder.py
```

2. Emit a synthetic plugin trace or real `hermes chat -q` smoke trace after sourcing `/root/.hermes/.env`.

3. Verify via Latitude MCP:

```text
listUsers(projectSlug="dewey")
getUsersOverview(projectSlug="dewey")
listTraces(projectSlug="dewey", limit=5)
```

Expected readback after the fix:

```text
listUsers: userId ${OWNER_EMAIL}, userEmail ${OWNER_EMAIL}, traceCount > 0
getUsersOverview: uniqueUsers >= 1, identifiedTraces >= 1, identifiedSessions >= 1
listTraces: newest trace has userId ${OWNER_EMAIL}
```

Observed validation in this session:

```text
uniqueUsers: 1
identifiedTraces: 2
totalTraces: 19
identifiedSessions: 2
totalSessions: 14
userId: ${OWNER_EMAIL}
userEmail: ${OWNER_EMAIL}
```

## Caveats

- Old traces are not backfilled; only future traces include user identity.
- A running Hermes process may have cached the old plugin/config. Start a new Hermes session or restart Hermes to guarantee user tagging.
- Patching inside `/usr/local/lib/hermes-agent/venv/.../site-packages` is not update-safe. A Hermes or plugin upgrade may overwrite it; prefer upstreaming this env-driven user-id support or keeping a small reapply patch under the observability setup notes.
- Choose a stable identifier deliberately. For a single-user personal Hermes VM, an email like `${OWNER_EMAIL}` is reasonable. For multi-user gateway deployments, do not hardcode the owner email for every trace; derive the user id from the platform/user context instead.
