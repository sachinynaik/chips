"""Run alembic migrations against a target database without editing alembic.ini.

alembic.ini keeps a checked-in placeholder `sqlalchemy.url`; migrations/env.py has
no environment-variable override. This builds the Config in memory and overrides
the URL there, mirroring the pattern scripts/test-in-wsl-docker.sh already uses
for the test harness's Postgres.
"""

from __future__ import annotations

import os

from alembic import command
from alembic.config import Config


def build_alembic_config(database_url: str, ini_path: str = "alembic.ini") -> Config:
    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    command.upgrade(build_alembic_config(database_url), "head")


if __name__ == "__main__":
    main()
