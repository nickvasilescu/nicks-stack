# Orgo disk resize: block size ≠ filesystem size

When Nick/Orgo increases disk (or CPU) on a running computer, the block device may grow while the root filesystem does not. Always verify live.

## Ground truth checks

```bash
nproc
free -h
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
df -h /
```

Do not trust Orgo API cpu/ram/disk fields alone. API may still show cpu:4 while nproc is 8.

## Common post-resize state

- lsblk: vda 30G (or larger)
- df -h /: still ~7.8G at 80%+
- Cause: ext4 not auto-grown after block enlarge

## Grow online (whole-disk root, common on Orgo metal)

Remote exec PATH often omits /sbin and /usr/sbin. Use absolute paths.

```bash
/sbin/tune2fs -l /dev/vda | egrep 'Block count|Block size|Free blocks|Filesystem state'
/sbin/resize2fs /dev/vda
df -h /
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
```

Expected: on-line resizing; larger block count; df near full disk size; use% drops sharply.

If root is a partition: growpart then /sbin/resize2fs on the partition device (cloud-guest-utils).

## Example (Budgetdog ops 2026-07-10)

- Disk block: 30G after Nick resize
- FS before: 7.8G, 83% used
- After /sbin/resize2fs /dev/vda: 30G, 22% used (~23G free)
- CPU live: 8; RAM still 8G; API still reported cpu 4

## Related

- references/fleet-remote-exec.md (exec PATH pitfalls, gateway recycle)
- managed-hermes-on-orgo pitfalls on disk headroom