#!/usr/bin/env python3
"""
Refresh the unified benchmark dashboard in a workspace.

This script:
  1. Copies the static ``dashboard.html`` asset into the workspace root
     (only if missing or the packaged asset is newer).
  2. Scans the workspace for ``iteration-*/benchmark.json`` files and writes
     a small ``iterations.json`` manifest that the dashboard consumes at
     runtime.

Because the dashboard loads JSON over ``fetch()``, it must be served over
HTTP. Run from the workspace root::

    python -m http.server 8000

and open ``http://localhost:8000/dashboard.html``.

Usage:
    python refresh_dashboard.py [workspace_root]

If ``workspace_root`` is omitted, the script auto-detects the latest
``*-workspace`` folder (or falls back to CWD) — mirroring
``compile_benchmark.py``.

No third-party dependencies — stdlib only.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

SCRIPT_DIR  = Path(__file__).parent
ASSET_PATH  = SCRIPT_DIR / "assets" / "dashboard.html"
OUTPUT_NAME = "dashboard.html"
MANIFEST    = "iterations.json"


def _auto_detect_workspace(cwd: Path) -> Path:
    """Return the latest ``*-workspace`` child of cwd, or cwd itself."""
    candidates = [p for p in cwd.iterdir() if p.is_dir() and p.name.endswith("-workspace")]
    if not candidates:
        return cwd
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _copy_asset(dest: Path) -> str:
    """Copy ``dashboard.html`` only if missing or asset is newer. Returns status label."""
    if not ASSET_PATH.exists():
        print(f"Error: packaged dashboard asset missing at {ASSET_PATH}", file=sys.stderr)
        sys.exit(1)

    if not dest.exists():
        shutil.copy2(ASSET_PATH, dest)
        return "copied"

    if ASSET_PATH.stat().st_mtime > dest.stat().st_mtime:
        shutil.copy2(ASSET_PATH, dest)
        return "updated"

    return "unchanged"


def _build_manifest(workspace_root: Path) -> list[dict]:
    """Collect iteration-*/benchmark.json entries sorted by mtime desc."""
    entries = []
    for p in workspace_root.rglob("iteration-*/benchmark.json"):
        if not p.is_file():
            continue
        rel = p.relative_to(workspace_root).as_posix()
        entries.append({
            "id":    p.parent.name,
            "path":  rel,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                            .isoformat(timespec="seconds")
                            .replace("+00:00", "Z"),
        })
    entries.sort(key=lambda e: e["mtime"], reverse=True)
    return entries


def _write_manifest(workspace_root: Path, entries: list[dict]) -> Path:
    path = workspace_root / MANIFEST
    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "iterations":   entries,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh the unified benchmark dashboard + iterations manifest.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("workspace_root", nargs="?", default=None,
                        help="Workspace directory containing iteration-*/benchmark.json (default: auto-detect)")
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root) if args.workspace_root else _auto_detect_workspace(Path.cwd())
    workspace_root = workspace_root.resolve()
    if not workspace_root.exists() or not workspace_root.is_dir():
        print(f"Error: workspace root not found or not a directory: {workspace_root}", file=sys.stderr)
        sys.exit(1)

    dest_html = workspace_root / OUTPUT_NAME
    status = _copy_asset(dest_html)

    entries = _build_manifest(workspace_root)
    manifest_path = _write_manifest(workspace_root, entries)

    print(f"Workspace:     {workspace_root}")
    print(f"dashboard.html {status}: {dest_html}")
    print(f"Manifest:      {manifest_path} ({len(entries)} iteration(s))")
    if not entries:
        print("Warning: no iteration-*/benchmark.json files found.", file=sys.stderr)

    print()
    print("Serve locally:")
    print(f"    cd {workspace_root}")
    print( "    python -m http.server 8000")
    print( "    open http://localhost:8000/dashboard.html")


if __name__ == "__main__":
    main()
