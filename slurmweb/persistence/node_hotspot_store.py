# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import threading
import time
import typing as t
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import sessionmaker

from ..metrics.hotspots import build_hotspot_events_from_metric_series
from ..models.db import sqlalchemy_url
from ..models.modes import NodeMetricSample


logger = logging.getLogger(__name__)


class NodeHotspotStore:
    def __init__(
        self,
        settings,
        node_metrics_db,
        cluster_name: str,
        hostname_label: str = "hostname",
    ):
        self._settings = settings
        self._node_metrics_db = node_metrics_db
        self._cluster_name = cluster_name
        self._hostname_label = hostname_label
        self._engine = sa.create_engine(sqlalchemy_url(settings), future=True)
        self._Session = sessionmaker(bind=self._engine, future=True)
        self._stop = threading.Event()
        self._thread: t.Optional[threading.Thread] = None

    def validate_connection(self):
        with self._engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="slurmweb-node-hotspot-store",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self):
        logger.info("Node hotspot persistence thread started")
        interval = max(int(getattr(self._settings, "snapshot_interval", 60)), 30)
        retention = max(int(getattr(self._settings, "retention_days", 180)), 1)
        while not self._stop.is_set():
            try:
                sampled_at = datetime.now(tz=timezone.utc)
                captured = self.capture_snapshot(sampled_at=sampled_at)
                deleted = self.cleanup(retention)
                logger.info(
                    "Node hotspot persistence cycle completed: cluster=%s sampled_at=%s captured_nodes=%d retention_days=%d deleted_rows=%d interval_seconds=%d",
                    self._cluster_name,
                    sampled_at.isoformat(),
                    captured,
                    retention,
                    deleted,
                    interval,
                )
            except Exception as err:
                logger.warning("Node hotspot persistence cycle failed: %s", err)
            self._stop.wait(interval)

    def capture_snapshot(self, sampled_at: t.Optional[datetime] = None):
        sampled_at = sampled_at or datetime.now(tz=timezone.utc)
        nodes = self._node_metrics_db.node_instant_metrics_all(
            hostname_label=self._hostname_label
        )
        if not nodes:
            return 0
        rows = []
        for node_name, values in nodes.items():
            rows.append(
                {
                    "cluster": self._cluster_name,
                    "node": node_name,
                    "sampled_at": sampled_at,
                    "cpu_usage": values.get("cpu_usage"),
                    "memory_usage": values.get("memory_usage"),
                }
            )

        stmt = pg_insert(NodeMetricSample).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["cluster", "node", "sampled_at"],
            set_={
                "cpu_usage": stmt.excluded.cpu_usage,
                "memory_usage": stmt.excluded.memory_usage,
            },
        )
        with self._Session.begin() as session:
            session.execute(stmt)
        return len(rows)

    def cleanup(self, retention_days: int):
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=retention_days)
        with self._Session.begin() as session:
            result = session.execute(
                sa.delete(NodeMetricSample).where(NodeMetricSample.sampled_at < cutoff)
            )
        return int(result.rowcount or 0)

    def cluster_node_hotspots(
        self,
        start_time: datetime,
        end_time: datetime,
        threshold: float = 80.0,
        limit: int = 10,
    ) -> t.Dict[str, t.Any]:
        if start_time >= end_time:
            raise ValueError("start must be earlier than end")

        with self._Session() as session:
            rows = (
                session.query(NodeMetricSample)
                .filter(NodeMetricSample.cluster == self._cluster_name)
                .filter(NodeMetricSample.sampled_at >= start_time)
                .filter(NodeMetricSample.sampled_at <= end_time)
                .order_by(NodeMetricSample.sampled_at.asc(), NodeMetricSample.node.asc())
                .all()
            )

        metrics: t.Dict[str, t.Dict[str, t.List[t.List[t.Any]]]] = {
            "cpu": {},
            "memory": {},
        }
        sampled_timestamps = set()
        for row in rows:
            timestamp_ms = int(row.sampled_at.timestamp() * 1000)
            sampled_timestamps.add(row.sampled_at)
            if row.cpu_usage is not None:
                metrics["cpu"].setdefault(row.node, []).append([timestamp_ms, row.cpu_usage])
            if row.memory_usage is not None:
                metrics["memory"].setdefault(row.node, []).append([timestamp_ms, row.memory_usage])

        if len(sampled_timestamps) >= 2:
            ordered = sorted(sampled_timestamps)
            deltas = [
                int((ordered[index] - ordered[index - 1]).total_seconds())
                for index in range(1, len(ordered))
                if ordered[index] > ordered[index - 1]
            ]
            step_seconds = max(min(deltas) if deltas else 60, 1)
        else:
            step_seconds = max(int(getattr(self._settings, "snapshot_interval", 60)), 1)

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
