#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
import uuid
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


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


def _normalize_session_value(value: str) -> str:
    normalized = value.replace("\\", "/")
    normalized = re.sub(r"-jvsc-[^.]+(?=\.ipynb$)", "", normalized)
    normalized = re.sub(
        r"-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}(?=\.ipynb$)",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _session_strings(session: dict) -> set[str]:
    values: set[str] = set()
    for key in ("path", "name"):
        raw = session.get(key, "")
        if not isinstance(raw, str) or not raw:
            continue
        normalized = _normalize_session_value(raw)
        for candidate in (
            raw,
            os.path.basename(raw),
            normalized,
            os.path.basename(normalized),
        ):
            if candidate:
                values.add(candidate)
    return values


def _notebook_like_match(query: str, candidate: str) -> bool:
    query_base = os.path.basename(query)
    candidate_base = os.path.basename(candidate)
    query_stem, query_ext = os.path.splitext(query_base)
    candidate_stem, candidate_ext = os.path.splitext(candidate_base)

    if not query_stem:
        return False
    if query_ext and query_ext.lower() != candidate_ext.lower():
        return False
    return candidate_stem == query_stem or candidate_stem.startswith(f"{query_stem}-")


def _session_matches_substring(session: dict, kernel_for: str) -> bool:
    for value in _session_strings(session):
        if kernel_for in value:
            return True
        if _notebook_like_match(kernel_for, value):
            return True
    return False


def _session_matches_regex(session: dict, pattern: re.Pattern[str]) -> bool:
    for value in _session_strings(session):
        if pattern.search(value):
            return True
    return False


def _build_ws_url(base_url: str, kernel_id: str, token: str | None) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    # Preserve any base path (e.g., /user/name)
    path = parsed.path.rstrip("/")
    ws_path = f"{path}/api/kernels/{kernel_id}/channels"
    ws_url = urlunparse((scheme, parsed.netloc, ws_path, "", "", ""))
    return _add_token(ws_url, token)


def _parse_server_list(stdout: str) -> list[dict]:
    payload = stdout.strip()
    if not payload:
        return []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        # Fallback if output contains non-JSON lines before the JSON array.
        match = re.search(r"(\[\s*{.*}\s*\])\s*$", payload, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, dict)]


