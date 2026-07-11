# HermesBible Obsidian / Knowledge Vault Patterns

Condensed from an in-session review of HermesBible community flows. HermesBible is unofficial; use official Hermes docs for commands/config. These notes capture practical vault patterns worth reusing.

## Sources Consulted

- `https://hermesbible.com/flows/index-md-folder-structure-faster-hermes-agent`
- `https://hermesbible.com/flows/my-hermes-and-obsidian-setup-and-use-cases`
- `https://hermesbible.com/flows/context-os-for-hermes-agent`
- `https://hermesbible.com/flows/3-agent-research-department-notebooklm-obsidian`
- `https://hermesbible.com/tags/obsidian`

## INDEX.md / Folder Structure Flow

Main thesis: agents do not navigate folders like humans. A folder structure without maps forces the agent to open wrong files and burn context on navigation.

Reusable rules:

1. Put an `INDEX.md` at the root of each major folder.
2. Use one concern per folder rather than broad content-type buckets.
3. Number folders/files to indicate reading order.
4. Keep index files short: subfolders, canonical files, and where to start.
5. Do not create `INDEX.md` in every tiny folder; too many maps become overhead.
6. Avoid deep nesting; depth makes the agent read structures instead of work.
7. Keep top-level categories under roughly 10–12 items.
8. Mention archives explicitly in indexes so the agent knows when to ignore or search them.
9. Do not chase perfect renumbering; directional order is enough.
10. Avoid renaming stable folders because index pointers and wikilinks break.

Representative index shape:

```markdown
# Brand Index

This folder holds the current brand system.

## Folder Map
| Folder | Purpose | Updated |
|---|---|---:|
| `01.Brand System/` | Visual identity, topic scope, voice | 2026-06-11 |
| `02.Editorial Strategy/` | Article direction, title rules, queue | 2026-06-11 |

## Canonical Files
| File | Purpose |
|---|---|
| `01.Brand System/01.Brand System.md` | Visual identity, colors, typography |

## Where To Go
- Start with `01.Brand System/04.Direction.md` for mission.
- Use `02.Editorial Strategy/01.Articles.md` for article selection.
```

## Hermes + Obsidian Personal Setup Flow

Main thesis: Obsidian works well for Hermes because the agent can manipulate local Markdown directly. This lowers agent friction compared with remote/database-heavy systems like Notion when the agent is the primary actor.

Patterns worth copying:

- Voice-note capture: user sends messy thoughts through Telegram/iMessage; Hermes transcribes, preserves raw transcript, produces cleaned note, adds metadata/tags, links related context, and drafts follow-up material.
- Business ideas: each idea becomes a structured one-pager, not a bullet in a giant list. Include competitive research, open questions, differentiation angles, and proposed MVP scope.
- Content engine: archive posts/newsletters locally; compare published vs local copies; attach links/media; mine old writing for new connections.
- Fitness/health or other specialized profile: use separate Hermes profiles when the role has its own memory, toolset, and cadence.
- Recipes and other messy captures: create formatting skills after repeated cleanup work so future notes are uniform.
- Purchases/payments: keep oversight and caps; do not grant broad financial autonomy by default.

Principles:

1. Build the plane as you fly it. Start with a blank vault and one useful workflow.
2. Do not overcomplicate. Avoid importing every old note or adopting a whole second-brain religion upfront.
3. Balance friction between user, knowledgebase, and agent. If the agent is primary actor, local Markdown wins.
4. Push the system with real use cases; failures reveal missing tooling/process.

Security notes:

- Use a password manager and a separate agent account/vault where possible.
- Do not expose open ports unnecessarily.
- Use separate internet accounts for agents to reduce blast radius.
- Whitelist trusted instruction channels.
- Maintain normal operational security: 2FA, password manager, least privilege.

## Context OS Flow

Main thesis: memory is infrastructure, not one toggle. The practical stack has layers.

Layer summary:

1. `SOUL.md` — identity/personality/operating contract.
2. `MEMORY.md` + `USER.md` — tiny always-on warm cache.
3. Structured/external memory — discrete facts and semantic recall.
4. `session_search` / state DB — archive with receipts, not prompt stuffing.
5. Context compression — survival gear for current long sessions, not long-term continuity.
6. Skills — procedural memory: how to execute workflows.
7. Project-local context files — local behavior rules without global pollution.
8. Obsidian/Nexus/local vault — second brain/library; not auto-injected.
9. Self-improving files — after-action learning, if actually wired.
10. Cron jobs — scheduled context loops that create/consume context.
11. Hooks/plugins/MCP — expansion surfaces for external systems.

Operational distinction:

```text
MEMORY.md      = warm cache
Obsidian vault = library / source of truth
session_search = transcript archive
skills         = SOPs / procedures
external memory = semantic/fact recall
cron           = circulatory system
```

## 3-Agent Research Department Flow

Main thesis: separate profiles prevent role/context pollution. A shared Obsidian vault is the coordination layer.

Roles:

- Scout: cheap/high-volume model. Finds signals only. Writes raw findings to inbox. Does not analyze.
- Analyst: strong reasoning model. Verifies and synthesizes. Writes structured notes, entities, contradictions.
- Briefer: cheap model. Reads recent synthesis and current projects. Produces short prioritized brief.

Vault structure from the flow:

```text
vault/
  inbox/          # raw findings from Scout
  sources/        # processed source pages
  synthesis/      # Analyst structured notes
  briefs/         # archived morning briefs
  entities/       # people, companies, products
  contradictions/ # flagged conflicts
  .last-pushed    # sync tracking
```

Config pattern:

```bash
WIKI_PATH=<your vault path>
OBSIDIAN_VAULT_PATH=<your vault path>
```

Coordination pattern:

```text
SCOUT every few hours -> writes Markdown files to inbox/
ANALYST daily -> wake gate checks inbox; if files exist, process and move them
BRIEFER daily -> reads recent synthesis and emits brief
```

Why files before Kanban: for a linear Scout -> Analyst -> Briefer pipeline, a file inbox plus wake gate is simpler, cheaper, and easier to debug. Add Kanban when the workflow has branching dependencies, many roles, or task state management.

## Recommended Application to This User

For this user's Hermes-on-Orgo setup:

```text
/root/agent-knowledge/
  INDEX.md
  SCHEMA.md
  01.Agent Operating System/
  02.Current Projects/
  03.Research Pipeline/
  04.People and Organizations/
  05.Tools and Systems/
  06.SOPs and Skills/
  07.Capture/
  90.Archive/
  attachments/
```

Immediate notes to create:

- `01.Agent Operating System/01.Hermes.md`
- `01.Agent Operating System/02.Permissions.md`
- `01.Agent Operating System/03.Memory Policy.md`
- `01.Agent Operating System/04.Tool Stack.md`
- `01.Agent Operating System/05.Security Model.md`
- `05.Tools and Systems/AgentMail.md`
- `05.Tools and Systems/AgentPhone.md`
- `05.Tools and Systems/Agentcard.md`
- `05.Tools and Systems/AgentScore.md`
- `05.Tools and Systems/Composio.md`
- `05.Tools and Systems/Orgo VM.md`
- `05.Tools and Systems/Mem0.md`

Do not overbuild. Start with these, then let real agent use determine additional structure.
