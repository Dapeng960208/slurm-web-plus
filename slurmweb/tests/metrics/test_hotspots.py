# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import unittest

from slurmweb.metrics.hotspots import build_hotspot_events_from_metric_series


class TestBuildHotspotEventsFromMetricSeries(unittest.TestCase):
    def test_builds_hotspot_events_from_persisted_samples(self):
        metrics = {
            "cpu": {
                "cn1": [
                    [1713949200000, 81.0],
                    [1713949260000, 92.5],
                    [1713949320000, 79.9],
                ]
            },
            "memory": {
                "cn2": [
                    [1713949200000, 75.0],
                    [1713949260000, 84.0],
                    [1713949320000, 85.0],
                ]
            },
        }

        events = build_hotspot_events_from_metric_series(
            metrics,
            threshold=80.0,
            step_seconds=60,
            limit=10,
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["node"], "cn2")
        self.assertEqual(events[0]["metric"], "memory")
        self.assertEqual(events[0]["duration_seconds"], 120)
        self.assertEqual(events[1]["node"], "cn1")
        self.assertEqual(events[1]["metric"], "cpu")
        self.assertEqual(events[1]["peak_usage"], 92.5)
