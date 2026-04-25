# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import unittest
import tempfile
import os
from pathlib import Path

from slurmweb.markdown import render_html


class TestMessage(unittest.TestCase):
    def test_service_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            message_path = Path(tmpdir) / "message.md"
            message_path.write_text("Hello, *world*!")
            self.assertEqual(
                render_html(message_path),
                "<p>Hello, <em>world</em>!</p>",
            )

    def test_empty_service_message(self):
        self.assertEqual(render_html(os.devnull), "")

    def test_not_existing_service_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "not-found.md"
            with self.assertRaises(FileNotFoundError) as ctx:
                render_html(missing_path)
            self.assertEqual(ctx.exception.filename, str(missing_path))
