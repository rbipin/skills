#!/usr/bin/env python3
"""
Backwards-compatible shim: forwards to ``refresh_dashboard.py``.

The old Jinja-per-iteration flow has been replaced by a single static
``dashboard.html`` at the workspace root that loads ``iterations.json``
at runtime. This shim preserves the legacy entrypoint.

Usage (either form works)::

    python generate_dashboard.py                     # auto-detect workspace
    python generate_dashboard.py WORKSPACE_ROOT      # explicit workspace
    python generate_dashboard.py path/benchmark.json # legacy — workspace inferred

Prefer ``refresh_dashboard.py`` for new call sites.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

SCRIPT_DIR = Path(__file__).parent
TARGET     = SCRIPT_DIR / "refresh_dashboard.py"


def _rewrite_argv(argv: list[str]) -> list[str]:
    """Map a legacy ``benchmark.json`` argument onto its workspace root."""
    if len(argv) < 2:
        return argv
    p = Path(argv[1])
    if p.name == "benchmark.json" and p.parent.name.startswith("iteration-"):
        workspace = p.parent.parent
        print(f"[shim] interpreting workspace as {workspace}", file=sys.stderr)
        return [argv[0], str(workspace)] + argv[2:]
    return argv


def main() -> None:
    if not TARGET.exists():
        print(f"Error: refresh_dashboard.py not found at {TARGET}", file=sys.stderr)
        sys.exit(1)
    sys.argv = _rewrite_argv(sys.argv)
    runpy.run_path(str(TARGET), run_name="__main__")


if __name__ == "__main__":
    main()
