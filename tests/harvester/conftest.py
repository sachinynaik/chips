import pytest

@pytest.fixture(scope="session")
def _container():
    yield None

@pytest.fixture(scope="session")
def alembic_url(_container):
    return ""

@pytest.fixture(scope="session", autouse=True)
def apply_migrations(alembic_url):
    pass
