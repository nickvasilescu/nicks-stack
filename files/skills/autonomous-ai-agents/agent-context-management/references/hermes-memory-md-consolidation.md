# Hermes MEMORY.md consolidation (char cap)

## Problem

Watchdog / operator email: `MEMORY.md at N% of cap, writes will start failing`. Rules "don't stick" (Eidelman/Dane-class) when the store rejects writes.

Typical cap: **16_000 chars** (confirm per box). Alert often ~80–92%.

Path: `~/.hermes/memories/MEMORY.md` (and `USER.md` separately).

## Procedure

1. Read live file + char count (not just byte size if encoding matters).
2. Backup: `~/.hermes/memories/backups/MEMORY.md.bak-<UTC>`
3. Full archive to agent knowledge vault (Obsidian Brain / Sources/Memory).
4. Compact rewrite:
   - Cardinal rules stay hot
   - Dedupe people/rules
   - Long-form → archive
   - **No plaintext secrets**
5. Target **≤50% of cap** after cleanup; never leave ≥90%.
6. Report before/after counts to operator; optional customer-facing reply if they forwarded the alert.

## Remote apply

Use Orgo REST bash or fleet-remote-exec. Prefer writing via Python on the remote (avoid shell-variable expansion eating `$MEM` paths when nesting local + remote shells).

## Not this skill

Token window / compaction threshold → main SKILL.md workflow. MEMORY.md is durable agent notes, not the LLM context compressor.