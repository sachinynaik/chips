"""RED: Cortex Bus — BusRegistry and create_bus tests."""
import pytest
from unittest.mock import MagicMock, call
from mcp.server.fastmcp import FastMCP


def test_registry_starts_empty():
    from chips.mcp.bus import BusRegistry
    assert BusRegistry().module_names == []


def test_registry_registers_module():
    from chips.mcp.bus import BusRegistry
    reg = BusRegistry()
    m = MagicMock()
    m.name = "memory"
    reg.add(m)
    assert "memory" in reg.module_names


def test_registry_rejects_duplicate_name():
    from chips.mcp.bus import BusRegistry
    reg = BusRegistry()
    m1 = MagicMock()
    m1.name = "memory"
    m2 = MagicMock()
    m2.name = "memory"
    reg.add(m1)
    with pytest.raises(ValueError, match="memory"):
        reg.add(m2)


def test_registry_mount_calls_register_on_all_modules():
    from chips.mcp.bus import BusRegistry
    reg = BusRegistry()
    ma = MagicMock()
    ma.name = "a"
    mb = MagicMock()
    mb.name = "b"
    reg.add(ma)
    reg.add(mb)
    app = FastMCP("test")
    reg.mount(app)
    ma.register.assert_called_once_with(app)
    mb.register.assert_called_once_with(app)


def test_registry_mount_passes_same_app_instance():
    from chips.mcp.bus import BusRegistry
    reg = BusRegistry()
    modules = [MagicMock() for _ in range(3)]
    for i, m in enumerate(modules):
        m.name = f"mod_{i}"
        reg.add(m)
    app = FastMCP("test")
    reg.mount(app)
    for m in modules:
        assert m.register.call_args == call(app)


def test_create_bus_returns_fastmcp_named_chips_cortex():
    from chips.mcp.bus import create_bus
    app, _ = create_bus(
        conn_factory=MagicMock(),
        embedder=MagicMock(),
        compressor=MagicMock(),
        policy_loader=MagicMock(),
    )
    assert isinstance(app, FastMCP)
    assert app.name == "chips-cortex"


def test_create_bus_registers_all_nine_modules():
    from chips.mcp.bus import create_bus
    _, registry = create_bus(
        conn_factory=MagicMock(),
        embedder=MagicMock(),
        compressor=MagicMock(),
        policy_loader=MagicMock(),
    )
    expected = {
        "memory", "git", "brief",
        "diffs", "runtime", "workflow",
        "contracts", "tests_ctx", "policy",
    }
    assert set(registry.module_names) == expected
