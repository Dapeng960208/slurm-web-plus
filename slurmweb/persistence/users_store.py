# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import json

from ..models.db import psycopg_connect_kwargs


class UsersStore:
    def __init__(self, settings):
        self._settings = settings
        self._pool = None

    def _init_pool(self):
        import psycopg2.pool

        self._pool = psycopg2.pool.SimpleConnectionPool(
            1,
            3,
            **psycopg_connect_kwargs(self._settings),
        )

    def _get_conn(self):
        if self._pool is None:
            self._init_pool()
        return self._pool.getconn()

    def _release_conn(self, conn):
        if self._pool is not None:
            self._pool.putconn(conn)

    def validate_connection(self):
        """Eagerly validate PostgreSQL connectivity.

        This is used during agent startup so operational errors such as
        authentication failure or missing database are logged immediately with
        their original message.
        """

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            self._release_conn(conn)

    def upsert_ldap_user(self, username, fullname, groups):
        if not username:
            return

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (
                        username, fullname, groups,
                        ldap_synced_at, created_at, updated_at
                    ) VALUES (%s, %s, %s::jsonb, NOW(), NOW(), NOW())
                    ON CONFLICT (username) DO UPDATE SET
                        fullname       = EXCLUDED.fullname,
                        groups         = EXCLUDED.groups,
                        ldap_synced_at = EXCLUDED.ldap_synced_at,
                        updated_at     = NOW()
                    """,
                    (username, fullname, json.dumps(groups or [])),
                )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._release_conn(conn)

    def list_ldap_users(self, username=None, page=1, page_size=50):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                filters = []
                params = []

                if username:
                    filters.append("username ILIKE %s")
                    params.append(f"%{username}%")

                where_clause = ""
                if filters:
                    where_clause = "WHERE " + " AND ".join(filters)

                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM users
                    {where_clause}
                    """,
                    params,
                )
                total = cur.fetchone()[0]

                offset = (page - 1) * page_size
                params.extend([page_size, offset])
                cur.execute(
                    f"""
                    SELECT username, fullname
                    FROM users
                    {where_clause}
                    ORDER BY username ASC
                    LIMIT %s OFFSET %s
                    """,
                    params,
                )
                return {
                    "items": [
                        {"username": username, "fullname": fullname}
                        for username, fullname in cur.fetchall()
                    ],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
        finally:
            self._release_conn(conn)
