# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import typing as t
import logging

from .base import BaseAdapter


logger = logging.getLogger(__name__)


def _optional_number(value: t.Any) -> dict:
    if isinstance(value, dict):
        return {
            "set": value.get("set", value.get("number") is not None),
            "infinite": value.get("infinite", False),
            "number": value.get("number", 0),
        }
    if value is None:
        return {"set": False, "infinite": False, "number": 0}
    return {"set": True, "infinite": False, "number": int(value)}


def _normalize_status(value: t.Any) -> t.List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def _normalize_exit_code(value: t.Any) -> t.Any:
    if not isinstance(value, dict):
        return value

    signal = value.get("signal")
    signal_name = ""
    signal_id = None
    if isinstance(signal, dict):
        signal_name = signal.get("name", "")
        signal_id = signal.get("id", signal.get("signal_id"))
    else:
        signal_id = signal

    normalized = {
        "status": _normalize_status(value.get("status")),
        "return_code": _optional_number(value.get("return_code")),
        "signal": {
            "id": _optional_number(signal_id),
            "name": signal_name,
        },
    }

    if not normalized["status"]:
        return_code = normalized["return_code"]
        normalized["status"] = [
            "SUCCESS" if return_code.get("number", 0) == 0 else "FAILED"
        ]

    return normalized


def _normalize_step_id(value: t.Any) -> t.Any:
    if not isinstance(value, dict):
        return value
    return f"{value.get('job_id', 0)}.{value.get('step_id', 0)}"


class AdapterV0_0_39(BaseAdapter):
    """Adapter from API version 0.0.39 to 0.0.40."""

    _JOB_TIME_FIELDS = (
        "submit_time",
        "start_time",
        "end_time",
        "accrue_time",
        "eligible_time",
        "last_sched_evaluation",
        "preempt_time",
        "preemptable_time",
        "pre_sus_time",
        "resize_time",
        "suspend_time",
        "deadline",
    )

    _NODE_TIME_FIELDS = (
        "boot_time",
        "last_busy",
        "slurmd_start_time",
        "reason_changed_at",
    )

    def adapt_slurm_jobs(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_39.adapt_slurm_jobs()")
        for job in data:
            job["job_state"] = _normalize_status(job.get("job_state"))
            for field in self._JOB_TIME_FIELDS:
                if field in job:
                    job[field] = _optional_number(job.get(field))
            for field in ("exit_code", "derived_exit_code"):
                if field in job:
                    job[field] = _normalize_exit_code(job.get(field))
        return data

    def adapt_slurm_nodes(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_39.adapt_slurm_nodes()")
        for node in data:
            for field in self._NODE_TIME_FIELDS:
                if field in node:
                    node[field] = _optional_number(node.get(field))
        return data

    def adapt_slurm_reservations(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_39.adapt_slurm_reservations()")
        for reservation in data:
            for field in ("start_time", "end_time"):
                if field in reservation:
                    reservation[field] = _optional_number(reservation.get(field))
        return data

    def adapt_slurmdb_jobs(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_39.adapt_slurmdb_jobs()")
        for job in data:
            for field in ("exit_code", "derived_exit_code"):
                if field in job:
                    job[field] = _normalize_exit_code(job.get(field))
            for step in job.get("steps", []):
                step["state"] = _normalize_status(step.get("state"))
                if "exit_code" in step:
                    step["exit_code"] = _normalize_exit_code(step.get("exit_code"))
                if isinstance(step.get("step"), dict) and "id" in step["step"]:
                    step["step"]["id"] = _normalize_step_id(step["step"]["id"])
        return data

    def adapt_slurmdb_associations(self, data: t.Any) -> t.Any:
        logger.debug("running AdapterV0_0_39.adapt_slurmdb_associations()")
        cluster = self.cluster_name_hint or "unknown"
        for association in data:
            association["id"] = {
                "account": association.get("account", ""),
                "cluster": cluster,
                "partition": "",
                "user": association.get("user", ""),
                "id": 0,
            }
        return data
