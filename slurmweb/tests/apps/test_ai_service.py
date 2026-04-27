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
from slurmweb.permission_rules import permission_rules_allow


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
        self._next_tool_call_id = 1

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
        interface_key,
        status_code,
        input_payload: dict,
        result_summary,
        status: str,
        error,
        duration_ms,
    ):
        created_at = datetime.now(timezone.utc)
        self.tool_calls.append(
            {
                "id": self._next_tool_call_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "cluster": cluster,
                "username": username,
                "tool_name": tool_name,
                "permission": permission,
                "interface_key": interface_key,
                "status_code": status_code,
                "input_payload": input_payload,
                "result_summary": result_summary,
                "status": status,
                "error": error,
                "duration_ms": duration_ms,
                "created_at": created_at,
            }
        )
        self._next_tool_call_id += 1

    def list_tool_calls(self, cluster: str, username: str, conversation_id: int, limit=200):
        owner = self.get_conversation(cluster, username, conversation_id)
        if owner is None:
            return []
        return [
            dict(row)
            for row in self.tool_calls
            if row["conversation_id"] == conversation_id
        ][:limit]


class DummyPolicy:
    def __init__(self, allowed_rules):
        self.allowed_rules = set(allowed_rules)

    def allowed_user_permission(self, user, resource: str, operation: str, scope: str = "*"):
        return permission_rules_allow(self.allowed_rules, resource, operation, scope)


