# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from urllib.parse import quote_plus


def psycopg_connect_kwargs(settings):
    return {
        "host": settings.host,
        "port": settings.port,
        "dbname": settings.database,
        "user": settings.user,
        "password": settings.password,
    }


def sqlalchemy_url(settings):
    username = quote_plus(str(settings.user))
    password = getattr(settings, "password", None)
    auth = username
    if password not in (None, ""):
        auth = f"{auth}:{quote_plus(str(password))}"
    database = quote_plus(str(settings.database))
    return (
        f"postgresql+psycopg2://{auth}@{settings.host}:{settings.port}/{database}"
    )

