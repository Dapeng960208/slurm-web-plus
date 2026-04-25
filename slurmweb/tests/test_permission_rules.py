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
            "admin/system",
        ]:
            self.assertIn(resource, resources)

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
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["roles-view"],
            ["admin/access-control:view:*"],
        )
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["roles-manage"],
            ["admin/access-control:edit:*", "admin/access-control:delete:*"],
        )
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["view-own-jobs"],
            ["jobs:view:self", "user/analysis:view:self"],
        )
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["cancel-own-jobs"],
            ["jobs:delete:self"],
        )
        self.assertCountEqual(
            DEFAULT_LEGACY_PERMISSION_MAP["manage-ai"],
            ["admin/ai:view:*", "admin/ai:edit:*", "admin/ai:delete:*"],
        )

    def test_default_seed_roles_grant_jobs_self_to_user_and_admin_pages_to_admin(self):
        roles = {role["name"]: set(role["permissions"]) for role in default_seed_roles()}

        self.assertIn("jobs:view:self", roles["user"])
        self.assertIn("jobs:delete:self", roles["user"])
        self.assertNotIn("jobs:view:*", roles["user"])
        self.assertNotIn("admin/system:view:*", roles["user"])
        self.assertNotIn("admin/access-control:view:*", roles["user"])
        self.assertNotIn("users-admin:view:*", roles["user"])

        self.assertIn("jobs:view:*", roles["admin"])
        self.assertIn("jobs:edit:*", roles["admin"])
        self.assertIn("jobs:delete:*", roles["admin"])
        self.assertIn("admin/system:view:*", roles["admin"])
        self.assertIn("admin/system:edit:*", roles["admin"])
        self.assertIn("admin/system:delete:*", roles["admin"])
        self.assertIn("admin/access-control:view:*", roles["admin"])
        self.assertIn("admin/access-control:edit:*", roles["admin"])
        self.assertIn("admin/access-control:delete:*", roles["admin"])

    def test_permission_rules_allow_self_scope_only_for_matching_scope(self):
        self.assertTrue(permission_rules_allow(["jobs:view:self"], "jobs", "view", "self"))
        self.assertFalse(permission_rules_allow(["jobs:view:self"], "jobs", "view", "*"))
        self.assertTrue(
            permission_rules_allow(["admin/system:edit:*"], "admin/system", "view", "*")
        )