def discover_servers(token_fallback: str | None) -> list[dict[str, str | None]]:
    try:
        proc = subprocess.run(
            ["jupyter", "server", "list", "--jsonlist"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []

    servers: list[dict[str, str | None]] = []
    for item in _parse_server_list(proc.stdout):
        url = item.get("url", "")
        if not isinstance(url, str) or not url:
            continue

        token = item.get("token")
        root_dir = item.get("root_dir")

        normalized_token = token if isinstance(token, str) and token else None
        if not normalized_token:
            normalized_token = token_fallback

        servers.append(
            {
                "base_url": _normalize_base_url(url),
                "token": normalized_token,
                "root_dir": root_dir if isinstance(root_dir, str) else None,
            }
        )
    return servers


def _query_sessions(base_url: str, token: str | None) -> list[dict]:
    url = _add_token(f"{base_url}/api/sessions", token)
    data = _http_get_json(url)
    if not isinstance(data, list):
        raise RuntimeError("Unexpected /api/sessions response shape.")
    return [entry for entry in data if isinstance(entry, dict)]


def _collect_records(
    servers: list[dict[str, str | None]],
) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []

    for server in servers:
        base_url = server["base_url"]
        token = server.get("token")

        try:
            sessions = _query_sessions(base_url, token)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{base_url}: {exc}")
            continue

        for session in sessions:
            kernel = session.get("kernel", {})
            if not isinstance(kernel, dict):
                continue

            kernel_id = kernel.get("id")
            if not isinstance(kernel_id, str) or not kernel_id:
                continue

            records.append(
                {
                    "kernel_id": kernel_id,
                    "server_base_url": base_url,
                    "server_token": token,
                    "session": session,
                }
            )

    return records, errors


def _print_search_context(
    servers: list[dict[str, str | None]], errors: list[str]
) -> None:
    print("Searched servers:")
    for server in servers:
        print(f"- {server['base_url']}")
    if errors:
        print("Session query errors:")
        for err in errors:
            print(f"- {err}")


def _record_line(record: dict) -> str:
    session = record.get("session", {})
    path = session.get("path", "") if isinstance(session, dict) else ""
    name = session.get("name", "") if isinstance(session, dict) else ""
    return (
        f"{record['kernel_id']} | {record['server_base_url']} | "
        f"path={path} | name={name}"
    )


def resolve_kernel_target(
    servers: list[dict[str, str | None]],
    kernel_id: str | None,
    kernel_match: str | None,
) -> tuple[str, str | None, str]:
    records, errors = _collect_records(servers)
    if not records:
        print("Unable to find any running sessions on the selected servers.")
        _print_search_context(servers, errors)
        sys.exit(1)

    matches: list[dict]
    no_match_message: str

    if kernel_id:
        matches = [record for record in records if record["kernel_id"] == kernel_id]
        no_match_message = f"No sessions matched kernel id: {kernel_id}"
    elif kernel_match:
        if kernel_match.startswith("re:"):
            pattern = kernel_match[3:]
            try:
                regex = re.compile(pattern)
            except re.error as exc:
                print(f"Invalid regex: {exc}")
                sys.exit(1)

            matches = [
                record
                for record in records
                if _session_matches_regex(record["session"], regex)
            ]
            no_match_message = f"No sessions matched regex: {pattern}"
        else:
            matches = [
                record
                for record in records
                if _session_matches_substring(record["session"], kernel_match)
            ]
            no_match_message = f"No sessions matched substring: {kernel_match}"
    else:
        print("Missing --kernel-id (or use --kernel-match).")
        sys.exit(1)

    if not matches:
        print(no_match_message)
        _print_search_context(servers, errors)
        sys.exit(1)

    if len(matches) > 1:
        print("Multiple matches found. Specify --kernel-id or refine --kernel-match:")
        for record in matches:
            print(_record_line(record))
        sys.exit(1)

    chosen = matches[0]
    return chosen["server_base_url"], chosen.get("server_token"), chosen["kernel_id"]


def execute_code(
    base_url: str,
    token: str | None,
    kernel_id: str,
    code: str,
    timeout: int,
    json_output: bool,
    result_only: bool,
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

    try:
        while True:
            raw = ws.recv()
            data = json.loads(raw)
            msg_type = data.get("msg_type")
            parent_id = data.get("parent_header", {}).get("msg_id")

            if msg_type != "status" and parent_id != msg_id:
                continue

            if msg_type == "stream":
                if result_only:
                    continue
                content = data.get("content", {})
                text = content.get("text", "")
                if json_output:
                    outputs.append({"type": "stream", "content": content})
                elif text:
                    print(text, end="")
            elif msg_type in ("execute_result", "display_data"):
                if result_only and msg_type != "execute_result":
                    continue
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
    finally:
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
        default=None,
        help="Jupyter server base URL, e.g. http://localhost:8080",
    )
    parser.add_argument(
        "--auto-discover",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Discover running Jupyter servers with `jupyter server list` when "
            "--base-url is omitted."
        ),
    )
    parser.add_argument(
        "--token", default=None, help="Jupyter token (optional if server is open)"
    )
    parser.add_argument("--kernel-id", help="Kernel ID to execute against")
    parser.add_argument(
        "--kernel-match",
        help="Match session path/name to resolve kernel ID. Use 're:<pattern>' for regex.",
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
    parser.add_argument(
        "--result-only",
        action="store_true",
        help="Only emit execute_result values (plus errors).",
    )
    args = parser.parse_args()

    if args.base_url:
        servers = [
            {
                "base_url": _normalize_base_url(args.base_url),
                "token": args.token,
                "root_dir": None,
            }
        ]
    else:
        if not args.auto_discover:
            print("Missing --base-url. Enable --auto-discover or provide --base-url.")
            sys.exit(1)
        servers = discover_servers(args.token)
        if not servers:
            print(
                "No running Jupyter servers found via `jupyter server list`. "
                "Provide --base-url manually."
            )
            sys.exit(1)

    if args.kernel_id and args.kernel_match:
        print("Provide only one of --kernel-id or --kernel-match.")
        sys.exit(1)

    if not args.kernel_id and not args.kernel_match:
        print("Missing --kernel-id (or use --kernel-match).")
        sys.exit(1)

    if args.kernel_id and args.base_url:
        base_url = servers[0]["base_url"]
        token = servers[0].get("token")
        kernel_id = args.kernel_id
    else:
        base_url, token, kernel_id = resolve_kernel_target(
            servers, args.kernel_id, args.kernel_match
        )

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

    execute_code(
        base_url,
        token,
        kernel_id,
        code,
        args.timeout,
        args.json,
        args.result_only,
    )


if __name__ == "__main__":
    main()
