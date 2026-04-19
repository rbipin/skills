"""Host-agent-specific metrics collectors.

Each submodule exposes:
    collect(session_id: str | None, *, current_only: bool = False) -> dict
    resolve_session_id(*, current_only: bool = False) -> str | None
"""
