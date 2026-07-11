---
name: agent-obsidian-vault
description: Build agent-readable Obsidian knowledge vaults.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Obsidian, Agents, Knowledgebase, Context, Hermes]
---

# Agent Obsidian Vaults

This skill builds and maintains a local Obsidian/markdown vault that Hermes and other agents can navigate quickly. It does not turn Obsidian into hot memory or replace Hermes `memory`, `session_search`, or skills; it creates a readable library and operating manual that workflows access on demand. The bootstrap helper in `scripts/bootstrap_agent_vault.py` is stdlib-only and never overwrites existing notes.

## When to Use

- The user asks to build an Obsidian vault for Hermes, agents, or an AI assistant.
- The user asks to make an existing vault faster or easier for an agent to navigate.
- The user mentions HermesBible vault advice, `INDEX.md`, LLM Wiki, or an agent knowledgebase.
- The user wants Scout → Analyst → Briefer, research, briefing, or file-inbox workflows.
- The user wants to connect Hermes memory, skills, `session_search`, cron, and Obsidian cleanly.
- The user wants to vault **managed customer agents / people / companies** (Orgo VMs, Hermes agents) into the production vault.

## Prerequisites

- A resolved absolute vault path. Prefer an existing `OBSIDIAN_VAULT_PATH`; otherwise choose a simple local path such as `/root/agent-knowledge` or `~/agent-knowledge`.
- Python 3 to run the stdlib bootstrap script.
- Obsidian is optional. The vault is plain Markdown on disk; Obsidian is only the human UI.
- For LLM Wiki use, set `WIKI_PATH` to the same absolute path as `OBSIDIAN_VAULT_PATH`.
- For Hermes command/config facts, official Hermes docs or the `hermes-agent` skill are authoritative. HermesBible is an unofficial community workflow reference.
- No credentials are required unless you add sync, messaging, NotebookLM, or paid external services.

## How to Run

Load this skill with `skill_view`, resolve `scripts/bootstrap_agent_vault.py` against the returned skill directory, then invoke the script through the `terminal` tool:

```bash
python3 /absolute/path/to/scripts/bootstrap_agent_vault.py /root/agent-knowledge
```

For rebuilding an existing synced vault that will replace the old vault, first read `references/staged-vault-rebuild.md`. Use a backup + migration workspace + staged flow; do not refactor the live synced vault in place. If the existing vault is messy or legacy-heavy and the user wants a clean agent-native restart, read `references/clean-v3-agent-vault.md` and build a deliberate V3 seed with a per-file manifest instead of bulk-copying old notes. When the user wants to inspect a staged vault in Obsidian before cutover, read `references/staged-vault-inspection.md` and disable Sync/Publish in the staged copy first. When the user explicitly wants the clean/staged vault to replace the cloud-synced Obsidian vault, read `references/obsidian-sync-cloud-replacement.md` before touching Sync remotes.

After bootstrapping, use `read_file`, `search_files`, `write_file`, and `patch` for note work. Do not pass `$OBSIDIAN_VAULT_PATH` literally to file tools; resolve it first and pass an absolute path.

## Quick Reference

```text
https://www.hermesbible.com/llms-full.txt
https://www.hermesbible.com/flows/index-md-folder-structure-faster-hermes-agent
https://www.hermesbible.com/flows/my-hermes-and-obsidian-setup-and-use-cases
https://www.hermesbible.com/flows/3-agent-research-department-notebooklm-obsidian
https://www.hermesbible.com/flows/context-os-for-hermes-agent
https://hermes-agent.nousresearch.com/docs

OBSIDIAN_VAULT_PATH=/absolute/vault
WIKI_PATH=/absolute/vault
hermes config env-path
hermes dashboard -> Config -> search "WIKI"
python3 /absolute/path/to/scripts/bootstrap_agent_vault.py /absolute/vault
python3 /absolute/path/to/scripts/bootstrap_agent_vault.py --check /absolute/vault
```

## Procedure

