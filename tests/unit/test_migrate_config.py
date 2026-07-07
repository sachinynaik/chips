from __future__ import annotations

from pathlib import Path

from chips.ops.migrate import build_alembic_config


def test_build_alembic_config_overrides_sqlalchemy_url():
    cfg = build_alembic_config("postgresql://user:pass@example-host:5498/chips_prod")
    assert (
        cfg.get_main_option("sqlalchemy.url")
        == "postgresql://user:pass@example-host:5498/chips_prod"
    )


def test_build_alembic_config_leaves_checked_in_ini_untouched():
    build_alembic_config("postgresql://user:pass@example-host:5498/chips_prod")
    assert "driver://user:pass@localhost/dbname" in Path("alembic.ini").read_text()