class DummySlurmrestd:
    cluster_name = "test-cluster"
    slurm_version = "25.11"
    api_version = "0.0.44"

    @staticmethod
    def jobs():
        return [{"job_id": 123, "job_state": ["RUNNING"], "association": {"user": "alice"}}]

    @staticmethod
    def job(job_id: int):
        owner = "alice" if int(job_id) == 123 else "bob"
        return {
            "job_id": job_id,
            "job_state": ["RUNNING"],
            "name": "train",
            "association": {"user": owner},
        }

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
    def account(name: str):
        return {"name": name}

    @staticmethod
    def associations():
        return [{"account": "research", "user": "alice"}]

    @staticmethod
    def users():
        return [{"name": "alice"}]

    @staticmethod
    def user(name: str):
        return {"name": name}

    @staticmethod
    def job_cancel(job_id: int, payload=None):
        return {"job_id": job_id, "cancelled": True, "payload": payload, "warnings": [], "errors": []}

    @staticmethod
    def job_update(job_id: int, payload):
        return {"job_id": job_id, "updated": True, "payload": payload, "warnings": [], "errors": []}

    @staticmethod
    def qos_update(payload):
        return {"updated": True, "payload": payload, "warnings": [], "errors": []}

    @staticmethod
    def supports_write_operations():
        return True

    @staticmethod
    def discover():
        return ("test-cluster", "25.11", "0.0.44")

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
                    "dashboard:view:*",
                    "analysis:view:*",
                    "jobs:view:*",
                    "resources:view:*",
                    "jobs/filter-partitions:view:*",
                    "qos:view:*",
                    "reservations:view:*",
                    "accounts:view:*",
                    "jobs-history:view:*",
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
            '{"type":"tool_call","tool":"query_agent_interface","arguments":{"interface_key":"job","arguments":{"job_id":"123"}}}',
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
        self.assertEqual(self.conversation_store.tool_calls[0]["tool_name"], "query_agent_interface")
        self.assertEqual(self.conversation_store.tool_calls[0]["interface_key"], "job")
        self.assertEqual(self.conversation_store.tool_calls[0]["permission"], "dynamic-query")
        self.assertEqual(self.conversation_store.tool_calls[0]["status_code"], 200)
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

    def test_stream_chat_can_chain_multiple_interfaces_before_final_answer(self):
        self._create_model()
        provider = mock.Mock()
        provider.complete.side_effect = [
            '{"type":"tool_call","tool":"query_agent_interface","arguments":{"interface_key":"job","arguments":{"job_id":"123"}}}',
            '{"type":"tool_call","tool":"query_agent_interface","arguments":{"interface_key":"jobs/history","arguments":{"job_id":"123","limit":"5"}}}',
            '{"type":"final","content":"Job 123 is running and history data was also checked."}',
        ]

        with mock.patch("slurmweb.ai.service.get_provider_client", return_value=provider):
            generator = self.service.stream_chat(self.user, {"message": "job 123 full context?"})
            output = "".join(list(generator()))

        self.assertIn("event: tool_start", output)
        self.assertEqual(len(self.conversation_store.tool_calls), 2)
        self.assertEqual(
            [call["interface_key"] for call in self.conversation_store.tool_calls],
            ["job", "jobs/history"],
        )

    def test_tool_registry_enforces_permission_mapping(self):
        self._create_model()
        self.app.policy = DummyPolicy({"dashboard:view:*"})
        self.service.tools.app = self.app

        with self.assertRaises(AIToolPermissionError):
            self.service.tools.execute(
                self.user,
                conversation_id=1,
                tool_name="query_agent_interface",
                arguments={"interface_key": "job", "arguments": {"job_id": 123}},
                message_id=1,
            )

        self.assertEqual(self.conversation_store.tool_calls[-1]["permission"], "dynamic-query")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status"], "error")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status_code"], 403)

    def test_query_interface_rejects_unsupported_interface(self):
        self._create_model()

        with self.assertRaises(AIToolExecutionError):
            self.service.tools.execute(
                self.user,
                conversation_id=1,
                tool_name="query_agent_interface",
                arguments={"interface_key": "unsupported", "arguments": {"job_id": 123}},
                message_id=1,
            )

        self.assertEqual(self.conversation_store.tool_calls[-1]["tool_name"], "query_agent_interface")
        self.assertEqual(self.conversation_store.tool_calls[-1]["interface_key"], "unsupported")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status"], "error")

    def test_write_interface_requires_matching_user_permission(self):
        self._create_model()

        with self.assertRaises(AIToolPermissionError):
            self.service.tools.execute(
                self.user,
                conversation_id=1,
                tool_name="mutate_agent_interface",
                arguments={"interface_key": "job/cancel", "arguments": {"job_id": 123}},
                message_id=1,
            )

        self.assertEqual(self.conversation_store.tool_calls[-1]["status_code"], 403)

        self.app.policy = DummyPolicy({"jobs:delete:self"})
        self.service.tools.app = self.app

        result = self.service.tools.execute(
            self.user,
            conversation_id=1,
            tool_name="mutate_agent_interface",
            arguments={"interface_key": "job/cancel", "arguments": {"job_id": 123}},
            message_id=1,
        )

        self.assertEqual(result["interface_key"], "job/cancel")
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(self.conversation_store.tool_calls[-1]["permission"], "dynamic-mutate")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status"], "ok")

        with self.assertRaises(AIToolPermissionError):
            self.service.tools.execute(
                self.user,
                conversation_id=1,
                tool_name="mutate_agent_interface",
                arguments={"interface_key": "job/cancel", "arguments": {"job_id": 456}},
                message_id=1,
            )

        self.assertEqual(self.conversation_store.tool_calls[-1]["interface_key"], "job/cancel")
        self.assertEqual(self.conversation_store.tool_calls[-1]["status_code"], 403)

        self.app.policy = DummyPolicy({"jobs:delete:*"})
        self.service.tools.app = self.app

        result = self.service.tools.execute(
            self.user,
            conversation_id=1,
            tool_name="mutate_agent_interface",
            arguments={"interface_key": "job/cancel", "arguments": {"job_id": 456}},
            message_id=1,
        )

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(self.conversation_store.tool_calls[-1]["status"], "ok")

    def test_get_conversation_detail_includes_tool_calls(self):
        self._create_model()
        conversation = self.conversation_store.create_conversation(
            cluster="test",
            username="alice",
            title="Existing",
            model_config_id=1,
        )
        self.conversation_store.add_message(conversation["id"], "user", "m1", model_config_id=1)
        self.conversation_store.record_tool_call(
            conversation_id=conversation["id"],
            message_id=1,
            cluster="test",
            username="alice",
            tool_name="query_agent_interface",
            permission="dynamic-query",
            interface_key="job",
            status_code=200,
            input_payload={"job_id": 123},
            result_summary="job payload",
            status="ok",
            error=None,
            duration_ms=8,
        )

        details = self.service.get_conversation_detail(self.user, conversation["id"])

        self.assertEqual(len(details["tool_calls"]), 1)
        self.assertEqual(details["tool_calls"][0]["interface_key"], "job")
        self.assertEqual(details["tool_calls"][0]["status_code"], 200)
