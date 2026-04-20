# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import logging
import os
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from rfl.settings import RuntimeSettings
from rfl.settings.errors import (
    SettingsDefinitionError,
    SettingsOverrideError,
    SettingsSiteLoaderError,
)

from slurmweb.apps._defaults import SlurmwebAppDefaults
from slurmweb.models.db import sqlalchemy_url
from slurmweb.models.modes import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")
target_metadata = Base.metadata


def load_database_url_from_agent_settings():
    """Prefer the agent runtime configuration over the placeholder Alembic URL.

    This allows operators to run `alembic upgrade head` directly on production
    servers without copying database credentials into alembic.ini.
    """

    site_configuration = Path(
        os.environ.get(
            "SLURMWEB_AGENT_INI", SlurmwebAppDefaults.AGENT.site_configuration
        )
    )
    settings_definition = Path(
        os.environ.get(
            "SLURMWEB_AGENT_SETTINGS_DEFINITION",
            SlurmwebAppDefaults.AGENT.settings_definition,
        )
    )

    if not settings_definition.exists():
        logger.debug(
            "Agent settings definition %s not found, keeping sqlalchemy.url from "
            "alembic.ini",
            settings_definition,
        )
        return

    if not site_configuration.exists():
        logger.debug(
            "Agent configuration %s not found, keeping sqlalchemy.url from "
            "alembic.ini",
            site_configuration,
        )
        return

    try:
        settings = RuntimeSettings.yaml_definition(settings_definition)
        settings.override_ini(site_configuration)
    except (
        SettingsDefinitionError,
        SettingsSiteLoaderError,
        SettingsOverrideError,
    ) as err:
        logger.warning(
            "Unable to load agent database settings from %s: %s. Falling back to "
            "sqlalchemy.url from alembic.ini",
            site_configuration,
            err,
        )
        return

    if not settings.database.enabled:
        logger.info(
            "Database support is disabled in %s, keeping sqlalchemy.url from "
            "alembic.ini",
            site_configuration,
        )
        return

    config.set_main_option("sqlalchemy.url", sqlalchemy_url(settings.database))
    logger.info("Loaded sqlalchemy.url from agent configuration %s", site_configuration)


load_database_url_from_agent_settings()


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
