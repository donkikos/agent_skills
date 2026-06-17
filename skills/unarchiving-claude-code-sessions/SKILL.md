---
name: unarchiving-claude-code-sessions
description: Use when a user wants to unarchive, restore, un-hide, or bring back an archived Claude Code / CCD session on macOS — the Code tab has a delete icon but no unarchive button, so the session's isArchived flag must be flipped to false on disk and the app restarted.
metadata:
  short-description: Restore an archived Claude Code session by flipping isArchived on disk
---

# Unarchiving Claude Code Sessions (macOS)

Claude Desktop's Code tab can archive sessions but has **no native unarchive
button** — hovering an archived session only offers delete. The session metadata,
including the `isArchived` flag, lives in a local JSON file. Unarchiving means
flipping that one field to `false` and restarting the app.

There is also no tool for this: `mcp__ccd_session_mgmt__archive_session` is
one-directional and `list_sessions` is read-only. Editing the file is the
supported workaround.

## When to use

- "unarchive this session", "restore that archived chat", "bring back session X"
- "there's no unarchive button" / "how do I undo archiving a Code session"
- You have a sessionId (from `mcp__ccd_session_mgmt__list_sessions` with
  `include_archived: true`) or a title keyword to locate.

## Where sessions live

```
~/Library/Application Support/Claude/claude-code-sessions/<orgId>/<userId>/local_<sessionId>.json
```

**Note:** NOT `local-agent-mode-sessions/` — that directory holds plugin/skill
data, not session transcripts. Sessions may show Linux `cwd` paths (remote agent
sessions); their metadata JSON still lives locally on the Mac.

## Workflow

### 1) Find the session file

If you have the sessionId:
```bash
grep -rl "<sessionId>" ~/Library/Application\ Support/Claude/claude-code-sessions/
```

Or find archived sessions by title keyword:
```bash
grep -rl '"isArchived":true' ~/Library/Application\ Support/Claude/claude-code-sessions/ \
  | xargs grep -l '"title":"[^"]*<keyword>'
```

### 2) Verify before editing

Confirm the title and that there is exactly one `isArchived` occurrence:
```bash
grep -o '"title":"[^"]*"' "$f" | head -1
grep -c '"isArchived"' "$f"      # expect 1
```

### 3) Back up, then flip the single field

```bash
cp "$f" "$f.bak"
perl -0777 -i -pe 's/"isArchived":true/"isArchived":false/' "$f"
grep -o '"isArchived":[^,]*' "$f"   # verify => false
```

### 4) Restart Claude Desktop

Quit and reopen the app. Session state is cached in memory; the session
reappears in the active list only after a restart.

### 5) Clean up

Once you confirm it's back, delete the `.bak`.

## Common mistakes

- **Wrong directory** (`local-agent-mode-sessions/`) — it won't contain the session.
- **Touching other fields** — flip only the one `isArchived` boolean; leave the
  rest of the JSON untouched.
- **Expecting it without a restart** — the in-memory cache must be reloaded.
- **Blind sed/perl with multiple matches** — always confirm `grep -c` returns 1 first.
