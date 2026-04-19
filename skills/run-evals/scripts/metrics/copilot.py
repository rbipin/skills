"""GitHub Copilot CLI metrics collector.

Reads ~/.copilot/session-state/<id>/events.jsonl and produces a canonical
timing.json.
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

SESSION_STATE_DIR = Path.home() / ".copilot" / "session-state"
HOST_AGENT = "copilot"


def _parse_ts(ts: str) -> datetime:
    ts = ts.rstrip("Z")
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)


def _find_active() -> str | None:
    if not SESSION_STATE_DIR.exists():
        return None
    for d in SESSION_STATE_DIR.iterdir():
        if d.is_dir() and list(d.glob("inuse.*.lock")):
            return d.name
    return None


def _find_most_recent() -> str | None:
    if not SESSION_STATE_DIR.exists():
        return None
    kids = [d for d in SESSION_STATE_DIR.iterdir() if d.is_dir()]
    if not kids:
        return None
    return max(kids, key=lambda p: p.stat().st_mtime).name


def resolve_session_id(*, current_only: bool = False) -> str | None:
    if current_only:
        return _find_active()
    return _find_active() or _find_most_recent()


def collect(session_id: str | None = None, *, current_only: bool = False) -> dict[str, Any]:
    sid = session_id or resolve_session_id(current_only=current_only)
    if not sid:
        return empty_canonical(HOST_AGENT)

    session_dir = SESSION_STATE_DIR / sid
    events = read_jsonl(session_dir / "events.jsonl")
    if not events:
        out = empty_canonical(HOST_AGENT)
        out["session_id"] = sid
        return out

    start_event = next((e for e in events if e.get("type") == "session.start"), None)
    if not start_event:
        out = empty_canonical(HOST_AGENT)
        out["session_id"] = sid
        return out

    start_time = _parse_ts(start_event["timestamp"])
    shutdown_event = next((e for e in events if e.get("type") == "session.shutdown"), None)
    canonical = empty_canonical(HOST_AGENT)
    canonical["session_id"] = sid
    canonical["started"] = start_time.isoformat()

    if shutdown_event:
        sd = shutdown_event.get("data", {})
        end_time = _parse_ts(shutdown_event["timestamp"])
        duration_s = (end_time - start_time).total_seconds()

        model_metrics = sd.get("modelMetrics", {})
        total_input = sum(m.get("usage", {}).get("inputTokens", 0) for m in model_metrics.values())
        total_output = sum(m.get("usage", {}).get("outputTokens", 0) for m in model_metrics.values())
        total_cache_r = sum(m.get("usage", {}).get("cacheReadTokens", 0) for m in model_metrics.values())
        total_cache_w = sum(m.get("usage", {}).get("cacheWriteTokens", 0) for m in model_metrics.values())
        total_reason = sum(m.get("usage", {}).get("reasoningTokens", 0) for m in model_metrics.values())
        current_ctx = sd.get("currentTokens", 0)
        current_model = sd.get("currentModel", "unknown")

        canonical.update({
            "ended": end_time.isoformat(),
            "duration_seconds": round(duration_s, 3),
            "api_duration_ms": sd.get("totalApiDurationMs", 0),
            "premium_requests": sd.get("totalPremiumRequests", 0),
            "model": current_model,
        })
        canonical["tokens"].update({
            "input": total_input,
            "output": total_output,
            "total": total_input + total_output,
            "cache_read": total_cache_r,
            "cache_write": total_cache_w,
            "reasoning": total_reason,
            "context_window_used": current_ctx,
            "context_window_max": MODEL_CONTEXT_SIZES.get(current_model),
            "context_window_used_pct": derive_context_pct(current_ctx, current_model),
        })
        canonical["token_breakdown"] = {
            "system_prompt": sd.get("systemTokens", 0),
            "tool_definitions": sd.get("toolDefinitionsTokens", 0),
            "conversation": sd.get("conversationTokens", 0),
        }
        for name, m in model_metrics.items():
            usage = m.get("usage", {})
            requests = m.get("requests", {})
            canonical["model_breakdown"][name] = {
                "api_calls": requests.get("count", 0),
                "premium_cost": requests.get("cost", 0),
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
                "cache_read_tokens": usage.get("cacheReadTokens", 0),
                "cache_write_tokens": usage.get("cacheWriteTokens", 0),
                "reasoning_tokens": usage.get("reasoningTokens", 0),
            }
    else:
        end_time = datetime.now(timezone.utc)
        premium = sum(1 for e in events if e.get("type") == "user.message")
        total_output = sum(
            e.get("data", {}).get("outputTokens", 0)
            for e in events if e.get("type") == "assistant.message"
        )
        current_model = next(
            (e.get("data", {}).get("newModel") for e in events if e.get("type") == "session.model_change"),
            "unknown",
        )
        canonical.update({
            "ended": "active",
            "duration_seconds": round((end_time - start_time).total_seconds(), 3),
            "premium_requests": premium,
            "model": current_model,
        })
        canonical["tokens"]["output"] = total_output
        canonical["tokens"]["total"] = total_output

    return canonical
