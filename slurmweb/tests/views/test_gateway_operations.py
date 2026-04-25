# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from ..lib.gateway import TestGatewayBase, fake_slurmweb_agent
from ..lib.utils import mock_agent_aio_response


class TestGatewayOperations(TestGatewayBase):
    def setUp(self):
        self.setup_app()
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_analysis_ping(self, mock_proxy_agent):
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"pings":[{"hostname":"admin","responding":true}]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.get("/api/agents/foo/analysis/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["pings"][0]["hostname"], "admin")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "analysis/ping"))

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.delete")
    def test_job_cancel_forwards_delete_body(self, mock_delete):
        _, mock_delete.return_value = mock_agent_aio_response(
            content='{"supported":true,"operation":"jobs.cancel","warnings":[],"errors":[],"result":{"job_id":101}}'
        )

        response = self.client.delete(
            "/api/agents/foo/job/101/cancel",
            json={"signal": "TERM"},
        )

        self.assertEqual(response.status_code, 200)
        mock_delete.assert_called_once_with(
            f"http://foo/v{fake_slurmweb_agent('foo').version}/job/101/cancel",
            headers=mock.ANY,
            json={"signal": "TERM"},
        )
