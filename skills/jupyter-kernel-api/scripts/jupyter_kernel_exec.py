#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
import json
import re
import sys
import uuid
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import urlopen, Request


def _add_token(url: str, token: str | None) -> str:
    if not token:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode({'token': token})}"


def _http_get_json(url: str) -> list | dict:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req) as resp:
        return json.load(resp)


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _build_ws_url(base_url: str, kernel_id: str, token: str | None) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    # Preserve any base path (e.g., /user/name)
    path = parsed.path.rstrip("/")
    ws_path = f"{path}/api/kernels/{kernel_id}/channels"
    ws_url = urlunparse((scheme, parsed.netloc, ws_path, "", "", ""))
    return _add_token(ws_url, token)


def resolve_kernel_id(base_url: str, token: str | None, kernel_for: str) -> str:
    url = _add_token(f"{base_url}/api/sessions", token)
    data = _http_get_json(url)
    matches = []
    for s in data:
        path = s.get("path", "")
        if kernel_for in path:
            k = s.get("kernel", {})
            matches.append((k.get("id"), k.get("name"), path))
    if not matches:
        print(f"No sessions matched substring: {kernel_for}")
        sys.exit(1)
    if len(matches) > 1:
        print("Multiple matches found. Specify a kernel id or refine the substring:")
        for kid, kname, path in matches:
            print(kid, kname, path)
        sys.exit(1)
    return matches[0][0]


def resolve_kernel_id_regex(base_url: str, token: str | None, pattern: str) -> str:
    url = _add_token(f"{base_url}/api/sessions", token)
    data = _http_get_json(url)
    matches = []
    try:
        rx = re.compile(pattern)
    except re.error as e:
        print(f"Invalid regex: {e}")
        sys.exit(1)
    for s in data:
        path = s.get("path", "")
        if rx.search(path):
            k = s.get("kernel", {})
            matches.append((k.get("id"), k.get("name"), path))
    if not matches:
        print(f"No sessions matched regex: {pattern}")
        sys.exit(1)
    if len(matches) > 1:
        print("Multiple matches found. Specify a kernel id or refine the regex:")
        for kid, kname, path in matches:
            print(kid, kname, path)
        sys.exit(1)
    return matches[0][0]


def resolve_kernel_id_match(base_url: str, token: str | None, match: str) -> str:
    if match.startswith("re:"):
        return resolve_kernel_id_regex(base_url, token, match[3:])
    return resolve_kernel_id(base_url, token, match)


def execute_code(
    base_url: str,
    token: str | None,
    kernel_id: str,
    code: str,
    timeout: int,
    json_output: bool,
) -> None:
    try:
        import websocket  # type: ignore
    except Exception:
        print(
            "Missing dependency: websocket-client. Install with: pip install websocket-client"
        )
        sys.exit(2)

    ws_url = _build_ws_url(base_url, kernel_id, token)
    ws = websocket.create_connection(ws_url)
    ws.settimeout(timeout)

    msg_id = uuid.uuid4().hex
    session_id = uuid.uuid4().hex
    header = {
        "msg_id": msg_id,
        "username": "api",
        "session": session_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "msg_type": "execute_request",
        "version": "5.3",
    }
    msg = {
        "header": header,
        "parent_header": {},
        "metadata": {},
        "content": {
            "code": code,
            "silent": False,
            "store_history": True,
            "user_expressions": {},
            "allow_stdin": False,
            "stop_on_error": True,
        },
        "channel": "shell",
    }
    ws.send(json.dumps(msg))

    outputs = []
    had_error = False
    while True:
        raw = ws.recv()
        data = json.loads(raw)
        msg_type = data.get("msg_type")
        parent_id = data.get("parent_header", {}).get("msg_id")

        if msg_type == "stream":
            content = data.get("content", {})
            text = content.get("text", "")
            if json_output:
                outputs.append({"type": "stream", "content": content})
            elif text:
                print(text, end="")
        elif msg_type in ("execute_result", "display_data"):
            content = data.get("content", {})
            payload = content.get("data", {})
            if json_output:
                outputs.append({"type": msg_type, "content": content})
            else:
                text = payload.get("text/plain")
                if text:
                    print(text)
                else:
                    print(json.dumps(payload))
        elif msg_type == "error":
            content = data.get("content", {})
            had_error = True
            if json_output:
                outputs.append({"type": "error", "content": content})
            else:
                tb = content.get("traceback", [])
                if tb:
                    print("\n".join(tb))
                else:
                    print(content)
        elif msg_type == "status":
            state = data.get("content", {}).get("execution_state")
            if state == "idle" and parent_id == msg_id:
                break

    ws.close()
    if json_output:
        print(
            json.dumps(
                {
                    "kernel_id": kernel_id,
                    "msg_id": msg_id,
                    "status": "error" if had_error else "ok",
                    "outputs": outputs,
                }
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute code on an existing Jupyter kernel via API."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Jupyter server base URL, e.g. http://localhost:8080",
    )
    parser.add_argument(
        "--token", default=None, help="Jupyter token (optional if server is open)"
    )
    parser.add_argument("--kernel-id", help="Kernel ID to execute against")
    parser.add_argument(
        "--kernel-match",
        help="Match session path to resolve kernel ID. Use 're:<pattern>' for regex.",
    )
    parser.add_argument(
        "--code",
        help="Inline code to execute (literal \\n sequences are converted to newlines)",
    )
    parser.add_argument("--code-file", help="Path to file with code to execute")
    parser.add_argument(
        "--code-stdin", action="store_true", help="Read code from stdin"
    )
    parser.add_argument(
        "--timeout", type=int, default=60, help="WebSocket read timeout seconds"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON summary of outputs"
    )
    args = parser.parse_args()

    base_url = _normalize_base_url(args.base_url)

    kernel_id = args.kernel_id
    if not kernel_id and args.kernel_match:
        kernel_id = resolve_kernel_id_match(base_url, args.token, args.kernel_match)
    if not kernel_id:
        print("Missing --kernel-id (or use --kernel-for).")
        sys.exit(1)

    code_sources = sum(bool(x) for x in (args.code, args.code_file, args.code_stdin))
    if code_sources > 1:
        print("Provide only one of --code, --code-file, or --code-stdin.")
        sys.exit(1)
    if code_sources == 0:
        print("Missing code. Use --code, --code-file, or --code-stdin.")
        sys.exit(1)

    if args.code_file:
        with open(args.code_file, "r", encoding="utf-8") as f:
            code = f.read()
    elif args.code_stdin:
        code = sys.stdin.read()
    else:
        code = args.code.replace("\\n", "\n")

    execute_code(base_url, args.token, kernel_id, code, args.timeout, args.json)


if __name__ == "__main__":
    main()