0. Decide whether this should be greenfield or a migrated rebuild.
   - If the existing vault is messy, huge, or mostly legacy, prefer a clean new staged vault and treat the old vault as cold source material.
   - Do not bulk-promote thousands of legacy notes into active folders just because they can be copied safely.
   - A migration that preserves everything is a good archive/staging artifact, but it is not automatically a good production agent vault.
   - Production agent vaults should start with a sparse root, populated current projects/open loops/decisions, a root `VAULT-INDEX.md`/`INDEX.md`, explicit `SCHEMA.md`, `AGENTS.md`/`CLAUDE.md`/`HERMES.md` compatibility files, and a promotion workflow from legacy sources.
   - Prefer lifecycle/write-permission folders for clean agent vaults: `inbox/` for triage, `raw/` for immutable source truth, `wiki/` for synthesis, `projects/` for active work, `AI/` for session logs and generated outputs, `restricted/` for private/finance boundaries, and `archive/` for cold history.
   - Add a short `description` frontmatter field on every note so agents can assess relevance before opening the body; include `agent-written` and `synthesized` flags for trust and promotion state.
   - Use wikilinks for internal references, Markdown links for external URLs, and validate that every new note links to at least one existing note.
   - Initialize git in the vault and commit validated agent edits; Obsidian Sync is not the rollback layer for agent-generated changes.
   - Keep raw imports, compiled vaults, and old personal notes outside normal retrieval unless the user asks for legacy provenance.

1. Resolve authority and sources.
   - Use HermesBible for workflow patterns: `INDEX.md`, concern-based folders, numbered order, file-inbox coordination, and context-layer architecture.
   - Use the official Hermes docs or `skill_view(name="hermes-agent")` for commands, config semantics, provider setup, tools, profiles, cron, and gateway behavior.
   - If the user references a prior conversation, use `session_search` before asking them to repeat it.

2. Resolve the vault path before editing.
   - If the user gave a path, use it.
   - If not, check `OBSIDIAN_VAULT_PATH` or `WIKI_PATH` with `terminal`.
   - If still unset, choose a simple path and state the assumption.

3. For existing synced vault rebuilds, preflight before any restructure.
   - Create a migration workspace outside the synced vault.
   - Create and verify an archive backup with checksum; Obsidian Sync is not a rollback plan.
   - Audit read-only and write reports outside the vault.
   - If `Private/` or finance material is in scope, avoid printing sensitive contents into tool output, reports, or remote research prompts.
   - Build V2 in a staging path and cut over only after verification and explicit approval.
   - Use `references/staged-vault-rebuild.md` for the full pattern.

4. Bootstrap the smallest useful agent-native vault.
   - Invoke `scripts/bootstrap_agent_vault.py` through `terminal`.
   - Expected starter shape:

