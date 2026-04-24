# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase, mock

from cryptography.fernet import Fernet

from slurmweb.ai.crypto import AISecretCipher
from slurmweb.ai.service import (
    AIProviderValidationError,
    AIService,
    DEFAULT_MAX_HISTORY_MESSAGES,
    DEFAULT_MAX_ROUNDS,
    DEFAULT_STREAM_CHUNK_SIZE,
)
from slurmweb.ai.tools import AIToolExecutionError, AIToolPermissionError


class InMemoryConfigStore:
    def __init__(self):
        self._items = []
        self._next_id = 1

    def list_configs(self, cluster: str):
        return [dict(item) for item in self._items if item["cluster"] == cluster]

    def get_config(self, cluster: str, config_id: int):
        for item in self._items:
            if item["cluster"] == cluster and item["id"] == config_id:
                return dict(item)
        return None

    def get_default_config(self, cluster: str):
        for item in self._items:
            if item["cluster"] == cluster and item["enabled"] and item["is_default"]:
                return dict(item)
        return None

    def count_enabled_configs(self, cluster: str):
        return len(
            [item for item in self._items if item["cluster"] == cluster and item["enabled"]]
        )

    def create_config(self, cluster: str, payload: dict):
        if payload.get("is_default"):
            for item in self._items:
                if item["cluster"] == cluster:
                    item["is_default"] = False
        now = datetime.now(timezone.utc)
        row = {
            "id": self._next_id,
            "cluster": cluster,
            "created_at": now,
            "updated_at": now,
        }
        row.update(payload)
        self._next_id += 1
        self._items.append(row)
        return dict(row)

    def update_config(self, cluster: str, config_id: int, payload: dict):
        for item in self._items:
            if item["cluster"] == cluster and item["id"] == config_id:
                if payload.get("is_default"):
                    for other in self._items:
                        if other["cluster"] == cluster and other["id"] != config_id:
                            other["is_default"] = False
                item.update(payload)
                item["updated_at"] = datetime.now(timezone.utc)
                return dict(item)
        return None

    def delete_config(self, cluster: str, config_id: int):
        before = len(self._items)
        self._items = [
            item
            for item in self._items
            if not (item["cluster"] == cluster and item["id"] == config_id)
        ]
        return len(self._items) != before


class InMemoryConversationStore:
    def __init__(self):
        self.conversations = []
        self.messages = []
        self.tool_calls = []
        self._next_conversation_id = 1
        self._next_message_id = 1

    def create_conversation(self, cluster: str, username: str, title: str, model_config_id=None):
        row = {
            "id": self._next_conversation_id,
            "cluster": cluster,
            "username": username,
            "title": title,
            "model_config_id": model_config_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_message": None,
        }
        self._next_conversation_id += 1
        self.conversations.append(row)
        return dict(row)

    def get_conversation(self, cluster: str, username: str, conversation_id: int):
        for row in self.conversations:
            if (
                row["cluster"] == cluster
                and row["username"] == username
                and row["id"] == conversation_id
            ):
                return dict(row)
        return None

    def list_conversations(self, cluster: str, username: str, limit=100):
        rows = [
            dict(row)
            for row in self.conversations
            if row["cluster"] == cluster and row["username"] == username
        ]
        rows.sort(key=lambda item: (item["updated_at"], item["id"]), reverse=True)
        return rows[:limit]

    def add_message(self, conversation_id: int, role: str, content: str, model_config_id=None, metadata=None):
        row = {
            "id": self._next_message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "model_config_id": model_config_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
        }
        self._next_message_id += 1
        self.messages.append(row)
        for conversation in self.conversations:
            if conversation["id"] == conversation_id:
                conversation["updated_at"] = row["created_at"]
                conversation["last_message"] = content
                if model_config_id is not None:
                    conversation["model_config_id"] = model_config_id
                break
        return dict(row)

    def list_messages(self, cluster: str, username: str, conversation_id: int, limit=100):
        owner = self.get_conversation(cluster, username, conversation_id)
        if owner is None:
            return []
        rows = [
            dict(row)
            for row in self.messages
            if row["conversation_id"] == conversation_id
        ]
        rows.sort(key=lambda item: (item["created_at"], item["id"]))
        return rows[:limit]

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
        self.tool_calls.append(
            {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "cluster": cluster,
                "username": username,
                "tool_name": tool_name,
                "permission": permission,
                "input_payload": input_payload,
                "result_summary": result_summary,
                "status": status,
                "error": error,
                "duration_ms": duration_ms,
            }
        )


class DummyPolicy:
    def __init__(self, allowed_actions):
        self.allowed_actions = set(allowed_actions)

    def allowed_user_action(self, user, action: str):
        return action in self.allowed_actions


