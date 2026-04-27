# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import unittest
from unittest import mock

from slurmweb.persistence.access_control_store import AccessControlStore


class TestAccessControlStore(unittest.TestCase):
    def test_normalize_legacy_role_actions_moves_removed_actions_into_permissions(self):
        store = AccessControlStore(settings=mock.Mock(), legacy_permission_map={
            "edit-own-jobs": ["jobs:edit:self"],
            "view-ai": ["ai:view:*", "admin/ai:view:*"],
            "admin-manage": ["*:*:*"],
        })
        conn = mock.MagicMock()
        cur = mock.Mock()
        cur.fetchall.return_value = [
            {
                "id": 1,
                "actions": ["edit-own-jobs", "view-ai", "admin-manage"],
                "permissions": ["jobs:view:self"],
            }
        ]
        conn.cursor.return_value.__enter__.return_value = cur
        store._get_conn = mock.Mock(return_value=conn)
        store._release_conn = mock.Mock()

        updated = store.normalize_legacy_role_actions()

        self.assertEqual(updated, 1)
        cur.execute.assert_any_call("SELECT id, actions, permissions FROM roles ORDER BY id ASC")
        update_call = cur.execute.call_args_list[1]
        self.assertEqual(update_call.args[0].strip().splitlines()[0], "UPDATE roles")
        self.assertEqual(update_call.args[1][2], 1)
        self.assertEqual(update_call.args[1][0].adapted, ["admin-manage"])
        self.assertCountEqual(
            update_call.args[1][1].adapted,
            ["jobs:view:self", "jobs:edit:self", "ai:view:*", "admin/ai:view:*", "*:*:*"],
        )
        conn.commit.assert_called_once_with()
