# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock
import urllib

from slurmweb.slurmrestd import SlurmrestdFilteredCached
from slurmweb.cache import CachingService, CacheKey
from slurmweb.errors import SlurmwebCacheError

from ..lib.utils import all_slurm_api_versions
from ..lib.slurmrestd import TestSlurmrestdBase, basic_authentifier


class TestSlurmrestdFilteredCached(TestSlurmrestdBase):
    def setUp(self):
        self.settings = self.load_agent_settings_definition()
        self.settings.cache.enabled = True
        self.cache = CachingService(
            self.settings.cache.host,
            self.settings.cache.port,
            self.settings.cache.password,
        )
        self.slurmrestd = SlurmrestdFilteredCached(
            urllib.parse.urlparse("unix:///dev/null"),
            basic_authentifier(),
            ["0.0.44"],
            self.settings.filters,
            self.settings.cache,
            self.cache,
        )

    @all_slurm_api_versions
    def test_not_in_cache(self, slurm_version, api_version):
        self.setup_slurmrestd(slurm_version, api_version)
        [asset] = self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-jobs", "jobs")],
        )
        self.slurmrestd.service.get = mock.Mock(return_value=None)
        self.slurmrestd.service.put = mock.Mock()
        self.slurmrestd.service.count_hit = mock.Mock()
        self.slurmrestd.service.count_miss = mock.Mock()
        jobs = self.slurmrestd.jobs()
        for idx in range(len(jobs)):
            self.assertEqual(jobs[idx]["job_id"], asset[idx]["job_id"])
        # Check SlurmrestdFilteredCached has tried to get jobs from cache
        self.slurmrestd.service.get.assert_called_once_with(CacheKey("jobs"))
        # Check SlurmrestdFilteredCached has up jobs in cache with corresponding
        # expiration timeout.
        self.slurmrestd.service.put.assert_called_once_with(
            CacheKey("jobs"), jobs, self.settings.cache.jobs
        )
        self.slurmrestd.service.count_hit.assert_not_called()
        self.slurmrestd.service.count_miss.assert_called_once_with(CacheKey("jobs"))

    @all_slurm_api_versions
    def test_in_cache(self, slurm_version, api_version):
        self.setup_slurmrestd(slurm_version, api_version)
        [asset] = self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-jobs", "jobs")],
        )
        self.slurmrestd.service.get = mock.Mock(return_value=asset)
        self.slurmrestd.service.put = mock.Mock()
        self.slurmrestd.service.count_hit = mock.Mock()
        self.slurmrestd.service.count_miss = mock.Mock()
        jobs = self.slurmrestd.jobs()
        for idx in range(len(jobs)):
            self.assertEqual(jobs[idx]["job_id"], asset[idx]["job_id"])
        # Check SlurmrestdFilteredCached has tried to get jobs from cache.
        self.slurmrestd.service.get.assert_called_once_with(CacheKey("jobs"))
        # Check SlurmrestdFilteredCached has not put jobs again in cache.
        self.slurmrestd.service.put.assert_not_called()
        self.slurmrestd.service.count_hit.assert_called_once_with(CacheKey("jobs"))
        self.slurmrestd.service.count_miss.assert_not_called()

    @all_slurm_api_versions
    def test_cache_get_error(self, slurm_version, api_version):
        self.setup_slurmrestd(slurm_version, api_version)
        [asset] = self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-jobs", "jobs")],
        )
        # Check behaviour when SlurmwebCacheError in raised at get()
        self.slurmrestd.service.get = mock.Mock(
            side_effect=SlurmwebCacheError("fake cache error")
        )
        self.slurmrestd.service.put = mock.Mock()
        with self.assertRaisesRegex(SlurmwebCacheError, "^fake cache error$"):
            self.slurmrestd.jobs()
        self.slurmrestd.service.get.assert_called_once_with(CacheKey("jobs"))
        self.slurmrestd.service.put.assert_not_called()

    @all_slurm_api_versions
    def test_cache_put_error(self, slurm_version, api_version):
        self.setup_slurmrestd(slurm_version, api_version)
        [asset] = self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-jobs", "jobs")],
        )
        # Check behaviour when SlurmwebCacheError in raised at put()
        self.slurmrestd.service.get = mock.Mock(return_value=None)
        self.slurmrestd.service.put = mock.Mock(
            side_effect=SlurmwebCacheError("fake cache error")
        )
        with self.assertRaisesRegex(SlurmwebCacheError, "^fake cache error$"):
            self.slurmrestd.jobs()
        self.slurmrestd.service.get.assert_called_once_with(CacheKey("jobs"))
        self.slurmrestd.service.put.assert_called_once()

    @all_slurm_api_versions
    def test_query_filters_cached_jobs(self, slurm_version, api_version):
        self.setup_slurmrestd(slurm_version, api_version)
        [asset] = self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-jobs", "jobs")],
        )
        selected = asset[0]
        self.slurmrestd.service.get = mock.Mock(return_value=asset)
        self.slurmrestd.service.put = mock.Mock()
        self.slurmrestd.service.count_hit = mock.Mock()
        self.slurmrestd.service.count_miss = mock.Mock()

        jobs = self.slurmrestd.jobs(
            query={
                "users": [selected["user_name"]],
                "states": selected["job_state"],
                "accounts": [selected["account"]],
                "qos": [selected["qos"]],
                "partitions": [selected["partition"]],
            }
        )

        self.assertGreaterEqual(len(jobs), 1)
        for job in jobs:
            self.assertEqual(job["user_name"], selected["user_name"])
            self.assertEqual(job["account"], selected["account"])
            self.assertEqual(job["qos"], selected["qos"])
            self.assertEqual(job["partition"], selected["partition"])
            self.assertTrue(
                set(state.lower() for state in selected["job_state"])
                & set(state.lower() for state in job["job_state"])
            )
        self.slurmrestd.service.get.assert_called_once_with(CacheKey("jobs"))
        self.slurmrestd.service.put.assert_not_called()
        self.slurmrestd.service.count_hit.assert_called_once_with(CacheKey("jobs"))

    def test_reservation_write_operations_invalidate_reservations_cache(self):
        self.setup_slurmrestd("25.11.0", "0.0.44")
        self.slurmrestd.service.delete = mock.Mock()
        self.slurmrestd.request_json = mock.Mock(
            return_value={"warnings": [], "errors": [], "reservations": []}
        )

        self.slurmrestd.reservation_create({"name": "maint"})
        self.slurmrestd.reservation_update("maint", {"users": ["alice"]})
        self.slurmrestd.reservation_delete("maint")

        self.assertEqual(
            self.slurmrestd.service.delete.mock_calls,
            [
                mock.call(CacheKey("reservations")),
                mock.call(CacheKey("reservations")),
                mock.call(CacheKey("reservations")),
            ],
        )
