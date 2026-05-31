from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_bus_main_configures_telemetry_before_running():
    fake_app = MagicMock()

    with patch("chips.mcp.bus.configure_telemetry") as configure, patch(
        "chips.mcp.bus.create_bus", return_value=(fake_app, MagicMock())
    ):
        from chips.mcp import bus

        bus.main()

    configure.assert_called_once_with("chips-cortex")
    fake_app.run.assert_called_once_with(transport="sse")
