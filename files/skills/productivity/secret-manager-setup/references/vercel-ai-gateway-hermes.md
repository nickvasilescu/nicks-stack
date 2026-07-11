# Vercel AI Gateway with Hermes and 1Password

Use this when wiring Vercel AI Gateway into Hermes as a named OpenAI-compatible provider while keeping the existing default provider unchanged.

## Credential identity

- Runtime env var: `AI_GATEWAY_API_KEY`
- Vercel plaintext gateway keys are one-time secrets shaped like `vck_...`.
- Vercel API responses and dashboards also expose a key `id`, commonly UUID-shaped. The UUID is not usable as the bearer token.
- The create-key response distinguishes them as `apiKeyString` (secret) versus `id` (identifier). Vercel cannot reveal `apiKeyString` again after creation.

A 36-character UUID stored as the API key is a strong wrong-value signal. Do not map or trust it merely because the field exists.

## 1Password mapping

Example Dewey reference:

```bash
hermes secrets 1password set AI_GATEWAY_API_KEY \
  'op://Hermes/Hermes Agent Secrets/VERCEL_AI_GATEWAY_API_KEY'
rm -f ~/.hermes/cache/op_cache.json
hermes secrets 1password sync
hermes secrets 1password status
```

Never print the resolved secret. Metadata-only checks may report length, whether it matches UUID syntax, and whether it starts with the expected vendor prefix.

## Named Hermes provider

Vercel AI Gateway speaks OpenAI Chat Completions at `https://ai-gateway.vercel.sh/v1`. Configure it as an additional named provider instead of replacing the user's current default:

```bash
hermes config set providers.vercel-ai-gateway.name 'Vercel AI Gateway'
hermes config set providers.vercel-ai-gateway.base_url 'https://ai-gateway.vercel.sh/v1'
hermes config set providers.vercel-ai-gateway.key_env 'AI_GATEWAY_API_KEY'
hermes config set providers.vercel-ai-gateway.transport 'chat_completions'
```

The supported CLI is preferable when direct file tools refuse writes to security-sensitive Hermes configuration.

Use it without changing the default:

```bash
hermes chat --provider custom:vercel-ai-gateway --model <provider/model-id>
```

Inside an interactive session, named custom providers use the `custom:<name>:<model>` form.

## Validation sequence

1. Resolve the 1Password field and classify its shape without printing it.
2. Require a real authenticated generation request, not merely model discovery.
3. Run a Hermes one-shot request through `custom:vercel-ai-gateway`.
4. Run a small tool-calling request before declaring agent use operational.
5. Only then consider making it a default or fallback provider.

Important: `GET /v1/models` may return HTTP 200 even when the supplied credential is invalid. It is not a sufficient authentication smoke test. Validate with `POST /v1/chat/completions` using a currently listed model. A 401 saying to create/set `AI_GATEWAY_API_KEY`, combined with a UUID-shaped stored value, means the key ID was saved instead of the one-time `vck_...` secret.

## Recovery from a saved key ID

1. Create a new AI Gateway API key in Vercel.
2. Copy the one-time `vck_...` value immediately.
3. Replace the 1Password field value. Do not paste it into chat or logs.
4. Clear the Hermes 1Password cache.
5. Repeat the authenticated chat-completion and Hermes tool-call smokes.
