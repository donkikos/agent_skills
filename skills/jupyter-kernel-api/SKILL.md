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
1) **Server URL** (host + port). If not provided, use `jupyter server list`.
2) **Auth**: token or password. If a token appears in the server list URL, use it.
3) **Kernel selection**: kernel ID, or a notebook path/name substring to match.
4) **Code to run**.

## Workflow

### 1) Discover the server (no abstraction)
- Run `jupyter server list` (or `jupyter notebook list`) to get URL + token.
- If none running, ask the user for URL and token/password.

### 2) Select kernel (minimal abstraction)
Use the script to resolve a kernel by notebook path substring, or pass a kernel id directly. If multiple matches are found, the script exits with a message so you can ask a single follow‑up question.

If you need to see all sessions, do it directly (no abstraction):

```bash
curl -s "<BASE_URL>/api/sessions?token=<TOKEN>" | python -m json.tool
```

### 3) Execute code on the chosen kernel
Provide code inline, from a file, or via stdin (for multiline without temp files):

```bash
python skills/jupyter-kernel-api/scripts/jupyter_kernel_exec.py \
  --base-url http://localhost:8080 \
  --token <TOKEN> \
  --kernel-id <KERNEL_ID> \
  --code "print('hello')"
```

Or:

```bash
python skills/jupyter-kernel-api/scripts/jupyter_kernel_exec.py \
  --base-url http://localhost:8080 \
  --token <TOKEN> \
  --kernel-id <KERNEL_ID> \
  --code-file /path/to/code.py

```bash
cat <<'PY' | python skills/jupyter-kernel-api/scripts/jupyter_kernel_exec.py \
  --base-url http://localhost:8080 \
  --token <TOKEN> \
  --kernel-id <KERNEL_ID> \
  --code-stdin
print("hello from stdin")
PY
```

If the user gives a notebook name/path instead of a kernel ID, pass `--kernel-match <substring>` to select the matching session automatically. If multiple match, the script prints candidates and exits so you can ask a single follow‑up question.

For regex matching, use `--kernel-match "re:<pattern>"`.

### 4) Return results
The script prints:
- `stream` output (stdout/stderr)
- `execute_result` (text/plain)
- `error` traceback (if any)

Summarize the output and show key lines. If the kernel is busy, wait for `status: idle` for the request’s `msg_id`.

For structured output, pass `--json` to emit a single JSON summary. Use `--timeout <seconds>` to override the WebSocket read timeout.

## Notes / Troubleshooting
- **Secrets**: tokens are sensitive—don’t paste them into logs or commit them.
- **Sandbox**: if localhost networking is blocked, rerun commands with escalated permissions.
- **WebSocket dependency**: the script uses `websocket-client`. Install it in the active venv if missing.
- **Base URL**: include any server base path (e.g., `http://host:port/user/name`). The script handles it.
