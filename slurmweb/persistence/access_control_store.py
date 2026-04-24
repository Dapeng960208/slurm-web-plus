# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from typing import Iterable, List, Tuple

from ..models.db import psycopg_connect_kwargs


class AccessControlStore:
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
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            self._release_conn(conn)

    def _role_name_exists(self, cur, name: str, exclude_role_id=None) -> bool:
        if exclude_role_id is None:
            cur.execute("SELECT 1 FROM roles WHERE name = %s", (name,))
        else:
            cur.execute(
                "SELECT 1 FROM roles WHERE name = %s AND id != %s",
                (name, exclude_role_id),
            )
        return cur.fetchone() is not None

    def list_roles(self):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, description, actions, created_at, updated_at
                    FROM roles
                    ORDER BY name ASC
                    """
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "actions": row["actions"] or [],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def create_role(self, name: str, description: str, actions: List[str]):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if self._role_name_exists(cur, name):
                    raise ValueError(f"Role {name} already exists")
                cur.execute(
                    """
                    INSERT INTO roles (name, description, actions, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW(), NOW())
                    RETURNING id, name, description, actions, created_at, updated_at
                    """,
                    (name, description, psycopg2.extras.Json(actions)),
                )
                row = cur.fetchone()
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._release_conn(conn)

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "actions": row["actions"] or [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def update_role(self, role_id: int, name: str, description: str, actions: List[str]):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if self._role_name_exists(cur, name, exclude_role_id=role_id):
                    raise ValueError(f"Role {name} already exists")
                cur.execute(
                    """
                    UPDATE roles
                    SET name = %s,
                        description = %s,
                        actions = %s::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, name, description, actions, created_at, updated_at
                    """,
                    (
                        name,
                        description,
                        psycopg2.extras.Json(actions),
                        role_id,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._release_conn(conn)

        return None if row is None else {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "actions": row["actions"] or [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def delete_role(self, role_id: int) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
                deleted = cur.rowcount
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._release_conn(conn)
        return bool(deleted)

    def user_permissions(self, username: str) -> Tuple[set, set]:
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT r.name, r.actions
                    FROM users u
                    JOIN user_roles ur ON ur.user_id = u.id
                    JOIN roles r ON r.id = ur.role_id
                    WHERE u.username = %s
                    ORDER BY r.name ASC
                    """,
                    (username,),
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        role_names = set()
        actions = set()
        for row in rows:
            role_names.add(row["name"])
            actions.update(row["actions"] or [])
        return role_names, actions

    def list_users(self, username=None, page=1, page_size=50):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                filters = []
                params = []
                if username:
                    filters.append("u.username ILIKE %s")
                    params.append(f"%{username}%")
                where_sql = ""
                if filters:
                    where_sql = "WHERE " + " AND ".join(filters)

                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM users u
                    {where_sql}
                    """,
                    params,
                )
                total = cur.fetchone()["count"]

                offset = (page - 1) * page_size
                cur.execute(
                    f"""
                    SELECT
                        u.username,
                        u.fullname,
                        u.policy_roles,
                        u.policy_actions,
                        COALESCE(
                            json_agg(
                                json_build_object('id', r.id, 'name', r.name)
                                ORDER BY r.name
                            ) FILTER (WHERE r.id IS NOT NULL),
                            '[]'::json
                        ) AS custom_roles
                    FROM users u
                    LEFT JOIN user_roles ur ON ur.user_id = u.id
                    LEFT JOIN roles r ON r.id = ur.role_id
                    {where_sql}
                    GROUP BY u.id, u.username, u.fullname, u.policy_roles, u.policy_actions
                    ORDER BY u.username ASC
                    LIMIT %s OFFSET %s
                    """,
                    params + [page_size, offset],
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        items = []
        for row in rows:
            custom_roles = row["custom_roles"] or []
            custom_actions = sorted(
                {
                    action
                    for role in self._user_roles_detail(row["username"]).get("custom_roles", [])
                    for action in role.get("actions", [])
                }
            )
            items.append(
                {
                    "username": row["username"],
                    "fullname": row["fullname"],
                    "policy_roles": row["policy_roles"] or [],
                    "policy_actions": row["policy_actions"] or [],
                    "custom_roles": custom_roles,
                    "custom_actions": custom_actions,
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _ensure_user(self, cur, username: str):
        cur.execute(
            """
            INSERT INTO users (username, groups, created_at, updated_at)
            VALUES (%s, '[]'::jsonb, NOW(), NOW())
            ON CONFLICT (username) DO UPDATE SET updated_at = NOW()
            RETURNING id
            """,
            (username,),
        )
        row = cur.fetchone()
        return row["id"] if isinstance(row, dict) else row[0]

    def _role_ids_exist(self, cur, role_ids: Iterable[int]) -> bool:
        role_ids = list(role_ids)
        if not role_ids:
            return True
        cur.execute(
            "SELECT COUNT(*) FROM roles WHERE id = ANY(%s)",
            (role_ids,),
        )
        row = cur.fetchone()
        count = row["count"] if isinstance(row, dict) else row[0]
        return count == len(set(role_ids))

    def _user_roles_detail(self, username: str):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        u.username,
                        u.fullname,
                        u.policy_roles,
                        u.policy_actions,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'id', r.id,
                                    'name', r.name,
                                    'description', r.description,
                                    'actions', r.actions
                                )
                                ORDER BY r.name
                            ) FILTER (WHERE r.id IS NOT NULL),
                            '[]'::json
                        ) AS custom_roles
                    FROM users u
                    LEFT JOIN user_roles ur ON ur.user_id = u.id
                    LEFT JOIN roles r ON r.id = ur.role_id
                    WHERE u.username = %s
                    GROUP BY u.id, u.username, u.fullname, u.policy_roles, u.policy_actions
                    """,
                    (username,),
                )
                return cur.fetchone()
        finally:
            self._release_conn(conn)

    def get_user_roles(self, username: str):
        row = self._user_roles_detail(username)
        if row is None:
            return None

        custom_roles = row["custom_roles"] or []
        custom_actions = sorted(
            {
                action
                for role in custom_roles
                for action in (role.get("actions") or [])
            }
        )
        return {
            "username": row["username"],
            "fullname": row["fullname"],
            "policy_roles": row["policy_roles"] or [],
            "policy_actions": row["policy_actions"] or [],
            "custom_roles": custom_roles,
            "custom_actions": custom_actions,
        }

    def set_user_roles(self, username: str, role_ids: List[int]):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                user_id = self._ensure_user(cur, username)
                if not self._role_ids_exist(cur, role_ids):
                    raise ValueError("One or more roles were not found")
                cur.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
                if role_ids:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO user_roles (user_id, role_id, created_at)
                        VALUES %s
                        """,
                        [(user_id, role_id) for role_id in sorted(set(role_ids))],
                        template="(%s, %s, NOW())",
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

        return self.get_user_roles(username)
