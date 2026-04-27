# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from slurmweb.ai.service import AIProviderValidationError
from slurmweb.version import get_version

from ..lib.agent import TestAgentBase


class TestAgentAIViews(TestAgentBase):
    def setUp(self):
        self.setup_client()

    def _enable_ai(self):
        self.app.ai_enabled = True
        self.app.ai_service = mock.Mock()

    def _enable_rules(self, *rules):
        self.app.access_control_enabled = True
        self.app.access_control_store = mock.Mock()
        self.app.access_control_store.user_permissions.return_value = ([], [], list(rules))
        self.app.policy._access_control_enabled = True
        self.app.policy.set_access_control_store(self.app.access_control_store)

    def test_info_reports_ai_capabilities_when_disabled(self):
        response = self.client.get("/info")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["ai"],
            {
                "enabled": False,
                "configurable": False,
                "streaming": False,
                "persistence": False,
                "available_models_count": 0,
                "default_model_id": None,
                "providers": [],
                "tool_mode": "mixed",
            },
        )
        self.assertEqual(response.json["capabilities"]["ai"], response.json["ai"])

    def test_info_reports_ai_capabilities_when_enabled(self):
        self._enable_ai()
        self.app.ai_service.capabilities.return_value = {
            "enabled": True,
            "configurable": True,
            "streaming": True,
            "persistence": True,
            "available_models_count": 2,
            "default_model_id": 12,
            "providers": [{"key": "qwen", "label": "Qwen"}],
            "tool_mode": "mixed",
        }

        response = self.client.get("/info")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["ai"]["default_model_id"], 12)
        self.assertEqual(response.json["capabilities"]["ai"]["available_models_count"], 2)

    def test_ai_configs(self):
        self._enable_ai()
        self._enable_rules("admin/ai:view:*")
        self.app.ai_service.list_configs.return_value = [
            {
                "id": 3,
                "name": "qwen-prod",
                "provider": "qwen",
                "display_name": "Qwen Prod",
                "model": "qwen3-coder",
                "enabled": True,
                "is_default": True,
                "secret_configured": True,
                "secret_mask": "sk-***",
            }
        ]

        response = self.client.get(f"/v{get_version()}/ai/configs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["items"][0]["name"], "qwen-prod")
        self.app.ai_service.list_configs.assert_called_once_with()

    def test_ai_configs_require_view_ai_permission(self):
        self._enable_ai()
        self._enable_rules()
        response = self.client.get(f"/v{get_version()}/ai/configs")

        self.assertEqual(response.status_code, 403)

    def test_create_ai_config_validation_error(self):
        self._enable_ai()
        self._enable_rules("admin/ai:edit:*")
        self.app.ai_service.create_model_config.side_effect = AIProviderValidationError(
            "api_key is required"
        )
        response = self.client.post(
            f"/v{get_version()}/ai/configs",
            json={"name": "qwen-prod", "provider": "qwen"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("api_key is required", response.get_data(as_text=True))

    def test_validate_ai_config(self):
        self._enable_ai()
        self._enable_rules("admin/ai:edit:*")
        self.app.ai_service.validate_model_config.return_value = {
            "result": "ok",
            "provider": "qwen",
            "model": "qwen3-coder",
            "sample": "PONG",
            "last_validated_at": "2026-04-24T00:00:00+00:00",
        }

        response = self.client.post(f"/v{get_version()}/ai/configs/7/validate", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["sample"], "PONG")
        self.app.ai_service.validate_model_config.assert_called_once_with(7)

    def test_ai_chat_stream(self):
        self._enable_ai()
        self._enable_rules("ai:view:*")

        def _generator():
            yield 'event: conversation\ndata: {"conversation_id": 11}\n\n'
            yield 'event: content\ndata: {"delta": "hello"}\n\n'
            yield 'event: done\ndata: {"conversation_id": 11}\n\n'

        self.app.ai_service.stream_chat.return_value = _generator

        response = self.client.post(
            f"/v{get_version()}/ai/chat/stream",
            json={"message": "hello"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/event-stream")
        self.assertIn("event: conversation", response.get_data(as_text=True))
        self.app.ai_service.stream_chat.assert_called_once()
        self.assertEqual(
            self.app.ai_service.stream_chat.call_args.args[1],
            {"message": "hello"},
        )

    def test_ai_conversation_detail_not_found(self):
        self._enable_ai()
        self._enable_rules("ai:view:*")
        self.app.ai_service.get_conversation_detail.return_value = None
        response = self.client.get(f"/v{get_version()}/ai/conversations/42")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["description"], "AI conversation 42 not found")

    def test_ai_conversation_detail_returns_tool_calls(self):
        self._enable_ai()
        self._enable_rules("ai:view:*")
        self.app.ai_service.get_conversation_detail.return_value = {
            "id": 42,
            "title": "job detail",
            "model_config_id": 1,
            "created_at": "2026-04-27T00:00:00Z",
            "updated_at": "2026-04-27T00:00:01Z",
            "messages": [],
            "tool_calls": [
                {
                    "id": 7,
                    "tool_name": "query_agent_interface",
                    "interface_key": "job",
                    "status_code": 200,
                    "status": "ok",
                    "duration_ms": 12,
                    "input_payload": {"job_id": 123},
                    "result_summary": "job payload",
                    "error": None,
                    "created_at": "2026-04-27T00:00:01Z",
                }
            ],
        }

        response = self.client.get(f"/v{get_version()}/ai/conversations/42")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["tool_calls"][0]["interface_key"], "job")
        self.assertEqual(response.json["tool_calls"][0]["status_code"], 200)

    def test_ai_configs_fail_when_ai_disabled(self):
        self.app.ai_enabled = False
        self.app.ai_service = None
        self._enable_rules("admin/ai:view:*")
        response = self.client.get(f"/v{get_version()}/ai/configs")

        self.assertEqual(response.status_code, 501)
        self.assertEqual(response.json["description"], "AI assistant is disabled")
