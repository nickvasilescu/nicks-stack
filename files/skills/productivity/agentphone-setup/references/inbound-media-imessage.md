# AgentPhone inbound media and iMessage image troubleshooting

Session-derived reference for debugging cases where a user sends an image over iMessage and Hermes replies as if it received an empty message.

## Durable finding

AgentPhone represents image-only inbound messages as an `agent.message` event whose text/body may be empty while media is carried in a media field.

Authoritative docs observed on `https://docs.agentphone.ai/documentation/guides/messages.md` and `.../webhooks.md` state:

- SMS, MMS, and iMessage all arrive as unified `agent.message` events.
- Inbound message data includes `message` plus `mediaUrl`.
- For image/video/file messages, `mediaUrl` points to hosted media.
- `body`/`message` may be empty when only media was sent.
- Multiple iMessage carousel images may arrive as separate messages, each with its own `mediaUrl`.
- SMS images arrive as `channel: "mms"`.

Representative webhook shape:

```json
{
  "event": "agent.message",
  "channel": "imessage",
  "data": {
    "conversationId": "conv_...",
    "from": "+155...",
    "to": "+155...",
    "message": "",
    "mediaUrl": "https://storage.googleapis.com/inbound-file-store/abc123_IMG_5414.png",
    "direction": "inbound",
    "receivedAt": "2025-01-15T12:01:00Z"
  }
}
```

## Failure mode

If an inbound bridge extracts only text fields such as `message`, `messageBody`, `transcript`, or `reactionType`, it will reduce an image-only iMessage to an empty inbound text. Hermes will then see no image and may answer “didn’t get anything.”

A working AgentPhone/iMessage pipeline can therefore still fail at the local bridge layer even when:

- the AgentPhone number is active and type `imessage`,
- per-agent webhook registration is active,
- the AgentPhone conversation history records an inbound message at the image-send time,
- bridge logs show `agent.message` with empty text.

## Bridge implementation checklist

When handling `agent.message`, extract and preserve media fields in addition to text:

- `data.mediaUrl`
- `data.media_url`
- `data.mediaUrls`
- `data.media_urls`
- optionally message-history variants: `mediaUrl`, `mediaUrls`, `media_url`, `media_urls`

Normalize to a list of strings, e.g. `media_urls: list[str]`.

Pass media to Hermes explicitly in the one-shot prompt:

```text
Inbound media URLs:
- https://...

If media URLs are present, inspect them with vision/image tools before replying.
```

For robustness, prefer downloading each media URL to a local cache first and pass local file paths to Hermes, because hosted URLs can be signed or expire.

## Logging guidance

Do not log raw signed media URLs by default. Log safe metadata:

- media present: true/false
- media count
- channel
- message id
- maybe host and a URL hash

If debugging a live issue, temporarily log a redacted raw payload or a sanitized payload that keeps `mediaUrl` host and extension but strips query parameters/tokens.

## Verification recipe

1. Send a text-only iMessage and confirm normal bridge behavior.
2. Send a single image-only iMessage.
3. Confirm webhook logs show `media_count > 0`, not just empty text.
4. Confirm Hermes prompt includes media URL/path.
5. Confirm Hermes uses vision/image analysis and replies about the image.
6. Send a multiple-image iMessage carousel and verify either multiple events or multiple media URLs are handled.

## Avoid this incorrect diagnosis

Do not conclude “iMessage did not work” just because inbound text is empty. For media-only iMessage/MMS, empty text plus `mediaUrl` is expected.