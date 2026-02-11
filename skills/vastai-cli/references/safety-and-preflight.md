# Safety and Preflight

This reference defines balanced guardrails for reliable command execution.

## Risk Levels

### Low Risk

Read-only and diagnostics.

Examples:

- `show ...`
- `search ...`
- `logs ...`
- `ssh-url`, `scp-url`

Default action:

- Execute directly, still verify IDs and context.

### Medium Risk

State-changing but reversible operations.

Examples:

- `start instance`
- `stop instance`
- `reboot instance`
- `copy`, `cloud copy`
- `update instance`

Default action:

- Run short preflight, then execute.
- Always run immediate post-check.

### High Risk

Irreversible or broad-impact operations.

Examples:

- `destroy instance`
- `destroy instances`
- destructive remote commands via `execute` (e.g. `rm`)
- team/role/key mutations with account-wide impact

Default action:

- Require explicit confirmation with target IDs listed.
- State irreversible consequences before running.

## Universal Preflight Checklist

1. Confirm intent and success condition.
2. Confirm exact target IDs.
3. Capture current state:
   - `vastai show instance <ID> --raw` (or relevant `show` command)
4. Confirm prerequisites:
   - image/disk for create
   - connection IDs for cloud copy
   - source/destination paths for transfer
5. For high risk:
   - require explicit confirmation before execution

## Post-Command Verification Checklist

1. Re-run the relevant `show` command in `--raw` mode.
2. Validate state transition matches expected outcome.
3. For transfer commands, verify destination files and size stability.
4. If mismatch, switch to recovery ladder immediately.

## Recovery Ladder

1. Re-check command syntax with `vastai <command> --help`.
2. Re-check current state with `show ... --raw`.
3. Retry with corrected target/options.
4. If blocked by capacity/scheduling, provision replacement instance.
5. For destructive mistakes, document impact and rebuild from known-good sources.

## Confirmation Templates

Use explicit confirmations for high-risk actions.

Destroy single instance:

- "Confirm destroy of instance `<ID>`. This is irreversible and deletes instance data."

Destroy multiple instances:

- "Confirm destroy of instances `<ID_1>`, `<ID_2>`, ... . This is irreversible."

Destructive execute command:

- "Confirm remote destructive command on `<ID>`: `<COMMAND>`."

## Practical Defaults

- Prefer `--raw` output for verification.
- Use `--explain` when behavior is unclear.
- Prefer narrow, single-target commands over bulk commands unless explicitly requested.
