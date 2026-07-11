# AgentPhone outbound media (Hermes → iMessage)

## Durable finding

Hermes emits local media delivery markers such as:

```text
MEDIA:/tmp/agentphone-media/example.png
```

That works natively on Telegram. AgentPhone `POST /v1/messages` does **not** accept local filesystem paths. It requires:

- `media_url` for a single public HTTPS URL, **or**
- `media_urls` for multiple URLs (carousel)

Providing **both** `media_url` and `media_urls` returns HTTP 400:
`Provide either media_url or media_urls, not both`.

## Failure mode (observed 2026-07-09)

Bridge sent only:

```json
{"to_number": "...", "body": "... MEDIA:/tmp/..."}
```

API responses showed `"media_urls": []`. Users received the literal `MEDIA:` string, not an image.

## Working bridge behavior

1. Parse Hermes final text for:
   - whole-line `MEDIA:/abs/path`
   - inline `MEDIA:` tokens
   - markdown images `![](url_or_path)`
   - whole-line bare image URLs
2. Strip those tokens from the text body.
3. For local paths: copy into bridge cache, serve under `PUBLIC_URL/media/{token}/{name}`.
4. Call AgentPhone with `media_url` (one file) or `media_urls` (many), never both.
5. Attach media on the first reply bubble only.

## Verification

1. Generate or use a local PNG under `/tmp/agentphone-media/`.
2. Simulate Hermes output with a `MEDIA:` line.
3. Confirm bridge log `reply_sent` has non-empty `media_urls` / response media.
4. Confirm `media_served` when AgentPhone fetches the public URL.
5. Confirm iMessage shows an image attachment, not a `MEDIA:` path string.

## Docs

- https://docs.agentphone.ai/documentation/guides/messages.md
