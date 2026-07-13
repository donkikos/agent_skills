---
name: update-changelog
description: Update a project's changelog from Git history and net file diffs only. Use when Codex needs to add, revise, or review CHANGELOG.md entries, summarize user-facing changes, or compare changes since the most recent commit that modified the changelog; if the user specifies a tag, commit, branch, or range, use that ref instead. Do not edit package version files, create branches, commit, tag, merge, or push.
---

# Update Changelog

## Overview

Update changelog entries from repository changes while preserving the project's existing changelog format. Keep the scope to changelog content only.

Research the changes thoroughly, then write sparingly: a changelog records **what changed for the reader**, not how it was built. Thorough input, terse output.

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
   - This step is research. Commit messages and diffs explain *how* the change works — that context is for you, not for the entry.

4. Match the existing changelog style.
   - Read the current top sections and bottom comparison links before editing.
   - Preserve heading style, ordering, link format, tense, and bullet style. Length is governed by step 5, not by the most verbose existing entry.
   - Prefer categories already used by the project, commonly `Added`, `Changed`, `Fixed`, and `Removed`; omit empty categories.

5. Write each entry as one line.
   - Add entries under an existing `Unreleased` section by default. For a numbered section, run `date +%Y-%m-%d` and use that exact date only when the user asks.
   - **An entry is one line: the user-visible change, plus at most the one identifier the reader would act on — a command, flag, file, config key, or API name.** Write it from the reader's side: what they can now do, or the symptom that is gone.
     - Added / Changed: name the capability or the difference, and the command/flag/file that exposes it.
     - Fixed: state the symptom the reader saw (e.g. `` `cpu_percent` was always `0.0` ``). The cause and the fix are in the commit.
   - What the reader never types, opens, or sets stays out of the entry and lives in the commit body and docs: internal mechanism, root cause, defaults, fallbacks, "best-effort", "takes effect on the next run". The changelog is *what changed*; git is *how*.
   - Self-check per bullet: if it reaches for "because", "so that", or "instead of", or runs to a second sentence, it has drifted into mechanism — cut back to the change.
   - Update comparison links only when the changelog already uses them and the target section requires one.

   Example — the same fix, bloated then right:
   > ❌ Per-run `cpu_percent` in `metrics.jsonl` was always `0.0` because the runner rebuilt psutil handles every monitor sample; handles are now cached across samples so CPU is measured over the interval. Takes effect on new run launches.
   >
   > ✅ `cpu_percent` in `metrics.jsonl` was always `0.0`.

6. Verify before finishing.
   - Re-run a focused diff of the changelog.
   - Coverage: every material net change has an entry, or a clear reason for omission.
   - Shape: each entry matches step 5 — one line, a user-visible change, no mechanism/cause/caveat. Trim any bullet that regressed into how-it-works.
   - Ensure no package version files, branch state, commits, tags, merges, or pushes were changed as part of this skill.
