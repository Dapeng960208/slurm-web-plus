# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock
import urllib

import requests
import pytest

from slurmweb.slurmrestd import Slurmrestd

from ..lib.slurmrestd import TestSlurmrestdBase, basic_authentifier


class TestSlurmrestdWriteOperations(TestSlurmrestdBase):
    def setUp(self):
        self.slurmrestd = Slurmrestd(
            urllib.parse.urlparse("unix:///dev/null"),
            basic_authentifier(),
            ["0.0.44", "0.0.43", "0.0.42", "0.0.41", "0.0.40", "0.0.39"],
        )

    def test_request_json_uses_session_request_and_payload(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "result": "ok",
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        result = self.slurmrestd.request_json(
            "DELETE",
            "slurm",
            "job/101",
            payload={"signal": "TERM"},
            query={"verbose": True},
        )

        self.assertEqual(result["result"], "ok")
        self.slurmrestd.session.request.assert_called_once_with(
            "DELETE",
            "http+unix://slurmrestd/slurm/v0.0.44/job/101",
            headers=mock.ANY,
            json={"signal": "TERM"},
            params={"verbose": True},
        )

    def test_supports_write_operations_for_supported_versions(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        self.assertTrue(self.slurmrestd.supports_write_operations())

    def test_supports_write_operations_for_unsupported_versions(self):
        self.setup_slurmrestd("23.02.0", "0.0.40")
        self.assertFalse(self.slurmrestd.supports_write_operations())

    def test_associations_update_injects_current_cluster_when_missing(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        self.slurmrestd.cluster_name = "test-cluster"
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "associations": [],
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        self.slurmrestd.associations_update(
            {"associations": [{"account": "ip-user", "user": "guojianpeng"}]}
        )

        self.slurmrestd.session.request.assert_called_once_with(
            "POST",
            "http+unix://slurmrestd/slurmdb/v0.0.44/associations",
            headers=mock.ANY,
            json={
                "associations": [
                    {
                        "account": "ip-user",
                        "user": "guojianpeng",
                        "cluster": "test-cluster",
                    }
                ]
            },
            params=None,
        )

    def test_associations_delete_uses_query_filters(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        self.slurmrestd.cluster_name = "test-cluster"
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "associations": [],
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        self.slurmrestd.associations_delete(
            {"associations": [{"account": "ip-user", "user": "guojianpeng"}]}
        )

        self.slurmrestd.session.request.assert_called_once_with(
            "DELETE",
            "http+unix://slurmrestd/slurmdb/v0.0.44/association",
            headers=mock.ANY,
            json=None,
            params={
                "account": "ip-user",
                "user": "guojianpeng",
                "cluster": "test-cluster",
            },
        )

    def test_associations_delete_rejects_wide_payload(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        self.slurmrestd.cluster_name = "test-cluster"

        with pytest.raises(ValueError):
            self.slurmrestd.associations_delete({"associations": [{"account": "ip-user"}]})

    def test_qos_update_wraps_light_payload_and_sets_defaults(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "qos": [],
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        self.slurmrestd.qos_update({"name": "debug", "description": "Debug QOS"})

        self.slurmrestd.session.request.assert_called_once_with(
            "POST",
            "http+unix://slurmrestd/slurmdb/v0.0.44/qos",
            headers=mock.ANY,
            json={
                "qos": [
                    {
                        "name": "debug",
                        "description": "Debug QOS",
                        "limits": {
                            "max": {
                                "jobs": {
                                    "per": {
                                        "user": {
                                            "set": True,
                                            "infinite": False,
                                            "number": 100,
                                        }
                                    },
                                    "active_jobs": {
                                        "per": {
                                            "user": {
                                                "set": True,
                                                "infinite": False,
                                                "number": 10,
                                            }
                                        }
                                    },
                                },
                                "wall_clock": {
                                    "per": {
                                        "job": {
                                            "set": True,
                                            "infinite": False,
                                            "number": 8640,
                                        }
                                    }
                                },
                            }
                        },
                    }
                ]
            },
            params=None,
        )

    def test_qos_update_keeps_explicit_limit_values(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "qos": [],
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        self.slurmrestd.qos_update(
            {
                "qos": [
                    {
                        "name": "long",
                        "max_submit_jobs_per_user": 25,
                        "MaxJobsPerUser": 4,
                        "MaxWallDurationPerJob": 2880,
                    }
                ]
            }
        )

        sent_payload = self.slurmrestd.session.request.call_args.kwargs["json"]
        qos = sent_payload["qos"][0]
        self.assertEqual(qos["limits"]["max"]["jobs"]["per"]["user"]["number"], 25)
        self.assertEqual(
            qos["limits"]["max"]["jobs"]["active_jobs"]["per"]["user"]["number"], 4
        )
        self.assertEqual(
            qos["limits"]["max"]["wall_clock"]["per"]["job"]["number"], 2880
        )
        self.assertNotIn("max_submit_jobs_per_user", qos)
        self.assertNotIn("MaxJobsPerUser", qos)
        self.assertNotIn("MaxWallDurationPerJob", qos)

    def test_accounts_update_wraps_light_payload(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "accounts": [],
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        self.slurmrestd.accounts_update({"name": "science", "description": "Science"})

        self.slurmrestd.session.request.assert_called_once_with(
            "POST",
            "http+unix://slurmrestd/slurmdb/v0.0.44/accounts",
            headers=mock.ANY,
            json={
                "accounts": [
                    {
                        "name": "science",
                        "description": "Science",
                        "organization": "Science",
                    }
                ]
            },
            params=None,
        )

    def test_accounts_update_defaults_organization_to_name_when_description_missing(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        response = mock.create_autospec(requests.Response)
        response.url = "/mocked/query"
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {
            "warnings": [],
            "errors": [],
            "accounts": [],
        }
        self.slurmrestd.session.request = mock.Mock(return_value=response)

        self.slurmrestd.accounts_update({"name": "science"})

        sent_payload = self.slurmrestd.session.request.call_args.kwargs["json"]
        self.assertEqual(
            sent_payload,
            {
                "accounts": [
                    {
                        "name": "science",
                        "organization": "science",
                    }
                ]
            },
        )
