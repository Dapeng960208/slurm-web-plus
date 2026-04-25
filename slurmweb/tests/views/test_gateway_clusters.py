# Copyright (c) 2025 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from ..lib.gateway import TestGatewayBase, fake_slurmweb_agent
from ..lib.utils import mock_agent_aio_response


class TestGatewayViews(TestGatewayBase):
    def setUp(self):
        self.setup_app()

    def _expected_cluster(self, name, permissions):
        agent = fake_slurmweb_agent(name)
        return {
            "capabilities": agent.capabilities,
            "database": True,
            "infrastructure": name,
            "metrics": True,
            "cache": True,
            "name": name,
            "node_metrics": False,
            "user_metrics": False,
            "persistence": False,
            "permissions": permissions,
            "racksdb": True,
            "access_control": False,
            "ai": agent.ai,
        }

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_one_agent(self, mock_get):
        permissions, mock_get.return_value = mock_agent_aio_response(
            asset="permissions"
        )
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})

        response = self.client.get("/api/clusters")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0], self._expected_cluster("foo", permissions))

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_multiple_agents(self, mock_get):
        permissions, mock_get.return_value = mock_agent_aio_response(
            asset="permissions"
        )
        self.app_set_agents(
            {
                "foo": fake_slurmweb_agent("foo"),
                "bar": fake_slurmweb_agent("bar"),
                "baz": fake_slurmweb_agent("baz"),
            }
        )
        response = self.client.get("/api/clusters")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 3)
        self.assertCountEqual(
            response.json,
            [
                self._expected_cluster("foo", permissions),
                self._expected_cluster("bar", permissions),
                self._expected_cluster("baz", permissions),
            ],
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_agent_error(self, mock_get):
        _, mock_get.return_value = mock_agent_aio_response(
            status=404, content="not found"
        )
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        with self.assertLogs("slurmweb", level="ERROR") as cm:
            response = self.client.get("/api/clusters")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 0)
        self.assertCountEqual(
            response.json,
            [],
        )
        self.assertEqual(
            cm.output,
            [
                "ERROR:slurmweb.views.gateway:Unable to retrieve permissions from "
                "cluster foo: 404"
            ],
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_denied_no_hide(self, mock_get):
        permissions = {"actions": []}
        _, mock_get.return_value = mock_agent_aio_response(content=permissions)
        self.app_set_agents(
            {"foo": fake_slurmweb_agent("foo"), "bar": fake_slurmweb_agent("bar")}
        )
        response = self.client.get("/api/clusters")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 2)
        self.assertCountEqual(
            response.json,
            [
                self._expected_cluster("foo", permissions),
                self._expected_cluster("bar", permissions),
            ],
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_denied_hide(self, mock_get):
        permissions = {"actions": []}
        _, mock_get.return_value = mock_agent_aio_response(content=permissions)
        self.app_set_agents(
            {"foo": fake_slurmweb_agent("foo"), "bar": fake_slurmweb_agent("bar")}
        )
        # Enable UI hide denied parameter
        self.app.settings.ui.hide_denied = True
        response = self.client.get("/api/clusters")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 0)
        self.assertCountEqual(response.json, [])
