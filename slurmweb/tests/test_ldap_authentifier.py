# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import TestCase, mock

from slurmweb.tests.lib.ldap_stub import ensure_ldap_stub

ensure_ldap_stub()

from rfl.authentication.errors import LDAPAuthenticationError
from rfl.authentication.ldap import LDAPAuthentifier
from slurmweb.ldap_ext import patch_ldap_authentifier

patch_ldap_authentifier()


class DummyURI:
    def __init__(self, value="ldap://localhost"):
        self._value = value

    def geturl(self):
        return self._value


class DummyPagedControl:
    controlType = "1.2.840.113556.1.4.319"

    def __init__(self, cookie=b""):
        self.cookie = cookie


class DummyConnection:
    def __init__(self):
        self.search_s_side_effect = []
        self.search_ext_calls = []
        self.result3_side_effect = []

    def search_s(self, base, scope, search_filter, attrs):
        effect = self.search_s_side_effect.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect

    def search_ext(self, base, scope, search_filter, attrs, serverctrls=None):
        self.search_ext_calls.append((base, scope, search_filter, attrs, serverctrls))
        return len(self.search_ext_calls)

    def result3(self, msgid):
        effect = self.result3_side_effect.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect

    def unbind_s(self):
        return None


class TestLDAPAuthentifierPatched(TestCase):
    def make_authentifier(self, **overrides):
        params = {
            "uri": DummyURI(),
            "user_base": ["ou=dc,dc=example,dc=org", "ou=ext,dc=example,dc=org"],
            "group_base": ["ou=groups,dc=example,dc=org", "ou=roles,dc=example,dc=org"],
            "user_class": "user",
            "user_name_attribute": "sAMAccountName",
            "user_fullname_attribute": "cn",
            "group_name_attribute": "cn",
            "lookup_user_dn": True,
        }
        params.update(overrides)
        return LDAPAuthentifier(**params)

    def test_lookup_user_dn_tries_multiple_bases(self):
        auth = self.make_authentifier()
        conn1 = DummyConnection()
        conn2 = DummyConnection()
        conn2.search_s_side_effect = [
            [("CN=alice,OU=ext,DC=example,DC=org", {"sAMAccountName": [b"alice"]})]
        ]

        with mock.patch.object(auth, "connection", side_effect=[conn1, conn2]):
            with mock.patch.object(auth, "_bind") as mock_bind:
                import ldap

                conn1.search_s_side_effect = [ldap.NO_SUCH_OBJECT()]
                dn = auth._lookup_user_dn("alice")

        self.assertEqual(dn, "CN=alice,OU=ext,DC=example,DC=org")
        self.assertEqual(mock_bind.call_count, 2)

    def test_lookup_user_dn_raises_on_duplicate_across_bases(self):
        auth = self.make_authentifier()
        conn1 = DummyConnection()
        conn2 = DummyConnection()
        conn1.search_s_side_effect = [
            [("CN=alice,OU=dc,DC=example,DC=org", {"sAMAccountName": [b"alice"]})]
        ]
        conn2.search_s_side_effect = [
            [("CN=alice,OU=ext,DC=example,DC=org", {"sAMAccountName": [b"alice"]})]
        ]

        with mock.patch.object(auth, "connection", side_effect=[conn1, conn2]):
            with mock.patch.object(auth, "_bind"):
                with self.assertRaisesRegex(LDAPAuthenticationError, "Too many users found"):
                    auth._lookup_user_dn("alice")

    def test_get_groups_merges_multiple_group_bases(self):
        auth = self.make_authentifier()
        connection = DummyConnection()
        connection.search_s_side_effect = [
            [("CN=grp1", {"cn": [b"grp1"]})],
            [("CN=grp2", {"cn": [b"grp2"]}), ("CN=grp1", {"cn": [b"grp1"]})],
        ]

        groups = auth._get_groups(connection, "alice", "cn=alice", gid=None)

        self.assertEqual(groups, ["grp1", "grp2"])

    @mock.patch("slurmweb.ldap_ext.SimplePagedResultsControl")
    def test_list_user_dn_uses_paged_search(self, mock_paged_control):
        auth = self.make_authentifier(user_base=["ou=dc,dc=example,dc=org"])
        mock_paged_control.return_value = mock.Mock(
            controlType="1.2.840.113556.1.4.319",
            cookie=b"",
        )
        connection = DummyConnection()
        connection.result3_side_effect = [
            (
                None,
                [("CN=alice", {"sAMAccountName": [b"alice"]})],
                1,
                [DummyPagedControl(cookie=b"next")],
            ),
            (
                None,
                [("CN=bob", {"sAMAccountName": [b"bob"]})],
                2,
                [DummyPagedControl(cookie=b"")],
            ),
        ]

        users = auth._list_user_dn(connection)

        self.assertEqual(users, [("alice", "CN=alice"), ("bob", "CN=bob")])
        self.assertEqual(len(connection.search_ext_calls), 2)

    @mock.patch("slurmweb.ldap_ext.SimplePagedResultsControl", None)
    def test_list_user_dn_size_limit_reports_base(self):
        auth = self.make_authentifier(user_base=["ou=dc,dc=example,dc=org"])
        connection = DummyConnection()
        import ldap

        connection.search_s_side_effect = [ldap.SIZELIMIT_EXCEEDED({"desc": "Size limit exceeded"})]

        with self.assertRaisesRegex(
            LDAPAuthenticationError,
            "Users search exceeded directory size limit in base ou=dc,dc=example,dc=org",
        ):
            auth._list_user_dn(connection)
