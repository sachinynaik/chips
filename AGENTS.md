# Repository Guidelines

## Project Structure & Module Organization
Core code lives under `src/chips/` and is split by responsibility: `compiler/` builds briefs and policies, `harvester/` ingests and enriches repository signals, `memory/` stores findings, and `mcp/` exposes the MCP server and tool modules. Tests mirror that structure under `tests/` with focused suites such as `tests/compiler/`, `tests/harvester/`, `tests/mcp/`, `tests/memory/`, and `tests/unit/`. Database migrations live in `migrations/versions/`. Architecture notes and product docs live in `docs/`.

## Build, Test, and Development Commands
Use Python 3.13 and `uv`.

- `uv sync --dev`: install runtime and development dependencies.
- `uv run pytest`: run the full test suite.
- `uv run coverage run -m pytest` then `uv run coverage report`: run tests with coverage; the repo fails below 90%.
- `uv run alembic upgrade head`: apply local database migrations.
- `uv run python -m chips.mcp.bus`: start the MCP server over SSE.

Set `CHIPS_DB_URL` before running database-backed code. Optional local model settings include `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_COMPRESS_MODEL`, and `CHIPS_POLICY_FILE`.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and explicit type hints on public APIs. Keep modules narrowly scoped and prefer small helpers over large mixed-purpose files. Preserve the current import style and keep re-exports intentional, as in `src/chips/mcp/server.py`.

## Testing Guidelines
Pytest is the test runner, with `pytest-asyncio` enabled for async code. Name tests `test_*.py` and keep them near the subsystem they cover. Add or update tests with every behavior change, especially for MCP modules, enrichment analyzers, and migrations. For schema work, include a migration test or repository test that proves the new path end to end.

## Commit & Pull Request Guidelines
Recent history follows concise conventional prefixes such as `feat:`, `fix:`, and `chore:` followed by an imperative summary. Keep commits focused and describe the user-visible or architectural change plainly, for example `feat: add tenant filtering to memory queries`. PRs should explain intent, list verification commands run, link the related issue, and include sample output or screenshots when MCP responses, docs, or operator-facing behavior change.
