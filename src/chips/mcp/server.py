from __future__ import annotations

from chips.mcp.bus import create_bus, main  # noqa: F401

app, _registry = create_bus()

__all__ = ["app", "main"]
