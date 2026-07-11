# Composio vs Hermes auth

## Rule

Composio manages its own OAuth/API-key connections and proxies tool calls. It does not export raw secrets for Hermes `secrets.onepassword` maps, `.env`, or `auth.json`.

## Mapping

| Need | Correct source |
|---|---|
| Hermes native Exa | EXA_API_KEY via 1Password |
| Hermes Firecrawl | FIRECRAWL_API_KEY + enable web-firecrawl |
| Hermes Browser Use | BROWSER_USE_API_KEY (header X-Browser-Use-API-Key) |
| Hermes Spotify | hermes auth spotify |
| Hermes Discord gateway | Discord bot token + intents (not Composio user OAuth) |
| Composio Discord/Exa/Firecrawl tools | Composio connection ACTIVE; use COMPOSIO tools |

Parallel paths are fine (Composio Exa and Hermes EXA_API_KEY at once).

## When user asks to fetch credentials from Composio

Answer no for raw keys. Either map keys from 1Password into Hermes, or use Composio tools as the access layer.
