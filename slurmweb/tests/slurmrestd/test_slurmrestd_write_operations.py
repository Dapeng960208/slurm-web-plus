# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock
import urllib

import requests

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
