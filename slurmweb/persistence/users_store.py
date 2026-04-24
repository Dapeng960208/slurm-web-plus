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

    def upsert_ldap_user(
        self,
        username,
        fullname,
        groups,
        policy_roles=None,
        policy_actions=None,
    ):
        if not username:
            return

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (
                        username, fullname, groups,
                        policy_roles, policy_actions,
                        ldap_synced_at, permission_synced_at,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, NOW(), NOW(), NOW(), NOW())
                    ON CONFLICT (username) DO UPDATE SET
                        fullname            = EXCLUDED.fullname,
                        groups              = EXCLUDED.groups,
                        policy_roles        = EXCLUDED.policy_roles,
                        policy_actions      = EXCLUDED.policy_actions,
                        ldap_synced_at      = EXCLUDED.ldap_synced_at,
                        permission_synced_at = EXCLUDED.permission_synced_at,
                        updated_at          = NOW()
                    """,
                    (
                        username,
                        fullname,
                        json.dumps(groups or []),
                        json.dumps(policy_roles or []),
                        json.dumps(policy_actions or []),
                    ),
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

    def get_ldap_user(self, username):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT username, fullname, groups, ldap_synced_at
                         , policy_roles, policy_actions, permission_synced_at
                    FROM users
                    WHERE username = %s
                    """,
                    (username,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "username": row[0],
                    "fullname": row[1],
                    "groups": row[2] or [],
                    "ldap_synced_at": row[3],
                    "policy_roles": row[4] or [],
                    "policy_actions": row[5] or [],
                    "permission_synced_at": row[6],
                }
        finally:
            self._release_conn(conn)

    def list_cached_users_for_policy_refresh(self):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT username, fullname, groups
                    FROM users
                    ORDER BY username ASC
                    """
                )
                return [
                    {
                        "username": username,
                        "fullname": fullname,
                        "groups": groups or [],
                    }
                    for username, fullname, groups in cur.fetchall()
                ]
        finally:
            self._release_conn(conn)

    def update_policy_snapshot(self, username, policy_roles, policy_actions):
        if not username:
            return False

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET policy_roles = %s::jsonb,
                        policy_actions = %s::jsonb,
                        permission_synced_at = NOW(),
                        updated_at = NOW()
                    WHERE username = %s
                    """,
                    (
                        json.dumps(policy_roles or []),
                        json.dumps(policy_actions or []),
                        username,
                    ),
                )
                updated = cur.rowcount
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._release_conn(conn)
        return bool(updated)
