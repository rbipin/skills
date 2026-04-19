#!/usr/bin/env python3
"""
Detect Host Agent

Probes the environment and prints a single token to stdout identifying which
AI CLI is hosting the current session:

    copilot | claude | codex | unknown

Detection order (first match wins):
  1. Env override: EVAL_HOST_AGENT=<name>
  2. GitHub Copilot CLI — ~/.copilot/session-state/<id>/ with a recent dir
                          or env COPILOT_AGENT_ID
  3. Claude Code CLI    — ~/.claude/projects/*/*.jsonl with a recent file
                          or env CLAUDE_CODE_SESSION_ID / CLAUDECODE
  4. OpenAI Codex CLI   — ~/.codex/sessions or ~/.openai/sessions
                          or env CODEX_SESSION_ID / OPENAI_CLI_SESSION_ID
  5. unknown            — exit non-zero with guidance

Usage:
    python detect_host_agent.py            # prints token + exits 0 on match
    python detect_host_agent.py --verbose  # prints reason after the token
    python detect_host_agent.py --json     # prints {"host": "...", "reason": "..."}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from time import time

RECENT_WINDOW_S = 600  # 10 minutes


def _has_recent_child(directory: Path, pattern: str = "*") -> bool:
    if not directory.exists():
        return False
    now = time()
    for p in directory.glob(pattern):
        try:
            if (now - p.stat().st_mtime) <= RECENT_WINDOW_S:
                return True
        except OSError:
            continue
    return False


def detect() -> tuple[str, str]:
    """Return (host, reason). host is one of copilot/claude/codex/unknown."""
    override = os.environ.get("EVAL_HOST_AGENT", "").strip().lower()
    if override in {"copilot", "claude", "codex"}:
        return override, f"EVAL_HOST_AGENT={override}"

    # GitHub Copilot CLI
    copilot_dir = Path.home() / ".copilot" / "session-state"
    if os.environ.get("COPILOT_AGENT_ID"):
        return "copilot", "env COPILOT_AGENT_ID set"
    if copilot_dir.exists() and _has_recent_child(copilot_dir, "*"):
        return "copilot", f"recent session in {copilot_dir}"

    # Claude Code CLI
    claude_dir = Path.home() / ".claude" / "projects"
    if os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDECODE"):
        return "claude", "env CLAUDE_CODE_SESSION_ID / CLAUDECODE set"
    if claude_dir.exists() and _has_recent_child(claude_dir, "*/*.jsonl"):
        return "claude", f"recent session in {claude_dir}"

    # OpenAI Codex / ChatGPT CLI
    for env_name in ("CODEX_SESSION_ID", "OPENAI_CLI_SESSION_ID"):
        if os.environ.get(env_name):
            return "codex", f"env {env_name} set"
    for d in (Path.home() / ".codex" / "sessions", Path.home() / ".openai" / "sessions"):
        if d.exists() and _has_recent_child(d, "*.jsonl"):
            return "codex", f"recent session in {d}"

    # Fall back on stale directories (signal the host even if no session active)
    if copilot_dir.exists():
        return "copilot", f"existing {copilot_dir} (no recent session)"
    if claude_dir.exists():
        return "claude", f"existing {claude_dir} (no recent session)"
    for d in (Path.home() / ".codex" / "sessions", Path.home() / ".openai" / "sessions"):
        if d.exists():
            return "codex", f"existing {d} (no recent session)"

    return "unknown", "no known host-agent session state found"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="Also print detection reason on stderr")
    parser.add_argument("--json", action="store_true", help="Emit JSON object to stdout")
    args = parser.parse_args()

    host, reason = detect()

    if args.json:
        print(json.dumps({"host": host, "reason": reason}))
    else:
        print(host)
        if args.verbose:
            print(f"  reason: {reason}", file=sys.stderr)

    if host == "unknown":
        print(
            "\nNo known host-agent session state detected. Set EVAL_HOST_AGENT "
            "to one of: copilot | claude | codex",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
