# Nick's Stack 🚀

A ready-to-go **Hermes AI agent** on an Orgo cloud computer — it texts you on **Telegram**, runs your apps through **Composio**, auto-replies to **SMS**, keeps notes in **Obsidian**, and more. You bring your own keys; **nothing here is shared or pre-filled — the template ships with zero secrets.**

Wired exactly like a real, working agent VM, with a **scan-a-QR** Telegram setup so you're chatting with your agent in about two minutes.


---

## What's in the box

| | |
|---|---|
| **Agent** | Hermes (Nous) · model `gpt-5.5` |
| **Chat** | Telegram — scan a QR on first boot, no BotFather |
| **Apps** | Composio (`x-consumer-api-key`) → Gmail, Slack, Calendar, Notion, +1000 |
| **Phone** | AgentPhone SMS / iMessage auto-responder |
| **Email** | AgentMail (via Composio, or a direct key) |
| **Cards** | AgentCard virtual cards |
| **Tracing** | Latitude observability |
| **Notes** | Obsidian + a `HermesVault` the agent reads & writes |
| **Desktop** | branded wallpaper + one-click setup icon |

---

## 🟢 Easiest way to run it

1. **Make an Orgo account** → [orgo.ai](https://orgo.ai).
2. **Launch the template** (see *Run your own copy* below, or use the gallery entry if you're on the curated catalog).
3. On the desktop, the **Nick's Stack Setup** window walks you through:
   - **Connect Nous** (a quick sign-in — this is what lets `gpt-5.5` think).
   - **Scan the QR** with your phone → tap **Create Bot** in Telegram → your personal bot is live. 🎉
4. **Text your bot.** You're done.

**Optional power-ups** — add anytime by just telling the agent your key in chat, or dropping it in the setup fields: a Composio consumer key (`ck_…`), an AgentPhone key (for SMS auto-replies), a Latitude key (to watch every call), an AgentCard account.

> **Your keys stay yours.** They live only on *your* running computer (`~/.hermes/.env`) — never in this repo, the template, or anyone else's hands.

---

## 🛠️ Run your own copy

Publishing + building a template on Orgo needs a **Scale plan** (launching is any-paid-plan). Then it's one command each:

```bash
export ORGO_API_KEY=sk_live_...                 # orgo.ai → API keys

python3 build_template.py                        # assemble + validate locally
python3 build_template.py --build                # publish + build the golden image (streams to "ready")
python3 build_template.py --launch <WORKSPACE_ID># spin up a VM from it
```

Prefer one file? **`nicks-stack.orgo.yaml`** is the entire template, self-contained and key-less — publish it directly if you don't want to run the script.

### Make it yours
Everything is assembled from the plain files in [`files/`](files/):

- `config.yaml` — the Hermes config (model, MCP servers, plugins)
- `SOUL.md` — the agent's personality
- `onboard.sh` / `telegram-pair.py` — the first-boot QR setup
- `seed-sms-cron.py` — the AgentPhone SMS auto-responder
- `skills/`, `plugins/`, `vault/` — bundled skills, the Latitude plugin, the Obsidian vault

Edit those, bump the version, and rebuild:

```bash
VERSION=0.1.2 python3 build_template.py --build
```

`build_template.py` handles the full **publish → build → stream → launch** flow against the Orgo REST API (there are no template commands in the `orgo` CLI — REST is the path).

---

## FAQ

**Do I need to code?** No — the launch + QR flow is point-and-click. Coding only matters if you want to *modify* it.
**Where do my keys go?** Only onto your own VM. This repo and the template contain none.
**The model says it needs access?** `gpt-5.5` is a Nous model — make sure your Nous account has it (the first-boot sign-in covers this).
**Can I change the personality or model?** Yes — edit `SOUL.md` / `config.yaml` and rebuild.

---

MIT licensed. Hermes Agent is by [Nous Research](https://github.com/NousResearch/hermes-agent); Orgo is at [orgo.ai](https://orgo.ai).
