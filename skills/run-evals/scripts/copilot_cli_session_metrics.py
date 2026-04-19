#!/usr/bin/env python3
"""Backward-compatibility shim for the Copilot CLI metrics script.

Forwards all arguments to `capture_metrics.py --host copilot`, which is the
new host-agnostic dispatcher. The original CLI surface is preserved
(--current, --session, --json, --save-id, --all, --days, --no-breakdown)
so in-flight iterations continue to work.

New code should call `python capture_metrics.py --host copilot ...` directly.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DISPATCHER = SCRIPT_DIR / "capture_metrics.py"


def main() -> int:
    if not DISPATCHER.exists():
        print(f"Error: dispatcher not found: {DISPATCHER}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(DISPATCHER), "--host", "copilot", *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
