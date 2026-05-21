import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def _container():
    yield None

@pytest.fixture(scope="session")
def alembic_url(_container):
    return ""

@pytest.fixture(scope="session", autouse=True)
def apply_migrations(alembic_url):
    pass

# ---------------------------------------------------------------------------
# Windows-safe tmp_path override
# On Windows, the system temp dir may be inaccessible due to pytest-asyncio's
# fixture wrapping.  Redirect to a project-local directory instead.
# ---------------------------------------------------------------------------

_LOCAL_TMP_ROOT = Path(__file__).parent.parent.parent.parent / ".pytest_tmp"

@pytest.fixture()
def tmp_path(request, tmp_path_factory):
    """Use a project-local temp dir to avoid Windows AppData permission issues."""
    name = request.node.name
    # sanitise for filesystem
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
    p = _LOCAL_TMP_ROOT / safe
    p.mkdir(parents=True, exist_ok=True)
    yield p
    # cleanup on success (leave on failure for inspection)
    try:
        import shutil
        shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass
