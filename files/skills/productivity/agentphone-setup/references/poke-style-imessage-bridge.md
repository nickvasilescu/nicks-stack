# Poke-style iMessage bridge notes

Session-derived reference for making an AgentPhone inbound iMessage bridge feel messaging-native without destroying legibility.

## Architecture

```text
Inbound iMessage
  -> AgentPhone webhook
  -> local bridge
  -> one-shot `hermes chat -Q -m <model> --provider <provider> ...`
  -> AgentPhone `/v1/messages`
```

For webhook-mode AgentPhone agents, AgentPhone is mostly transport. The response model/settings are Hermes settings, not `modelTier` on the AgentPhone hosted voice agent.

## Per-bridge model override (CRITICAL: use CLI flags, not env vars)

Different model for iMessage than the global Hermes config. The bridge reads `AGENTPHONE_HERMES_MODEL` and `AGENTPHONE_HERMES_PROVIDER` from its env file and passes them as **CLI flags** (`-m` and `--provider`) to the `hermes chat` subprocess.

**PITFALL:** `HERMES_INFERENCE_MODEL` / `HERMES_INFERENCE_PROVIDER` env vars do NOT work for `hermes chat` mode. They only work for `hermes -z` (oneshot) and `hermes --tui`. If you set them as env vars on the subprocess, the bridge will silently fall back to the global config model, which means iMessage will report whatever model Telegram/CLI is using. This was a real bug observed in production: iMessage Dewey reported `z-ai/glm-5.2` (the Telegram model) instead of `deepseek/deepseek-v4-flash` because the env var was ignored.

Correct implementation — pass as CLI flags in the command construction:

```python
cmd = [hermes_bin, "chat", "-Q", "--source", "agentphone-bridge", "--max-turns", str(max_turns)]
bridge_model = CONFIG.get("AGENTPHONE_HERMES_MODEL", "")
if bridge_model:
    cmd.extend(["-m", bridge_model])
bridge_provider = CONFIG.get("AGENTPHONE_HERMES_PROVIDER", "")
if bridge_provider:
    cmd.extend(["--provider", bridge_provider])
cmd.extend(["-q", prompt])
```

Bridge env file:

```env
# In bridge env file (e.g. /root/.hermes_agentphone_bridge/env)
AGENTPHONE_HERMES_MODEL=deepseek/deepseek-v4-flash
AGENTPHONE_HERMES_PROVIDER=openrouter
```

This only affects the iMessage bridge subprocess. CLI, gateway (Telegram, Discord, etc.), and other surfaces keep using the global model from `config.yaml`. The `hermes_start` log event includes the model and provider override values for verification.

To find available models on OpenRouter:

```bash
curl -s https://openrouter.ai/api/v1/models | python3 -c "
import sys,json
data=json.load(sys.stdin)
for m in data.get('data',[]):
    if 'deepseek' in m['id'].lower():
        print(m['id'], '-', m.get('name',''))
"
```

To verify which model the bridge is actually using, check `events.log` for `hermes_start` entries with the `model` field, AND send a test iMessage asking "what model are u running?" — the response should match the override, not the global config model.

## Reasoning effort and service tier

Do not hard-code a reasoning level into the bridge recipe. Set the user's requested global defaults with supported Hermes config keys:

```bash
hermes config set agent.reasoning_effort high   # none|minimal|low|medium|high|xhigh
hermes config set agent.service_tier fast
```

A bridge that launches a fresh default-profile `hermes chat` subprocess for each inbound message inherits these values from `config.yaml`. Model/provider CLI overrides (`-m`, `--provider`) do not independently lower reasoning or disable the fast tier. Do not invent an `AGENTPHONE_HERMES_REASONING_EFFORT` variable unless the bridge code explicitly implements and tests it.

Important distinctions:

- `display.show_reasoning: false` hides reasoning text in the interface; it does not disable model reasoning.
- A raw config value of `none`, `false`, or `disabled` disables reasoning. An unset value falls back to Hermes/provider defaults.
- `service_tier: fast` is the user-facing Hermes setting. Provider request construction may normalize it to the provider's priority-tier wire value.
- Reasoning and service-tier support is provider/model dependent. OpenAI Codex Responses models consume these settings; a non-OpenAI OpenRouter model may ignore or translate them differently.

Verification must test effective loading, not merely inspect YAML:

1. Load the active Hermes config and pass `agent.reasoning_effort` through `parse_reasoning_effort`; confirm the expected enabled/effort mapping.
2. Start a new one-shot Hermes process using the same profile, model, and provider as the bridge and require an exact smoke-test response.
3. Confirm the bridge env has no lower per-process override and that its command does not select another profile.
4. For fresh-process bridges, no bridge restart is needed after changing these defaults; the next inbound message loads them. Long-lived gateway or CLI sessions may require `/new`, `/restart`, or relaunch.

