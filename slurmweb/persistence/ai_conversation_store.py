# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json

from ..models.db import psycopg_connect_kwargs


class AIConversationStore:
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

    def create_conversation(self, cluster: str, username: str, title: str, model_config_id=None):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO ai_conversations (
                        cluster, username, title, model_config_id, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, NOW(), NOW())
                    RETURNING *
                    """,
                    (cluster, username, title, model_config_id),
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
        return dict(row)

    def get_conversation(self, cluster: str, username: str, conversation_id: int):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT c.*, m.content AS last_message
                    FROM ai_conversations c
                    LEFT JOIN LATERAL (
                        SELECT content
                        FROM ai_messages
                        WHERE conversation_id = c.id
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1
                    ) m ON TRUE
                    WHERE c.cluster = %s AND c.username = %s AND c.id = %s
                    """,
                    (cluster, username, conversation_id),
                )
                row = cur.fetchone()
        finally:
            self._release_conn(conn)
        return None if row is None else dict(row)

    def list_conversations(self, cluster: str, username: str, limit=100):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT c.*, m.content AS last_message
                    FROM ai_conversations c
                    LEFT JOIN LATERAL (
                        SELECT content
                        FROM ai_messages
                        WHERE conversation_id = c.id
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1
                    ) m ON TRUE
                    WHERE c.cluster = %s AND c.username = %s
                    ORDER BY c.updated_at DESC, c.id DESC
                    LIMIT %s
                    """,
                    (cluster, username, limit),
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)
        return [dict(row) for row in rows]

    def add_message(self, conversation_id: int, role: str, content: str, model_config_id=None, metadata=None):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO ai_messages (
                        conversation_id, role, content, model_config_id, metadata, created_at
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
                    RETURNING *
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        model_config_id,
                        json.dumps(metadata or {}),
                    ),
                )
                row = cur.fetchone()
                cur.execute(
                    """
                    UPDATE ai_conversations
                    SET model_config_id = COALESCE(%s, model_config_id),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (model_config_id, conversation_id),
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
        return dict(row)

    def list_messages(self, cluster: str, username: str, conversation_id: int, limit=100):
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT m.*
                    FROM ai_messages m
                    JOIN ai_conversations c ON c.id = m.conversation_id
                    WHERE c.cluster = %s AND c.username = %s AND c.id = %s
                    ORDER BY m.created_at ASC, m.id ASC
                    LIMIT %s
                    """,
                    (cluster, username, conversation_id, limit),
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)
        return [dict(row) for row in rows]

    def record_tool_call(
        self,
        conversation_id: int,
        message_id,
        cluster: str,
        username: str,
        tool_name: str,
        permission: str,
        input_payload: dict,
        result_summary,
        status: str,
        error,
        duration_ms,
    ):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_tool_calls (
                        conversation_id, message_id, cluster, username, tool_name,
                        permission, input_payload, result_summary, status, error,
                        duration_ms, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s::jsonb, %s, %s, %s,
                        %s, NOW()
                    )
                    """,
                    (
                        conversation_id,
                        message_id,
                        cluster,
                        username,
                        tool_name,
                        permission,
                        json.dumps(input_payload or {}),
                        result_summary,
                        status,
                        error,
                        duration_ms,
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
