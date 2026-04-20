# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from pathlib import Path

from ..models.db import sqlalchemy_url


def run_database_migrations(database_settings):
    from alembic import command
    from alembic.config import Config

    package_root = Path(__file__).resolve().parents[1]
    alembic_ini = package_root / "alembic.ini"
    script_location = package_root / "alembic"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url(database_settings))
    command.upgrade(config, "head")
