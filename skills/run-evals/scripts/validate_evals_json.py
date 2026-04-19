#!/usr/bin/env python3
"""
Validate evals.json

Checks that an evals.json file has the expected shape before a pipeline run.
Exits 0 on success, 1 on failure, printing line-precise errors.

Required top-level shape:
    {
        "skill_name": "<string>",       # recommended, not strictly required
        "evals": [
            {
                "id": <int>,
                "prompt": "<string>",
                "assertions": ["<string>", ...]
            },
            ...
        ]
    }

Usage:
    python validate_evals_json.py path/to/evals.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def _err(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path} does not exist"]

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"{path}: invalid JSON at line {e.lineno} col {e.colno}: {e.msg}"]

    if not isinstance(data, dict):
        return [f"{path}: top-level must be a JSON object"]

    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append(f"{path}: 'evals' must be a non-empty list")
        return errors

    seen_ids: set[int] = set()
    for i, ev in enumerate(evals):
        loc = f"evals[{i}]"
        if not isinstance(ev, dict):
            errors.append(f"{loc}: must be an object")
            continue
        if "id" not in ev or not isinstance(ev["id"], int):
            errors.append(f"{loc}.id: required integer")
        elif ev["id"] in seen_ids:
            errors.append(f"{loc}.id: duplicate id {ev['id']}")
        else:
            seen_ids.add(ev["id"])

        if not isinstance(ev.get("prompt"), str) or not ev["prompt"].strip():
            errors.append(f"{loc}.prompt: required non-empty string")

        assertions = ev.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"{loc}.assertions: required non-empty list of strings")
        else:
            for j, a in enumerate(assertions):
                if not isinstance(a, str) or not a.strip():
                    errors.append(f"{loc}.assertions[{j}]: must be a non-empty string")

    return errors


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="Path to evals.json")
    args = p.parse_args()

    errors = validate(Path(args.path))
    if errors:
        for e in errors:
            _err(e)
        sys.exit(1)

    print(f"✔ {args.path} is valid")


if __name__ == "__main__":
    main()
