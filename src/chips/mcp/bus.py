from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from mcp.server.fastmcp import FastMCP

from chips.compiler.compressor import OllamaCompressor
from chips.compiler.policy import PolicyLoader
from chips.harvester.embedding import OllamaEmbedder
from chips.observability.tracing import configure_telemetry


@runtime_checkable
class BusModule(Protocol):
    name: str

    def register(self, app: FastMCP) -> None: ...


class BusRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, BusModule] = {}

    def add(self, module: BusModule) -> None:
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' is already registered")
        self._modules[module.name] = module

    def mount(self, app: FastMCP) -> None:
        for module in self._modules.values():
            module.register(app)

    @property
    def module_names(self) -> list[str]:
        return list(self._modules.keys())


def _get_conn():
    import psycopg
    return psycopg.connect(os.environ["CHIPS_DB_URL"])


def _get_embedder() -> OllamaEmbedder:
    return OllamaEmbedder(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "nomic-embed-text"),
    )


def _get_compressor() -> OllamaCompressor:
    return OllamaCompressor(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_COMPRESS_MODEL", "qwen2.5-coder:1.5b"),
    )


def _get_policy_loader() -> PolicyLoader:
    policy_path = os.getenv("CHIPS_POLICY_FILE", "cortex_policy.yaml")
    return PolicyLoader.from_file(policy_path)


def create_bus(
    conn_factory=None,
    embedder=None,
    compressor=None,
    policy_loader=None,
) -> tuple[FastMCP, BusRegistry]:
    from chips.mcp.modules.brief import BriefModule
    from chips.mcp.modules.briefs import BriefsModule
    from chips.mcp.modules.constraints import ConstraintsModule
    from chips.mcp.modules.contracts import ContractsModule
    from chips.mcp.modules.diffs import DiffsModule
    from chips.mcp.modules.feedback import FeedbackModule
    from chips.mcp.modules.git import GitModule
    from chips.mcp.modules.health import HealthModule
    from chips.mcp.modules.memory import MemoryModule
    from chips.mcp.modules.policy import PolicyModule
    from chips.mcp.modules.runtime import RuntimeModule
    from chips.mcp.modules.tests_ctx import TestsModule
    from chips.mcp.modules.workflow import WorkflowModule

    if conn_factory is None:
        conn_factory = _get_conn
    if embedder is None:
        embedder = _get_embedder()
    if compressor is None:
        compressor = _get_compressor()
    if policy_loader is None:
        policy_loader = _get_policy_loader()

    app = FastMCP("chips-cortex")
    registry = BusRegistry()

    registry.add(MemoryModule(conn_factory=conn_factory, embedder=embedder))
    registry.add(GitModule(conn_factory=conn_factory))
    registry.add(FeedbackModule(conn_factory=conn_factory))
    registry.add(BriefModule(
        conn_factory=conn_factory,
        embedder=embedder,
        compressor=compressor,
        policy_loader=policy_loader,
    ))
    registry.add(DiffsModule(conn_factory=conn_factory))
    registry.add(HealthModule())
    registry.add(RuntimeModule())
    registry.add(WorkflowModule())
    registry.add(ContractsModule(conn_factory=conn_factory))
    registry.add(ConstraintsModule(conn_factory=conn_factory))
    registry.add(TestsModule(conn_factory=conn_factory))
    registry.add(PolicyModule(policy_loader=policy_loader))
    registry.add(BriefsModule(conn_factory=conn_factory))

    registry.mount(app)
    return app, registry


def main() -> None:
    configure_telemetry("chips-cortex")
    app, _ = create_bus()
    app.run(transport="sse")


if __name__ == "__main__":
    main()
