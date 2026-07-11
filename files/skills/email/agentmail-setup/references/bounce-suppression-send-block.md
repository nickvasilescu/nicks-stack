# AgentMail bounce suppression (send block)

## Error shape

```text
MessageRejectedError
Status code: 403
Body: {"name":"MessageRejectedError","message":"Message rejected: Recipient(s) blocked: user@domain.com (bounced)"}
```

Means: AgentMail **did not attempt delivery**. Address is on the org **send block** list after a prior bounce, reject, or spam complaint.

Docs: https://docs.agentmail.to/knowledge-base/emails-bouncing.md · https://docs.agentmail.to/knowledge-base/api-403-error.md · https://docs.agentmail.to/lists.md

## Example (2026-07-09)

- Target: `michael@momentumamp.com`
- List entry: `GET /v0/lists/send/block/michael@momentumamp.com`
- Fields: `reason: bounced`, `direction: send`, `list_type: block`, `created_at: 2026-06-23T22:31:08.999Z`
- Domain-level block for `momentumamp.com` was **not** present (404)
- Fix: `DELETE` that entry → 204; re-GET 404; send from `${AGENTMAIL_INBOX}` succeeded with SES messageId

## API cheatsheet

```http
GET    /v0/lists/send/block
GET    /v0/lists/send/block/{email}
DELETE /v0/lists/send/block/{email}
GET    /v0/lists/receive/block
GET    /v0/metrics   # message.bounced, message.rejected, message.complained
```

Auth: `Authorization: Bearer $AGENTMAIL_API_KEY`

## Decision tree

1. Outbound 403 blocked/bounced? → GET send/block entry.
2. Reason bounced + address known good? → DELETE, resend, capture messageId.
3. Missing **inbound** message? → list inbox + receive/block. If other vendor mail lands, not suppression.
4. Still need delivery and AgentMail blocked? → operator Gmail fallback; document both paths.

## Do not

- Blame content/spam words first for this exact 403 string
- Conflate with himalaya app-password or gws OAuth failures on customer VMs
- Mass-delete the entire send/block list (230+ entries observed on one org)
