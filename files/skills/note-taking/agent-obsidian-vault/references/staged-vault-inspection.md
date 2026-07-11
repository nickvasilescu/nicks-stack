# Staged Vault Inspection in Obsidian

Use this reference after a staged V2 vault has passed script verification and the user wants to inspect it in the VM/GUI before cutover.

## Goal

Open the staged vault as a separate local Obsidian vault without replacing the live vault and without syncing the staged structure.

## Safety Rules

- Do not cut over just because the staged vault is opened for inspection.
- Do not open the staged vault with Obsidian Sync enabled.
- Keep `/root/Dewey-Vault` unchanged until the user explicitly approves cutover.
- Back up the global Obsidian config before changing which vault opens by default.

## Procedure

1. Verify the staged vault exists and has root contracts:

```bash
[ -d /root/dewey-vault-migration/staging/Dewey-Vault.v2-staged ]
[ -f /root/dewey-vault-migration/staging/Dewey-Vault.v2-staged/INDEX.md ]
[ -f /root/dewey-vault-migration/staging/Dewey-Vault.v2-staged/SCHEMA.md ]
```

2. Disable Sync and Publish inside the staged vault before opening it:

```text
/root/dewey-vault-migration/staging/Dewey-Vault.v2-staged/.obsidian/core-plugins.json
```

Set:

```json
"sync": false,
"publish": false
```

3. If the Obsidian GUI cannot open the staged folder through the file chooser, register the staged vault in the global Obsidian config after backing it up:

```text
/root/.config/obsidian/obsidian.json
```

Backup example:

```text
/root/dewey-vault-migration/backups/obsidian.json.before-open-staged-v2.json
```

Add a vault entry with:

```json
{
  "path": "/root/dewey-vault-migration/staging/Dewey-Vault.v2-staged",
  "open": true
}
```

and set other vault entries' `open` fields to `false`.

4. Launch Obsidian through the `terminal` tool using the VM display:

```bash
DISPLAY=:99 obsidian --no-sandbox --disable-gpu
```

5. Bring the Obsidian window forward only if the user asked to see it:

```bash
DISPLAY=:99 xdotool search --onlyvisible --class 'obsidian' windowactivate %@
```

6. Verify visually that the active window title names the staged vault and that the left tree shows V2 folders:

```text
Dewey-Vault.v2-staged - Obsidian
00.Migration Reports
01.Agent Operating System
02.Current Projects
03.People and Organizations
04.Research Pipeline
05.Tools and Systems
06.Capture
07.Operations
08.SOPs and Skills
90.Archive
99.Raw Imports
attachments
AGENTS
HERMES
INDEX
SCHEMA
```

## Pitfalls

- `obsidian /path/to/vault` may print `Command line interface is not enabled`; use the GUI vault manager or config registration fallback.
- Opening a staged vault copied from a synced source can inherit `sync: true`; disable it before inspection.
- File chooser behavior varies. If path entry opens the folder contents but does not select it, config registration is more deterministic.
- Clicking the vault name in the lower-left file explorer is not always the vault switcher; the command palette command `Manage vaults` is more reliable.

## Verification

The active window title should contain:

```text
Dewey-Vault.v2-staged - Obsidian
```

and the staged vault should still reside under:

```text
/root/dewey-vault-migration/staging/Dewey-Vault.v2-staged
```

not `/root/Dewey-Vault`.