# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import unittest

from slurmweb.permission_rules import (
    DEFAULT_LEGACY_PERMISSION_MAP,
    access_control_catalog,
    default_seed_roles,
    permission_rules_allow,
    permission_rules_to_legacy_actions,
)


class TestPermissionRules(unittest.TestCase):
    def test_access_control_catalog_moves_admin_pages_under_admin_resources(self):
        catalog = access_control_catalog()
        resources = {
            resource["resource"]: resource
            for group in catalog["groups"]
            for resource in group["resources"]
        }

        self.assertIn("jobs", resources)
        self.assertCountEqual(resources["jobs"]["operations"], ["view", "edit", "delete"])
        self.assertCountEqual(resources["jobs"]["scopes"], ["*", "self"])

        for resource in [
            "admin/ai",
            "admin/ldap-cache",
            "admin/cache",
            "admin/access-control",
        ]:
            self.assertIn(resource, resources)
        self.assertNotIn("admin/system", resources)

        for resource in [
            "settings/ai",
            "settings/ldap-cache",
            "settings/cache",
            "settings/access-control",
        ]:
            self.assertNotIn(resource, resources)

    def test_legacy_permission_map_uses_admin_resources(self):
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["cache-view"],
            ["admin/cache:view:*", "admin/ldap-cache:view:*"],
        )
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["cache-reset"],
            ["admin/cache:edit:*"],
        )
        for action in [
            "view-own-jobs",
            "edit-own-jobs",
            "cancel-own-jobs",
            "roles-view",
            "roles-manage",
            "view-ai",
            "manage-ai",
        ]:
            self.assertNotIn(action, DEFAULT_LEGACY_PERMISSION_MAP)
        self.assertCountEqual(DEFAULT_LEGACY_PERMISSION_MAP["admin-manage"], ["*:*:*"])

    def test_default_seed_roles_grant_jobs_self_to_user_and_global_read_edit_to_admin(self):
        roles = {role["name"]: set(role["permissions"]) for role in default_seed_roles()}

        self.assertIn("jobs:view:self", roles["user"])
        self.assertIn("jobs:edit:self", roles["user"])
        self.assertIn("jobs:delete:self", roles["user"])
        self.assertIn("user/analysis:view:self", roles["user"])
        self.assertNotIn("jobs:view:*", roles["user"])
        self.assertNotIn("ai:view:*", roles["user"])
        self.assertNotIn("resources:edit:*", roles["user"])
        self.assertNotIn("accounts:delete:*", roles["user"])
        self.assertNotIn("admin/system:view:*", roles["user"])
        self.assertNotIn("admin/access-control:view:*", roles["user"])
        self.assertNotIn("users-admin:view:*", roles["user"])

        self.assertEqual(roles["admin"], {"*:view:*", "*:edit:*"})
        self.assertNotIn("*:delete:*", roles["admin"])

    def test_permission_rules_to_legacy_actions_exposes_admin_manage_only_for_super_admin_rules(self):
        actions = permission_rules_to_legacy_actions(
            ["*:view:*", "*:edit:*"],
            DEFAULT_LEGACY_PERMISSION_MAP,
        )

        self.assertNotIn("admin-manage", actions)

        super_admin_actions = permission_rules_to_legacy_actions(
            ["*:*:*"],
            DEFAULT_LEGACY_PERMISSION_MAP,
        )
        self.assertIn("admin-manage", super_admin_actions)

    def test_permission_rules_allow_self_scope_only_for_matching_scope(self):
        self.assertTrue(permission_rules_allow(["jobs:view:self"], "jobs", "view", "self"))
        self.assertFalse(permission_rules_allow(["jobs:view:self"], "jobs", "view", "*"))
        self.assertTrue(
            permission_rules_allow(["admin/ai:edit:*"], "admin/ai", "view", "*")
        )
        self.assertTrue(permission_rules_allow(["*:view:*"], "admin/ai", "view", "*"))
        self.assertTrue(permission_rules_allow(["*:edit:*"], "jobs", "edit", "self"))
        self.assertFalse(permission_rules_allow(["*:edit:*"], "jobs", "delete", "self"))
