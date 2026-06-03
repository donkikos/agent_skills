#!/usr/bin/env python3
"""Convert a Claude Code session .jsonl transcript into agent-friendly markdown.

Claude Code stores each session as a JSONL file under
``~/.claude/projects/<slug>/<session-id>.jsonl``. Each line is one event.
This tool keeps the meaningful conversation (user prompts, assistant text +
thinking, tool calls and their results) and drops the harness noise
(queue-operation, last-prompt, mode, system stop-hook summaries, hook
attachments, and injected skill-instruction text blocks).

Usage:
    export_session.py INPUT.jsonl [-o OUTPUT.md]
    export_session.py INPUT.jsonl --result-cap 2000

If -o/--output is omitted, writes alongside the input as
``<session-id>.md`` in the current directory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Entry "type" values that are pure harness bookkeeping, never conversation.
NOISE_TYPES = {"queue-operation", "last-prompt", "mode", "system", "attachment"}


def load(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def fmt_ts(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts


def is_skill_injection(text: str) -> bool:
    """System-injected text blocks (skill bodies, caveats) — not user-authored."""
    return text.startswith("Base directory for this skill:") or text.startswith(
        "Caveat: The messages below"
    )


def fence(text: str, lang: str = "") -> str:
    t = text.rstrip("\n")
    bt = "```"
    while bt in t:  # widen the fence if the body contains backtick runs
        bt += "`"
    return f"{bt}{lang}\n{t}\n{bt}"


def trim(text: str, cap: int) -> tuple[str, bool]:
    if cap <= 0 or len(text) <= cap:
        return text, False
    return text[:cap], True


def render_tool_use(b: dict) -> str:
    name = b.get("name", "?")
    inp = b.get("input", {})
    out = [f"**🔧 Tool call → `{name}`**"]
    if name == "Bash":
        if inp.get("description"):
            out.append(f"_{inp['description']}_")
        out.append(fence(inp.get("command", ""), "bash"))
    elif name == "Edit":
        out.append(f"`{inp.get('file_path', '')}`")
        out.append("Old:")
        out.append(fence(inp.get("old_string", "")))
        out.append("New:")
        out.append(fence(inp.get("new_string", "")))
    elif name == "Write":
        out.append(f"`{inp.get('file_path', '')}`")
        out.append(fence(inp.get("content", "")))
    else:
        out.append(fence(json.dumps(inp, indent=2), "json"))
    return "\n\n".join(out)


def tool_result_text(b: dict) -> str:
    """tool_result.content is either a plain string or a list of typed blocks."""
    c = b.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for x in c:
            if isinstance(x, dict):
                if x.get("type") == "text":
                    parts.append(x.get("text", ""))
                else:
                    parts.append(json.dumps(x))
            else:
                parts.append(str(x))
        return "\n".join(parts)
    return json.dumps(c)


def render_tool_result(b: dict, cap: int) -> str:
    txt = tool_result_text(b)
    body, trimmed = trim(txt, cap)
    label = "❌ Tool result (error)" if b.get("is_error") else "✅ Tool result"
    note = f"\n\n_(output truncated — {len(txt)} chars total)_" if trimmed else ""
    return f"<details>\n<summary>{label}</summary>\n\n{fence(body)}{note}\n</details>"


def convert(rows: list[dict], result_cap: int, think_cap: int) -> str:
    out: list[str] = []

    meta = next((r for r in rows if r.get("type") == "user" and r.get("sessionId")), {})
    timestamps = [r.get("timestamp") for r in rows if r.get("timestamp")]

    out += [
        "# Session Transcript",
        "",
        f"- **Session ID:** `{meta.get('sessionId', '')}`",
        f"- **Project:** `{meta.get('cwd', '')}`",
        f"- **Git branch:** `{meta.get('gitBranch', '')}`",
        f"- **Started:** {fmt_ts(timestamps[0]) if timestamps else ''}",
        f"- **Ended:** {fmt_ts(timestamps[-1]) if timestamps else ''}",
        "",
        "---",
        "",
    ]

    for r in rows:
        t = r.get("type")
        if t in NOISE_TYPES:
            continue

        if t == "user":
            c = r.get("message", {}).get("content")
            text_blocks, tr_blocks = [], []
            if isinstance(c, str):
                if c.startswith("<command-message>") or c.startswith("<command-name>"):
                    m = re.search(r"<command-name>([^<]*)</command-name>", c)
                    text_blocks.append(("cmd", (m.group(1).strip() if m else c.strip())))
                elif c.strip():
                    text_blocks.append(("text", c))
            elif isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and not is_skill_injection(b.get("text", "")):
                        text_blocks.append(("text", b["text"]))
                    elif b.get("type") == "tool_result":
                        tr_blocks.append(b)
            for kind, val in text_blocks:
                out += [f"## 👤 User — {fmt_ts(r.get('timestamp'))}", ""]
                out.append(f"_Invoked skill/command: `{val}`_" if kind == "cmd" else val.rstrip())
                out.append("")
            for b in tr_blocks:
                out += [render_tool_result(b, result_cap), ""]

        elif t == "assistant":
            c = r.get("message", {}).get("content")
            if not isinstance(c, list):
                continue
            header_done = False

            def header():
                nonlocal header_done
                if not header_done:
                    out.extend([f"## 🤖 Assistant — {fmt_ts(r.get('timestamp'))}", ""])
                    header_done = True

            for b in c:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "thinking":
                    th = b.get("thinking", "").strip()
                    if th:
                        header()
                        body, _ = trim(th, think_cap)
                        out += ["<details>\n<summary>💭 Thinking</summary>\n\n" + body + "\n</details>", ""]
                elif bt == "text":
                    txt = b.get("text", "").strip()
                    if txt:
                        header()
                        out += [txt, ""]
                elif bt == "tool_use":
                    header()
                    out += [render_tool_use(b), ""]

    text = "\n".join(out)
    while "\n\n\n\n" in text:
        text = text.replace("\n\n\n\n", "\n\n\n")
    return text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Path to the session .jsonl transcript")
    p.add_argument("-o", "--output", help="Output .md path (default: ./<session-id>.md)")
    p.add_argument("--result-cap", type=int, default=4000,
                   help="Max chars per tool result before truncation (0 = unlimited; default 4000)")
    p.add_argument("--think-cap", type=int, default=0,
                   help="Max chars per thinking block (0 = unlimited; default 0)")
    args = p.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        print(f"error: no such file: {src}", file=sys.stderr)
        return 1

    rows = load(str(src))
    md = convert(rows, args.result_cap, args.think_cap)

    if args.output:
        out_path = Path(args.output)
    else:
        sid = next((r.get("sessionId") for r in rows if r.get("sessionId")), None) or src.stem
        out_path = Path.cwd() / f"{sid}.md"

    out_path.write_text(md)
    print(f"Wrote {out_path} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
