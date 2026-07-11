# Dewey vendor key probes (metadata only)

Use after `op read` of a field. Print length + prefix class + HTTP status only. Never print the secret.

## Inventory fields without dumping values

```bash
op item get "Hermes Agent Secrets" --vault Dewey --format json \
  | python3 -c '
import json,sys
d=json.load(sys.stdin)
for f in d.get("fields",[]):
    v=f.get("value")
    has=bool(v)
    cls="none"
    if has:
        s=str(v).strip()
        for p in ("sk-or-","sk-ant-","xai-","fc-","bu_","ghp_","github_pat_"):
            if s.startswith(p): cls=p; break
        else:
            cls="uuid-like" if len(s)==36 and s.count("-")==4 else "other"
    print(f.get("label"), "has="+str(has), "len="+str(len(str(v)) if has else 0), "class="+cls)
'
```

Write JSON to a temp file, parse, then **unlink** the temp file so multi-secret dumps do not linger.

## Probe patterns

### EXA

```text
POST https://api.exa.ai/search
Authorization: Bearer <key>
{"query":"test","numResults":1}
expect 200
```

### Firecrawl

```text
GET https://api.firecrawl.dev/v1/team/credit-usage
Authorization: Bearer <key>
expect 200; may include remaining_credits
```

### Browser Use

```text
GET https://api.browser-use.com/api/v2/tasks
X-Browser-Use-API-Key: <key>
expect 200 JSON with items/totalItems
```

Do not use bare `Authorization: Bearer` for Browser Use discovery; v2 often returns `X-Browser-Use-API-Key header is required`.

### OpenRouter

```text
GET https://openrouter.ai/api/v1/auth/key
Authorization: Bearer <key>
expect 200
```

### xAI API key

```text
GET https://api.x.ai/v1/models
Authorization: Bearer <key>
expect 200
```

### GitHub PAT

```text
GET https://api.github.com/user
Authorization: Bearer <pat>
Accept: application/vnd.github+json
User-Agent: hermes-pat-check
expect 200 + login
```

## Map only after pass

```bash
hermes secrets 1password set EXA_API_KEY 'op://Hermes/Hermes Agent Secrets/EXA_API_KEY'
hermes secrets 1password set FIRECRAWL_API_KEY 'op://Hermes/Hermes Agent Secrets/FIRECRAWL_API_KEY'
hermes secrets 1password set BROWSER_USE_API_KEY 'op://Hermes/Hermes Agent Secrets/BROWSER_USE_API_KEY'
hermes secrets 1password set OPENROUTER_API_KEY 'op://Hermes/Hermes Agent Secrets/OPENROUTER_API_KEY'
hermes secrets 1password set XAI_API_KEY 'op://Hermes/Hermes Agent Secrets/XAI_API_KEY'
hermes secrets 1password sync
hermes secrets 1password status
```

Optional plugin enable after Firecrawl map:

```bash
hermes plugins enable web-firecrawl
```

New session required for plugin + secret injection to fully apply.