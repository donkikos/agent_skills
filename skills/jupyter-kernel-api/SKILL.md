---
name: jupyter-kernel-api
description: Find running Jupyter Server kernels and execute custom code via the server API/WebSocket. Use when a user wants to connect to an existing Jupyter kernel, select it with minimal questions, run code, and return results.
metadata:
  short-description: Run code on an existing Jupyter kernel
---

# Jupyter Kernel API

Use this skill when the user wants to connect to an *existing* Jupyter Server kernel and run code via the server API (REST + WebSocket).

## Minimal questions to ask
Ask only what you can’t infer automatically:
1) **Server URL** (optional): the script auto-discovers running servers with `jupyter server list` if `--base-url` is omitted.
2) **Auth**: token or password. If a token appears in the server list URL, use it.
3) **Kernel selection**: kernel ID, or a notebook path/name substring to match.
4) **Code to run**.
5) **Output style** (only when needed): normal output vs `--result-only` for clean value extraction.

## Workflow

### 0) Resolve the skill directory (portable)
- Use the skill’s file path (shown in the skill metadata/context) to locate resources.
- Compute `SKILL_DIR` as the parent directory of `SKILL.md`.
- Run scripts via absolute paths like `$SKILL_DIR/scripts/...` (don’t rely on CWD; `cd` into `SKILL_DIR` if needed).

### 1) Discover server(s)
- Preferred: let the script auto-discover servers by omitting `--base-url`.
- Use explicit `--base-url` when you must target one specific server (host/port/base path).
- If needed, inspect servers directly:

```bash
jupyter server list
```

### 2) Select kernel
- Pass `--kernel-id` when known.
- Otherwise use `--kernel-match <substring>`.
- Matching checks both session `path` and `name`, and handles VS Code style notebook names like `to_accelerate_2-jvsc-...ipynb`.
- For regex matching, use `--kernel-match "re:<pattern>"`.
- If multiple matches are found, the script prints candidates with `kernel_id | server_url | path | name` so you can ask one follow-up question.

If you need to inspect sessions manually:

```bash
curl -s "<BASE_URL>/api/sessions?token=<TOKEN>" | python -m json.tool
```

### 3) Execute code on the chosen kernel
Provide code inline, from a file, or via stdin (for multiline without temp files). Inline `--code` supports literal `\n` sequences for newlines, but `--code-stdin` is preferred for real multiline.

Auto-discovery example:

```bash
python "$SKILL_DIR/scripts/jupyter_kernel_exec.py" \
  --kernel-match to_accelerate_2.ipynb \
  --code "1+1"
```

Explicit server example:

```bash
python "$SKILL_DIR/scripts/jupyter_kernel_exec.py" \
  --base-url http://localhost:8090 \
  --token <TOKEN> \
  --kernel-id <KERNEL_ID> \
  --code "print('hello')"
```

File and stdin examples:

```bash
python "$SKILL_DIR/scripts/jupyter_kernel_exec.py" \
  --base-url http://localhost:8090 \
  --token <TOKEN> \
  --kernel-id <KERNEL_ID> \
  --code-file /path/to/code.py
```

```bash
cat <<'PY' | python "$SKILL_DIR/scripts/jupyter_kernel_exec.py" \
  --base-url http://localhost:8090 \
  --token <TOKEN> \
  --kernel-id <KERNEL_ID> \
  --code-stdin
print("hello from stdin")
PY
```

### 4) Return results
Default output can include:
- `stream` output (stdout/stderr)
- `execute_result` (text/plain)
- `display_data`
- `error` traceback

Use `--result-only` when you want only computed values from `execute_result` (plus errors).

For structured output, pass `--json` to emit a single JSON summary. Use `--timeout <seconds>` to override the WebSocket read timeout.

## Notes / Troubleshooting
- **Secrets**: tokens are sensitive—don’t paste them into logs or commit them.
- **Sandbox**: if localhost networking is blocked, rerun commands with escalated permissions.
- **WebSocket dependency**: the script uses `websocket-client`. Install it in the active venv if missing.
- **Base URL path**: include any server base path (e.g., `http://host:port/user/name`). The script handles it.
- **No auto-discovered servers**: provide `--base-url` explicitly.
