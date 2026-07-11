---
name: coding-agent-routing
description: "Use when choosing Hermes vs Claude Code / Codex / Grok Build for coding work, wiring multi-CLI specialist setup, or diagnosing specialist auth/availability on Dewey."
version: 1.3.2
author: Hermes Agent (Dewey)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Routing, Claude, Codex, Grok, Orchestration, Auth]
    related_skills: [claude-code, codex, grok, hermes-agent]
    created_by: agent
---

# Coding Agent Routing (Hermes = conductor)

Use this skill whenever a coding/refactor/PR/issue task could be done by Hermes tools **or** an external coding CLI, or when setting up/auth'ing those CLIs. Hermes is the only conductor. Claude Code, Codex CLI, and Grok Build are specialists (sibling processes).

## Architecture (two layers)

| Layer | What it is | Config / auth |
|-------|------------|----------------|
| **A. Hermes brain** | Model that runs Hermes (tools, memory, gateway) | `hermes model` / `~/.hermes/auth.json` |
| **B. Specialist CLI** | External coding agent Hermes spawns via terminal | Separate login per CLI; see `references/headless-cli-auth.md` |

Do not confuse them. Hermes `openai-codex` or `xai-oauth` does not log into `codex` or `grok` binaries.

## Rule 0 — Hermes alone by default

Do the work with Hermes file/terminal tools when:

- Ops, research, memory, messaging, MCPs, cron, multi-platform
- Small/surgical: ≤3 files, clear patch, roughly under 10 minutes
- Needs Hermes-only context (user memory, gateway UX, standing goals)
- Verification of someone else's work (`git diff`, tests)

**Do not** spawn a specialist for rename-one-function or "what does this file do?"

## When to spawn a specialist

Spawn when the job is multi-file / multi-turn agentic coding for ~5–40+ minutes and would bloat Hermes context.

| Job shape | Specialist | Headless invoke (preferred) |
|-----------|------------|-----------------------------|
| Careful large refactor, PR polish, high precision | **Claude Code** | `claude -p '…' --max-turns N` |
| Git feature builds, `codex review`, parallel issues | **Codex CLI** | `codex exec '…'` (git repo; `pty=true`) |
| SuperGrok coding quota, scratch without git, parallel Grok worker | **Grok Build** | `grok --no-auto-update -p '…'` |

If Claude/Codex are not authenticated **or** return usage-limit errors, fall back to **Grok Build** or Hermes alone. Never claim a specialist ran if auth/smoke failed.

**Codex usage limits:** Auth can succeed while inference fails with a ChatGPT/Codex usage-limit error. Treat as "specialist unavailable"; fall back; do not retry-loop until the stated reset time or credits land.

## Standing policy (this machine / Dewey)

Auth snapshot (verify with `claude auth status`, `codex login status`, `test -f ~/.grok/auth.json` if unsure):

- Claude Code: Claude Max (`nickv@testkey.com`) — preferred careful multi-file specialist
- Codex CLI: ChatGPT logged in — may hit usage limits; fall back if inference errors
- Grok Build: SuperGrok OAuth (`~/.grok/auth.json`) — default fallback / SuperGrok coding / no-git

1. **Conductor brain:** Hermes model stays as configured (often `xai-oauth` / Grok). Do not flip brain mid-task without user ask.
2. **Default coding solo (when a specialist is warranted):**
   - Prefer **Claude Code** for careful multi-file work
   - Prefer **Codex** for git-centric builds/reviews/batch issues when not usage-limited
   - Prefer **Grok Build** when xAI quota is the point, no git, or Claude/Codex unavailable
3. **One writer per dirty tree.** Parallel work → separate git worktrees.
4. **Verify always.** After any specialist: `git status`/`git diff`, tests if applicable. Specialist stdout is a self-report.
5. **Risk:** auth/payments/destructive → no yolo; tight allowed tools; Hermes reviews before commit/push.
6. **Low risk autonomous:** Claude skip-permissions (print mode preferred); Codex `--full-auto`; Grok `--always-approve`.

## Quick decision checklist

1. Hermes-only tools needed? → Hermes
2. Scope S (≤3 files)? → Hermes
3. Scope M/L agentic coding? → pick specialist by table
4. Multiple independent issues? → worktrees + one specialist each
5. Unsure? → one builds, Hermes reviews the diff

