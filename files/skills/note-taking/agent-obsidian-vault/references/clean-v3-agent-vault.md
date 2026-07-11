# Clean V3 Agent Vault Pattern

Use this reference when the user wants a fresh agent-readable Obsidian vault, especially after a messy or overgrown existing vault made agents slow or confused.

## Core Lesson

A lossless migration is not automatically an agent-native vault. A staged copy that preserves thousands of legacy notes is useful as a cold source and rollback artifact, but it should not become the production agent operating vault unless it has been deliberately distilled.

For messy personal/legacy vaults, prefer a clean V3 seed with explicit per-file rationale. Do not bulk-copy old notes into active context.

## Target Architecture

Prefer lifecycle and write-permission folders over topic folders:

```text
AGENTS.md                  # shared constitution
CLAUDE.md                  # Claude Code discovery/compatibility shim
HERMES.md                  # Hermes-specific operating shim
VAULT-INDEX.md             # dashboard agents read first
INDEX.md                   # compatibility pointer to VAULT-INDEX
SCHEMA.md                  # flat metadata/link/naming schema
active-context.md          # session-start current state
LOG.md                     # append-only operational trace

inbox/                     # raw captures waiting for triage
raw/                       # immutable source truth and legacy pointers
wiki/                      # synthesized durable knowledge and MOCs
projects/                  # active work, tasks, decisions, ideas
AI/                        # agent sessions, deliverables, scratch, knowledge
restricted/                # private/finance permission boundary
archive/                   # closed or cold historical material
attachments/               # support files referenced by notes
.claude/skills/            # optional Claude/Obsidian skills; do not vendor blindly
.obsidian/                 # local Obsidian config; staged vaults disable Sync/Publish
```

## Required Frontmatter

Keep the schema flat and universal. Every Markdown seed note should include at least:

```yaml
---
title: "Human title"
type: "index"
status: "active"
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
tags: ["agent-vault"]
aliases: []
description: "Under 150 characters so agents can judge relevance before opening."
agent-written: true
synthesized: true
visibility: "normal"
source: "hermes"
source-path: ""
source-url: ""
confidence: "verified"
---
```

Important fields:

- `description`: lets agents assess relevance cheaply.
- `agent-written`: calibrates trust in agent-generated notes.
- `synthesized`: distinguishes raw captures from promoted knowledge.
- `visibility`: marks `normal`, `private`, or `finance` boundaries.
- `source-path` / `source-url`: preserves provenance without copying raw material.

## Deliberate-File Manifest

For greenfield V3 builds, create every seed file from an explicit manifest containing:

- relative path
- category, e.g. `markdown`, `git-config`, `obsidian-config`
- rationale for why the file exists

Store the manifest inside the vault, e.g. `AI/knowledge/v3-file-manifest.md`, and also write an external build report under the migration workspace. The manifest must include non-Markdown files such as `.gitignore` and `.obsidian/core-plugins.json`; omitting them weakens the “deliberate per-file” guarantee.

## Validation Rules

Before presenting the vault:

1. Validate every Markdown file has required flat frontmatter.
2. Validate `description` length is reasonable, ideally <=150 chars.
3. Validate `tags` and `aliases` are YAML lists.
4. Validate every new Markdown note has at least one wikilink to an existing note.
5. Validate every wikilink resolves; never create dead internal links.
6. Treat Markdown links as external links only.
7. Exclude `.git/` internals from validation counts and note checks.
8. Confirm `.obsidian/core-plugins.json` has `sync: false` and `publish: false` for staged review.
9. Confirm the live vault has not acquired V3 markers before cutover.

## Git Discipline

Initialize git in the staged V3 vault and commit the seed after validation:

```bash
git init -b main
git config user.name 'Hermes Agent'
git config user.email 'hermes-agent@local'
git add -A
git commit -m 'Seed clean V3 agent vault'
git status --short
```

Git is the rollback and review layer for agent edits. Obsidian Sync is not a safe rollback mechanism for generated changes.

## Obsidian Inspection

Before opening a staged vault in Obsidian:

- verify root contracts exist;
- disable Sync and Publish in the staged vault;
- back up `/root/.config/obsidian/obsidian.json` before registering the staged vault;
- register the staged vault as open and other vaults as not open;
- launch Obsidian under the VM display;
- visually verify the window title contains the staged vault name and a canonical note such as `VAULT-INDEX` is open.

Expected V3 verification title example:

```text
VAULT-INDEX - Dewey-Agent-Vault.v3-clean - Obsidian 1.12.7
```

## Hermes Integration Before Cutover

For review/testing, it is acceptable to point Hermes at the staged V3 vault while leaving the production vault untouched:

```bash
OBSIDIAN_VAULT_PATH=/root/dewey-vault-migration/staging/Dewey-Agent-Vault.v3-clean
WIKI_PATH=/root/dewey-vault-migration/staging/Dewey-Agent-Vault.v3-clean
```

Rules:

1. Back up the Hermes env file before editing it.
2. Edit only `OBSIDIAN_VAULT_PATH` and `WIKI_PATH`; do not print or rewrite unrelated secrets.
3. Verify by printing only those two lines and checking required root contracts (`VAULT-INDEX.md`, `SCHEMA.md`, `AGENTS.md`, `HERMES.md`).
4. Existing Hermes sessions need `/reload` or a restart to see `.env` changes; fresh sessions pick them up automatically.
5. Record the staged integration in `active-context.md`, `LOG.md`, and project tasks, then commit the change.
6. After production cutover, repoint both variables to `/root/Dewey-Vault`; do not leave them pointing at the old staging directory.

## Obsidian Runtime Config Drift

Opening a staged vault in Obsidian may create or modify local UI config files such as:

```text
.obsidian/app.json
.obsidian/appearance.json
.obsidian/core-plugins.json
```

Treat this as expected UI-local drift, not a validation failure, but keep the repository clean:

- ignore volatile local UI files in `.gitignore` when they are not deliberate seed artifacts;
- preserve and commit intentional safety config, especially `sync: false` and `publish: false` in `.obsidian/core-plugins.json`;
- normalize JSON with a trailing newline before committing;
- re-run the V3 validator after Obsidian has touched the vault.

## Private and Finance Boundary

Do not import old `Private/` or finance contents blindly. Seed explicit permission boundaries instead:

```text
restricted/AGENTS.md
restricted/private/AGENTS.md
restricted/private/private-index.md
restricted/finance/AGENTS.md
restricted/finance/finance-index.md
```

Private should be deny-by-default. Finance can be read/write only when explicitly scoped by the user.

## Pitfalls

- Do not confuse “classified import” with “agent operating vault.”
- Do not cut over after opening a staged vault for inspection; inspection is not approval.
- Do not bulk-promote legacy projects. Promote only current, useful items after review.
- Do not create a polished-looking folder tree with placeholder `Active Projects`, `Open Loops`, or `Decisions`; seed real current state, even if small.
- Do not vendor external Claude/Obsidian skills blindly. Create a placeholder and install only after explicit choice or verified source.
- Do not let git internals inflate validation counts or trigger frontmatter checks.
