---
name: run-release-process
description: Guide and execute a guarded software release workflow with SemVer version selection, version file updates, release branch handling, staging, commits, merges, tags, pushes, hotfix handling, and next development version preparation. Use when Codex is asked to release a version, prepare a release branch, tag a version, run a hotfix or patch release, or move main/dev branches through a release process.
---

# Run Release Process

## Overview

Run a release as an explicit, checkpointed Git workflow. Keep changelog preparation, version updates, branch operations, commits, merges, tags, pushes, and next-development setup deliberate and visible.

## Core Rules

- Ask for clarification when the target version or release type is ambiguous.
- Ensure the changelog is fully updated before version changes. Use whatever changelog update skill is available, such as `$update-changelog` or `$keep-a-changelog`; if no suitable skill is available or the target changelog workflow is unclear, ask the user how to handle the changelog update.
- A released changelog must not contain an `Unreleased` section. At release, convert the `Unreleased` heading into the dated version section — do not leave an empty `Unreleased` behind. Re-add a fresh empty `Unreleased` section only on the development branch, in the next-development step. This way every released snapshot (release branch, main, tag) is clean and only the development branch carries the accumulator.
- Confirm before staging, committing, merging, tagging, pushing, or changing branches when the action is consequential or not already explicitly requested.
- Run `git status` before each commit and before branch transitions.
- Use `--no-ff --no-edit` for merges so merge history is preserved and no editor opens.
- Use Git's default merge commit messages. Do not supply custom merge messages.
- Stop on merge conflicts, failed checks, unexpected dirty files, or failed Git commands; report the exact state and ask how to proceed.

## Version Rules

Use SemVer `X.Y.Z`.

- Exact version request: use the version named by the user.
- Major: `X.Y.Z` -> `X+1.0.0`.
- Minor: `X.Y.Z` -> `X.Y+1.0`.
- Patch or hotfix: `X.Y.Z` -> `X.Y.Z+1`.
- Next development version uses `.dev0`.
- After a normal minor or patch release, default next development version to the next minor: `X.Y.Z` -> `X.(Y+1).0.dev0`.
- After a major release to `A.0.0`, default next development version to `A.1.0.dev0` unless the repository uses a different convention.

Find version files from the repository's conventions. Common Python targets are:

- `pyproject.toml`: `version = "X.Y.Z"` or `version = "X.Y.Z.dev0"`.
- Package `__init__.py`: `__version__ = "X.Y.Z"` or `__version__ = "X.Y.Z.dev0"`.

Do not assume those paths are present; inspect the project first.

## Standard Workflow

1. Preflight.
   - Run `git branch --show-current` and `git status`.
   - Identify the current version, target version, default branch names, remote name, and version files.
   - If the user did not specify an exact version, calculate it from the requested release type and confirm when there is any doubt.

2. Prepare the release branch.
   - Use `release/{version}` unless the repository has a different established convention.
   - If not already on the correct branch, ask before checking it out or creating it.
   - Create a missing release branch from the current branch only after user approval.

3. Complete changelog and version updates.
   - Ensure the changelog update is complete using an available changelog skill or explicit user direction.
   - Run `date +%Y-%m-%d` when a dated changelog section is needed.
   - Convert the `Unreleased` section into `[{version}] - {date}` in place, preserving its entries. Do not leave an empty `Unreleased` heading on the release branch — the released changelog must not have one (see Core Rules).
   - Update every repository version source required for the release version.
   - Show the resulting diff to the user before committing when practical.

4. Validate.
   - Run the project's configured tests, lint, or build checks when they are discoverable and reasonable for the change scope.
   - If checks are unavailable or too expensive, state that before continuing.

5. Commit release preparation.
   - Run `git status`.
   - Ask before staging any unstaged files, listing the files to stage.
   - Commit with `chore: prepare release {version}` after approval.
   - Ask before pushing the release branch.

6. Merge, tag, and push.
   - Ask whether to finish the release and merge to the main branch.
   - Checkout the main branch, then merge the release branch with `git merge release/{version} --no-ff --no-edit`.
   - Ask before creating the tag; use a light tag named exactly `{version}` unless the repository requires another tag format.
   - Ask before pushing main and tags.

7. Prepare the next development version.
   - Ask whether to update the development branch.
   - Checkout the development branch and merge main with `git merge main --no-ff --no-edit`.
   - Ask whether the next cycle is minor or major; default to next minor when the user has no preference.
   - Update version files to the calculated `.dev0` version.
   - Add a fresh, empty `Unreleased` section at the top of the changelog (above the just-released version section). This is the only place the `Unreleased` heading is reintroduced after a release.
   - Commit with `chore: prepare for {next_version} development` after approval.
   - Ask before pushing the development branch.

## Hotfix Workflow

Use this path for urgent patch releases from a hotfix branch.

1. Verify the current branch is the intended hotfix branch; ask if it is not.
2. Calculate or confirm the patch version.
3. Ensure the changelog is fully updated using an available changelog skill or explicit user direction. Convert any `Unreleased` heading into the dated hotfix version section; the hotfix branch and main must not carry an empty `Unreleased` (see Core Rules).
4. Update all required version files to the patch version.
5. Commit with `chore: prepare hotfix release {version}` after staging approval.
6. Checkout main and merge the hotfix branch with `--no-ff --no-edit`.
7. Create a light tag named exactly `{version}` after approval.
8. Checkout the development branch and merge main with `--no-ff --no-edit`. Ensure the development branch has a fresh, empty `Unreleased` section at the top of the changelog (add one if absent).
9. During conflicts, keep the development branch's `.dev0` version numbers while preserving the hotfix changelog entry.
10. Push branches and tags only after explicit approval.