## Poke-style tiers

1. **Smart ack**: send a short working ack only for task-like messages, not casual chatter.
2. **Typing keepalive**: send typing indicators during long tasks.
3. **Final reply chunking**: split conversational status replies into 2-3 readable bubbles.
4. **Progress update**: at most one extra generic progress text after a long delay, e.g. ~45s.
5. **Interruption**: a new inbound message in the same conversation cancels/suppresses the stale Hermes run.
6. **Reactions**: use iMessage reactions for trivial closers like `haha`, `nice`, or `thanks` when supported.

## Acks: generic only (CRITICAL user preference)

**Use generic acks only. Do NOT attempt keyword extraction from the user's message.**

### Why keyword extraction was rejected

An earlier iteration used regex-based keyword extraction to build "contextual" acks like `checking github repo now` or `digging into that email`. This was rejected after repeated production failures:

- `looking into youre on agentphone imessage` — extracted second-person pronouns from "go double check youre on agentphone imessage"
- `on it, anything` — extracted "anything" from "you dont need to do anything just curious"
- `pulling up have` — extracted "have" from "do u have a connector to doordash?"
- `on it, sure` — extracted "sure" from "are u sure you know what model youre running?"

The fundamental problem: regex-based NLU is fragile. No matter how many guards, stop words, and patterns you add, there will always be messages where extraction produces word salad. The ack's job is to say "I got your message, I'm working on it." That's it. The contextual connection comes from Dewey's actual answer naturally referencing what was asked.

### Correct implementation

Static generic acks, no keyword extraction, no templates with placeholders:

```python
ACK_TEMPLATES = [
    "on it",
    "checking now",
    "looking into it",
    "yep, give me a sec",
    "digging in",
]

PROGRESS_TEMPLATES = [
    "still working on it",
    "still checking, taking a bit",
    "verifying before i answer",
]

def pick_ack(lines: list[str], last: list[str]) -> str:
    """Pick a random ack line, avoiding repeating the last one."""
    available = [l for l in lines if l != last[0]] or lines
    return random.choice(available)
```

### Key rules

- **Never fully disable acks** unless the user explicitly asks. Users like the conversational feel.
- **Never use keyword extraction** — it produces word salad. Generic acks are always safe.
- **Progress messages should also be generic** — same static list, no keyword injection.
- **Interruption acks stay as `got it, switching`** — that's already contextual (it references the act of switching tasks).
- **Suppress normal ack when interruption ack was sent** — don't send both `got it, switching` and `on it` for the same replacement request.

## False failure vs real failure

If the user only sees “Hermes hit an internal error while generating a reply,” check `events.log` for `hermes_failed` and `returncode` before blaming webhooks or models. SIGABRT (`-6`) after a successful `Turn ended` is often cleanup abort with a good answer discarded. Full diagnostic + bridge stdout-recovery fix: `references/hermes-bridge-false-failure.md`.

## Final reply chunking

- Split conversational status replies into 2-3 readable bubbles.
- Min chars ~120, target ~160, max chunks 3.
- Split at sentence/paragraph boundaries only.
- Do **not** split copyable artifacts. Drafted emails, drafted texts, code, tables, structured outputs, and anything the user may paste elsewhere should stay as one bubble even if long.
- Detect copyable drafts with patterns like `i'd send:`, `i'd reply:`, `draft:`, `reply:`, `Subject:`, `To:`, or greeting+signoff structures such as `Hey Name, ... Nick`.
- Keep chunking semantic. Never split URLs, code fences, markdown tables, or a sentence fragment just because a character threshold fired.

## Verification recipe

Use synthetic tests that do not send real messages:

- A screenshot-style short conversational answer should split into 2 bubbles.
- A copyable email draft with greeting and signoff should return `1` chunk.
- A code block or table should return `1` chunk.
- Starting a second job for the same conversation should mark the old job cancelled, terminate its fake subprocess, and set `interrupted_previous=True` on the new job.
- `should_send_ack({... '_skip_ack': True})` should return `False` with reason `already-interrupted-ack`.
- Verify acks never produce word salad: `pick_ack` should always return one of the static strings.
- Mock subprocess that prints a good final reply then exits `-6` or `1` should still deliver the good reply once stdout recovery is implemented (see `references/hermes-bridge-false-failure.md`).

Then restart and verify:

```bash
supervisorctl restart agentphone-bridge
supervisorctl status agentphone-bridge
curl -fsS https://<bridge-host>/health
```

Also run AgentPhone webhook test if MCP is available.
