"""RED: Stub Cortex Bus module tests — diffs, runtime, workflow, contracts, tests_ctx, policy."""
from unittest.mock import MagicMock
from mcp.server.fastmcp import FastMCP


# ── DiffsModule ──────────────────────────────────────────────────────────────

def test_diffs_module_name():
    from chips.mcp.modules.diffs import DiffsModule
    assert DiffsModule().name == "diffs"


def test_diffs_module_get_diffs_returns_expected_shape():
    from chips.mcp.modules.diffs import DiffsModule
    result = DiffsModule().get_diffs(scope=None)
    assert "diffs" in result
    assert "status" in result
    assert isinstance(result["diffs"], list)


def test_diffs_module_registers_tool():
    from chips.mcp.modules.diffs import DiffsModule
    app = FastMCP("test")
    DiffsModule().register(app)
    assert "get_diffs" in list(app._tool_manager._tools.keys())


# ── RuntimeModule ─────────────────────────────────────────────────────────────

def test_runtime_module_name():
    from chips.mcp.modules.runtime import RuntimeModule
    assert RuntimeModule().name == "runtime"


def test_runtime_module_returns_expected_shape():
    from chips.mcp.modules.runtime import RuntimeModule
    result = RuntimeModule().get_runtime_context(scope=None)
    assert "spans" in result
    assert "status" in result
    assert isinstance(result["spans"], list)


def test_runtime_module_registers_tool():
    from chips.mcp.modules.runtime import RuntimeModule
    app = FastMCP("test")
    RuntimeModule().register(app)
    assert "get_runtime_context" in list(app._tool_manager._tools.keys())


# ── WorkflowModule ────────────────────────────────────────────────────────────

def test_workflow_module_name():
    from chips.mcp.modules.workflow import WorkflowModule
    assert WorkflowModule().name == "workflow"


def test_workflow_module_returns_expected_shape():
    from chips.mcp.modules.workflow import WorkflowModule
    result = WorkflowModule().get_workflow_state(scope=None)
    assert "workflows" in result
    assert "status" in result
    assert isinstance(result["workflows"], list)


def test_workflow_module_registers_tool():
    from chips.mcp.modules.workflow import WorkflowModule
    app = FastMCP("test")
    WorkflowModule().register(app)
    assert "get_workflow_state" in list(app._tool_manager._tools.keys())


# ── ContractsModule ───────────────────────────────────────────────────────────

def test_contracts_module_name():
    from chips.mcp.modules.contracts import ContractsModule
    assert ContractsModule().name == "contracts"


def test_contracts_module_returns_expected_shape():
    from chips.mcp.modules.contracts import ContractsModule
    result = ContractsModule().get_contracts(scope=None)
    assert "contracts" in result
    assert "status" in result
    assert isinstance(result["contracts"], list)


def test_contracts_module_registers_tool():
    from chips.mcp.modules.contracts import ContractsModule
    app = FastMCP("test")
    ContractsModule().register(app)
    assert "get_contracts" in list(app._tool_manager._tools.keys())


# ── TestsModule ───────────────────────────────────────────────────────────────

def test_tests_module_name():
    from chips.mcp.modules.tests_ctx import TestsModule
    assert TestsModule().name == "tests_ctx"


def test_tests_module_returns_expected_shape():
    from chips.mcp.modules.tests_ctx import TestsModule
    result = TestsModule().get_test_context(scope=None)
    assert "tests" in result
    assert "status" in result
    assert isinstance(result["tests"], list)


def test_tests_module_registers_tool():
    from chips.mcp.modules.tests_ctx import TestsModule
    app = FastMCP("test")
    TestsModule().register(app)
    assert "get_test_context" in list(app._tool_manager._tools.keys())


# ── PolicyModule ──────────────────────────────────────────────────────────────

def test_policy_module_name():
    from chips.mcp.modules.policy import PolicyModule
    assert PolicyModule(policy_loader=MagicMock()).name == "policy"


def test_policy_module_returns_scope_forbidden_and_required():
    from chips.mcp.modules.policy import PolicyModule
    from chips.compiler.policy import Policy
    loader = MagicMock()
    loader.for_scope.return_value = [
        Policy(scope="valet.checkout", forbidden=["no direct db writes"], required=["use repository pattern"])
    ]
    result = PolicyModule(policy_loader=loader).get_policy(scope="valet.checkout")
    assert result["scope"] == "valet.checkout"
    assert "forbidden" in result
    assert "required" in result
    assert "no direct db writes" in result["forbidden"]


def test_policy_module_passes_scope_to_loader():
    from chips.mcp.modules.policy import PolicyModule
    loader = MagicMock()
    loader.for_scope.return_value = []
    PolicyModule(policy_loader=loader).get_policy(scope="auth")
    loader.for_scope.assert_called_once_with("auth")


def test_policy_module_registers_tool():
    from chips.mcp.modules.policy import PolicyModule
    app = FastMCP("test")
    PolicyModule(policy_loader=MagicMock()).register(app)
    assert "get_policy" in list(app._tool_manager._tools.keys())
