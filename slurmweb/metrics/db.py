# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import typing as t
import collections
import re
from datetime import datetime, timedelta, timezone
import asyncio
import logging

import aiohttp

from rfl.core.asyncio import asyncio_run

from ..errors import SlurmwebMetricsDBError
from .hotspots import build_hotspot_events_from_metric_series

SlurmWebRangeResolutionSet = collections.namedtuple(
    "SlurmWebRangeResolutionSet", ["hour", "day", "week"]
)

SlurmWebRangeResolution = collections.namedtuple(
    "SlurmWebRangeResolution", ["step", "range", "rounding"]
)


logger = logging.getLogger(__name__)


class SlurmwebMetricId:
    def __init__(self, name, key=None):
        self.name = name
        if key:
            self.key = key
        else:
            self.key = name


class SlurmwebMetricQuery:
    def __init__(
        self,
        endpoint,
        ids: t.List[SlurmwebMetricId],
        resolution: SlurmWebRangeResolutionSet,
        agg=None,
        label_as_key=None,
        key=None,
    ):
        self.endpoint = endpoint
        self.ids = ids
        self.resolution = resolution
        self.agg = agg
        self.label_as_key = label_as_key
        self.key = key


class SlurmwebMetricsDB:
    PARTITION_SUPPORTED_METRICS = {"nodes", "cores", "gpus", "memory", "jobs"}

    RANGE_RESOLUTIONS = {
        "30s": SlurmWebRangeResolutionSet(
            hour=SlurmWebRangeResolution("30s", "1h", 30),
            day=SlurmWebRangeResolution("10m", "1d", 600),
            week=SlurmWebRangeResolution("1h", "1w", 3600),
        ),
        "1m": SlurmWebRangeResolutionSet(
            hour=SlurmWebRangeResolution("1m", "1h", 60),
            day=SlurmWebRangeResolution("10m", "1d", 600),
            week=SlurmWebRangeResolution("1h", "1w", 3600),
        ),
    }
    METRICS_QUERY_PARAMS = {
        "nodes": SlurmwebMetricQuery(
            "query",
            [SlurmwebMetricId("slurm_nodes")],
            RANGE_RESOLUTIONS["30s"],
            agg="avg_over_time",
            label_as_key="state",
        ),
        "cores": SlurmwebMetricQuery(
            "query",
            [SlurmwebMetricId("slurm_cores")],
            RANGE_RESOLUTIONS["30s"],
            agg="avg_over_time",
            label_as_key="state",
        ),
        "gpus": SlurmwebMetricQuery(
            "query",
            [SlurmwebMetricId("slurm_gpus")],
            RANGE_RESOLUTIONS["30s"],
            agg="avg_over_time",
            label_as_key="state",
        ),
        "memory": SlurmwebMetricQuery(
            "query",
            [SlurmwebMetricId("slurm_memory")],
            RANGE_RESOLUTIONS["30s"],
            agg="avg_over_time",
            label_as_key="state",
        ),
        "jobs": SlurmwebMetricQuery(
            "query",
            [SlurmwebMetricId("slurm_jobs")],
            RANGE_RESOLUTIONS["30s"],
            agg="avg_over_time",
            label_as_key="state",
        ),
        "cache": SlurmwebMetricQuery(
            "query_range",
            [
                SlurmwebMetricId("slurmweb_cache_hit_total", "hit"),
                SlurmwebMetricId("slurmweb_cache_miss_total", "miss"),
            ],
            RANGE_RESOLUTIONS["1m"],
        ),
        "users": SlurmwebMetricQuery(
            "query",
            [SlurmwebMetricId("slurmweb_user_submissions_last_minute")],
            RANGE_RESOLUTIONS["1m"],
            agg="avg_over_time",
            label_as_key="user",
        ),
    }

    REQUEST_BASE_PATH = "/api/v1/"

    def __init__(self, base_uri, job):
        self.base_uri = base_uri
        self.job = job

    def request(
        self,
        metric,
        last,
        partition=None,
        start_time: t.Optional[datetime] = None,
        end_time: t.Optional[datetime] = None,
    ):
        params = self.METRICS_QUERY_PARAMS[metric]
        if metric not in self.PARTITION_SUPPORTED_METRICS:
            partition = None
        return self._merge_results(
            asyncio_run(
                self._requests(
                    metric,
                    params,
                    last,
                    partition,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
        )

    def _merge_results(self, results):
        merge = {}
        for result in results:
            merge.update(result)
        return merge

    async def _requests(
        self,
        metric,
        params,
        last,
        partition,
        start_time: t.Optional[datetime] = None,
        end_time: t.Optional[datetime] = None,
    ):
        """Return the list of available clusters with permissions. Clusters on which
        request to get permissions failed are filtered out."""
        return await asyncio.gather(
            *[
                self._request(
                    metric,
                    *self._query(
                        metric,
                        id,
                        params,
                        last,
                        partition,
                        start_time=start_time,
                        end_time=end_time,
                    ),
                    partition,
                )
                for id in params.ids
            ]
        )

    def _resolve_resolution(
        self,
        params: SlurmwebMetricQuery,
        last: str,
        start_time: t.Optional[datetime] = None,
        end_time: t.Optional[datetime] = None,
    ) -> SlurmWebRangeResolution:
        if start_time is not None and end_time is not None:
            duration = end_time - start_time
            if duration <= timedelta(hours=2):
                return params.resolution.hour
            if duration <= timedelta(days=7):
                return params.resolution.day
            return params.resolution.week

        try:
            return getattr(params.resolution, last)
        except AttributeError as err:
            raise SlurmwebMetricsDBError(f"Unsupported metric range {last}") from err

    def _empty_result(self, metric):
        if metric == "memory":
            return {"allocated": [], "idle": []}
        if metric in {"nodes", "cores", "gpus"}:
            return {
                "idle": [],
                "mixed": [],
                "allocated": [],
                "drain": [],
                "down": [],
                "error": [],
                "fail": [],
                "unknown": [],
            }
        if metric == "jobs":
            return {
                "running": [],
                "pending": [],
                "completing": [],
                "completed": [],
                "cancelled": [],
                "suspended": [],
                "preempted": [],
                "failed": [],
                "timeout": [],
                "node_fail": [],
                "boot_fail": [],
                "deadline": [],
                "out_of_memory": [],
                "unknown": [],
            }
        return {}

    async def _request(self, metric, id, params, query, partition=None):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_uri.geturl()}{self.REQUEST_BASE_PATH}{query}"
                logger.debug("Send metrics request %s", url)
                async with session.get(url) as response:
                    if response.status != 200:
                        raise SlurmwebMetricsDBError(
                            f"Unexpected response status {response.status} for metrics "
                            f"database request {url}"
                        )
                    try:
                        json = await response.json()
                    except aiohttp.client_exceptions.ContentTypeError as err:
                        raise SlurmwebMetricsDBError(
                            "Unsupported Content-Type for metrics database request "
                            f"{url}"
                        ) from err
        except aiohttp.ClientConnectionError as err:
            raise SlurmwebMetricsDBError(
                f"Metrics database connection error: {str(err)}"
            ) from err

        # Check result is not empty
        if not json["data"]["result"]:
            if partition is not None and metric in self.PARTITION_SUPPORTED_METRICS:
                return self._empty_result(metric)
            raise SlurmwebMetricsDBError(f"Empty result for query {query}")
        try:
            result = {}
            for _result in json["data"]["result"]:
                if params.label_as_key:
                    _key = _result["metric"][params.label_as_key]
                else:
                    _key = id.key
                result[_key] = [
                    # Convert timestamp for second to millisecond and values from
                    # string to floats.
                    [t_v_pair[0] * 1000, float(t_v_pair[1])]
                    for t_v_pair in _result["values"]
                ]
            return result
        except RuntimeError as err:
            raise SlurmwebMetricsDBError(
                f"Unexpected result on metrics query {query}"
            ) from err

    def _query(
        self,
        metric,
        id,
        params,
        last,
        partition=None,
        start_time: t.Optional[datetime] = None,
        end_time: t.Optional[datetime] = None,
    ):
        resolution = self._resolve_resolution(
            params,
            last,
            start_time=start_time,
            end_time=end_time,
        )
        range = None

        def _rounded_timetstamp(timestamp):
            return timestamp - timestamp % resolution.rounding

        labels = [f"job='{self.job}'"]
        if metric in self.PARTITION_SUPPORTED_METRICS:
            labels.append(f"partition='{'' if partition is None else partition}'")
        filter = "{" + ",".join(labels) + "}"
        if params.agg:
            if start_time is not None and end_time is not None:
                start = _rounded_timetstamp(start_time.timestamp())
                end = _rounded_timetstamp(end_time.timestamp())
                query_range = f"&start={start}&end={end}&step={resolution.step}"
                promql = f"{params.agg}({id.name}{filter}[{resolution.step}])"
                return id, params, (f"query_range?query={promql}{query_range}")
            range = f"[{resolution.range}:{resolution.step}]"
            _promql = f"{params.agg}({id.name}{filter}[{resolution.step}]){range}"
        else:
            end = datetime.now()
            start = end
            if last == "hour":
                start = end - timedelta(hours=1)
            elif last == "day":
                start = end - timedelta(days=1)
            elif last == "week":
                start = end - timedelta(days=7)
            else:
                raise SlurmwebMetricsDBError(f"Unsupported metric range {last}")
            if start_time is not None and end_time is not None:
                start = start_time
                end = end_time
            range = (
                f"&start={_rounded_timetstamp(start.timestamp())}&"
                f"end={_rounded_timetstamp(end.timestamp())}&step={resolution.step}"
            )
            _promql = (
                f"{id.name}{filter}-{id.name}{filter} offset {resolution.step} {range}"
            )
        return id, params, (f"{params.endpoint}?query={_promql}")

    def _duration_resolution(self, duration: timedelta) -> SlurmWebRangeResolution:
        if duration <= timedelta(hours=2):
            return self.RANGE_RESOLUTIONS["30s"].hour
        if duration <= timedelta(days=7):
            return self.RANGE_RESOLUTIONS["30s"].day
        return self.RANGE_RESOLUTIONS["30s"].week

    def node_instant_metrics(self, node_name: str, hostname_label: str = "hostname"):
        """
        Query Prometheus for instant node_exporter metrics for a specific node.
        Returns a dict with CPU, memory, and disk usage percentages.
        """
        queries = {
            "cpu_usage": f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle",{hostname_label}="{node_name}"}}[1m])) * 100)',
            "memory_usage": f'100 * (1 - (node_memory_MemAvailable_bytes{{{hostname_label}="{node_name}"}} / node_memory_MemTotal_bytes{{{hostname_label}="{node_name}"}}))',
            "disk_usage": f'100 - ((node_filesystem_avail_bytes{{mountpoint="/",{hostname_label}="{node_name}"}} / node_filesystem_size_bytes{{mountpoint="/",{hostname_label}="{node_name}"}}) * 100)',
        }

        async def _fetch_all():
            results = {}
            async with aiohttp.ClientSession() as session:
                for key, promql in queries.items():
                    url = f"{self.base_uri.geturl()}{self.REQUEST_BASE_PATH}query?query={promql}"
                    logger.debug("Node metrics request: %s", url)
                    try:
                        async with session.get(url) as response:
                            if response.status != 200:
                                logger.warning(
                                    "Metrics query %s returned status %d", key, response.status
                                )
                                results[key] = None
                                continue
                            json_data = await response.json()
                            if (
                                json_data.get("data", {}).get("result")
                                and len(json_data["data"]["result"]) > 0
                            ):
                                value = float(json_data["data"]["result"][0]["value"][1])
                                results[key] = round(value, 2)
                            else:
                                results[key] = None
                    except Exception as err:
                        logger.warning("Error fetching %s for node %s: %s", key, node_name, err)
                        results[key] = None
            return results

        return asyncio_run(_fetch_all())

    def node_instant_metrics_all(self, hostname_label: str = "hostname"):
        queries = {
            "cpu_usage": f'100 - (avg by ({hostname_label}) (rate(node_cpu_seconds_total{{mode="idle"}}[1m])) * 100)',
            "memory_usage": (
                f"100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))"
            ),
        }

        async def _fetch_all():
            results: t.Dict[str, t.Dict[str, t.Optional[float]]] = {}
            async with aiohttp.ClientSession() as session:
                for metric_key, promql in queries.items():
                    url = f"{self.base_uri.geturl()}{self.REQUEST_BASE_PATH}query?query={promql}"
                    logger.debug("Node metrics all request: %s", url)
                    try:
                        async with session.get(url) as response:
                            if response.status != 200:
                                raise SlurmwebMetricsDBError(
                                    "Unexpected response status "
                                    f"{response.status} for metrics database request {url}"
                                )
                            json_data = await response.json()
                    except aiohttp.ClientConnectionError as err:
                        raise SlurmwebMetricsDBError(
                            f"Metrics database connection error: {str(err)}"
                        ) from err

                    for item in json_data.get("data", {}).get("result", []):
                        node_name = item.get("metric", {}).get(hostname_label)
                        if not node_name:
                            continue
                        try:
                            value = round(float(item["value"][1]), 2)
                        except (TypeError, ValueError, IndexError, KeyError) as err:
                            raise SlurmwebMetricsDBError(
                                f"Unexpected result on metrics query {promql}"
                            ) from err
                        results.setdefault(node_name, {})[metric_key] = value
            return results

        return asyncio_run(_fetch_all())

    def user_history_metrics(self, username: str, last: str):
        try:
            resolution = getattr(self.RANGE_RESOLUTIONS["1m"], last)
        except AttributeError as err:
            raise SlurmwebMetricsDBError(f"Unsupported metric range {last}") from err

        end = datetime.now()
        if last == "hour":
            start = end - timedelta(hours=1)
        elif last == "day":
            start = end - timedelta(days=1)
        elif last == "week":
            start = end - timedelta(days=7)
        else:
            raise SlurmwebMetricsDBError(f"Unsupported metric range {last}")

        def _rounded_timestamp(timestamp):
            return int(timestamp - timestamp % resolution.rounding)

        start_ts = _rounded_timestamp(start.timestamp())
        end_ts = _rounded_timestamp(end.timestamp())
        promql = (
            f"slurmweb_user_submissions_last_minute"
            f"{{job='{self.job}',user='{username}'}}"
        )

        async def _fetch():
            async with aiohttp.ClientSession() as session:
                url = (
                    f"{self.base_uri.geturl()}{self.REQUEST_BASE_PATH}query_range"
                    f"?query={promql}&start={start_ts}&end={end_ts}&step={resolution.step}"
                )
                logger.debug("User history metrics request: %s", url)
                try:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise SlurmwebMetricsDBError(
                                "Unexpected response status "
                                f"{response.status} for metrics database request {url}"
                            )
                        try:
                            json_data = await response.json()
                        except aiohttp.client_exceptions.ContentTypeError as err:
                            raise SlurmwebMetricsDBError(
                                "Unsupported Content-Type for metrics database request "
                                f"{url}"
                            ) from err
                except aiohttp.ClientConnectionError as err:
                    raise SlurmwebMetricsDBError(
                        f"Metrics database connection error: {str(err)}"
                    ) from err

                result = json_data.get("data", {}).get("result", [])
                if not result:
                    return {"submissions": []}
                try:
                    values = [
                        [int(t_v_pair[0] * 1000), round(float(t_v_pair[1]), 2)]
                        for t_v_pair in result[0]["values"]
                    ]
                except (TypeError, ValueError, IndexError, KeyError) as err:
                    raise SlurmwebMetricsDBError(
                        f"Unexpected result on metrics query {promql}"
                    ) from err
                return {"submissions": values}

        return asyncio_run(_fetch())

    def node_history_metrics(
        self,
        node_name: str,
        last: str,
        hostname_label: str = "hostname",
        start_time=None,
        end_time=None,
    ):
        """
        Query Prometheus for historical node_exporter metrics for a specific node.
        Returns a dict with CPU, memory, and disk usage series.
        """
        if start_time is not None and end_time is not None:
            start = start_time
            end = end_time
            duration = end - start
            resolution = self._duration_resolution(duration)
        else:
            try:
                resolution = getattr(self.RANGE_RESOLUTIONS["30s"], last)
            except AttributeError as err:
                raise SlurmwebMetricsDBError(f"Unsupported metric range {last}") from err

            end = datetime.now()
            if last == "hour":
                start = end - timedelta(hours=1)
            elif last == "day":
                start = end - timedelta(days=1)
            elif last == "week":
                start = end - timedelta(days=7)
            else:
                raise SlurmwebMetricsDBError(f"Unsupported metric range {last}")

        def _rounded_timestamp(timestamp):
            return int(timestamp - timestamp % resolution.rounding)

        start_ts = _rounded_timestamp(start.timestamp())
        end_ts = _rounded_timestamp(end.timestamp())

        queries = {
            "cpu_usage": f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle",{hostname_label}="{node_name}"}}[1m])) * 100)',
            "memory_usage": f'100 * (1 - (node_memory_MemAvailable_bytes{{{hostname_label}="{node_name}"}} / node_memory_MemTotal_bytes{{{hostname_label}="{node_name}"}}))',
            "disk_usage": f'100 - ((node_filesystem_avail_bytes{{mountpoint="/",{hostname_label}="{node_name}"}} / node_filesystem_size_bytes{{mountpoint="/",{hostname_label}="{node_name}"}}) * 100)',
        }

        async def _fetch_all():
            results = {}
            async with aiohttp.ClientSession() as session:
                for key, promql in queries.items():
                    url = (
                        f"{self.base_uri.geturl()}{self.REQUEST_BASE_PATH}query_range"
                        f"?query={promql}&start={start_ts}&end={end_ts}&step={resolution.step}"
                    )
                    logger.debug("Node history metrics request: %s", url)
                    try:
                        async with session.get(url) as response:
                            if response.status != 200:
                                raise SlurmwebMetricsDBError(
                                    "Unexpected response status "
                                    f"{response.status} for metrics database request {url}"
                                )
                            try:
                                json_data = await response.json()
                            except aiohttp.client_exceptions.ContentTypeError as err:
                                raise SlurmwebMetricsDBError(
                                    "Unsupported Content-Type for metrics database request "
                                    f"{url}"
                                ) from err
                    except aiohttp.ClientConnectionError as err:
                        raise SlurmwebMetricsDBError(
                            f"Metrics database connection error: {str(err)}"
                        ) from err

                    if not json_data["data"]["result"]:
                        raise SlurmwebMetricsDBError(f"Empty result for query {promql}")

                    try:
                        results[key] = [
                            [int(t_v_pair[0] * 1000), round(float(t_v_pair[1]), 2)]
                            for t_v_pair in json_data["data"]["result"][0]["values"]
                        ]
                    except (TypeError, ValueError, IndexError, KeyError) as err:
                        raise SlurmwebMetricsDBError(
                            f"Unexpected result on metrics query {promql}"
                        ) from err
            return results

        return asyncio_run(_fetch_all())

    def cluster_node_hotspots(
        self,
        node_names: t.Sequence[str],
        hostname_label: str = "hostname",
        start_time: t.Optional[datetime] = None,
        end_time: t.Optional[datetime] = None,
        threshold: float = 80.0,
        limit: int = 10,
    ) -> t.Dict[str, t.Any]:
        if start_time is None or end_time is None:
            end_time = datetime.now(tz=timezone.utc)
            start_time = end_time - timedelta(days=3)
        if start_time >= end_time:
            raise SlurmwebMetricsDBError("start must be earlier than end")

        duration = end_time - start_time
        resolution = self._duration_resolution(duration)
        step_seconds = resolution.rounding
        start_ts = int(start_time.timestamp() - start_time.timestamp() % resolution.rounding)
        end_ts = int(end_time.timestamp() - end_time.timestamp() % resolution.rounding)
        if not node_names:
            return {
                "window": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
                "threshold": threshold,
                "events": [],
            }

        matcher = "|".join(re.escape(node_name) for node_name in sorted(set(node_names)))
        node_filter = f'{hostname_label}=~"^(?:{matcher})$"'
        queries = {
            "cpu": (
                f'100 - (avg by ({hostname_label}) '
                f'(rate(node_cpu_seconds_total{{mode="idle",{node_filter}}}[1m])) * 100)'
            ),
            "memory": (
                f"100 * (1 - (node_memory_MemAvailable_bytes{{{node_filter}}} / "
                f"node_memory_MemTotal_bytes{{{node_filter}}}))"
            ),
        }

        async def _fetch():
            results = {}
            async with aiohttp.ClientSession() as session:
                for metric_key, promql in queries.items():
                    url = (
                        f"{self.base_uri.geturl()}{self.REQUEST_BASE_PATH}query_range"
                        f"?query={promql}&start={start_ts}&end={end_ts}&step={resolution.step}"
                    )
                    logger.debug("Cluster node hotspot metrics request: %s", url)
                    try:
                        async with session.get(url) as response:
                            if response.status != 200:
                                raise SlurmwebMetricsDBError(
                                    "Unexpected response status "
                                    f"{response.status} for metrics database request {url}"
                                )
                            json_data = await response.json()
                    except aiohttp.ClientConnectionError as err:
                        raise SlurmwebMetricsDBError(
                            f"Metrics database connection error: {str(err)}"
                        ) from err

                    series = {}
                    for item in json_data.get("data", {}).get("result", []):
                        node_name = item.get("metric", {}).get(hostname_label)
                        if not node_name:
                            continue
                        series[node_name] = [
                            [int(timestamp * 1000), round(float(value), 2)]
                            for timestamp, value in item.get("values", [])
                        ]
                    results[metric_key] = series
            return results

        metrics = asyncio_run(_fetch())
        events = build_hotspot_events_from_metric_series(
            metrics,
            threshold=threshold,
            step_seconds=step_seconds,
            limit=limit,
        )
        return {
            "window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "threshold": threshold,
            "events": events,
        }