class DummySlurmrestd:
    @staticmethod
    def jobs():
        return [{"job_id": 123, "job_state": ["RUNNING"]}]

    @staticmethod
    def job(job_id: int):
        return {"job_id": job_id, "job_state": ["RUNNING"], "name": "train"}

    @staticmethod
    def nodes():
        return [{"name": "cn01", "cpus": 64, "real_memory": 1024, "alloc_memory": 512, "gres": ""}]

    @staticmethod
    def nodes_unfiltered():
        return DummySlurmrestd.nodes()

    @staticmethod
    def partitions():
        return [{"name": "gpu"}]

    @staticmethod
    def qos():
        return [{"name": "normal"}]

    @staticmethod
    def reservations():
        return [{"name": "maint"}]

    @staticmethod
    def accounts():
        return [{"name": "research"}]

    @staticmethod
    def associations():
        return [{"account": "research", "user": "alice"}]

    @staticmethod
    def _optional_number_value(value, default):
        return default if value is None else value

    @staticmethod
    def node_gres_extract_gpus(_gres):
        return 0


class TestAIService(TestCase):
    def setUp(self):
        self.config_store = InMemoryConfigStore()
        self.conversation_store = InMemoryConversationStore()
        self.secret_cipher = AISecretCipher(Fernet.generate_key().decode())
        self.app = SimpleNamespace(
            ai_enabled=True,
            settings=SimpleNamespace(
                service=SimpleNamespace(cluster="test"),
                ai=SimpleNamespace(enabled=True),
                node_metrics=SimpleNamespace(node_hostname_label="instance"),
            ),
            policy=DummyPolicy(
                {
                    "view-jobs",
                    "view-stats",
                    "view-nodes",
                    "view-partitions",
                    "view-qos",
                    "view-reservations",
                    "view-accounts",
                    "associations-view",
                    "view-history-jobs",
                }
            ),
            slurmrestd=DummySlurmrestd(),
            node_metrics_db=None,
            jobs_store=mock.Mock(query=mock.Mock(return_value={"jobs": [], "total": 0})),
        )
        self.user = SimpleNamespace(login="alice")
        self.service = AIService(
            app=self.app,
            config_store=self.config_store,
            conversation_store=self.conversation_store,
            secret_cipher=self.secret_cipher,
        )

    def _create_model(self, **overrides):
        payload = {
            "name": "openai-prod",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "display_name": "OpenAI Prod",
            "api_key": "sk-secret-1234",
            "enabled": True,
            "is_default": True,
        }
        payload.update(overrides)
        return self.service.create_model_config(payload)

    def test_create_model_config_encrypts_secret_and_masks_response(self):
        created = self._create_model()

        stored = self.config_store.get_config("test", created["id"])

        self.assertTrue(created["secret_configured"])
        self.assertEqual(created["secret_mask"], "***1234")
        self.assertNotIn("api_key", created)
        self.assertNotEqual(stored["secret_ciphertext"], "sk-secret-1234")
        self.assertEqual(
            self.secret_cipher.decrypt(stored["secret_ciphertext"]),
            "sk-secret-1234",
        )

    def test_update_model_config_switches_default_and_keeps_secret(self):
        first = self._create_model(name="first", display_name="First", is_default=True)
        second = self._create_model(
            name="second",
            display_name="Second",
            model="gpt-4.1",
            api_key="sk-secret-5678",
            is_default=False,
        )

        before = self.config_store.get_config("test", second["id"])["secret_ciphertext"]
        updated = self.service.update_model_config(
            second["id"],
            {
                "display_name": "Second Updated",
                "is_default": True,
            },
        )

        first_row = self.config_store.get_config("test", first["id"])
        second_row = self.config_store.get_config("test", second["id"])

        self.assertTrue(updated["is_default"])
        self.assertEqual(updated["display_name"], "Second Updated")
        self.assertFalse(first_row["is_default"])
        self.assertTrue(second_row["is_default"])
        self.assertEqual(second_row["secret_ciphertext"], before)
        self.assertEqual(updated["secret_mask"], "***5678")

    def test_validate_model_config_updates_timestamp(self):
        created = self._create_model(provider="google", model="gemini-2.5-pro")

        provider = mock.Mock()
        provider.validate.return_value = {"ok": True, "sample": "PONG"}
        with mock.patch("slurmweb.ai.service.get_provider_client", return_value=provider):
            result = self.service.validate_model_config(created["id"])

        stored = self.config_store.get_config("test", created["id"])
        self.assertEqual(result["result"], "ok")
        self.assertEqual(result["sample"], "PONG")
        self.assertIsNotNone(stored["last_validated_at"])
        self.assertIsNone(stored["last_validation_error"])

    def test_validate_model_config_requires_secret_for_non_ollama(self):
        created = self._create_model()

        with self.assertRaises(AIProviderValidationError):
            self.service.update_model_config(
                created["id"],
                {"api_key": "", "clear_secret": True},
            )

    def test_stream_chat_persists_messages_and_tool_audit(self):
        self._create_model()
        provider = mock.Mock()
        provider.complete.side_effect = [
            '{"type":"tool_call","tool":"get_job","arguments":{"job_id":"123"}}',
            '{"type":"final","content":"Job 123 is running."}',
        ]

        with mock.patch("slurmweb.ai.service.get_provider_client", return_value=provider):
            generator = self.service.stream_chat(self.user, {"message": "job 123?"})
            output = "".join(list(generator()))

        self.assertIn("event: conversation", output)
        self.assertIn("event: tool_start", output)
        self.assertIn("event: tool_end", output)
        self.assertIn("event: content", output)
        self.assertIn("event: complete", output)
        self.assertIn("event: done", output)
        self.assertEqual(len(self.conversation_store.conversations), 1)
        self.assertEqual(len(self.conversation_store.messages), 2)
        self.assertEqual(self.conversation_store.messages[0]["role"], "user")
        self.assertEqual(self.conversation_store.messages[1]["role"], "assistant")
        self.assertEqual(len(self.conversation_store.tool_calls), 1)
        self.assertEqual(self.conversation_store.tool_calls[0]["tool_name"], "get_job")
        self.assertEqual(self.conversation_store.tool_calls[0]["permission"], "view-jobs")
        self.assertEqual(self.conversation_store.tool_calls[0]["status"], "ok")

    def test_service_uses_default_runtime_limits(self):
        self._create_model()
        provider = mock.Mock()
        provider.complete.side_effect = [
            '{"type":"final","content":"'
            + ("x" * (DEFAULT_STREAM_CHUNK_SIZE + 5))
            + '"}'
        ]

        with mock.patch("slurmweb.ai.service.get_provider_client", return_value=provider):
            generator = self.service.stream_chat(self.user, {"message": "hello"})
            output = "".join(list(generator()))

        self.assertEqual(provider.complete.call_count, 1)
        self.assertEqual(DEFAULT_MAX_ROUNDS, 4)
        self.assertEqual(DEFAULT_MAX_HISTORY_MESSAGES, 24)
        self.assertEqual(DEFAULT_STREAM_CHUNK_SIZE, 32)
        self.assertGreaterEqual(output.count("event: content"), 2)

    def test_service_honors_agent_runtime_settings_when_defined(self):
        self._create_model()
        self.app.settings.ai.max_rounds = 1
        self.app.settings.ai.max_history_messages = 1
        self.app.settings.ai.stream_chunk_size = 5

        provider = mock.Mock()
        provider.complete.return_value = '{"type":"final","content":"abcdefghij"}'
        conversation = self.conversation_store.create_conversation(
            cluster="test",
            username="alice",
            title="Existing",
            model_config_id=1,
        )
        self.conversation_store.add_message(conversation["id"], "user", "m1", model_config_id=1)
        self.conversation_store.add_message(conversation["id"], "assistant", "m2", model_config_id=1)

        with mock.patch("slurmweb.ai.service.get_provider_client", return_value=provider):
            generator = self.service.stream_chat(
                self.user,
                {"message": "hello", "conversation_id": conversation["id"]},
            )
            output = "".join(list(generator()))

        self.assertEqual(provider.complete.call_count, 1)
        sent_messages = provider.complete.call_args.args[2]
        self.assertEqual(sent_messages[-1]["content"], "m1")
        self.assertEqual(output.count("event: content"), 2)

    def test_tool_registry_enforces_permission_mapping(self):
        self._create_model()
        self.app.policy = DummyPolicy({"view-stats"})
        self.service.tools.app = self.app

        with self.assertRaises(AIToolPermissionError):
            self.service.tools.execute(
                self.user,
                conversation_id=1,
                tool_name="get_job",
                arguments={"job_id": 123},
                message_id=1,
            )

        self.assertEqual(self.conversation_store.tool_calls[-1]["permission"], "view-jobs")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status"], "error")

    def test_fallback_readonly_api_rejects_unsupported_method(self):
        self._create_model()

        with self.assertRaises(AIToolExecutionError):
            self.service.tools.execute(
                self.user,
                conversation_id=1,
                tool_name="call_readonly_api",
                arguments={"method": "delete_job", "arguments": {"job_id": 123}},
                message_id=1,
            )

        self.assertEqual(self.conversation_store.tool_calls[-1]["tool_name"], "call_readonly_api")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status"], "error")
