# Agentmail metal rules (Hermes Orgo templates)

Condensed from live builds through `default/hermes-orgo-desktop-local@0.3.4` and `default/agentmail-agent@0.2.4`.

## Do

- Install Hermes in `apps[].install` with:
  `--non-interactive --skip-setup --skip-browser`
- Stage files under `/opt/<pkg>/`, install after Hermes
- `build.apt` includes `xz-utils`
- Single terminal: `{name, title, description, cwd}` only
- Lean `on_first_boot` (stamp dirs; no hermes CLI; no tmux create)
- Bridge secrets in `on_resume` into `~/.hermes/.env`
- `hermes plugins enable … --no-allow-tool-override`
- Poll `GET .../build` until `status=ready` before launch
- Bump semver; prune old account versions

## Do not

- Long Hermes `curl|bash` inside `build.run` (often `not_built`)
- Terminal `run` field (especially `bash -l`) → black Web Terminal
- Interactive plugin enable prompts in golden/boot scripts
- Bake personal API keys into golden images
- Claim success from `auto_build: building` alone
- Skip post-launch `validate` / `which hermes`

## Black Web Terminal recovery

1. Restart the computer (rotates VNC password)
2. Hard-refresh the browser
3. Reopen Terminal

If `orgo-tmux-startup.sh` contains nested `send-keys bash -l`, republish without terminal `run`.
