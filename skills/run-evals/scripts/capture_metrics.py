#!/usr/bin/env python3
"""
Capture Metrics — host-agnostic dispatcher.

Detects the host agent (GitHub Copilot CLI, Claude Code CLI, or OpenAI Codex
CLI) and delegates to the matching adapter under scripts/metrics/. Writes a
canonical timing.json that compile_benchmark.py can consume regardless of
host.

Usage:
    python capture_metrics.py --current --save-id session.txt
    python capture_metrics.py --session <id> --json timing.json
    python capture_metrics.py --json timing.json         # most recent session
    python capture_metrics.py --host copilot --current   # force host

The `--current` flag resolves the *active* session (host-specific heuristic);
without it, the most recent session is used.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

SCRIPT_DIR = Path(__file__).parent
# Ensure the metrics package is importable when this script is invoked directly.
sys.path.insert(0, str(SCRIPT_DIR))

SUPPORTED_HOSTS = ("copilot", "claude", "codex")


def _load_adapter(host: str):
    """Import metrics.<host> and return the module."""
    if host not in SUPPORTED_HOSTS:
        raise ValueError(f"Unsupported host: {host!r}. Expected one of {SUPPORTED_HOSTS}")
    return importlib.import_module(f"metrics.{host}")


def _detect_host() -> str:
    """Use detect_host_agent.detect() rather than shelling out."""
    detect_mod = importlib.import_module("detect_host_agent")
    host, _ = detect_mod.detect()
    return host


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--current", action="store_true",
                       help="Resolve the currently active session (host-specific heuristic)")
    group.add_argument("--session", metavar="SESSION_ID",
                       help="Capture a specific session by ID")

    parser.add_argument("--host", choices=SUPPORTED_HOSTS,
                        help="Force host agent instead of auto-detection "
                             "(or set EVAL_HOST_AGENT).")
    parser.add_argument("--json", nargs="?", const="timing.json", metavar="FILE",
                        help="Write canonical timing.json to FILE (default: timing.json)")
    parser.add_argument("--save-id", metavar="FILE",
                        help="Also write the resolved session ID to FILE "
                             "(useful with --current for recovery).")
    parser.add_argument("--print", action="store_true",
                        help="Print canonical JSON to stdout instead of a summary.")
    args = parser.parse_args()

    host = args.host or os.environ.get("EVAL_HOST_AGENT", "").strip().lower() or _detect_host()
    if host == "unknown" or host not in SUPPORTED_HOSTS:
        print(
            f"Error: could not determine host agent (got {host!r}). "
            "Pass --host or set EVAL_HOST_AGENT=copilot|claude|codex.",
            file=sys.stderr,
        )
        sys.exit(2)

    adapter = _load_adapter(host)

    # Resolve session ID first — lets us save-id even if collect() produces nothing.
    resolved = args.session or adapter.resolve_session_id(current_only=args.current)
    if args.save_id and resolved:
        Path(args.save_id).parent.mkdir(parents=True, exist_ok=True)
        Path(args.save_id).write_text(resolved, encoding="utf-8")
        print(f"  Session ID saved to: {Path(args.save_id).resolve()}")

    data = adapter.collect(resolved, current_only=args.current)

    if args.print:
        print(json.dumps(data, indent=2, default=str))
    else:
        sid = data.get("session_id") or "—"
        tok = data.get("tokens", {})
        print(f"  Host:       {data.get('host_agent')}")
        print(f"  Session:    {sid}")
        print(f"  Model:      {data.get('model')}")
        print(f"  Duration:   {data.get('duration_seconds')}s")
        print(f"  Tokens:     in={tok.get('input')} out={tok.get('output')} cache={tok.get('cache_read')}")
        print(f"  Premium:    {data.get('premium_requests')} request(s)")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  ✔ Metrics written to: {out.resolve()}")

    # Exit non-zero if we couldn't capture anything — useful in pipelines.
    if not data.get("session_id"):
        print("Warning: no session data captured.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
