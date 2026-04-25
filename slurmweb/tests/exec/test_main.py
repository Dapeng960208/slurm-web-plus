# Copyright (c) 2025 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import argparse
import io
import unittest
from unittest import mock

from slurmweb.version import get_version
from slurmweb.exec.main import SlurmwebExecMain
from slurmweb.exec.agent import SlurmwebExecAgent


class TestMainExec(unittest.TestCase):
    def test_register_args_defaults_to_plus_for_unknown_launcher(self):
        """Test that register_args() defaults prog to slurm-web-plus."""
        with mock.patch("sys.argv", ["pytest"]):
            parser = SlurmwebExecMain.register_args()
        self.assertIsInstance(parser, argparse.ArgumentParser)
        self.assertEqual(parser.prog, "slurm-web-plus")

    def test_register_args_preserves_legacy_launcher(self):
        """Test that register_args() preserves the legacy launcher name."""
        with mock.patch("sys.argv", ["slurm-web"]):
            parser = SlurmwebExecMain.register_args()
        self.assertEqual(parser.prog, "slurm-web")

    def test_register_args_preserves_plus_launcher(self):
        """Test that register_args() preserves the new launcher name."""
        with mock.patch("sys.argv", ["slurm-web-plus"]):
            parser = SlurmwebExecMain.register_args()
        self.assertEqual(parser.prog, "slurm-web-plus")

    def test_run_version(self):
        """Test that --version works at the main level."""
        with mock.patch("sys.argv", ["pytest"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with self.assertRaisesRegex(SystemExit, "0"):
                    SlurmwebExecMain.run(["--version"])
                output = stdout.getvalue()
                self.assertEqual(output, f"slurm-web-plus {get_version()}\n")

    def test_run_version_with_legacy_launcher(self):
        """Test that the legacy launcher keeps the legacy displayed name."""
        with mock.patch("sys.argv", ["slurm-web"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with self.assertRaisesRegex(SystemExit, "0"):
                    SlurmwebExecMain.run(["--version"])
                output = stdout.getvalue()
                self.assertEqual(output, f"slurm-web {get_version()}\n")

    def test_run_no_subcommand(self):
        """Test that run() handles no subcommand gracefully."""
        with mock.patch("sys.argv", ["pytest"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with self.assertRaisesRegex(SystemExit, "2"):
                    SlurmwebExecMain.run([])
                # Check help is printed
                self.assertIn("usage: slurm-web-plus [-h]", stdout.getvalue())

    def test_run_invalid_subcommand(self):
        """Test that run() handles invalid subcommand gracefully."""
        with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
            with self.assertRaisesRegex(SystemExit, "2"):
                SlurmwebExecMain.run(["invalid-subcommand"])
            # Check error about invalid subcommand
            self.assertIn("invalid-subcommand", stderr.getvalue())

    @mock.patch("slurmweb.apps.agent.SlurmwebAppAgent")
    def test_run_with_subcommand_agent(self, mock_slurmweb_app):
        """Test that run() correctly delegates to agent subcommand."""
        mock_app_instance = mock.Mock()

        mock_slurmweb_app.return_value = mock_app_instance
        SlurmwebExecMain.run(["agent", "--debug"])

        # Check app was called and run() was called
        mock_slurmweb_app.assert_called_once()
        mock_app_instance.run.assert_called_once()

    def test_run_keyboard_interrupt(self):
        """Test that KeyboardInterrupt is handled with exit code 130."""
        mock_app_instance = mock.Mock()
        mock_app_instance.run.side_effect = KeyboardInterrupt()

        with mock.patch.object(SlurmwebExecAgent, "app") as mock_app:
            mock_app.return_value = mock_app_instance
            with self.assertRaisesRegex(SystemExit, "130"):
                SlurmwebExecMain.run(["agent"])

    def test_register_args_subcommand_help(self):
        """Test that subcommand help is accessible."""
        with mock.patch("sys.argv", ["slurm-web"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with self.assertRaisesRegex(SystemExit, "0"):
                    SlurmwebExecMain.run(["agent", "--help"])
                self.assertIn("usage: slurm-web agent [-h]", stdout.getvalue())
