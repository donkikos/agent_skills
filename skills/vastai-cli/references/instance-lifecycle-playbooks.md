# Instance Lifecycle Playbooks

Use these playbooks for deterministic lifecycle execution with explicit checks.

## Playbook A: Rent a New Instance (Search -> Create/Launch -> Verify)

### Preflight

- Define hard requirements: GPU model/count, RAM, disk, geolocation, reliability.
- Choose provisioning path:
  - `create instance` when you already have a specific offer ID.
  - `launch instance` when auto-selecting top matching offer.

### Execute

1. Search offers:
   - `vastai search offers '<QUERY>' --order 'score-'`
2. Provision:
   - Specific offer: `vastai create instance <OFFER_ID> --image <IMAGE> --disk <GB> --ssh --direct`
   - Auto-pick: `vastai launch instance -g <GPU_NAME> -n <NUM_GPUS> -i <IMAGE> --disk <GB>`

### Verify

- `vastai show instance <INSTANCE_ID> --raw`
- Confirm:
  - expected instance ID exists
  - status is `running` or progressing from `scheduling`
  - connection details are present

### Recover

- If create/launch fails, tighten or relax query constraints and retry.
- If state stalls in `scheduling`, use Playbook B.

## Playbook B: Recover a Stuck or Unavailable Instance

### Preflight

- Snapshot state: `vastai show instance <INSTANCE_ID> --raw`
- Capture current status text and last known state.

### Execute

1. Start if stopped:
   - `vastai start instance <INSTANCE_ID>`
2. Re-check status:
   - `vastai show instance <INSTANCE_ID> --raw`

### Verify

- If instance remains in `scheduling` for ~30+ seconds, treat as resource unavailability.

### Recover

- Try `vastai reboot instance <INSTANCE_ID>` for transient runtime issues.
- If still unavailable and workload is blocked:
  - stop/destroy (only if safe), then provision a replacement with Playbook A.

## Playbook C: Controlled Pause and Resume

### Pause (cost control with data retention)

1. Preflight:
   - confirm no critical process is mid-write
   - confirm logs/artifacts are persisted where needed
2. Execute:
   - `vastai stop instance <INSTANCE_ID>`
3. Verify:
   - `vastai show instance <INSTANCE_ID> --raw` -> `stopped`

### Resume

1. Execute:
   - `vastai start instance <INSTANCE_ID>`
2. Verify:
   - `vastai show instance <INSTANCE_ID> --raw` -> `running`
3. Recover:
   - if `scheduling` persists, switch to Playbook B

## Playbook D: Safe Decommission (Irreversible)

### Preflight

- Confirm required data has been copied out and validated.
- Confirm target ID to avoid destroying the wrong instance.
- Explicitly acknowledge irreversibility.

### Execute

- `vastai destroy instance <INSTANCE_ID>`

### Verify

- `vastai show instances --raw` and ensure the target ID is absent.

### Recover

- No rollback for destroy. Recreate using Playbook A if needed.
