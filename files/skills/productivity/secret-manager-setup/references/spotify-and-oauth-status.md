# Spotify + provider OAuth status checks

## Spotify

```bash
hermes tools list | rg -i spotify
hermes plugins list --enabled --plain | rg spotify
hermes auth status spotify
```

Tools gate on `_check_spotify_available()` → `get_auth_status("spotify").logged_in`.
Pre-auth logs `check_fn _check_spotify_available returned False` are expected until OAuth completes.

After login:
- Empty devices / empty playback = open Spotify app (Connect target), not broken auth.
- Free: search/library/playlists. Premium: play/pause/skip/volume/queue.

Client ID: HERMES_SPOTIFY_CLIENT_ID. Tokens: auth.json providers.spotify.

## OpenAI Codex vs Anthropic

```bash
hermes auth status openai-codex   # ChatGPT OAuth; often already logged in
hermes auth status anthropic      # may be logged out even if anthropic-provider enabled
```

Do not demand OPENAI_API_KEY / ANTHROPIC_API_KEY when user intends OAuth and status is (or can be) logged in.
