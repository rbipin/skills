"""Claude Code CLI metrics collector.

Reads ~/.claude/projects/<slug>/<session-id>.jsonl and produces a canonical
timing.json. Session files contain a stream of turns with `message.usage`
blocks we sum across the session.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._common import (
    MODEL_CONTEXT_SIZES,
    derive_context_pct,
    empty_canonical,
    read_jsonl,
)

PROJECTS_DIR = Path.home() / ".claude" / "projects"
HOST_AGENT = "claude"


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    ts = ts.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _all_session_files() -> list[Path]:
    if not PROJECTS_DIR.exists():
        return []
    return list(PROJECTS_DIR.glob("*/*.jsonl"))


def _find_session_file(session_id: str) -> Path | None:
    if not PROJECTS_DIR.exists():
        return None
    matches = list(PROJECTS_DIR.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def _find_most_recent_file() -> Path | None:
    files = _all_session_files()
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def resolve_session_id(*, current_only: bool = False) -> str | None:
    f = _find_most_recent_file()
    if not f:
        return None
    if current_only:
        age_s = (datetime.now(timezone.utc).timestamp() - f.stat().st_mtime)
        if age_s > 600:
            return None
    return f.stem


def collect(session_id: str | None = None, *, current_only: bool = False) -> dict[str, Any]:
    if session_id:
        session_file = _find_session_file(session_id)
    else:
        sid = resolve_session_id(current_only=current_only)
        session_file = _find_session_file(sid) if sid else None

    if not session_file:
        return empty_canonical(HOST_AGENT)

    events = read_jsonl(session_file)
    canonical = empty_canonical(HOST_AGENT)
    canonical["session_id"] = session_file.stem

    if not events:
        return canonical

    total_input = total_output = total_cache_r = total_cache_w = total_reason = 0
    api_calls_by_model: dict[str, dict] = {}
    first_ts = last_ts = None
    model = "unknown"
    current_ctx = 0

    for e in events:
        ts = _parse_ts(e.get("timestamp", "") or e.get("time", ""))
        if ts:
            if not first_ts or ts < first_ts:
                first_ts = ts
            if not last_ts or ts > last_ts:
                last_ts = ts

        msg = e.get("message") if isinstance(e.get("message"), dict) else e
        usage = msg.get("usage") if isinstance(msg, dict) else None
        if not isinstance(usage, dict):
            continue

        inp = usage.get("input_tokens", 0) or 0
        out = usage.get("output_tokens", 0) or 0
        cr = usage.get("cache_read_input_tokens", 0) or 0
        cw = usage.get("cache_creation_input_tokens", 0) or 0
        rs = usage.get("reasoning_tokens", 0) or 0

        total_input += inp
        total_output += out
        total_cache_r += cr
        total_cache_w += cw
        total_reason += rs
        current_ctx = max(current_ctx, inp + cr + cw)

        m = msg.get("model") or e.get("model") or model
        if m:
            model = m
        slot = api_calls_by_model.setdefault(m or "unknown", {
            "api_calls": 0, "premium_cost": 0,
            "input_tokens": 0, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0, "reasoning_tokens": 0,
        })
        slot["api_calls"] += 1
        slot["input_tokens"] += inp
        slot["output_tokens"] += out
        slot["cache_read_tokens"] += cr
        slot["cache_write_tokens"] += cw
        slot["reasoning_tokens"] += rs

    duration_s = 0.0
    if first_ts and last_ts:
        duration_s = round((last_ts - first_ts).total_seconds(), 3)

    canonical.update({
        "started": first_ts.isoformat() if first_ts else "unknown",
        "ended": last_ts.isoformat() if last_ts else "unknown",
        "duration_seconds": duration_s,
        "api_duration_ms": 0,
        "premium_requests": sum(v["api_calls"] for v in api_calls_by_model.values()),
        "model": model,
    })
    canonical["tokens"].update({
        "input": total_input,
        "output": total_output,
        "total": total_input + total_output,
        "cache_read": total_cache_r,
        "cache_write": total_cache_w,
        "reasoning": total_reason,
        "context_window_used": current_ctx,
        "context_window_max": MODEL_CONTEXT_SIZES.get(model),
        "context_window_used_pct": derive_context_pct(current_ctx, model),
    })
    canonical["model_breakdown"] = api_calls_by_model
    return canonical
