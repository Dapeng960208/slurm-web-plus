# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import typing as t
from datetime import datetime, timezone


def build_hotspot_events_from_metric_series(
    metrics: t.Dict[str, t.Dict[str, t.List[t.List[t.Any]]]],
    threshold: float,
    step_seconds: int,
    limit: int = 10,
) -> t.List[t.Dict[str, t.Any]]:
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")

    def _extract_events(
        metric_name: str,
        series_by_node: t.Dict[str, t.List[t.List[t.Any]]],
    ) -> t.List[t.Dict[str, t.Any]]:
        events: t.List[t.Dict[str, t.Any]] = []
        max_gap_seconds = step_seconds * 2
        for node_name, values in series_by_node.items():
            ordered_values = sorted(values, key=lambda item: item[0])
            event_start = None
            event_end = None
            peak = threshold
            previous_ts = None
            for index, (timestamp_ms, value) in enumerate(ordered_values):
                ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                gap_break = (
                    previous_ts is not None
                    and int((ts - previous_ts).total_seconds()) > max_gap_seconds
                )
                is_hot = value >= threshold

                if gap_break and event_start is not None:
                    duration_seconds = max(
                        int((event_end - event_start).total_seconds()) + step_seconds,
                        step_seconds,
                    )
                    events.append(
                        {
                            "node": node_name,
                            "metric": metric_name,
                            "start": event_start.isoformat(),
                            "end": event_end.isoformat(),
                            "duration_seconds": duration_seconds,
                            "peak_usage": round(peak, 1),
                        }
                    )
                    event_start = None
                    event_end = None
                    peak = threshold

                if is_hot and event_start is None:
                    event_start = ts
                    event_end = ts
                    peak = value
                elif is_hot:
                    event_end = ts
                    peak = max(peak, value)

                if ((not is_hot) or index == len(ordered_values) - 1) and event_start is not None:
                    if is_hot:
                        event_end = ts
                    duration_seconds = max(
                        int((event_end - event_start).total_seconds()) + step_seconds,
                        step_seconds,
                    )
                    events.append(
                        {
                            "node": node_name,
                            "metric": metric_name,
                            "start": event_start.isoformat(),
                            "end": event_end.isoformat(),
                            "duration_seconds": duration_seconds,
                            "peak_usage": round(peak, 1),
                        }
                    )
                    event_start = None
                    event_end = None
                    peak = threshold

                previous_ts = ts
        return events

    events: t.List[t.Dict[str, t.Any]] = []
    for metric_name, series_by_node in metrics.items():
        events.extend(_extract_events(metric_name, series_by_node))
    events.sort(
        key=lambda item: (
            item["start"],
            item["duration_seconds"],
            item["peak_usage"],
        ),
        reverse=True,
    )
    return events[: max(limit, 0)]
