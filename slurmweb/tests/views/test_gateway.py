# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock
import tempfile
import os
import shutil

from rfl.authentication.user import AuthenticatedUser

from slurmweb.version import get_version

from ..lib.gateway import TestGatewayBase, fake_slurmweb_agent
from ..lib.utils import flask_version, mock_agent_aio_response


class TestGatewayViews(TestGatewayBase):
    def setUp(self):
        self.setup_app()

    def test_version(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, f"Slurm-web gateway v{get_version()}\n")

    def test_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # copy templates from vendor path
            tmpdir_templates = os.path.join(tmpdir, "templates")
            shutil.copytree(
                os.path.join(self.vendor_path, "templates"), tmpdir_templates
            )
            self.app.set_templates_folder(tmpdir_templates)

            # generate test markdown file
            self.app.settings.ui.message_login = os.path.join(tmpdir, "login.md")
            with open(self.app.settings.ui.message_login, "w+") as fh:
                fh.write("Hello, *world*!")

            # check rendered html
            response = self.client.get("/api/messages/login")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/html")
            self.assertIn("Hello, <em>world</em>!", response.text)

    def test_message_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # set not existing markdown message
            self.app.settings.ui.message_login = os.path.join(tmpdir, "not-found.md")
            with self.assertLogs("slurmweb", level="DEBUG") as cm:
                response = self.client.get("/api/messages/login")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(
                response.json["description"], "login service message not found"
            )
            self.assertEqual(
                cm.output,
                [
                    "DEBUG:slurmweb.views.gateway:Login service markdown file "
                    f"{self.app.settings.ui.message_login} not found"
                ],
            )

    def test_message_permission_error(self):
        if not hasattr(os, "geteuid"):
            self.skipTest("os.geteuid() is not available on this platform")
        if os.geteuid() == 0:
            self.skipTest("Cannot test permission error as root")
        with tempfile.TemporaryDirectory() as tmpdir:
            # copy templates from vendor path
            tmpdir_templates = os.path.join(tmpdir, "templates")
            shutil.copytree(
                os.path.join(self.vendor_path, "templates"), tmpdir_templates
            )
            self.app.set_templates_folder(tmpdir_templates)

            # generate test markdown file w/o read permission
            self.app.settings.ui.message_login = os.path.join(tmpdir, "message.md")
            with open(self.app.settings.ui.message_login, "w+") as fh:
                fh.write("Hello, *world*!")
            os.chmod(self.app.settings.ui.message_login, 0o200)
            if os.access(self.app.settings.ui.message_login, os.R_OK):
                self.skipTest("Platform does not enforce unreadable chmod semantics")

            response = self.client.get("/api/messages/login")
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.json["description"],
                "Permission error on login service markdown file "
                f"{self.app.settings.ui.message_login}",
            )

    def test_message_template_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # set not existing templates folder
            tmpdir_templates = os.path.join(tmpdir, "templates")
            self.app.set_templates_folder(tmpdir_templates)

            self.app.settings.ui.message_login = os.path.join(tmpdir, "message.md")
            with open(self.app.settings.ui.message_login, "w+") as fh:
                fh.write("Hello, *world*!")

            response = self.client.get("/api/messages/login")
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.json["description"],
                "message template message.html.j2 not found",
            )

    @mock.patch("slurmweb.views.gateway.async_cache_user_on_agents")
    def test_login_propagates_user_cache(self, mock_cache_user_on_agents):
        self.setup_app(use_token=False, conf_overrides={"ldap": True})
        self.app.authentifier.login = mock.Mock(
            return_value=AuthenticatedUser(
                login="test", fullname="Testing User", groups=["group"]
            )
        )
        response = self.client.post(
            "/api/login",
            data='{"user":"test","password":"secret"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["fullname"], "Testing User")
        self.assertEqual(response.json["groups"], ["group"])
        mock_cache_user_on_agents.assert_called_once()

    @mock.patch("slurmweb.views.gateway.async_cache_user_on_agents")
    def test_login_cache_failure_does_not_fail_authentication(self, mock_cache_user_on_agents):
        self.setup_app(use_token=False, conf_overrides={"ldap": True})
        self.app.authentifier.login = mock.Mock(
            return_value=AuthenticatedUser(
                login="test", fullname="Testing User", groups=["group"]
            )
        )
        mock_cache_user_on_agents.side_effect = RuntimeError("cache failed")
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            response = self.client.post(
                "/api/login",
                data='{"user":"test","password":"secret"}',
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "WARNING:slurmweb.views.gateway:Failed to propagate authenticated user cache to agents: cache failed",
            cm.output,
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.post")
    def test_login_retries_agent_refresh_when_cached_agents_empty(self, mock_post):
        self.setup_app(use_token=False, conf_overrides={"ldap": True})
        self.app.authentifier.login = mock.Mock(
            return_value=AuthenticatedUser(
                login="test", fullname="Testing User", groups=["group"]
            )
        )
        foo = fake_slurmweb_agent("foo")
        self.app.refresh_agents = mock.Mock(side_effect=[{}, {"foo": foo}])
        _, mock_post.return_value = mock_agent_aio_response(
            content='{"result":"User cache updated"}'
        )

        response = self.client.post(
            "/api/login",
            data='{"user":"test","password":"secret"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.app.refresh_agents.call_args_list,
            [mock.call(), mock.call(force=True)],
        )
        mock_post.assert_called_once_with(
            f"http://foo/v{foo.version}/users/cache",
            headers=mock.ANY,
            json={
                "username": "test",
                "fullname": "Testing User",
                "groups": ["group"],
            },
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.post")
    def test_login_propagates_user_cache_only_to_database_enabled_agents(self, mock_post):
        self.setup_app(use_token=False, conf_overrides={"ldap": True})
        self.app.authentifier.login = mock.Mock(
            return_value=AuthenticatedUser(
                login="test", fullname="Testing User", groups=["group"]
            )
        )
        foo = fake_slurmweb_agent("foo")
        bar = fake_slurmweb_agent("bar")
        bar.database = False
        self.app.refresh_agents = mock.Mock(return_value={"foo": foo, "bar": bar})
        _, mock_post.return_value = mock_agent_aio_response(
            content='{"result":"User cache updated"}'
        )

        response = self.client.post(
            "/api/login",
            data='{"user":"test","password":"secret"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.app.refresh_agents.assert_called_once_with()
        mock_post.assert_called_once_with(
            f"http://foo/v{foo.version}/users/cache",
            headers=mock.ANY,
            json={
                "username": "test",
                "fullname": "Testing User",
                "groups": ["group"],
            },
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_cache_stats(self, mock_get):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        asset, mock_get.return_value = mock_agent_aio_response(asset="cache-stats")
        response = self.client.get("/api/agents/foo/cache/stats")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json.keys(), ["hit", "miss"])

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_clusters_include_extended_capabilities(self, mock_get):
        permissions, mock_get.return_value = mock_agent_aio_response(
            asset="permissions"
        )
        foo = fake_slurmweb_agent("foo")
        foo.access_control = True
        foo.persistence = True
        foo.node_metrics = True
        foo.user_metrics = True
        foo.capabilities = {
            "job_history": True,
            "ldap_cache": True,
            "node_metrics": True,
            "user_metrics": {
                "enabled": True,
                "history_api": True,
                "summary_api": True,
            },
            "user_analytics": {
                "enabled": True,
                "prometheus_user_metrics": True,
                "user_activity_api": True,
            },
        }
        self.app_set_agents({"foo": foo})

        response = self.client.get("/api/clusters")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        cluster = response.json[0]
        self.assertEqual(cluster["name"], "foo")
        self.assertEqual(cluster["capabilities"], foo.capabilities)
        self.assertEqual(cluster["permissions"], permissions)
        self.assertEqual(cluster["access_control"], True)
        self.assertEqual(cluster["database"], True)
        self.assertEqual(cluster["metrics"], True)
        self.assertEqual(cluster["cache"], True)
        self.assertEqual(cluster["node_metrics"], True)
        self.assertEqual(cluster["user_metrics"], True)
        self.assertEqual(cluster["persistence"], True)
        self.assertEqual(cluster["racksdb"], True)
        self.assertIn("ai", cluster)
        mock_get.assert_called_once_with(
            f"http://foo/v{foo.version}/permissions",
            headers=mock.ANY,
        )

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_access_roles(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"items":[{"id":1,"name":"db-admin","actions":["admin-manage"]}]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.get("/api/agents/foo/access/roles")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["items"][0]["name"], "db-admin")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "access/roles"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_update_access_user_roles(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"username":"alice","role_ids":[1,2]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.put(
            "/api/agents/foo/access/users/alice/roles",
            json={"role_ids": [1, 2]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["role_ids"], [1, 2])
        self.assertEqual(
            mock_proxy_agent.call_args.args[:2],
            ("foo", "access/users/alice/roles"),
        )

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_job_history_detail(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (self.app.response_class(
            response='{"id": 12, "job_id": 1234}',
            status=200,
            mimetype="application/json",
        ), 200)
        response = self.client.get("/api/agents/foo/jobs/history/12")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["id"], 12)
        self.assertEqual(response.json["job_id"], 1234)
        mock_proxy_agent.assert_called_once()
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "jobs/history/12"))
        self.assertTrue(mock_proxy_agent.call_args.args[2])

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_ldap_cache_users(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"items": [{"username": "alice", "fullname": "Alice Doe"}], "total": 1, "page": 1, "page_size": 50}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )
        response = self.client.get("/api/agents/foo/users/cache")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "items": [{"username": "alice", "fullname": "Alice Doe"}],
                "total": 1,
                "page": 1,
                "page_size": 50,
            },
        )
        mock_proxy_agent.assert_called_once()
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "users/cache"))
        self.assertTrue(mock_proxy_agent.call_args.args[2])

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_ldap_cache_users_forwards_filters_to_agent(self, mock_get):
        foo = fake_slurmweb_agent("foo")
        self.app_set_agents({"foo": foo})
        _, mock_get.return_value = mock_agent_aio_response(
            content={
                "items": [{"username": "alice", "fullname": "Alice Doe"}],
                "total": 1,
                "page": 2,
                "page_size": 20,
            }
        )

        response = self.client.get(
            "/api/agents/foo/users/cache?username=ali&page=2&page_size=20"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["page"], 2)
        mock_get.assert_called_once_with(
            f"http://foo/v{foo.version}/users/cache?username=ali&page=2&page_size=20",
            headers=mock.ANY,
        )

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_user_metrics_history(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"submissions":[[1713956400000,2]]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )
        response = self.client.get("/api/agents/foo/user/alice/metrics/history?range=hour")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["submissions"], [[1713956400000, 2]])
        self.assertEqual(
            mock_proxy_agent.call_args.args[:2], ("foo", "user/alice/metrics/history")
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_user_metrics_history_forwards_range_to_agent(self, mock_get):
        foo = fake_slurmweb_agent("foo")
        self.app_set_agents({"foo": foo})
        _, mock_get.return_value = mock_agent_aio_response(
            content={"submissions": [[1713956400000, 2]]}
        )

        response = self.client.get(
            "/api/agents/foo/user/alice/metrics/history?range=day"
        )

        self.assertEqual(response.status_code, 200)
        mock_get.assert_called_once_with(
            f"http://foo/v{foo.version}/user/alice/metrics/history?range=day",
            headers=mock.ANY,
        )

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_user_tools_analysis(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"username":"alice","totals":{"completed_jobs":3},"tool_breakdown":[]}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )
        response = self.client.get(
            "/api/agents/foo/user/alice/tools/analysis?start=2026-04-24T00:00:00Z&end=2026-04-24T12:00:00Z"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["totals"]["completed_jobs"], 3)
        self.assertEqual(
            mock_proxy_agent.call_args.args[:2], ("foo", "user/alice/tools/analysis")
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_user_tools_analysis_requests_agent_url(self, mock_get):
        foo = fake_slurmweb_agent("foo")
        self.app_set_agents({"foo": foo})
        _, mock_get.return_value = mock_agent_aio_response(
            content={
                "username": "alice",
                "profile": None,
                "generated_at": None,
                "totals": {"completed_jobs": 0},
                "tool_breakdown": [],
            }
        )

        response = self.client.get(
            "/api/agents/foo/user/alice/tools/analysis?start=2026-04-24T00:00:00Z&end=2026-04-24T12:00:00Z"
        )

        self.assertEqual(response.status_code, 200)
        mock_get.assert_called_once_with(
            f"http://foo/v{foo.version}/user/alice/tools/analysis?start=2026-04-24T00:00:00Z&end=2026-04-24T12:00:00Z",
            headers=mock.ANY,
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_node_metrics(self, mock_get):
        foo = fake_slurmweb_agent("foo")
        self.app_set_agents({"foo": foo})
        _, mock_get.return_value = mock_agent_aio_response(
            content={
                "cpu_usage": 0.25,
                "memory_usage": 0.5,
                "disk_usage": 0.75,
            }
        )

        response = self.client.get("/api/agents/foo/node/cn1/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "cpu_usage": 0.25,
                "memory_usage": 0.5,
                "disk_usage": 0.75,
            },
        )
        mock_get.assert_called_once_with(
            f"http://foo/v{foo.version}/node/cn1/metrics",
            headers=mock.ANY,
        )

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_node_metrics_history(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"cpu_usage": [], "memory_usage": [], "disk_usage": []}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )
        response = self.client.get("/api/agents/foo/node/cn1/metrics/history?range=hour")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            ["cpu_usage", "memory_usage", "disk_usage"],
        )
        mock_proxy_agent.assert_called_once()
        self.assertEqual(
            mock_proxy_agent.call_args.args[:2], ("foo", "node/cn1/metrics/history")
        )
        self.assertTrue(mock_proxy_agent.call_args.args[2])

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_analysis_diag(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"mode":"primary"}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.get("/api/agents/foo/analysis/diag")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"mode": "primary"})
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "analysis/diag"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_analysis_ping(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"ok":true}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.get("/api/agents/foo/analysis/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"ok": True})
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "analysis/ping"))

    def test_admin_system_query_removed(self):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})

        response = self.client.get("/api/agents/foo/admin/system/licenses")

        self.assertEqual(response.status_code, 404)

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_update_job(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"result":"job updated"}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.post(
            "/api/agents/foo/job/123/update",
            data='{"priority": 1000}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"], "job updated")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "job/123/update"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_delete_job(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"result":"job cancelled"}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.delete(
            "/api/agents/foo/job/123/cancel",
            data='{"signal":"TERM"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"], "job cancelled")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "job/123/cancel"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_update_node(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"result":"node updated"}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.post(
            "/api/agents/foo/node/cn01/update",
            data='{"state":"DRAIN","reason":"maintenance"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"], "node updated")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "node/cn01/update"))

    @mock.patch("slurmweb.views.gateway.proxy_agent")
    def test_delete_node(self, mock_proxy_agent):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        mock_proxy_agent.return_value = (
            self.app.response_class(
                response='{"result":"node deleted"}',
                status=200,
                mimetype="application/json",
            ),
            200,
        )

        response = self.client.delete("/api/agents/foo/node/cn01/delete")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"], "node deleted")
        self.assertEqual(mock_proxy_agent.call_args.args[:2], ("foo", "node/cn01/delete"))

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_node_metrics_history_forwards_range_to_agent(self, mock_get):
        foo = fake_slurmweb_agent("foo")
        self.app_set_agents({"foo": foo})
        _, mock_get.return_value = mock_agent_aio_response(
            content={"cpu_usage": [], "memory_usage": [], "disk_usage": []}
        )

        response = self.client.get(
            "/api/agents/foo/node/cn1/metrics/history?range=week"
        )

        self.assertEqual(response.status_code, 200)
        mock_get.assert_called_once_with(
            f"http://foo/v{foo.version}/node/cn1/metrics/history?range=week",
            headers=mock.ANY,
        )

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.post")
    def test_cache_reset(self, mock_post):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        asset, mock_post.return_value = mock_agent_aio_response(asset="cache-reset")
        try:
            response = self.client.post("/api/agents/foo/cache/reset", json={})
        except TypeError:
            # FlaskClient.post() supports json argument since Flask 0.15.0, we need to
            # support Flask 0.12.2 on el8.
            response = self.client.post("/api/agents/foo/cache/reset", data={})
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json.keys(), ["hit", "miss"])

    @mock.patch("slurmweb.views.gateway.aiohttp.ClientSession.get")
    def test_unexpected_not_json(self, mock_get):
        self.app_set_agents({"foo": fake_slurmweb_agent("foo")})
        _, mock_get.return_value = mock_agent_aio_response(
            content="fail", fail_content_type=True
        )
        response = self.client.get("/api/agents/foo/jobs")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json,
            {
                "code": 500,
                "description": (
                    "Unsupported Content-Type for agent foo URL http://localhost/info: "
                    "0, message='', url='http://localhost/info'"
                ),
                "name": "Internal Server Error",
            },
        )

    @mock.patch("slurmweb.views.gateway.get_version")
    def test_unexpected_generic_exception(self, mock_version):
        # By default in development and testing mode, Flask propagate exceptions
        # occuring in views. Disable this behavior temporarily despite testing
        # mode in order to emulate production mode.
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        # Arbitrary generate KeyError in version view, to emulate generic
        # exception catched by Flask exception handler.
        mock_version.side_effect = KeyError("fake key error")
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 500)
        # When unexpected exceptions occur ,Flask < v1.1.0 provides the original
        # exception to HTTP/500 error handler. Newer versions of Flask provides
        # InternalServerError HTTPException generated by Flask. The processing
        # path of the error is different and leads to slightly different error
        # message eventually.
        if flask_version() < (1, 1, 0):
            self.assertEqual(
                response.json,
                {"code": 500, "description": "'fake key error'", "name": "KeyError"},
            )
        else:
            self.assertEqual(
                response.json,
                {
                    "code": 500,
                    "description": (
                        "The server encountered an internal error and was unable to "
                        "complete your request. Either the server is overloaded or "
                        "there is an error in the application."
                    ),
                    "name": "Internal Server Error",
                },
            )
        # Restore default exceptions propagation mode.
        self.app.config["PROPAGATE_EXCEPTIONS"] = None
