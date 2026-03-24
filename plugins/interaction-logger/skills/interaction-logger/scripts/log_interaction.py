#!/usr/bin/env python3
"""
Interaction Logger for Claude Code
Appends user prompts and Claude responses to a persistent JSONL history file.

Log file location (in priority order):
  1. INTERACTION_LOG_FILE env var  — absolute path to log file
  2. INTERACTION_LOG_DIR env var   — directory to write interaction_history.jsonl into
  3. Current working directory     — writes .interaction_history.jsonl in cwd

Session file location:
  1. INTERACTION_LOG_DIR env var   — same dir as log file
  2. Current working directory
"""

import argparse
import fcntl
import json
import os
import random
import string
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ── Config ──────────────────────────────────────────────────────────────────

SESSION_MAX_AGE_SECONDS = 8 * 60 * 60  # 8 hours


def _resolve_log_file() -> Path:
    if os.environ.get("INTERACTION_LOG_FILE"):
        return Path(os.environ["INTERACTION_LOG_FILE"])
    if os.environ.get("INTERACTION_LOG_DIR"):
        return Path(os.environ["INTERACTION_LOG_DIR"]) / "interaction_history.jsonl"
    return Path(os.getcwd()) / ".interaction_history.jsonl"


def _resolve_session_file() -> Path:
    if os.environ.get("INTERACTION_LOG_FILE"):
        return Path(os.environ["INTERACTION_LOG_FILE"]).parent / ".interaction_session"
    if os.environ.get("INTERACTION_LOG_DIR"):
        return Path(os.environ["INTERACTION_LOG_DIR"]) / ".interaction_session"
    return Path(os.getcwd()) / ".interaction_session"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _short_id(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def get_or_create_session(force_new: bool = False) -> str:
    session_file = _resolve_session_file()
    session_file.parent.mkdir(parents=True, exist_ok=True)

    if not force_new and session_file.exists():
        age = time.time() - session_file.stat().st_mtime
        if age < SESSION_MAX_AGE_SECONDS:
            return session_file.read_text().strip()

    session_id = _short_id(8)
    session_file.write_text(session_id)
    return session_id


def get_next_sequence(log_path: Path, session_id: str) -> int:
    if not log_path.exists():
        return 1
    seq = 0
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("session_id") == session_id:
                        seq = max(seq, entry.get("sequence", 0))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return seq + 1


def append_entry(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def get_context() -> dict:
    return {
        "cwd": os.getcwd(),
        "tool": "claude-code",
    }


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_log(args) -> None:
    log_path = _resolve_log_file()
    session_id = get_or_create_session()
    sequence = get_next_sequence(log_path, session_id)

    content = args.content
    if not content:
        content = sys.stdin.read()

    entry = {
        "id": _uuid(),
        "timestamp": _now_iso(),
        "session_id": session_id,
        "sequence": sequence,
        "role": args.role,
        "content": content,
        "context": get_context(),
    }

    append_entry(log_path, entry)
    print(f"[interaction-logger] Logged {args.role} entry (session={session_id}, seq={sequence})")


def cmd_new_session(args) -> None:
    session_id = get_or_create_session(force_new=True)
    print(f"[interaction-logger] New session started: {session_id}")


def cmd_view(args) -> None:
    log_path = _resolve_log_file()
    if not log_path.exists():
        print(f"No interaction history found at: {log_path}")
        return

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if args.session:
        entries = [e for e in entries if e.get("session_id") == args.session]

    if args.last:
        entries = entries[-args.last:]

    for e in entries:
        ts = e.get("timestamp", "")
        role = e.get("role", "?").upper()
        session = e.get("session_id", "?")
        seq = e.get("sequence", "?")
        content = e.get("content", "")
        if len(content) > 300 and not args.full:
            content = content[:300] + "… [truncated, use --full to see all]"
        print(f"\n{'─'*60}")
        print(f"[{ts}] {role}  session={session}  seq={seq}")
        print(f"{'─'*60}")
        print(content)

    print(f"\n{'─'*60}")
    print(f"Total entries shown: {len(entries)}")
    print(f"Log file: {log_path}")


def cmd_search(args) -> None:
    log_path = _resolve_log_file()
    if not log_path.exists():
        print(f"No interaction history found at: {log_path}")
        return

    keyword = args.search.lower()
    matches = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if keyword in entry.get("content", "").lower():
                    matches.append(entry)
            except json.JSONDecodeError:
                pass

    if not matches:
        print(f"No entries found matching: {args.search!r}")
        return

    for e in matches:
        ts = e.get("timestamp", "")
        role = e.get("role", "?").upper()
        session = e.get("session_id", "?")
        seq = e.get("sequence", "?")
        content = e.get("content", "")
        print(f"\n[{ts}] {role}  session={session}  seq={seq}")
        print(content[:500])

    print(f"\nFound {len(matches)} matching entries.")


def cmd_stats(args) -> None:
    log_path = _resolve_log_file()
    if not log_path.exists():
        print(f"No interaction history found at: {log_path}")
        return

    sessions = {}
    total = 0
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                sid = entry.get("session_id", "unknown")
                sessions.setdefault(sid, {"user": 0, "assistant": 0, "first": entry["timestamp"], "last": entry["timestamp"]})
                role = entry.get("role", "unknown")
                if role in ("user", "assistant"):
                    sessions[sid][role] += 1
                sessions[sid]["last"] = entry["timestamp"]
                total += 1
            except (json.JSONDecodeError, KeyError):
                pass

    print(f"\nInteraction History Stats")
    print(f"{'─'*50}")
    print(f"Total entries: {total}")
    print(f"Total sessions: {len(sessions)}")
    print(f"\nSessions (most recent first):")
    for sid, data in sorted(sessions.items(), key=lambda x: x[1]["last"], reverse=True):
        print(f"  {sid}  |  {data['user']} prompts, {data['assistant']} responses  |  {data['first'][:19]} → {data['last'][:19]}")
    print(f"\nLog file: {log_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Claude Code Interaction Logger")
    parser.add_argument("--role", choices=["user", "assistant"], help="Role of the entry to log")
    parser.add_argument("--content", type=str, default="", help="Content to log (or pass via stdin)")
    parser.add_argument("--new-session", action="store_true", help="Force start a new session")
    parser.add_argument("--view", action="store_true", help="View recent interactions")
    parser.add_argument("--last", type=int, default=20, help="Number of recent entries to show (with --view)")
    parser.add_argument("--full", action="store_true", help="Show full content without truncation")
    parser.add_argument("--session", type=str, help="Filter by session ID (with --view)")
    parser.add_argument("--search", type=str, help="Search for keyword in history")
    parser.add_argument("--stats", action="store_true", help="Show session statistics")

    args = parser.parse_args()

    if args.new_session:
        cmd_new_session(args)
    elif args.view:
        cmd_view(args)
    elif args.search:
        cmd_search(args)
    elif args.stats:
        cmd_stats(args)
    elif args.role:
        cmd_log(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()