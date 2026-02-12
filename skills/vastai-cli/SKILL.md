---
name: vastai-cli
description: Use Vast.ai CLI efficiently and safely for search, instance lifecycle, data movement, logs, and account operations with preflight, verification, and recovery playbooks.
---

# Vast.ai CLI Skill

Use this skill when you need reliable, efficient Vast.ai CLI execution with clear preflight checks, post-command verification, and fallback actions.

## When to Use This Skill

Invoke this skill when tasks involve:

- Finding and renting GPU instances
- Starting, stopping, rebooting, or destroying instances
- Moving data with `copy`, `cloud copy`, or `scp`
- Inspecting state with `show`, collecting logs, or running constrained remote commands
- Managing API keys, connections, teams, and other account-level CLI operations

Keywords: vast.ai, vastai, gpu instance, cloud copy, instance lifecycle, search offers, api key

## Core Workflow

Use this sequence for every operation:

1. Define intent
   - Clarify desired end state (e.g., "running instance", "data copied", "instance destroyed").
2. Preflight
   - Validate IDs and prerequisites (`instance`, `connection`, source/destination paths, current state).
3. Execute
   - Run the smallest command set needed to reach the target state.
4. Verify
   - Confirm with `vastai show ... --raw` or other direct checks immediately after execution.
5. Recover
   - If state is unexpected, follow playbook-specific fallback steps.

## Command Source of Truth

Prefer this precedence:

1. Installed CLI help (`vastai --help`, `vastai <command> --help`) for exact syntax on the current machine.
2. Official docs for semantics and caveats (`https://docs.vast.ai/cli`, `https://docs.vast.ai/cli/commands`).
3. Environment-specific runbooks only for optional integration guidance.

Primary references used for this skill:

- Vast.ai CLI docs: `https://docs.vast.ai/cli`
- Vast.ai CLI commands catalog: `https://docs.vast.ai/cli/commands`
- Local command inventory from `vastai --help` and key subcommand `--help` pages

## Safety Posture (Balanced)

- Low-risk commands (`show`, `search`, `logs`) can run directly.
- Medium-risk commands (`start`, `stop`, `reboot`, `update`, `copy`) require a quick preflight + explicit target verification.
- High-risk commands (`destroy instance`, bulk destroys, destructive `execute rm`) require explicit confirmation before execution.

Do not block power-user workflows, but always call out irreversible effects and provide a verification step.

## Command Routing

- Discovery and pricing: `search offers`, `search templates`, `show instances`
- Provisioning: `create instance`, `launch instance`
- Lifecycle: `show/start/stop/reboot/destroy`
- Data transfer: `copy`, `cloud copy`, `cancel copy`, `cancel sync`
- Access and debugging: `ssh-url`, `scp-url`, `logs`, `execute`
- Identity/admin: `set/create/show/delete/reset api-key`, team/subaccount operations

## References (Progressive Disclosure)

Load only what is needed:

- Command families and quick mapping:
  - `references/command-groups.md`
- Lifecycle flows (rent/start/recover/decommission):
  - `references/instance-lifecycle-playbooks.md`
- Data movement flows and constraints:
  - `references/data-transfer-playbooks.md`
- Guardrails, risk levels, and confirmation templates:
  - `references/safety-and-preflight.md`
- Multi-instance target disambiguation before decommission:
  - `references/instance-lifecycle-playbooks.md` (Playbook E)
