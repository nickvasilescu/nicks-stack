# Staged Obsidian Vault Rebuild Pattern

Use this reference when rebuilding an existing synced Obsidian vault into an agent-readable V2 vault that will eventually replace the old path.

## Core Rule

Do not refactor the live synced vault in place. Use staged replacement:

```text
/source/Live-Vault
/migration-workspace/backups/Live-Vault.backup-<timestamp>.tar.gz
/migration-workspace/reports/
/migration-workspace/staging/Live-Vault.v2-staged
```

Only after verification and explicit user approval:

```text
/source/Live-Vault -> /source/Live-Vault.legacy-<timestamp>
/migration-workspace/staging/Live-Vault.v2-staged -> /source/Live-Vault
```

## Preflight Sequence

1. Resolve the live vault path from Obsidian config or a known absolute path.
2. Create a migration workspace outside the synced vault.
3. Create a real archive backup and checksum; Obsidian Sync is not a backup.
4. Verify the backup with checksum and archive listing.
5. Run read-only audits and write reports outside the vault.
6. If private/sensitive material is in scope, audit by aggregate metadata only unless the user explicitly requests content inspection.
7. Produce a formal plan, schema, migration map, sensitive-boundary policy, and cutover checklist outside the live vault.
8. Build a deterministic migration script with `--dry-run`, `--stage`, and `--verify` modes.
9. Stage V2 outside the live vault.
10. Disable Sync/Publish in the staged copy before GUI inspection.
11. Verify staged V2 before cutover.
12. If the user wants to see the vault in the VM, follow `references/staged-vault-inspection.md`.

## Report Set

Useful preflight reports:

```text
AUDIT-SUMMARY.md
inventory.json
top-level-inventory.md
markdown-quality.json
duplicate-basenames.json
link-report.json
sensitive-boundaries.md
compiled-vaults-policy.md
proposed-v2-tree.md
```

## Sensitive Boundary Pattern

When `Private/` is included:

- copy byte-for-byte through scripts,
- preserve counts, sizes, and structure,
- do not print file bodies,
- avoid printing private filenames in reports unless explicitly requested,
- do not send private content to remote search/research tools.

When `Finance/` is read/write:

- preserve all current finance notes,
- generate a finance `INDEX.md`,
- allow future edits only under explicit task scope,
- keep an audit trail for finance edits.

## External Grounding Pattern

If the user has Composio or similar external research tools, use them only for general best-practice grounding. Do not send vault private/finance contents or sensitive filenames to remote tools.

Useful Composio sequence:

```bash
composio search "search web with exa" "crawl webpage with firecrawl" "perplexity web search" "context7 documentation lookup"
composio execute FIRECRAWL_SEARCH -d '{"q":"Obsidian vault best practices Markdown frontmatter internal links AI agent knowledge base","limit":8}'
composio execute EXA_SEARCH -d '{"query":"AI agent knowledge base markdown Obsidian vault INDEX.md frontmatter schema best practices","numResults":8}'
composio execute CONTEXT7_MCP_RESOLVE_LIBRARY_ID -d '{"libraryName":"Obsidian","query":"Obsidian documentation properties frontmatter internal links vault file format"}'
composio execute CONTEXT7_MCP_QUERY_DOCS -d '{"libraryId":"/websites/obsidian_md_help","query":"Properties YAML frontmatter internal links Markdown vault storage"}'
```

Grounding points that proved useful:

- Obsidian stores notes as local Markdown files, so filesystem staging is valid.
- Obsidian internal links are first-class and may auto-update on rename, but bulk renames still need staged path mapping.
- YAML frontmatter/properties are appropriate for queryable metadata.
- Dataview indexes YAML frontmatter and inline fields; flat controlled fields are easiest for agents and scripts.

## Cutover Blockers

Do not cut over if:

- backup checksum fails,
- staged V2 lacks root `INDEX.md`, `SCHEMA.md`, or agent rules,
- sensitive copy counts do not reconcile,
- raw imports are still in active search paths,
- Obsidian is actively writing or Sync is running through half-migrated state,
- the user has not explicitly approved cutover.
