# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import typing as t
import urllib
import logging

import requests
from ClusterShell.NodeSet import NodeSet

from .unix import SlurmrestdUnixAdapter
from .auth import SlurmrestdAuthentifier
from .adapters import build_adaptation_chain
from ..cache import CacheKey
from .errors import (
    SlurmrestdNotFoundError,
    SlurmrestdInvalidResponseError,
    SlurmrestConnectionError,
    SlurmrestdAuthenticationError,
    SlurmrestdInternalError,
)
from ..errors import SlurmwebConfigurationError

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from rfl.settings import RuntimeSettings
    from ..cache import CachingService


class Slurmrestd:
    WRITE_SUPPORTED_VERSIONS = {"0.0.41", "0.0.42", "0.0.43", "0.0.44"}

    def __init__(
        self,
        uri: urllib.parse.ParseResult,
        auth: SlurmrestdAuthentifier,
        supported_versions: t.List[str],
        cluster_name_hint: t.Optional[str] = None,
    ):
        self.session = requests.Session()

        # When using local authenciation, ensure slurmrestd URI is a Unix socket. For
        # authentication on TCP/IP socket, JWT authentication is required.
        if auth.method == "local" and uri.scheme != "unix":
            raise SlurmwebConfigurationError(
                "slurmrestd local authentication is only supported with unix socket URI"
            )

        if uri.scheme == "unix":
            self.prefix = "http+unix://slurmrestd"
            self.session.mount(self.prefix, SlurmrestdUnixAdapter(uri.path))
        else:
            self.prefix = uri.geturl()

        self.auth = auth
        self.supported_versions = supported_versions
        self.cluster_name_hint = cluster_name_hint

        # Initialized in discover()
        self.cluster_name = None
        self.slurm_version = None
        self.api_version = None

    def _validate_response(self, response, ignore_notfound: bool) -> None:
        """Validate slurmrestd response or abort agent resquest with error."""
        self._validate_status(response, ignore_notfound)
        self._validate_json(response)

    def _validate_status(self, response, ignore_notfound: bool) -> None:
        """Check response status code. When HTTP/401, raise
        SlurmrestdAuthenticationError. When HTTP/404 and ignore_notfound is False, raise
        SlurmrestdNotFoundError."""
        # FIXME: There is a regression in Slurm 25.11.0 which return HTTP/500 in this
        # case, see https://support.schedmd.com/show_bug.cgi?id=24052 for details.
        # This is a temporary workaround to accept both HTTP/401 and HTTP/500.
        if response.status_code == 401 or (
            response.status_code == 500
            and response.text.strip() == "Authentication does not apply to request"
        ):
            raise SlurmrestdAuthenticationError(response.url)
        if not ignore_notfound and response.status_code == 404:
            raise SlurmrestdNotFoundError(response.url)

    def _validate_json(self, response) -> None:
        """Check json reponse or abort with HTTP/500"""
        content_type = response.headers.get("content-type")
        if content_type != "application/json":
            logger.debug(
                "slurmrestd query %s response: %s", response.url, response.text
            )
            raise SlurmrestdInvalidResponseError(
                f"Unsupported Content-Type for slurmrestd response {response.url}: "
                f"{content_type}"
            )

    def _execute_request(
        self,
        component: str,
        api_version: str,
        endpoint: str,
        ignore_notfound=False,
        method: str = "GET",
        payload: t.Optional[t.Dict[str, t.Any]] = None,
        query: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> dict:
        """Execute HTTP request to slurmrestd API with provided API version and return
        parsed JSON result.

        Args:
            component: API component name ("slurm" or "slurmdb")
            api_version: API version to use
            endpoint: API endpoint path (e.g., "ping", "jobs", "job/123")
            ignore_notfound: If True, don't raise error on HTTP 404

        Returns:
            Parsed JSON response as a dictionary
        """
        # Compose query path with provided API version
        request_path = f"/{component}/v{api_version}/{endpoint}"

        try:
            request_url = f"{self.prefix}{request_path}"
            if method.upper() == "GET":
                response = self.session.get(
                    request_url,
                    headers=self.auth.headers(),
                    params=query,
                )
            else:
                response = self.session.request(
                    method,
                    request_url,
                    headers=self.auth.headers(),
                    json=payload,
                    params=query,
                )
        except requests.exceptions.ConnectionError as err:
            raise SlurmrestConnectionError(str(err))

        self._validate_response(response, ignore_notfound)

        result = response.json()
        if len(result["errors"]):
            error = result["errors"][0]
            raise SlurmrestdInternalError(
                error.get("error", "slurmrestd undefined error"),
                error.get("error_number", -1),
                error["description"],
                error["source"],
            )
        if "warnings" not in result:
            logger.error(
                "Unable to extract warnings from slurmrestd response to %s, "
                "unsupported Slurm version?",
                request_path,
            )
        elif len(result["warnings"]):
            logger.warning(
                "slurmrestd query %s warnings: %s", request_path, result["warnings"]
            )
        return result

    def _request(
        self,
        component: str,
        endpoint: str,
        key: t.Optional[str],
        ignore_notfound=False,
        method: str = "GET",
        payload: t.Optional[t.Dict[str, t.Any]] = None,
        query: t.Optional[t.Dict[str, t.Any]] = None,
    ):
        """Make a request to slurmrestd API with detected API version.

        Args:
            component: API component name ("slurm" or "slurmdb")
            endpoint: API endpoint path (e.g., "ping", "jobs", "job/123")
            key: Key to extract from response JSON
            ignore_notfound: If True, don't raise error on HTTP 404
        """
        # Ensure API version is discovered before making request
        if self.api_version is None:
            self.discover()

        result = self._execute_request(
            component,
            self.api_version,
            endpoint,
            ignore_notfound,
            method=method,
            payload=payload,
            query=query,
        )
        if key is None:
            return result
        return result[key]

    def request_json(
        self,
        method: str,
        component: str,
        endpoint: str,
        *,
        payload: t.Optional[t.Dict[str, t.Any]] = None,
        query: t.Optional[t.Dict[str, t.Any]] = None,
        key: t.Optional[str] = None,
        ignore_notfound: bool = False,
    ):
        return self._request(
            component,
            endpoint,
            key,
            ignore_notfound=ignore_notfound,
            method=method,
            payload=payload,
            query=query,
        )

    def supports_write_operations(self) -> bool:
        if self.api_version is None:
            self.discover()
        return self.api_version in self.WRITE_SUPPORTED_VERSIONS

    def discover(self) -> t.Tuple[str, str, str]:
        """Discover the actual slurmrestd API version and Slurm version by trying
        versions from the configured list. Returns a tuple of
        (cluster_name, slurm_version, api_version) and stores them in self.cluster_name,
        self.slurm_version and self.api_version."""
        if (
            self.cluster_name is not None
            and self.slurm_version is not None
            and self.api_version is not None
        ):
            return (self.cluster_name, self.slurm_version, self.api_version)

        # Try each configured supported slurmrestd API version in descending order
        for version in self.supported_versions:
            try:
                result = self._execute_request(
                    "slurm", version, "ping", ignore_notfound=True
                )
                # If we get here, the request was successful
                slurm_meta = result["meta"].get("slurm") or result["meta"].get("Slurm")
                if not isinstance(slurm_meta, dict):
                    raise KeyError("meta.slurm")
                self.cluster_name = slurm_meta.get(
                    "cluster", self.cluster_name_hint or "unknown"
                )
                self.slurm_version = slurm_meta["release"]
                self.api_version = version
                logger.info(
                    "Discovered slurmrestd Slurm version: %s and API version: %s",
                    self.slurm_version,
                    self.api_version,
                )
                return (self.cluster_name, self.slurm_version, self.api_version)
            except SlurmrestdNotFoundError:
                # Version not supported, try next
                logger.debug(
                    "Slurmrestd API version %s not supported, trying next", version
                )
                continue
            except (
                SlurmrestdInvalidResponseError,
                SlurmrestdInternalError,
                KeyError,
                ValueError,
            ) as err:
                logger.warning(
                    "Unable to parse Slurmrestd API ping response for version %s: %s",
                    version,
                    err,
                )
                continue

        # If we get here, no version worked
        raise SlurmrestConnectionError(
            f"Unable to discover slurmrestd API version. "
            f"Tried versions: {', '.join(self.supported_versions)}"
        )

    def jobs(self, **kwargs):
        return self._request("slurm", "jobs", "jobs", **kwargs)

    def ping_data(self):
        return self._request("slurm", "ping", "pings")

    def diag(self):
        return self._request("slurm", "diag", "statistics")

    def job_submit(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurm", "job/submit", payload=payload)

    def job_update(self, job_id: int, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurm", f"job/{job_id}", payload=payload)

    def job_cancel(self, job_id: int, payload: t.Optional[t.Dict[str, t.Any]] = None):
        return self.request_json(
            "DELETE",
            "slurm",
            f"job/{job_id}",
            payload=payload,
        )

    def jobs_by_node(self, node: str):
        """Select jobs not completed which are allocated the given node."""

        def on_node(job):
            """Return True if job is allocated this node."""
            if job["nodes"] == "":
                return False
            return node in NodeSet(job["nodes"])

        def terminated(job):
            """Return True if job is terminated."""
            for terminated_state in ["COMPLETED", "FAILED", "TIMEOUT"]:
                if terminated_state in job["job_state"]:
                    return True
            return False

        return [job for job in self.jobs() if on_node(job) and not terminated(job)]

    def jobs_states(self):
        # All Slurm jobs base states. Jobs can have only one of them.
        jobs = {
            "running": 0,
            "pending": 0,
            "completing": 0,
            "completed": 0,
            "cancelled": 0,
            "suspended": 0,
            "preempted": 0,
            "failed": 0,
            "timeout": 0,
            "node_fail": 0,
            "boot_fail": 0,
            "deadline": 0,
            "out_of_memory": 0,
            "unknown": 0,
        }
        total = 0
        for job in self.jobs():
            state_found = False
            for state in jobs.keys():
                if state.upper() in job["job_state"]:
                    jobs[state] += 1
                    state_found = True
                    break
            if not state_found:
                jobs["unknown"] += 1
            total += 1
        return jobs, total

    def _ctldjob(self, job_id: int, **kwargs):
        return self._request("slurm", f"job/{job_id}", "jobs", **kwargs)[0]

    def _acctjob(self, job_id: int, **kwargs):
        return self._request("slurmdb", f"job/{job_id}", "jobs", **kwargs)[0]

    def nodes(self, **kwargs):
        return self._request("slurm", "nodes", "nodes", **kwargs)

    @staticmethod
    def _optional_number_value(value, default=0):
        if isinstance(value, dict):
            if not value.get("set", False):
                return default
            return value.get("number", default)
        if value is None:
            return default
        return value

    def resources_states(self):
        # All Slurm nodes base states and some interesting flags such as drain and fail.
        nodes_states = {
            "idle": 0,
            "mixed": 0,
            "allocated": 0,
            "drain": 0,
            "down": 0,
            "error": 0,
            "fail": 0,
            "unknown": 0,
        }
        cores_states = {
            "idle": 0,
            "mixed": 0,
            "allocated": 0,
            "drain": 0,
            "down": 0,
            "error": 0,
            "fail": 0,
            "unknown": 0,
        }
        gpus_states = {
            "idle": 0,
            "mixed": 0,
            "allocated": 0,
            "drain": 0,
            "down": 0,
            "error": 0,
            "fail": 0,
            "unknown": 0,
        }
        memory_states = {
            "idle": 0.0,
            "allocated": 0.0,
        }
        nodes_total = 0
        cores_total = 0
        gpus_total = 0
        memory_total = 0.0
        nodes_getter = getattr(self, "nodes_unfiltered", None)
        nodes = nodes_getter() if callable(nodes_getter) else self.nodes()
        for node in nodes:
            cores = node["cpus"]
            node_gpus = self.node_gres_extract_gpus(node["gres"])
            real_memory = max(0, node.get("real_memory", 0))
            alloc_memory = max(0, min(real_memory, node.get("alloc_memory", 0)))
            idle_memory = max(real_memory - alloc_memory, 0)

            memory_states["idle"] += idle_memory / 1024
            memory_states["allocated"] += alloc_memory / 1024

            if "ERROR" in node["state"]:
                nodes_states["error"] += 1
                cores_states["error"] += cores
                gpus_states["error"] += node_gpus
            elif "FAIL" in node["state"]:
                nodes_states["fail"] += 1
                cores_states["fail"] += cores
                gpus_states["fail"] += node_gpus
            elif "MIXED" in node["state"]:
                nodes_states["mixed"] += 1
                # Look at number of actually allocated/idle cores
                cores_states["allocated"] += node["alloc_cpus"]
                cores_states["idle"] += node["alloc_idle_cpus"]
                allocated_gpus = self.node_gres_extract_gpus(node["gres_used"])
                gpus_states["allocated"] += allocated_gpus
                gpus_states["idle"] += node_gpus - allocated_gpus
            elif "ALLOCATED" in node["state"]:
                nodes_states["allocated"] += 1
                cores_states["allocated"] += cores
                allocated_gpus = self.node_gres_extract_gpus(node["gres_used"])
                gpus_states["allocated"] += allocated_gpus
                gpus_states["idle"] += node_gpus - allocated_gpus
            elif "DOWN" in node["state"]:
                nodes_states["down"] += 1
                cores_states["down"] += cores
                gpus_states["down"] += node_gpus
            elif "DRAIN" in node["state"]:
                nodes_states["drain"] += 1
                cores_states["drain"] += cores
                gpus_states["drain"] += node_gpus
            elif "IDLE" in node["state"]:
                nodes_states["idle"] += 1
                cores_states["idle"] += cores
                gpus_states["idle"] += node_gpus
            else:
                nodes_states["unknown"] += 1
                cores_states["unknown"] += cores
                gpus_states["unknown"] += node_gpus
            nodes_total += 1
            cores_total += cores
            gpus_total += node_gpus
            memory_total += real_memory / 1024
        return (
            nodes_states,
            cores_states,
            gpus_states,
            memory_states,
            nodes_total,
            cores_total,
            gpus_total,
            memory_total,
        )

    def node(self, node_name: str, **kwargs):
        try:
            return self._request("slurm", f"node/{node_name}", "nodes", **kwargs)[0]
        except SlurmrestdInternalError as err:
            if err.description.startswith("Failure to query node "):
                raise SlurmrestdNotFoundError(f"Node {node_name} not found")
            raise err

    def node_update(self, node_name: str, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurm", f"node/{node_name}", payload=payload)

    def node_delete(self, node_name: str):
        return self.request_json("DELETE", "slurm", f"node/{node_name}")

    def partitions(self, **kwargs):
        return self._request("slurm", "partitions", "partitions", **kwargs)

    def accounts(self, **kwargs):
        return self._request("slurmdb", "accounts", "accounts", **kwargs)

    def associations(self: str, **kwargs):
        return self._request("slurmdb", "associations", "associations", **kwargs)

    def reservations(self: str, **kwargs):
        return self._request("slurm", "reservations", "reservations", **kwargs)

    def reservation_create(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurm", "reservation", payload=payload)

    def reservation_update(
        self, reservation_name: str, payload: t.Dict[str, t.Any]
    ):
        return self.request_json(
            "POST",
            "slurm",
            f"reservation/{reservation_name}",
            payload=payload,
        )

    def reservation_delete(self, reservation_name: str):
        return self.request_json("DELETE", "slurm", f"reservation/{reservation_name}")

    def qos(self: str, **kwargs):
        return self._request("slurmdb", "qos", "qos", **kwargs)

    def account(self, account_name: str):
        return self._request("slurmdb", f"account/{account_name}", "accounts")[0]

    def accounts_update(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurmdb", "accounts", payload=payload)

    def account_delete(self, account_name: str):
        return self.request_json("DELETE", "slurmdb", f"account/{account_name}")

    def user(self, username: str):
        return self._request("slurmdb", f"user/{username}", "users")[0]

    def users(self):
        return self._request("slurmdb", "users", "users")

    def users_update(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurmdb", "users", payload=payload)

    def user_delete(self, username: str):
        return self.request_json("DELETE", "slurmdb", f"user/{username}")

    def associations_update(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurmdb", "associations", payload=payload)

    def associations_delete(self, payload: t.Dict[str, t.Any]):
        return self.request_json("DELETE", "slurmdb", "association", payload=payload)

    def qos_update(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurmdb", "qos", payload=payload)

    def qos_delete(self, qos_name: str):
        return self.request_json("DELETE", "slurmdb", f"qos/{qos_name}")

    def wckeys(self):
        return self._request("slurmdb", "wckeys", "wckeys")

    def wckeys_update(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurmdb", "wckeys", payload=payload)

    def wckey_delete(self, wckey_id: str):
        return self.request_json("DELETE", "slurmdb", f"wckey/{wckey_id}")

    def clusters(self):
        return self._request("slurmdb", "clusters", "clusters")

    def clusters_update(self, payload: t.Dict[str, t.Any]):
        return self.request_json("POST", "slurmdb", "clusters", payload=payload)

    def cluster_delete(self, cluster_name: str):
        return self.request_json("DELETE", "slurmdb", f"cluster/{cluster_name}")

    def licenses(self):
        return self._request("slurm", "licenses", "licenses")

    def shares(self):
        return self._request("slurm", "shares", "shares")

    def reconfigure(self):
        return self.request_json("GET", "slurm", "reconfigure")

    def slurmdb_diag(self):
        return self._request("slurmdb", "diag", "statistics")

    def slurmdb_config(self):
        return self.request_json("GET", "slurmdb", "config")

    def instances(self):
        return self._request("slurmdb", "instances", "instances")

    def tres(self):
        try:
            return self._request("slurmdb", "tres", "TRES")
        except KeyError:
            return self._request("slurmdb", "tres", "tres")

    @staticmethod
    def node_gres_extract_gpus(gres_full: str) -> int:
        """Return the number of GPU in gres string."""
        result = 0
        for gres_s in gres_full.split(","):
            if not len(gres_s):
                continue
            # Remove index if present
            gres_s = gres_s.split("(")[0]
            gres = gres_s.split(":")
            if gres[0] == "gpu":
                result += int(gres.pop())
        return result


class SlurmrestdAdapter(Slurmrestd):
    """Class that adapts responses from older slurmrestd API versions
    to the latest supported version using chained version adapters."""

    def __init__(
        self,
        uri: urllib.parse.ParseResult,
        auth: SlurmrestdAuthentifier,
        supported_versions: t.List[str],
        cluster_name_hint: t.Optional[str] = None,
    ):
        super().__init__(uri, auth, supported_versions, cluster_name_hint)
        # Will be set after discover() is called
        self._adaptation_chain = []

    def discover(self) -> t.Tuple[str, str, str]:
        """Discover API version and build adaptation chain if needed."""
        result = super().discover()

        # Target version is the highest supported version (first in descending list)
        target_version = self.supported_versions[0]

        # Build adaptation chain if API version is older than target
        if self.api_version != target_version:
            self._adaptation_chain = build_adaptation_chain(
                self.api_version,
                target_version,
                self.supported_versions,
                cluster_name_hint=self.cluster_name_hint,
            )
        else:
            self._adaptation_chain = []

        return result

    def _request(
        self,
        component: str,
        endpoint: str,
        key: t.Optional[str],
        ignore_notfound=False,
        method: str = "GET",
        payload: t.Optional[t.Dict[str, t.Any]] = None,
        query: t.Optional[t.Dict[str, t.Any]] = None,
    ):
        """Make request and adapt response data under the key if needed."""
        result = super()._request(
            component,
            endpoint,
            key,
            ignore_notfound,
            method=method,
            payload=payload,
            query=query,
        )

        # Apply adaptation chain to data under the key, passing component
        # for differentiation between slurmctld and slurmdbd jobs
        if self._adaptation_chain:
            for adapter in self._adaptation_chain:
                result = adapter.adapt(component, key, result)

        return result


class SlurmrestdFiltered(SlurmrestdAdapter):
    def __init__(
        self,
        uri: urllib.parse.ParseResult,
        auth: SlurmrestdAuthentifier,
        supported_versions: t.List[str],
        filters: "RuntimeSettings",
        cluster_name_hint: t.Optional[str] = None,
    ):
        super().__init__(uri, auth, supported_versions, cluster_name_hint)
        self.filters = filters

    @staticmethod
    def filter_item_fields(item: t.Dict, selection: t.Optional[t.List[str]]):
        for key in list(item.keys()):
            if key not in selection:
                del item[key]

    @staticmethod
    def filter_fields(
        items: t.Union[t.List, t.Dict],
        selection: t.Optional[t.List[str]],
    ):
        if selection is not None:
            if isinstance(items, list):
                for item in items:
                    SlurmrestdFiltered.filter_item_fields(item, selection)
            else:
                SlurmrestdFiltered.filter_item_fields(items, selection)
        return items

    def jobs(self, **kwargs):
        return SlurmrestdFiltered.filter_fields(super().jobs(**kwargs), self.filters.jobs)

    def jobs_unfiltered(self, **kwargs):
        """Return full job fields from slurmrestd, bypassing field filtering.
        Used by the persistence layer to capture all fields needed for storage."""
        return super().jobs(**kwargs)

    def _ctldjob(self, job_id: int, **kwargs):
        return SlurmrestdFiltered.filter_fields(
            super()._ctldjob(job_id, **kwargs), self.filters.ctldjob
        )

    def _acctjob(self, job_id: int, **kwargs):
        return SlurmrestdFiltered.filter_fields(
            super()._acctjob(job_id, **kwargs), self.filters.acctjob
        )

    def job(self, job_id: int):
        try:
            result = self._acctjob(job_id)
        except IndexError:
            raise SlurmrestdNotFoundError(f"Job {job_id} not found")
        # try to enrich result with additional fields from slurmctld
        try:
            result.update(self._ctldjob(job_id, ignore_notfound=True))
        except SlurmrestdInternalError as err:
            if err.error != 2017:
                raise err
            # pass the error, the job is just not available in ctld queue
        return result

    def nodes(self, **kwargs):
        return SlurmrestdFiltered.filter_fields(super().nodes(**kwargs), self.filters.nodes)

    def nodes_unfiltered(self, **kwargs):
        return super().nodes(**kwargs)

    def node(self, node_name: str):
        return SlurmrestdFiltered.filter_fields(
            super().node(node_name), self.filters.node
        )

    def partitions(self):
        return SlurmrestdFiltered.filter_fields(
            super().partitions(), self.filters.partitions
        )

    def accounts(self, **kwargs):
        return SlurmrestdFiltered.filter_fields(
            super().accounts(**kwargs), self.filters.accounts
        )

    def associations(self: str, **kwargs):
        return SlurmrestdFiltered.filter_fields(
            super().associations(**kwargs), self.filters.associations
        )

    def reservations(self: str, **kwargs):
        return SlurmrestdFiltered.filter_fields(
            super().reservations(**kwargs), self.filters.reservations
        )

    def qos(self: str, **kwargs):
        return SlurmrestdFiltered.filter_fields(super().qos(**kwargs), self.filters.qos)


class SlurmrestdFilteredCached(SlurmrestdFiltered):
    def __init__(
        self,
        uri: urllib.parse.ParseResult,
        auth: SlurmrestdAuthentifier,
        supported_versions: t.List[str],
        filters: "RuntimeSettings",
        cache: "RuntimeSettings",
        service: "CachingService",
        cluster_name_hint: t.Optional[str] = None,
    ):
        super().__init__(uri, auth, supported_versions, filters, cluster_name_hint)
        self.cache = cache
        self.service = service

    def _cached(
        self,
        key: "CacheKey",
        expiration: int,
        func: t.Callable,
        *args: t.Tuple[t.Any, ...],
        **kwargs: t.Dict[str, t.Any],
    ) -> t.Any:
        if not self.cache.enabled:
            return func(*args, **kwargs)
        data = self.service.get(key)
        if data is None:
            data = func(*args, **kwargs)
            self.service.put(key, data, expiration)
            self.service.count_miss(key)
        else:
            self.service.count_hit(key)
        return data

    def jobs(self, **kwargs):
        if kwargs:
            return super().jobs(**kwargs)
        return self._cached(CacheKey("jobs"), self.cache.jobs, super().jobs)

    def job(self, job_id: int):
        return self._cached(
            CacheKey(f"job-{job_id}", "individual-job"),
            self.cache.job,
            super().job,
            job_id,
        )

    def nodes(self, **kwargs):
        if kwargs:
            return super().nodes(**kwargs)
        return self._cached(CacheKey("nodes"), self.cache.nodes, super().nodes)

    def nodes_unfiltered(self, **kwargs):
        if kwargs:
            return super().nodes_unfiltered(**kwargs)
        return self._cached(
            CacheKey("nodes-unfiltered", "nodes"),
            self.cache.nodes,
            super().nodes_unfiltered,
        )

    def node(self, node_name: str):
        return self._cached(
            CacheKey(f"node-{node_name}", "individual-node"),
            self.cache.node,
            super().node,
            node_name,
        )

    def partitions(self):
        return self._cached(
            CacheKey("partitions"), self.cache.partitions, super().partitions
        )

    def accounts(self, **kwargs):
        if kwargs:
            return super().accounts(**kwargs)
        return self._cached(CacheKey("accounts"), self.cache.accounts, super().accounts)

    def associations(self, **kwargs):
        if kwargs:
            return super().associations(**kwargs)
        return self._cached(
            CacheKey("associations"), self.cache.associations, super().associations
        )

    def reservations(self, **kwargs):
        if kwargs:
            return super().reservations(**kwargs)
        return self._cached(
            CacheKey("reservations"), self.cache.reservations, super().reservations
        )

    def qos(self, **kwargs):
        if kwargs:
            return super().qos(**kwargs)
        return self._cached(CacheKey("qos"), self.cache.qos, super().qos)
