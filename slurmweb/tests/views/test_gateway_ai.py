# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from ..lib.gateway import TestGatewayBase, fake_slurmweb_agent
from ..lib.utils import mock_agent_aio_response


class TestGatewayAIViews(TestGatewayBase):
    def setUp(self):
        self.setup_app()

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_include_ai_capability(self, mock_get):
        permissions, mock_get.return_value = mock_agent_aio_response(asset="permissions")
        foo = fake_slurmweb_agent("foo")
        foo.ai = {
            "enabled": True,
            "configurable": True,
            "streaming": True,
            "persistence": True,
            "available_models_count": 2,
            "default_model_id": 9,
            "providers": [{"key": "qwen", "label": "Qwen"}],
            "tool_mode": "mixed",
        }
        foo.capabilities["ai"] = dict(foo.ai)
        self.app_set_agents({"foo": foo})

        response = self.client.get("/api/clusters")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]["ai"]["default_model_id"], 9)
        self.assertEqual(response.json[0]["capabilities"]["ai"]["available_models_count"], 2)
        self.assertEqual(response.json[0]["permissions"], permissions)

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_ai_configs_proxy(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"items":[{"id":1,"name":"qwen-prod","provider":"qwen"}]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.get("/api/agents/foo/ai/configs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["items"][0]["name"], "qwen-prod")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "ai/configs"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_validate_ai_config_proxy(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"result":"ok","sample":"PONG"}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.post("/api/agents/foo/ai/configs/5/validate", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"], "ok")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "ai/configs/5/validate"))

    @mock.patch("slurmweb.views.gateway.proxy_stream_agent")
    def test_ai_chat_stream_proxy(self, mock_proxy_stream_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_stream_agent.return_value = self.app.response_class(
            response='event: done\ndata: {"conversation_id": 3}\n\n',
            status=200,
            mimetype="text/event-stream",
        )

        response = self.client.post("/api/agents/foo/ai/chat/stream", json={"message": "hello"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/event-stream")
        self.assertIn("event: done", response.get_data(as_text=True))
        self.assertEqual(mock_proxy_stream_agent.call_args.args[:2], ("foo", "ai/chat/stream"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_ai_conversation_detail_proxy(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"id":12,"title":"GPU capacity","messages":[]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.get("/api/agents/foo/ai/conversations/12")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["title"], "GPU capacity")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "ai/conversations/12"))
