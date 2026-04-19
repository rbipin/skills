#!/usr/bin/env python3
"""
Set Up Iteration

Reads an evals.json, determines the next iteration number for a skill's
workspace, computes canonical slugs, and creates the folder layout the
orchestrator needs. Emits a machine-readable plan to stdout.

Usage:
    python setup_iteration.py <skill_name> <path/to/evals.json> [--workspace-root <dir>]

Output (JSON on stdout):
    {
        "skill_name": "create-skill",
        "iteration": 3,
        "iter_dir": "C:\\Repo\\skillname\\-workspace\\iteration-3",
        "evals": [
            {
                "id": 1,
                "slug": "create-create-skill",
                "folder": "eval-1-create-create-skill",
                "eval_dir": "...\\eval-1-create-create-skill-cash-office",
                "with_skill_dir": "...\\eval-1-.\\with_skill",
                "without_skill_dir": "...\\eval-1-.\\without_skill",
                "prompt": "...",
                "assertions": [...]
            },
            ...
        ]
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with",
    "from", "by", "is", "are", "be", "as", "at", "this", "that", "these",
    "those", "please", "create", "generate", "make",
}
MAX_SLUG_WORDS = 5


def slugify(prompt: str, max_words: int = MAX_SLUG_WORDS) -> str:
    """Deterministic kebab-case slug from a prompt."""
    # Strip non-alphanum to spaces, lowercase.
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", prompt).strip().lower()
    tokens = [t for t in cleaned.split() if t]
    # Drop stopwords, but fall back to raw tokens if that empties the list.
    meaningful = [t for t in tokens if t not in STOP_WORDS] or tokens
    return "-".join(meaningful[:max_words]) or "eval"


def next_iteration(workspace_root: Path) -> int:
    if not workspace_root.exists():
        return 1
    existing = []
    for d in workspace_root.iterdir():
        if d.is_dir():
            m = re.match(r"iteration-(\d+)$", d.name)
            if m:
                existing.append(int(m.group(1)))
    return (max(existing) + 1) if existing else 1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("skill_name", help="Name of the skill being evaluated (e.g. create-skill)")
    p.add_argument("evals_json", help="Path to the skill's evals.json")
    p.add_argument("--workspace-root", default=None,
                   help="Parent dir for <skill>-workspace/ (default: CWD)")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute plan but do not create folders")
    args = p.parse_args()

    evals_path = Path(args.evals_json)
    if not evals_path.exists():
        print(f"Error: {evals_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(evals_path, encoding="utf-8") as f:
        evals_data = json.load(f)
    evals = evals_data.get("evals") or []
    if not evals:
        print("Error: evals.json contains no evals", file=sys.stderr)
        sys.exit(1)

    root = Path(args.workspace_root) if args.workspace_root else Path.cwd()
    workspace = root / f"{args.skill_name}-workspace"
    n = next_iteration(workspace)
    iter_dir = workspace / f"iteration-{n}"

    plan_evals = []
    for e in evals:
        slug = slugify(e["prompt"])
        folder_name = f"eval-{e['id']}-{slug}"
        eval_dir = iter_dir / folder_name
        plan_evals.append({
            "id": e["id"],
            "slug": slug,
            "folder": folder_name,
            "eval_dir": str(eval_dir),
            "with_skill_dir": str(eval_dir / "with_skill"),
            "without_skill_dir": str(eval_dir / "without_skill"),
            "prompt": e["prompt"],
            "assertions": e.get("assertions", []),
        })

    if not args.dry_run:
        iter_dir.mkdir(parents=True, exist_ok=False)
        for pe in plan_evals:
            Path(pe["with_skill_dir"]).mkdir(parents=True, exist_ok=True)
            Path(pe["without_skill_dir"]).mkdir(parents=True, exist_ok=True)

    plan = {
        "skill_name": args.skill_name,
        "iteration": n,
        "iter_dir": str(iter_dir),
        "evals": plan_evals,
    }
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
