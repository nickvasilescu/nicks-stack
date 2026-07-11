# Composio Discord Bot toolkit — what Discord must supply

Source: `https://docs.composio.dev/toolkits/discordbot` (toolkit slug DISCORDBOT).

## Critical

**Composio Managed App not available.** You bring your own Discord application. Composio does not host a shared bot for this toolkit.

## Auth scheme: OAuth2 (BYO props)

| Prop | Required | Discord Developer Portal mapping |
|---|---|---|
| `client_id` | yes | Application / OAuth2 Client ID |
| `client_secret` | yes | OAuth2 Client Secret |
| `bearer_token` | yes | **Bot token** (Bot → Reset/Copy Token) |
| `generic_id` | yes (schema string) | Treat as app identifier if the connect UI labels it; often Application ID again |
| `oauth_redirect_uri?` | optional | Redirect Composio shows during Connect → paste under Discord OAuth2 Redirects |
| `scopes?` | optional | Usually `bot` (+ often `applications.commands`) |

## Minimum bag for Connect

1. Bot token → `bearer_token`
2. Client ID → `client_id`
3. Client secret → `client_secret`

Then invite the bot to the target guild with needed intents/permissions. Smoke: `DISCORDBOT_TEST_AUTH` after connect.

## Distinctions

- **Discordbot** toolkit = bot automation (this note).
- **Discord** toolkit = user OAuth surface (different product).
- Composio connections still do **not** export raw tokens into Hermes `.env` / 1Password maps (see `composio-vs-hermes-auth.md`).

## UX note (Orgo)

When Nick wants to watch, open docs/dashboard headed via `orgo-desktop open-url`. Accordion OAuth2 panels often miss pixel clicks; re-measure or use DOM extract while keeping headed paint visible.
