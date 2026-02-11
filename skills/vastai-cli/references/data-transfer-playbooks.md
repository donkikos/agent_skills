# Data Transfer Playbooks

Use this reference to choose the right transfer method and verify completion.

## Decision Matrix

- `vastai copy`:
  - Best for local <-> instance or instance <-> instance path sync.
  - Syntax: `[instance_id:]path` for source/destination.
- `vastai cloud copy`:
  - Best for cloud storage integrations (Drive/S3/Backblaze/Dropbox) and stopped-instance-friendly flows.
- `scp` via `vastai scp-url`:
  - Best for quick small file transfers.

## Preflight Checklist (All Transfer Types)

- Validate source path exists.
- Validate destination path and writable location.
- Confirm correct `INSTANCE_ID` and `CONNECTION_ID` where applicable.
- For cloud sync, verify feature compatibility:
  - cloud sync is documented for Docker-based instances.

## Playbook A: Cloud -> Instance or Instance -> Cloud

1. Discover connections:
   - `vastai show connections --raw`
2. Start transfer:
   - `vastai cloud copy --src <SRC> --dst <DST> --instance <INSTANCE_ID> --connection <CONNECTION_ID> --transfer "Cloud To Instance"`
   - or use `"Instance To Cloud"`
3. Verify completion:
   - check destination path repeatedly until sizes stabilize
   - inspect `vastai show instance <INSTANCE_ID> --raw` status messages for transfer progress
4. Recover if stuck:
   - `vastai cancel sync <DST_TARGET>`
   - rerun with corrected path/flags

## Playbook B: Instance <-> Local or Instance <-> Instance with `copy`

1. Execute transfer:
   - `vastai copy <SRC> <DST>`
2. Verify completion:
   - list destination and compare counts/sizes
3. Recover if stuck:
   - `vastai cancel copy <DST_TARGET>`
   - retry with corrected endpoint/path

Caution:

- Do not copy to `/root` or `/` destination directories.

## Playbook C: Small Ad-Hoc Transfers via SCP

1. Resolve connection helper:
   - `vastai scp-url <INSTANCE_ID>`
2. Transfer with standard `scp` syntax.
3. Verify with remote file listing and checksum/size checks when needed.

## Validation Pattern (Recommended)

For critical data movement, use a two-layer verification:

1. Operational status check:
   - CLI status (`show instance --raw`, transfer completion indicators)
2. Filesystem stability check:
   - at least two repeated file size checks with short interval

Treat transfer as complete only when both checks are consistent.
