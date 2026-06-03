---
name: update-changelog
description: Update a project's changelog from Git history and net file diffs only. Use when Codex needs to add, revise, or review CHANGELOG.md entries, summarize user-facing changes, or compare changes since the most recent commit that modified the changelog; if the user specifies a tag, commit, branch, or range, use that ref instead. Do not edit package version files, create branches, commit, tag, merge, or push.
---

# Update Changelog

## Overview

Update changelog entries from repository changes while preserving the project's existing changelog format. Keep the scope to changelog content only.

## Workflow

1. Locate the changelog file.
   - Prefer `CHANGELOG.md` at the repository root.
   - If multiple changelog files exist, choose the one matching the user's target package or ask when the target is unclear.

2. Determine the comparison baseline.
   - If the user names a tag, commit, branch, or range, use that exact baseline.
   - Otherwise find the most recent commit that modified the changelog:
     ```bash
     git log -n 1 --format=%H -- CHANGELOG.md
     ```
   - Compare the baseline to the current working tree, not only committed `HEAD`, so staged and unstaged changes are included:
     ```bash
     git diff --name-status <baseline>
     git diff --stat <baseline>
     git log --oneline <baseline>..HEAD
     ```
   - If the changelog has no history, inspect the whole available project history and current diff, then state that no prior changelog-update commit was found.

3. Review the net changes thoroughly.
   - Inspect every changed source, config, schema, documentation, and test file that may imply user-visible behavior.
   - Use per-file diffs for meaningful files:
     ```bash
     git diff <baseline> -- <path>
     ```
   - Treat lockfiles, generated files, formatting-only edits, and internal refactors as supporting evidence unless they affect users.

4. Match the existing changelog style.
   - Read the current top sections and bottom comparison links before editing.
   - Preserve heading style, ordering, link format, tense, and bullet style.
   - Use concise, single-level bullets.
   - Prefer categories already used by the project, commonly `Added`, `Changed`, `Fixed`, and `Removed`; omit empty categories.

5. Write changelog entries.
   - Add entries under an existing `Unreleased` section by default.
   - If the user explicitly asks for a numbered section, run `date +%Y-%m-%d` and use that exact date.
   - Mention concrete modules, commands, options, database tables, schemas, API names, or behavior when useful.
   - Avoid documenting purely internal churn unless it matters to downstream users.
   - Update comparison links only when the current changelog already uses them and the target section requires a link.

6. Verify before finishing.
   - Re-run a focused diff of the changelog.
   - Confirm every material net change has either a changelog entry or a clear reason for omission.
   - Ensure no package version files, branch state, commits, tags, merges, or pushes were changed as part of this skill.