```text
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

4. Treat `INDEX.md` as the agent's soft gate.
   - Root and major-folder indexes should contain: Folder Map, Canonical Files, Where To Go, and Rules for Hermes.
   - Read the relevant `INDEX.md` before editing inside a major folder.
   - Update indexes immediately after renaming or moving canonical notes.

5. Organize by concern, not content type.
   - Prefer `03.Research Pipeline/` over scattered `articles/`, `pdfs/`, and `notes/` folders.
   - Use numbers for reading order: `01.Hermes.md` before `02.Permissions.md`.
   - Keep each level under roughly 10-12 items; if it grows beyond that, split by concern.

6. Put each kind of knowledge in the right Hermes layer.
   - `memory`: compact durable facts and user preferences.
   - `session_search`: historical transcript receipts.
   - Skills: reusable procedures and exact workflows.
   - Obsidian vault: human-readable library, operating manual, research wiki, and project knowledgebase.
   - Cron: scheduled routines that create, refresh, or consume vault context.
   - Do not store secrets in the vault.

7. Configure Hermes to find the vault when requested.
   - Run `hermes config env-path` through `terminal` to locate the environment file.
   - For a staged V3 review, point Hermes at the staged vault path for testing only; do not repoint to `/root/Dewey-Vault` until production cutover has actually happened.
   - For production after explicit cutover approval, repoint both variables to the final canonical vault path.
   - Use a secret-safe env edit that changes only these keys and does not print unrelated `.env` contents:

```bash
OBSIDIAN_VAULT_PATH=/absolute/vault
WIKI_PATH=/absolute/vault
```

   - Verify by printing only the two relevant lines, checking required root contracts, and running the vault validator.
   - Existing Hermes sessions need `/reload` or a restart to see `.env` changes; fresh sessions pick them up automatically.
   - Obsidian Sync has three separate states: plugin enabled, local vault connected to a named remote, and actual upload/download running. Verify all three when the user asks for cloud sync.
   - If replacing an old cloud-synced vault with a clean V3 vault, read `references/obsidian-sync-cloud-replacement.md`, back up local vaults/config first, avoid merging into the old remote by accident, and verify the Sync activity log reaches `Fully synced`.

8. Add file-based agent pipelines only when a real workflow needs them.
   - For research, use a simple Scout → Analyst → Briefer pipeline: `inbox/`, `sources/`, `synthesis/`, `briefs/`, `entities/`, `contradictions/`.
   - Use confidence labels such as `[verified]`, `[likely]`, `[unverified]`, and `[conflicting]` in synthesized notes.
   - Prefer file inboxes and wake/check scripts for linear pipelines; move to Kanban only when roles, dependencies, or human-in-the-loop states become complex.

9. Maintain the vault by observed friction, not aesthetics.
   - Diagnose slow agent navigation by counting wrong files opened, stale files chosen, and clarification questions.
   - Add structure only where the agent gets lost.
   - Archive old material explicitly and tell the agent in `INDEX.md` not to search archives unless historical context is needed.

10. **Managed customer agents (Orgo / Hermes customer accounts).**
   - Soft gate: `wiki/managed-customer-agents.md` then person note + `projects/<slug>/overview.md`.
   - For every named customer account create **all three**: `wiki/people/…`, project pack (`overview` + `tasks` + `ideas`), registry row.
   - Overview must include copy-paste Orgo workspace id, computer id, dashboard URL, messaging channel; never secrets/tokens.
   - Evidence order: live Orgo IDs → VM probe → Granola → Slack Connect → Gmail. Full procedure: skill **`vault-managed-customer-agents`** (also `managed-hermes-on-orgo/references/customer-context-vaulting.md`).
   - Large fleets: flagship + fleet pattern, not one project per agency VM.
   - Same session: `active-projects`, `open-loops`, `people-directory`, `LOG`, optional `AI/sessions/…`, schema validator, git commit.

## Pitfalls

- HermesBible is unofficial. It is useful for community patterns, not the final authority on Hermes commands or config.
- Too many `INDEX.md` files slow the agent down. Put indexes at major folder roots, not every tiny subfolder.
- Content-type vaults look neat to humans but force agents to search across unrelated folders.
- Deep nesting creates navigation tax. Keep common paths shallow.
- Numbering is directional, not sacred. Do not renumber the whole vault for cosmetic order.
- Renames break `INDEX.md` pointers and wikilinks; stale names are worse than slightly awkward names.
- Obsidian Sync can leave Hermes reading a stale VPS copy while a laptop has newer notes.
- Obsidian Sync is not a backup for migrations; it can sync mistakes efficiently. Create a local archive backup and checksum before restructuring or deleting/replacing a remote.
- Enabling the Sync plugin is not enough: verify the named remote connection, click `Start syncing` if needed, and inspect the Sync activity log for uploads and a final `Fully synced` line.
- Once the user explicitly makes a staged V3 vault the cloud-synced vault, old validators that require "Sync disabled" are no longer authoritative; treat Sync-enabled as expected, but continue checking frontmatter, wikilinks, git status, and Sync activity logs.
- Do not connect a clean staged vault to an old remote unless the user explicitly wants a merge. To replace the cloud vault, delete/create remotes deliberately and preserve local backups first.
- Do not refactor a synced production vault in place. Stage V2 beside it, verify, then cut over by directory rename only after explicit approval.
- If the user includes `Private/` in scope, use aggregate metadata and copy-only scripts by default; never send private contents to web/research tools.
- The vault is a library, not hot memory. Do not duplicate every `memory` entry or raw transcript into Obsidian.
- File tools do not expand environment variables; resolve `OBSIDIAN_VAULT_PATH` and `WIKI_PATH` first.
- NotebookLM consumer automation can break because it depends on browser automation rather than a stable public API; keep a direct-Hermes synthesis fallback.

## Verification

```bash
python3 /absolute/path/to/scripts/bootstrap_agent_vault.py --check /absolute/vault
```

The check should print `PASS` and list the vault root, required indexes, `SCHEMA.md`, and required major folders. The helper accepts both the compact starter layout and staged V2 rebuilds with `07.Operations/`, `08.SOPs and Skills/`, and `99.Raw Imports/`.