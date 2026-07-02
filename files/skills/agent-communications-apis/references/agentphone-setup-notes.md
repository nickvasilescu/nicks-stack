# AgentPhone setup notes

Condensed notes from a successful AgentPhone setup for an assistant-owned phone number.

## Documentation entry points

- Docs index: `https://docs.agentphone.ai/llms.txt`
- Base API URL: `https://api.agentphone.ai/v1`
- Useful markdown pages:
  - `https://docs.agentphone.ai/api-reference.md`
  - `https://docs.agentphone.ai/documentation/guides/agents.md`
  - `https://docs.agentphone.ai/documentation/guides/phone-numbers.md`
  - `https://docs.agentphone.ai/documentation/guides/messages.md`

## Authentication and request quirk

Use bearer auth and a real User-Agent. A bare Python `urllib` request without `User-Agent` returned `403` with `error code: 1010`; retrying the same endpoints with `User-Agent: Hermes-Agent/1.0` succeeded.

Do not persist API keys in skills or memory.

## Discovery endpoints

```http
GET /numbers?limit=100&offset=0
GET /agents
GET /agents/voices
```

Use discovery before creating anything, especially when the user says they already pay for an available number.

## Hosted assistant setup

When the user wants the phone number to be the assistant’s own phone and does not provide a webhook backend, create or reuse a hosted-mode agent.

Good request fields:

```json
{
  "name": "Hermes AgentPhone Assistant",
  "description": "Personal Hermes AI assistant for AgentPhone SMS and calls.",
  "voiceMode": "hosted",
  "enableMessaging": true,
  "systemPrompt": "You are Hermes, a concise and helpful AI assistant. Handle SMS and voice calls on behalf of the user. Be clear, useful, and ask for clarification when needed. Do not claim to be human.",
  "beginMessage": "Hi, this is Hermes, an AI assistant. How can I help?",
  "modelTier": "balanced",
  "sttMode": "fast",
  "ambientSound": "none",
  "denoisingMode": "noise-cancellation",
  "language": "en-US"
}
```

## Attach and verify

Attach:

```http
POST /agents/{agent_id}/numbers
Content-Type: application/json

{"numberId":"..."}
```

Verify:

```http
GET /agents/{agent_id}
GET /numbers?limit=100&offset=0
```

Expected successful final shape:

```json
{
  "agent_voiceMode": "hosted",
  "number_agentId": "<agent_id>",
  "number_voiceRouting": {"method": "agent"}
}
```

## Pitfalls

- AgentPhone may mask phone numbers in list responses, e.g. `+141****3597`. If the user remembers “415 or something,” do not require visible `+1415` prefix; choose the active unattached `+141...`/nearby number when that is the only available matching resource.
- Do not release/delete numbers as part of setup; release is irreversible.
- Prefer `number_id` for sending messages when a default has been saved, because exact `from_number` may be masked in API list output.
