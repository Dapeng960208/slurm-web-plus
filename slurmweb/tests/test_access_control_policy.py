# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import unittest
from types import SimpleNamespace
from unittest import mock

from rfl.authentication.user import AuthenticatedUser

from slurmweb.access_control import AccessControlPolicyManager


class _FakeFilePolicy:
    def __init__(self):
        self.allow_anonymous = False
        self.loader = SimpleNamespace(definition=SimpleNamespace(actions={"view-jobs", "roles-view"}))

    def roles_actions(self, user):
        return {"user"}, set()

    def allowed_anonymous_action(self, action):
        return False

    def disable_anonymous(self):
        self.allow_anonymous = False


class TestAccessControlPolicy(unittest.TestCase):
    def test_allowed_user_permission_honors_jobs_self_scope(self):
        file_policy = _FakeFilePolicy()
        access_control_store = mock.Mock()
        access_control_store.user_permissions.return_value = (set(), set(), {"jobs:view:self"})
        manager = AccessControlPolicyManager(
            file_policy,
            access_control_enabled=True,
            access_control_store=access_control_store,
        )
        user = AuthenticatedUser(login="alice", fullname="Alice Doe", groups=["users"])

        self.assertTrue(manager.allowed_user_permission(user, "jobs", "view", "self"))
        self.assertFalse(manager.allowed_user_permission(user, "jobs", "view", "*"))

    def test_allowed_user_permission_supports_admin_resource_rules(self):
        file_policy = _FakeFilePolicy()
        access_control_store = mock.Mock()
        access_control_store.user_permissions.return_value = (
            set(),
            set(),
            {"admin/access-control:view:*", "admin/cache:edit:*"},
        )
        manager = AccessControlPolicyManager(
            file_policy,
            access_control_enabled=True,
            access_control_store=access_control_store,
        )
        user = AuthenticatedUser(login="alice", fullname="Alice Doe", groups=["users"])

        self.assertTrue(
            manager.allowed_user_permission(user, "admin/access-control", "view", "*")
        )
        self.assertTrue(manager.allowed_user_permission(user, "admin/cache", "edit", "*"))
        self.assertFalse(manager.allowed_user_permission(user, "settings/cache", "view", "*"))
