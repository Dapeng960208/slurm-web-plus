# Copyright (c) 2025 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from slurmweb.version import get_version

from ..lib.agent import TestAgentBase
from ..lib.utils import all_slurm_api_versions


class TestAgentPermissions(TestAgentBase):
    def _enable_access_control(self, custom_roles=None, custom_actions=None):
        self.app.access_control_enabled = True
        self.app.access_control_store = mock.Mock()
        self.app.access_control_store.user_permissions.return_value = (
            custom_roles or [],
            custom_actions or [],
        )
        self.app.policy._access_control_enabled = True
        self.app.policy.set_access_control_store(self.app.access_control_store)

    def test_permissions_user(self):
        self.setup_client()
        response = self.client.get(f"/v{get_version()}/permissions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict)
        self.assertEqual(len(response.json.keys()), 4)
        self.assertIn("actions", response.json)
        self.assertIn("roles", response.json)
        self.assertIn("rules", response.json)
        self.assertIn("sources", response.json)
        self.assertCountEqual(response.json["roles"], ["user"])
        self.assertCountEqual(
            response.json["actions"], self.app.policy.roles_actions(self.user)[1]
        )
        self.assertCountEqual(
            response.json["rules"], self.app.policy.roles_actions_rules(self.user)[2]
        )
        self.assertEqual(
            response.json["sources"]["custom"],
            {"roles": [], "actions": [], "rules": []},
        )
        self.assertCountEqual(
            response.json["sources"]["policy"]["roles"],
            ["user"],
        )
        self.assertCountEqual(
            response.json["sources"]["policy"]["actions"],
            self.app.policy.file_roles_actions(self.user)[1],
        )
        self.assertCountEqual(
            response.json["sources"]["policy"]["rules"],
            self.app.policy.file_rules(self.user),
        )
        self.assertIn("edit-own-jobs", response.json["actions"])
        self.assertIn("jobs:view:self", response.json["rules"])
        self.assertIn("jobs:edit:self", response.json["rules"])
        self.assertIn("jobs:delete:self", response.json["rules"])
        self.assertNotIn("jobs:edit:*", response.json["rules"])

    def test_permissions_custom_roles_union_from_access_control_store(self):
        self.setup_client()
        self._enable_access_control(
            custom_roles=["db-admin", "db-auditor"],
            custom_actions=["roles-view", "roles-manage"],
        )

        response = self.client.get(f"/v{get_version()}/permissions")

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json["roles"],
            ["user", "db-admin", "db-auditor"],
        )
        self.assertCountEqual(
            response.json["actions"],
            list(self.app.policy.file_roles_actions(self.user)[1])
            + ["roles-view", "roles-manage", "admin-manage"],
        )
        self.assertCountEqual(
            response.json["sources"]["policy"]["roles"],
            ["user"],
        )
        self.assertCountEqual(
            response.json["sources"]["custom"]["roles"],
            ["db-admin", "db-auditor"],
        )
        self.assertCountEqual(
            response.json["sources"]["custom"]["actions"],
            ["roles-view", "roles-manage"],
        )
        self.assertCountEqual(
            response.json["sources"]["custom"]["rules"],
            self.app.policy.action_rules(["roles-view", "roles-manage"]),
        )

    def test_permissions_custom_actions_expand_admin_manage_and_edit_own_jobs(self):
        self.setup_client()
        custom_actions = ["admin-manage", "edit-own-jobs"]
        self._enable_access_control(
            custom_roles=["db-admin"],
            custom_actions=custom_actions,
        )

        response = self.client.get(f"/v{get_version()}/permissions")

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json["sources"]["custom"]["roles"], ["db-admin"])
        self.assertCountEqual(response.json["sources"]["custom"]["actions"], custom_actions)
        self.assertCountEqual(
            response.json["sources"]["custom"]["rules"],
            self.app.policy.action_rules(custom_actions),
        )
        self.assertIn("admin/system:view:*", response.json["rules"])
        self.assertIn("admin/system:delete:*", response.json["rules"])
        self.assertIn("admin/cache:edit:*", response.json["rules"])
        self.assertNotIn("admin/cache:delete:*", response.json["rules"])
        self.assertIn("jobs:edit:self", response.json["rules"])
        self.assertIn("admin-manage", response.json["actions"])
        self.assertIn("edit-own-jobs", response.json["actions"])

    def test_permissions_anonymous(self):
        self.setup_client(anonymous_user=True)
        self.assertTrue(self.app.policy.allow_anonymous)
        response = self.client.get(f"/v{get_version()}/permissions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict)
        self.assertEqual(len(response.json.keys()), 4)
        self.assertIn("actions", response.json)
        self.assertIn("roles", response.json)
        self.assertIn("rules", response.json)
        self.assertIn("sources", response.json)
        # anonymous user should get the anonymous role and corresponding set of actions
        # when anonymous mode is enabled in policy.
        self.assertCountEqual(response.json["roles"], ["anonymous"])
        self.assertCountEqual(
            response.json["actions"], self.app.policy.roles_actions(self.user)[1]
        )
        self.assertCountEqual(
            response.json["rules"], self.app.policy.roles_actions_rules(self.user)[2]
        )

    def test_permissions_anonymous_disabled(self):
        self.setup_client(anonymous_user=True, anonymous_enabled=False)
        self.assertFalse(self.app.policy.allow_anonymous)
        response = self.client.get(f"/v{get_version()}/permissions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict)
        self.assertEqual(len(response.json.keys()), 4)
        self.assertIn("actions", response.json)
        self.assertIn("roles", response.json)
        self.assertIn("rules", response.json)
        self.assertIn("sources", response.json)
        # anonymous user should get no role or action when anonymous mode is disabled in
        # policy.
        self.assertCountEqual(response.json["roles"], [])
        self.assertCountEqual(response.json["actions"], [])
        self.assertCountEqual(response.json["rules"], [])

    def test_permissions_no_token(self):
        # permissions endpoint is guarded by @check_jwt decorator that must reply 403
        # to requests without bearer token.
        self.setup_client(use_token=False)
        self.assertTrue(self.app.policy.allow_anonymous)
        response = self.client.get(f"/v{get_version()}/permissions")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": "Not allowed to access endpoint without bearer token",
                "name": "Forbidden",
            },
        )

    @all_slurm_api_versions
    def test_action_anonymous_ok(self, slurm_version, api_version):
        # stats endpoint is authorized to anonymous role in default policy.
        self.setup_client(anonymous_user=True)
        [ping_asset, jobs_asset, nodes_asset] = self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [
                ("slurm-ping", "meta"),
                ("slurm-jobs", "jobs"),
                ("slurm-nodes", "nodes"),
            ],
        )
        response = self.client.get(f"/v{get_version()}/stats")
        self.assertEqual(response.status_code, 200)
        self.assertIn("jobs", response.json)

    def test_action_anonymous_disabled(self):
        # stats endpoint must be denied to anonymous tokens when anonymous role is
        # disabled in policy.
        self.setup_client(anonymous_enabled=False, anonymous_user=True)
        response = self.client.get(f"/v{get_version()}/stats")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": (
                    "Anonymous role is not allowed to perform action view-stats"
                ),
                "name": "Forbidden",
            },
        )

    def test_action_no_token_denied(self):
        # stats endpoint must be denied to requests without bearer token.
        self.setup_client(use_token=False)
        response = self.client.get(f"/v{get_version()}/stats")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": ("Not allowed to access endpoint without bearer token"),
                "name": "Forbidden",
            },
        )

    def test_action_anonymous_denied(self):
        # Test agent permission denied with @rbac_action decorator by calling /accounts
        # without authentication token, ie. as anonymous who is denied to access this
        # route in Slurm-web default authorization policy.
        self.setup_client(anonymous_user=True)
        response = self.client.get(f"/v{get_version()}/accounts")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": (
                    "Anonymous role is not allowed to perform action view-accounts"
                ),
                "name": "Forbidden",
            },
        )

    def test_invalid_token(self):
        self.setup_client()
        self.client.environ_base["HTTP_AUTHORIZATION"] = "Bearer failed"
        response = self.client.get(f"/v{get_version()}/jobs")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json,
            {
                "code": 401,
                "description": "Unable to decode token: Not enough segments",
                "name": "Unauthorized",
            },
        )
