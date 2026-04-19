"""Shared helpers for metrics collectors.

The canonical timing.json schema is documented in
assets/timing.schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODEL_CONTEXT_SIZES: dict[str, int] = {
    "claude-opus-4.7":    200_000,
    "claude-opus-4.6":    200_000,
    "claude-opus-4.5":    200_000,
    "claude-sonnet-4.6":  200_000,
    "claude-sonnet-4.5":  200_000,
    "claude-sonnet-4":    200_000,
    "claude-haiku-4.5":   200_000,
    "gpt-4.1":          1_047_576,
    "gpt-5.2":            128_000,
    "gpt-5.2-codex":      128_000,
    "gpt-5.3-codex":      128_000,
    "gpt-5.4":            128_000,
    "gpt-5.4-mini":       128_000,
    "gpt-5-mini":         128_000,
}


def empty_canonical(host_agent: str) -> dict[str, Any]:
    """Return a fresh canonical timing.json dict with zero/null defaults."""
    return {
        "host_agent": host_agent,
        "host_agent_version": None,
        "session_id": None,
        "model": "unknown",
        "started": "unknown",
        "ended": "unknown",
        "duration_seconds": 0.0,
        "api_duration_ms": 0,
        "premium_requests": 0,
        "tokens": {
            "input": 0,
            "output": 0,
            "total": 0,
            "cache_read": 0,
            "cache_write": 0,
            "reasoning": 0,
            "context_window_used": 0,
            "context_window_max": None,
            "context_window_used_pct": None,
        },
        "token_breakdown": {
            "system_prompt": 0,
            "tool_definitions": 0,
            "conversation": 0,
        },
        "model_breakdown": {},
    }


def derive_context_pct(current: int, model: str) -> float | None:
    if not current:
        return None
    max_ctx = MODEL_CONTEXT_SIZES.get(model)
    if not max_ctx:
        return None
    return round(current / max_ctx * 100, 2)


def write_json(data: Any, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return out.resolve()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def most_recent_child(directory: Path, pattern: str = "*") -> Path | None:
    if not directory.exists():
        return None
    kids = list(directory.glob(pattern))
    if not kids:
        return None
    return max(kids, key=lambda p: p.stat().st_mtime)
