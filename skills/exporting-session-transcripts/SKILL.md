---
name: exporting-session-transcripts
description: Use when a user wants a readable or agent-friendly markdown export of a Claude Code session, conversation log, or .jsonl transcript — converting the raw session JSONL under ~/.claude/projects/ into clean markdown with user prompts, assistant text, thinking, and tool calls/results, stripping harness noise.
metadata:
  short-description: Export a Claude Code session .jsonl to clean markdown
---

# Exporting Session Transcripts

Claude Code records every session as a JSONL file (one event per line) under
`~/.claude/projects/<project-slug>/<session-id>.jsonl`. This skill converts that
raw transcript into agent-friendly markdown: real conversation only, harness
bookkeeping removed.

## When to use

- "export this session as markdown", "give me a readable log of this conversation"
- "convert this `.jsonl` transcript", "agent-friendly export of session X"
- You have a path to a `*.jsonl` under `~/.claude/projects/...` to turn into docs.

## Workflow

### 0) Resolve the skill directory (portable)
Compute `SKILL_DIR` as the directory containing this `SKILL.md` (shown in the
skill's path/context). Run the script via an absolute path; don't rely on CWD.

### 1) Find the transcript
Session files live at `~/.claude/projects/<slug>/<session-id>.jsonl`. The slug is
the cwd with `/` replaced by `-`. If the user gave a path, use it directly.

```bash
ls -t ~/.claude/projects/*/*.jsonl | head    # most recent sessions
```

### 2) Run the converter

```bash
python3 "$SKILL_DIR/scripts/export_session.py" /path/to/<session-id>.jsonl
```

Writes `./<session-id>.md`. Pass `-o OUT.md` for a specific path. Run with
`--help` for all flags. Useful options:

- `-o, --output PATH` — output file (default `./<session-id>.md`)
- `--result-cap N` — truncate each tool result to N chars (default 4000; `0` = unlimited)
- `--think-cap N` — truncate each thinking block (default `0` = unlimited)

## What the output contains

- **Header** — session id, project cwd, git branch, start/end timestamps.
- **👤 User** turns — real prompts; slash commands shown as `_Invoked skill/command: …_`.
- **🤖 Assistant** turns — text inline; **💭 Thinking** in collapsible `<details>`;
  tool calls rendered per tool (Bash → command, Edit/Write → file + diff/content,
  others → JSON input).
- **Tool results** in collapsible `<details>`, truncated per `--result-cap`,
  errors flagged ❌.

## What it strips (and why it matters)

A naive line-by-line dump is wrong. The script drops these on purpose:

- Entry types that are pure harness bookkeeping: `queue-operation`, `last-prompt`,
  `mode`, `system` (stop-hook summaries), `attachment` (hook output dumps).
- Injected text blocks that look like user messages but aren't — skill bodies
  (`Base directory for this skill:` …) and `Caveat:` preambles.

It also handles the two shapes `tool_result.content` can take — a plain string,
or a list of typed blocks (`{type: text, ...}`) — which is easy to miss and
produces garbled output if mishandled.

## Notes

- Pure stdlib Python 3.9+ (uses `from __future__ import annotations`); no deps.
  Invoke with `python3` (the script is also executable: `chmod +x` then run directly).
- Idempotent and read-only on the source; it only writes the markdown output.
- Large sessions: keep `--result-cap` modest (e.g. 2000) for a scannable doc, or
  set it to `0` when you need the full tool output.
