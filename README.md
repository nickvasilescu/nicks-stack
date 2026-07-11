# Nick's Stack 🚀

A ready-to-go **Hermes AI agent** on an Orgo cloud computer — it texts you on **Telegram**, has its **own email inbox** (AgentMail) and **payment card** (AgentCard), answers **SMS / iMessage** (AgentPhone), runs your apps through **Composio**, traces every call to **Latitude**, operates Orgo computers (including itself), and keeps notes in **Obsidian**. You bring your own keys; **nothing here is shared or pre-filled — the template ships with zero secrets.**

Wired **exactly like Nick's live production agent** ("Dewey"), byte-for-byte from a full audit of that VM — same config, plugins, skills, and secret plane — with a **scan-a-QR** Telegram setup so you're chatting with your agent in about two minutes.

---

## What's in the box

| | |
|---|---|
| **Agent** | Hermes v0.18 (Nous) · model `gpt-5.5` (a ChatGPT/codex flip is documented) |
| **Chat** | Telegram — scan a QR on first boot, no BotFather |
| **Secrets** | a **1Password secret plane** — one service-account token resolves 19 keys at every start (`op://Hermes/Hermes Agent Secrets/…`) |
| **Apps** | Composio → Gmail, Slack, Calendar, Notion, +1000 |
| **Email** | AgentMail MCP — the agent's own inbox |
| **Cards** | AgentCard MCP — the agent completes the OAuth itself (baked runbook skill) |
| **Phone** | AgentPhone — MCP + a supervised **webhook bridge** (self-provisions a cloudflared tunnel; no polling cron) |
| **Tracing** | Latitude — an OTLP telemetry plugin *and* a chat-side MCP |
| **Self-operation** | Orgo MCP + 11 key-less local desktop-control tools (`orgo_desktop_*`) |
| **More MCP** | Linear (OAuth), X/Twitter, ideabrowser, vidiq — parked harmlessly until keys land |
| **Skills** | the 21-unit skill library from the live agent — setup runbooks for every integration above |
| **Notes** | Obsidian + a `HermesVault` the agent reads & writes |
| **Desktop** | branded wallpaper + one-click setup icon |

---

## 🟢 Easiest way to run it

1. **Make an Orgo account** → [orgo.ai](https://orgo.ai).
2. **Launch the template** (see *Run your own copy* below, or use the gallery entry if you're on the curated catalog).
3. On the desktop, the **Nick's Stack Setup** window walks you through:
   - **Connect Nous** (a quick sign-in — this is what lets `gpt-5.5` think; it even test-fires a 1-token call so a zero-credit account fails loudly).
   - **Scan the QR** with your phone → tap **Create Bot** in Telegram → your personal bot is live. 🎉
   - **Optional: paste a 1Password service-account token** — create vault `Hermes` → Secure Note `Hermes Agent Secrets` → fields named like the env vars, and every key resolves automatically from then on.
4. **Text your bot.** You're done.

**Optional power-ups** — add anytime by just telling the agent your key in chat, dropping it in the setup fields, or putting it in the 1Password note: Composio (`ck_…`), AgentMail (`am_…`), AgentPhone (the webhook bridge wakes itself on the next resume), Latitude, an Orgo API key, Linear (`hermes mcp login linear`), honcho memory. Parked integrations revive within 5 minutes of a key landing (or instantly via `/mcp` in chat).

> **Your keys stay yours.** They live only on *your* running computer (`~/.hermes/.env`, or your own 1Password vault) — never in this repo, the template, or anyone else's hands.

---

## 🛠️ Run your own copy

Publishing + building a template on Orgo needs a **Scale plan** (launching is any-paid-plan). Then it's one command each:

```bash
export ORGO_API_KEY=sk_live_...                 # orgo.ai → API keys

python3 build_template.py                        # assemble + validate locally
python3 build_template.py --build                # publish + build the golden image (streams to "ready")
python3 build_template.py --launch <WORKSPACE_ID># spin up a VM from it
```

### Make it yours
Everything is assembled from the plain files in [`files/`](files/):

- `config.yaml` — the Hermes config (model, 13 MCP servers, 16 plugins, the 1Password map)
- `SOUL.md` — the agent's personality (rigor contract, coding-agent routing, desktop control plane)
- `onboard.sh` / `telegram-pair.py` / `op-enable.py` — the first-boot setup
- `agentphone-bridge/` — the SMS/iMessage webhook bridge (supervised, dormant until keyed)
- `plugins/orgo-desktop-local/` + `scripts/` — the custom desktop-control plugin
- `local-packages/latitude-telemetry-hermes/` — the Latitude telemetry plugin (pip-installed at build)
- `skills/`, `vault/` — the skill library and the Obsidian vault

Edit those, bump the version, and rebuild:

```bash
VERSION=0.2.3 python3 build_template.py --build
```

`build_template.py` handles the full **publish → build → stream → launch** flow against the Orgo REST API (there are no template commands in the `orgo` CLI — REST is the path). The big file trees ship inside one deterministic base64 tarball — the publish endpoint caps the request body around 1 MB.

---

## FAQ

**Do I need to code?** No — the launch + QR flow is point-and-click. Coding only matters if you want to *modify* it.
**Where do my keys go?** Only onto your own VM (or your own 1Password vault). This repo and the template contain none.
**The model says it needs access?** `gpt-5.5` is a Nous model — make sure your Nous account has credits (the first-boot sign-in test-fires a call to check). Prefer ChatGPT? `hermes auth add openai-codex`, then set `model.default: gpt-5.6-sol` / `provider: openai-codex`.
**Why is 1Password off until I paste a token?** Without a token, the `op` CLI prompts interactively on every start — so the map ships disabled and flips on automatically the moment your token lands.
**Can I change the personality or model?** Yes — edit `SOUL.md` / `config.yaml` and rebuild (or just tell the agent).

---

MIT licensed. Hermes Agent is by [Nous Research](https://github.com/NousResearch/hermes-agent); Orgo is at [orgo.ai](https://orgo.ai).
