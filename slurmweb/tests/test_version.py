import unittest
from unittest import mock
from importlib import metadata

from slurmweb.version import get_version


class TestVersion(unittest.TestCase):
    @mock.patch("slurmweb.version.metadata.version")
    def test_get_version_falls_back_to_workspace_pyproject_when_package_metadata_missing(
        self, mock_version
    ):
        not_found = metadata.PackageNotFoundError("missing")
        mock_version.side_effect = [not_found, not_found]

        with mock.patch("slurmweb.version._workspace_version", return_value="6.0.0"):
            self.assertEqual(get_version(), "6.0.0")

    @mock.patch("slurmweb.version.metadata.version")
    def test_get_version_raises_when_metadata_and_workspace_version_are_unavailable(
        self, mock_version
    ):
        not_found = metadata.PackageNotFoundError("missing")
        mock_version.side_effect = [not_found, not_found]

        with mock.patch("slurmweb.version._workspace_version", return_value=None):
            with self.assertRaises(metadata.PackageNotFoundError):
                get_version()
