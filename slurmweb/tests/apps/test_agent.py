# Copyright (c) 2025 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import sys
import unittest
from unittest import mock

from slurmweb.errors import SlurmwebConfigurationError

from ..lib.agent import TestAgentBase, is_racksdb_available


class TestAgentApp(TestAgentBase):
    def test_app_loaded(self):
        # No error log must be emitted in this case. Note that assertNoLogs is available
        # starting from Python 3.10. For versions below, absence of logs is not checked.
        if sys.version_info < (3, 10):
            self.setup_client()
        else:
            with self.assertNoLogs("slurmweb", level="ERROR"):
                self.setup_client()

    @unittest.skipIf(not is_racksdb_available(), "RacksDB not installed")
    def test_app_racksdb_format_error(self):
        with self.assertLogs("slurmweb", level="ERROR") as cm:
            self.setup_client(racksdb_format_error=True)
        self.assertEqual(
            cm.output,
            [
                "ERROR:slurmweb.apps.agent:Unable to load RacksDB database: fake db "
                "format error"
            ],
        )

    @unittest.skipIf(not is_racksdb_available(), "RacksDB not installed")
    def test_app_racksdb_schema_error(self):
        with self.assertLogs("slurmweb", level="ERROR") as cm:
            self.setup_client(racksdb_schema_error=True)
        self.assertEqual(
            cm.output,
            [
                "ERROR:slurmweb.apps.agent:Unable to load RacksDB schema: fake db "
                "schema error"
            ],
        )

    def test_app_slurmrestd_socket_deprecated(self):
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            self.setup_client(slurmrestd_parameters=["socket=/test/slurmrestd.socket"])
        self.assertIn(
            "WARNING:slurmweb.apps.agent:Using deprecated parameter "
            "[slurmrestd]>socket to define [slurmrest]>uri, update your site agent "
            "configuration file",
            cm.output,
        )
        self.assertEqual(
            self.app.settings.slurmrestd.uri.geturl(), "unix:/test/slurmrestd.socket"
        )
        self.assertEqual(self.app.settings.slurmrestd.uri.scheme, "unix")
        self.assertEqual(
            self.app.settings.slurmrestd.uri.path, "/test/slurmrestd.socket"
        )

    def test_app_slurmrestd_auth_local_deprecated(self):
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            self.setup_client(slurmrestd_parameters=["auth=local"])
        self.assertIn(
            "WARNING:slurmweb.apps.agent:Using deprecated slurmrestd local "
            "authentication method, it is recommended to migrate to jwt authentication",
            cm.output,
        )
        self.assertEqual(self.app.settings.slurmrestd.auth, "local")

    @mock.patch("slurmweb.apps.agent.SlurmrestdFilteredCached")
    def test_app_slurmrestd_conf_error(self, mock_slurmrestd):
        mock_slurmrestd.side_effect = SlurmwebConfigurationError("fail")
        with self.assertRaisesRegex(SystemExit, "1"):
            with self.assertLogs("slurmweb", level="ERROR") as cm:
                self.setup_client()
        self.assertEqual(
            cm.output, ["CRITICAL:slurmweb.apps.agent:Configuration error: fail"]
        )

    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_enables_database_support_when_database_enabled(
        self, mock_users_store
    ):
        self.setup_client(database=True)
        mock_users_store.assert_called_once()
        mock_users_store.return_value.validate_connection.assert_called_once()

    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_continues_when_database_support_init_fails(self, mock_users_store):
        mock_users_store.return_value.validate_connection.side_effect = RuntimeError("boom")
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            self.setup_client(database=True, persistence=True)
        self.assertIn(
            "WARNING:slurmweb.apps.agent:Unable to initialize database support: boom",
            cm.output,
        )
        self.assertIsNone(self.app.users_store)
        self.assertIsNone(self.app.jobs_store)

    @mock.patch("slurmweb.persistence.access_control_store.AccessControlStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_enables_access_control_when_dependencies_ready(
        self, mock_users_store, mock_access_control_store
    ):
        self.setup_client(database=True, persistence=True, access_control_enabled=True)
        mock_users_store.assert_called_once()
        mock_access_control_store.assert_called_once()
        mock_access_control_store.return_value.validate_connection.assert_called_once()
        mock_access_control_store.return_value.normalize_legacy_role_actions.assert_called_once()
        mock_users_store.return_value.list_cached_users_for_policy_refresh.assert_called_once_with()
        self.assertTrue(self.app.access_control_enabled)

    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_warns_when_access_control_database_support_missing(self, mock_users_store):
        mock_users_store.return_value.validate_connection.side_effect = RuntimeError("boom")
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            self.setup_client(database=True, persistence=True, access_control_enabled=True)
        self.assertIn(
            "WARNING:slurmweb.apps.agent:Unable to initialize database support: boom",
            cm.output,
        )
        mock_users_store.return_value.list_cached_users_for_policy_refresh.assert_not_called()

    @mock.patch("slurmweb.persistence.access_control_store.AccessControlStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_refreshes_cached_policy_snapshots_on_startup(
        self, mock_users_store, mock_access_control_store
    ):
        mock_users_store.return_value.list_cached_users_for_policy_refresh.return_value = [
            {
                "username": "alice",
                "fullname": "Alice Doe",
                "groups": ["group"],
            }
        ]

        self.setup_client(database=True, persistence=True, access_control_enabled=True)

        mock_users_store.return_value.list_cached_users_for_policy_refresh.assert_called_once_with()
        mock_users_store.return_value.update_policy_snapshot.assert_called_once()
        args = mock_users_store.return_value.update_policy_snapshot.call_args.args
        self.assertEqual(args[0], "alice")
        self.assertIsInstance(args[1], list)
        self.assertIsInstance(args[2], list)

    @mock.patch("slurmweb.persistence.access_control_store.AccessControlStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_refreshes_cached_policy_snapshots_when_database_enabled_even_if_legacy_flag_false(
        self, mock_users_store, mock_access_control_store
    ):
        self.setup_client(database=True, persistence=True, access_control_enabled=False)

        mock_access_control_store.assert_called_once()
        mock_access_control_store.return_value.normalize_legacy_role_actions.assert_called_once()
        mock_access_control_store.return_value.seed_default_roles.assert_called_once()
        mock_users_store.return_value.list_cached_users_for_policy_refresh.assert_called_once_with()

    @mock.patch("slurmweb.persistence.access_control_store.AccessControlStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_continues_when_startup_policy_snapshot_refresh_fails_for_user(
        self, mock_users_store, mock_access_control_store
    ):
        mock_users_store.return_value.list_cached_users_for_policy_refresh.return_value = [
            {
                "username": "alice",
                "fullname": "Alice Doe",
                "groups": ["group"],
            },
            {
                "username": "bob",
                "fullname": "Bob Doe",
                "groups": [],
            },
        ]
        mock_users_store.return_value.update_policy_snapshot.side_effect = [
            RuntimeError("boom"),
            True,
        ]

        with self.assertLogs("slurmweb", level="WARNING") as cm:
            self.setup_client(database=True, persistence=True, access_control_enabled=True)

        self.assertIn(
            "WARNING:slurmweb.apps.agent:Unable to refresh startup policy snapshot for cached user alice: boom",
            cm.output,
        )
        self.assertEqual(mock_users_store.return_value.update_policy_snapshot.call_count, 2)

    @mock.patch("slurmweb.persistence.access_control_store.AccessControlStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_continues_when_loading_cached_users_for_startup_policy_refresh_fails(
        self, mock_users_store, mock_access_control_store
    ):
        mock_users_store.return_value.list_cached_users_for_policy_refresh.side_effect = RuntimeError(
            "boom"
        )

        with self.assertLogs("slurmweb", level="WARNING") as cm:
            self.setup_client(database=True, persistence=True, access_control_enabled=True)

        self.assertIn(
            "WARNING:slurmweb.apps.agent:Unable to load cached users for startup policy snapshot refresh: boom",
            cm.output,
        )
        mock_users_store.return_value.update_policy_snapshot.assert_not_called()

    @mock.patch("slurmweb.persistence.user_analytics_store.UserAnalyticsStore")
    @mock.patch("slurmweb.persistence.jobs_store.JobsStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_enables_user_metrics_when_dependencies_ready(
        self, mock_users_store, mock_jobs_store, mock_user_analytics_store
    ):
        self.setup_client(database=True, persistence=True, metrics=True, user_metrics=True)
        mock_users_store.assert_called_once()
        mock_jobs_store.assert_called_once()
        mock_user_analytics_store.assert_called_once()
        mock_user_analytics_store.return_value.start.assert_called_once()
        self.assertTrue(self.app.user_metrics_enabled)

    @mock.patch("slurmweb.persistence.user_analytics_store.UserAnalyticsStore")
    @mock.patch("slurmweb.persistence.jobs_store.JobsStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_enables_user_metrics_when_database_and_metrics_are_available(
        self, mock_users_store, mock_jobs_store, mock_user_analytics_store
    ):
        self.setup_client(database=True, persistence=False, metrics=True, user_metrics=True)
        mock_users_store.assert_called_once()
        mock_jobs_store.assert_called_once()
        mock_user_analytics_store.assert_called_once()
        mock_user_analytics_store.return_value.start.assert_called_once()
        self.assertTrue(self.app.user_metrics_enabled)
