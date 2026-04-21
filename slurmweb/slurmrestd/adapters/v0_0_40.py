# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import typing as t
import logging

from .base import BaseAdapter


logger = logging.getLogger(__name__)


def _unset_optional_number() -> dict:
    return {"set": False, "infinite": False, "number": 0}


class AdapterV0_0_40(BaseAdapter):
    """Adapter from API version 0.0.40 to 0.0.41."""

    def adapt_slurmdb_jobs(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_40.adapt_slurmdb_jobs()")
        for job in data:
            for field in (
                "stdin",
                "stdout",
                "stderr",
                "stdin_expanded",
                "stdout_expanded",
                "stderr_expanded",
            ):
                job.setdefault(field, "")
            if not isinstance(job.get("time"), dict):
                job["time"] = {}
            job["time"].setdefault("planned", _unset_optional_number())
        return data

    def adapt_slurmdb_associations(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_40.adapt_slurmdb_associations()")
        for association in data:
            association_id = association.get("id")
            if isinstance(association_id, dict):
                association["id"] = association_id.get("id", 0)
            elif association_id is None:
                association["id"] = 0
        return data