## Auth stores (do not confuse)

| Product | Auth | Powers |
|---------|------|--------|
| Hermes providers | `~/.hermes/auth.json` | Hermes brain only |
| Grok Build | `~/.grok/auth.json` | `grok` binary |
| Claude Code | Claude login / `CLAUDE_CODE_OAUTH_TOKEN` | `claude` binary |
| Codex CLI | `codex login` → `~/.codex` | `codex` binary |

Hermes `openai-codex` or `xai-oauth` credentials do **not** log into the specialist CLIs.

**Headless setup recipes** (device-auth, Claude FIFO paste, smokes): `references/headless-cli-auth.md`.

## Pre-flight before spawn

1. Binary on PATH (`command -v claude|codex|grok`).
2. Auth status / auth file present.
3. Optional cheap smoke; on usage-limit or auth error → fall back. Do not spin.

## Headless Claude auth (operator checklist)

When completing Claude login on headless hosts, follow `references/headless-cli-auth.md` (FIFO + `script`). Hard rules:

- Never inject an OAuth paste whose `#state` does not match the **live** waiter URL.
- Dead PKCE sessions cannot be revived; restart one clean waiter and give the user only that URL.
- `process submit` fails if background stdin is `/dev/null` — use the FIFO recipe, not bare background.
- SIGTERM notices for killed waiters are noise; only the live `state=` in `/tmp/claude-auth.out` counts.

## Project context

- Portable: `AGENTS.md` (cwd)
- Claude: `CLAUDE.md` / `.claude/`
- Hermes-only: `.hermes.md`
- Grok Build also reads CLAUDE.md / AGENTS.md

## Related skills

Load before orchestration: `claude-code`, `codex`, `grok`.

## Anti-patterns

- Two auto-approve agents on one dirty tree
- Specialist for a one-line fix
- Trusting "done" without reading the tree
- Assuming Hermes OAuth = CLI login
- Stacking brain=X and specialist=X for a 2-minute task
- Injecting a Claude OAuth code from a previous/killed login attempt
- Concurrent `claude auth login` waiters (wrong PKCE challenge)
- Retry-looping Codex after a usage-limit error

## Hermes control surfaces (not coding specialists)

Prefer **Hermes** UI over specialist desktops for agent hosts. Full decision table: `references/hermes-surfaces-vs-specialist-desktop.md`.

| Surface | When |
|---------|------|
| CLI / TUI / gateway | Default Dewey ops |
| `hermes dashboard --no-open --port 9119` | Visual config + embedded chat on Orgo (loopback; tunnel if remote) |
| `hermes desktop` | Optional Electron if user lives in Orgo GUI |
| Claude Desktop / Codex Desktop | Human preference only; **not** Hermes integration. Codex Desktop has no official Linux app. |

Dashboard: long-lived `background=true` daemon; ready log `HERMES_DASHBOARD_READY port=9119`; probe `curl … http://127.0.0.1:9119/`. On Orgo, **do not** claim the user can see it after only `browser_navigate` or CUA capture. Required path: `orgo-desktop doctor` (nonblack paint) → `orgo-desktop open-url http://127.0.0.1:9119` → `orgo-desktop screenshot` with nonblack pixels + window title (full recipe: `orgo-desktop-local` → `references/hermes-dashboard-on-orgo.md`). Surfaces decision table: `references/hermes-surfaces-vs-specialist-desktop.md`.

## Smoke script

```bash
bash ~/.hermes/skills/autonomous-ai-agents/coding-agent-routing/scripts/smoke-specialists.sh
```

Checks claude / codex (incl. usage-limit) / grok OAuth-only / dashboard :9119 without dumping secrets.

## References

- `references/headless-cli-auth.md` — device-auth + Claude FIFO PKCE (canonical auth cookbook)
- `references/hermes-surfaces-vs-specialist-desktop.md` — dashboard / Electron / Claude|Codex desktop decisions
- `scripts/smoke-specialists.sh` — board smoke (claude/codex/grok/dashboard)

## Success criteria

- Right layer used (Hermes vs specialist)
- Diff/tests verified by Hermes
- Concrete summary of files changed
- If auth/setup was involved: smoke or status proved the specialist is usable, not only logged in
