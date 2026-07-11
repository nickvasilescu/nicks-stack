# Obsidian Sync Cloud Replacement for a Clean Agent Vault

Use this reference when the user wants the newly built clean/staged agent vault to become the Obsidian Sync cloud vault, replacing an older remote vault.

## Core lesson

Do not assume "turn on Sync" means the vault is actually cloud-synced. Obsidian has three distinct states:

1. The Sync core plugin is enabled in `.obsidian/core-plugins.json`.
2. The local vault is connected to a named remote vault.
3. Sync is running and the activity log shows uploads plus `Fully synced`.

Treat the task as complete only after state 3 is verified in the Obsidian UI or Sync activity log.

## Safe sequence

1. Confirm intent: distinguish between:
   - opening the vault in Obsidian,
   - enabling the Sync plugin,
   - connecting to an existing remote,
   - replacing/deleting an existing remote and creating a new one.
2. Before destructive cloud changes, create fresh local backups of:
   - the old live/local vault,
   - the clean/staged vault,
   - Obsidian global config, usually `~/.config/obsidian/`.
3. Verify backup archives with checksums before deleting a remote vault.
4. In Obsidian settings, inspect Sync status:
   - `Sync: Uninitialized` or `Currently not connected to any remote vault` means the plugin is enabled but cloud Sync is not configured.
   - A red Sync/status icon can indicate uninitialized/disconnected state.
5. If an existing remote appears and the user wants the cloud vault updated to the clean V3 vault, do not connect and merge blindly. Existing remotes may contain the old vault.
6. If the user explicitly approves replacing the cloud remote:
   - delete the old remote through Obsidian Sync UI,
   - confirm the warning that server data/version history will be permanently deleted while local files stay intact,
   - create a new remote with a clear name,
   - choose the user-selected encryption mode,
   - connect the clean local vault to the new remote,
   - accept the local/remote merge prompt only if the remote was just created/empty.
7. Click `Start syncing`; connection alone is not enough.
8. Verify final state in the Sync pane:
   - connected to the expected remote name,
   - Sync status says running,
   - storage usage reflects uploaded data.
9. Open the Sync activity log and verify recent uploads plus a final `Fully synced` line. Check for visible errors.
10. Record the cloud-sync decision/status inside the vault and commit local metadata to git.
11. Wait again for those status-note edits to upload and verify another `Fully synced` entry.

## Encryption handling

Obsidian Sync may default to end-to-end encryption and require an encryption password. Do not invent, request in chat unnecessarily, or store that password in the vault. If the user chooses E2EE, pause so they can type the password directly in Obsidian. If the user chooses Standard encryption, select it explicitly and proceed without a password.

## Pitfalls

- Enabling `sync: true` in `core-plugins.json` is not proof that cloud Sync is active.
- Connecting a clean staged vault to an old remote can merge old content into the clean vault. Clarify before clicking `Connect`.
- Deleting a remote vault is permanent for Obsidian's server-side data and version history. Local backup first.
- Obsidian may show a generic "Confirm Merge Vault" prompt even when connecting to a newly created empty remote. Verify the remote was just created/empty before continuing.
- Sync logs can lag behind local edits. After writing status notes, wait and verify those edits upload too.
- Do not treat git and Obsidian Sync as substitutes: git records local agent edits and rollback points; Obsidian Sync moves the vault across devices.
