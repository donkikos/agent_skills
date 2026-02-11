# Vast.ai CLI Command Groups

This reference maps user intent to command families, using the installed CLI command surface and official docs semantics.

## Global Flags to Prefer

- `--raw`: machine-readable verification output.
- `--explain`: debug mapping from CLI call to API endpoint.
- `--api-key`: override default key location when needed.

## 1. Discovery and Inspection

Use when identifying resources or checking current state.

Common commands:

- `vastai search offers '<query>'`
- `vastai search templates '<query>'`
- `vastai show instances --raw`
- `vastai show instance <INSTANCE_ID> --raw`
- `vastai show connections --raw`

Immediate verification:

- Confirm IDs and status fields from `show ... --raw` output.

## 2. Provisioning

Use when creating or auto-selecting a rentable instance.

Common commands:

- `vastai create instance <OFFER_ID> --image <IMAGE> --disk <GB> --ssh --direct`
- `vastai launch instance -g <GPU_NAME> -n <NUM_GPUS> -i <IMAGE> [--disk <GB>]`

Immediate verification:

- `vastai show instance <NEW_INSTANCE_ID> --raw`
- Confirm state transition target (`running` or `scheduling`) and connection fields.

## 3. Instance Lifecycle

Use when changing runtime state.

Common commands:

- `vastai start instance <INSTANCE_ID>`
- `vastai stop instance <INSTANCE_ID>`
- `vastai reboot instance <INSTANCE_ID>`
- `vastai destroy instance <INSTANCE_ID>`
- `vastai destroy instances <ID_1> <ID_2> ...`

Immediate verification:

- `vastai show instance <INSTANCE_ID> --raw` after each change.

Notes:

- `stop` preserves instance data.
- `destroy` is irreversible.
- `start` can remain in `scheduling` if resources are unavailable.

## 4. Access and Debugging

Use when connecting, collecting diagnostics, or doing constrained remote ops.

Common commands:

- `vastai ssh-url <INSTANCE_ID>`
- `vastai scp-url <INSTANCE_ID>`
- `vastai logs <INSTANCE_ID> [--tail N] [--filter <PATTERN>]`
- `vastai execute <INSTANCE_ID> '<COMMAND>'`

Immediate verification:

- Verify expected command output or logs, then re-check state with `show instance --raw` if command affects runtime/storage.

## 5. Data Movement

Use when copying between local, instance, or cloud storage.

Common commands:

- `vastai copy <SRC> <DST>` where each side is `[instance_id:]path`
- `vastai cloud copy --src <SRC> --dst <DST> --instance <INSTANCE_ID> --connection <CONNECTION_ID> --transfer "Cloud To Instance|Instance To Cloud"`
- `vastai cancel copy <DST>`
- `vastai cancel sync <DST>`

Immediate verification:

- Re-check destination paths and file sizes over repeated intervals.
- Validate transfer status via `show instance --raw` status fields/messages.

Key caution:

- Avoid copying to `/root` or `/` as destination paths in CLI copy workflows.

## 6. Identity and Key Management

Use when configuring or rotating auth.

Common commands:

- `vastai set api-key`
- `vastai create api-key`
- `vastai show api-keys`
- `vastai delete api-key`
- `vastai reset api-key`

Immediate verification:

- `vastai show api-keys` and a low-risk command (`vastai show user --raw`) to validate auth.

## 7. Team and Subaccount Operations

Use for delegated access and shared operations.

Common commands:

- `vastai create subaccount`
- `vastai show subaccounts`
- `vastai invite team-member`
- `vastai remove team-member`
- `vastai create team-role`
- `vastai show team-roles`

Immediate verification:

- Run the corresponding `show` command after each mutation.

## 8. Host-Only Commands (Conditional)

Only use if the account is operating as a host.

Examples:

- `list machine`, `unlist machine`, `show machines`
- `schedule maint`, `cancel maint`

Verification:

- Always follow host mutations with `show machines --raw` and confirm intended state.
