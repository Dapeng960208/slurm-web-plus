# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json

from ..models.db import psycopg_connect_kwargs


class AIModelConfigStore:
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

    @staticmethod
    def _row_to_dict(row):
        return {
            "id": row["id"],
            "cluster": row["cluster"],
            "name": row["name"],
            "provider": row["provider"],
            "model": row["model"],
            "display_name": row["display_name"],
            "enabled": row["enabled"],
            "is_default": row["is_default"],
            "sort_order": row["sort_order"],
            "base_url": row["base_url"],
            "deployment": row["deployment"],
            "api_version": row["api_version"],
            "request_timeout": row["request_timeout"],
            "temperature": row["temperature"],
            "system_prompt": row["system_prompt"],
            "extra_options": row["extra_options"] or {},
            "secret_ciphertext": row["secret_ciphertext"],
            "secret_mask": row["secret_mask"],
            "last_validated_at": row["last_validated_at"],
            "last_validation_error": row["last_validation_error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_configs(self, cluster: str):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM ai_model_configs
                    WHERE cluster = %s
                    ORDER BY sort_order ASC, display_name ASC, id ASC
                    """,
                    (cluster,),
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)
        return [self._row_to_dict(row) for row in rows]

    def get_config(self, cluster: str, config_id: int):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM ai_model_configs
                    WHERE cluster = %s AND id = %s
                    """,
                    (cluster, config_id),
                )
                row = cur.fetchone()
        finally:
            self._release_conn(conn)
        return None if row is None else self._row_to_dict(row)

    def get_default_config(self, cluster: str):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM ai_model_configs
                    WHERE cluster = %s AND enabled = TRUE AND is_default = TRUE
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (cluster,),
                )
                row = cur.fetchone()
        finally:
            self._release_conn(conn)
        return None if row is None else self._row_to_dict(row)

    def count_enabled_configs(self, cluster: str) -> int:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM ai_model_configs
                    WHERE cluster = %s AND enabled = TRUE
                    """,
                    (cluster,),
                )
                return cur.fetchone()[0]
        finally:
            self._release_conn(conn)

    def create_config(self, cluster: str, payload: dict):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if payload.get("is_default"):
                    cur.execute(
                        """
                        UPDATE ai_model_configs
                        SET is_default = FALSE, updated_at = NOW()
                        WHERE cluster = %s
                        """,
                        (cluster,),
                    )
                cur.execute(
                    """
                    INSERT INTO ai_model_configs (
                        cluster, name, provider, model, display_name, enabled,
                        is_default, sort_order, base_url, deployment, api_version,
                        request_timeout, temperature, system_prompt, extra_options,
                        secret_ciphertext, secret_mask, last_validated_at,
                        last_validation_error, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::jsonb,
                        %s, %s, %s,
                        %s, NOW(), NOW()
                    )
                    RETURNING *
                    """,
                    (
                        cluster,
                        payload["name"],
                        payload["provider"],
                        payload["model"],
                        payload["display_name"],
                        payload["enabled"],
                        payload["is_default"],
                        payload["sort_order"],
                        payload.get("base_url"),
                        payload.get("deployment"),
                        payload.get("api_version"),
                        payload.get("request_timeout"),
                        payload.get("temperature"),
                        payload.get("system_prompt"),
                        json.dumps(payload.get("extra_options") or {}),
                        payload.get("secret_ciphertext"),
                        payload.get("secret_mask"),
                        payload.get("last_validated_at"),
                        payload.get("last_validation_error"),
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
        return self._row_to_dict(row)

    def update_config(self, cluster: str, config_id: int, payload: dict):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM ai_model_configs
                    WHERE cluster = %s AND id = %s
                    """,
                    (cluster, config_id),
                )
                current = cur.fetchone()
                if current is None:
                    return None
                if payload.get("is_default"):
                    cur.execute(
                        """
                        UPDATE ai_model_configs
                        SET is_default = FALSE, updated_at = NOW()
                        WHERE cluster = %s AND id != %s
                        """,
                        (cluster, config_id),
                    )
                merged = dict(current)
                merged.update(payload)
                cur.execute(
                    """
                    UPDATE ai_model_configs
                    SET name = %s,
                        provider = %s,
                        model = %s,
                        display_name = %s,
                        enabled = %s,
                        is_default = %s,
                        sort_order = %s,
                        base_url = %s,
                        deployment = %s,
                        api_version = %s,
                        request_timeout = %s,
                        temperature = %s,
                        system_prompt = %s,
                        extra_options = %s::jsonb,
                        secret_ciphertext = %s,
                        secret_mask = %s,
                        last_validated_at = %s,
                        last_validation_error = %s,
                        updated_at = NOW()
                    WHERE cluster = %s AND id = %s
                    RETURNING *
                    """,
                    (
                        merged["name"],
                        merged["provider"],
                        merged["model"],
                        merged["display_name"],
                        merged["enabled"],
                        merged["is_default"],
                        merged["sort_order"],
                        merged.get("base_url"),
                        merged.get("deployment"),
                        merged.get("api_version"),
                        merged.get("request_timeout"),
                        merged.get("temperature"),
                        merged.get("system_prompt"),
                        json.dumps(merged.get("extra_options") or {}),
                        merged.get("secret_ciphertext"),
                        merged.get("secret_mask"),
                        merged.get("last_validated_at"),
                        merged.get("last_validation_error"),
                        cluster,
                        config_id,
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
        return None if row is None else self._row_to_dict(row)

    def delete_config(self, cluster: str, config_id: int) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM ai_model_configs
                    WHERE cluster = %s AND id = %s
                    """,
                    (cluster, config_id),
                )
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
