from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chips.mcp.tools.briefs import get_brief as _get_brief
from chips.mcp.tools.briefs import record_outcome as _record_outcome


class BriefsModule:
    name = "briefs"

    def __init__(self, conn_factory) -> None:
        self._conn_factory = conn_factory

    def get_brief(self, brief_id: str) -> dict:
        conn = self._conn_factory()
        try:
            return _get_brief(conn, brief_id)
        finally:
            conn.close()

    def record_outcome(
        self,
        brief_id: str,
        outcome: str,
        notes: str | None = None,
    ) -> dict:
        conn = self._conn_factory()
        try:
            return _record_outcome(conn, brief_id, outcome, notes)
        finally:
            conn.close()

    def register(self, app: FastMCP) -> None:
        app.tool()(self.get_brief)
        app.tool()(self.record_outcome)
