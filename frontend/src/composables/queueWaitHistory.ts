/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import type { JobHistoryRecord, MetricRange, MetricValue } from '@/composables/GatewayAPI'

export type QueueWaitAggregation = 'minute' | 'hour' | 'day'

export function inferQueueWaitAggregation(options: {
  range: MetricRange
  start?: string
  end?: string
}): QueueWaitAggregation {
  const customDuration = resolveCustomWindowDuration(options.start, options.end)
  if (customDuration != null) {
    if (customDuration <= 24 * 60 * 60 * 1000) return 'minute'
    if (customDuration <= 7 * 24 * 60 * 60 * 1000) return 'hour'
    return 'day'
  }

  if (options.range === 'hour') return 'minute'
  if (options.range === 'day') return 'hour'
  return 'day'
}

export function buildQueueWaitSeries(
  historyJobs: JobHistoryRecord[],
  aggregation: QueueWaitAggregation
): MetricValue[] {
  if (!historyJobs.length) return []

  const buckets = new Map<number, { totalSeconds: number; count: number }>()

  for (const job of historyJobs) {
    const start = parseTimestamp(job.start_time)
    const submit = parseTimestamp(job.submit_time)
    if (!Number.isFinite(start) || !Number.isFinite(submit) || start < submit) continue

    const bucketKey = bucketTimestamp(start, aggregation)
    const bucket = buckets.get(bucketKey) ?? { totalSeconds: 0, count: 0 }
    bucket.totalSeconds += (start - submit) / 1000
    bucket.count += 1
    buckets.set(bucketKey, bucket)
  }

  return [...buckets.entries()]
    .sort((left, right) => left[0] - right[0])
    .map(([timestamp, bucket]) => [timestamp, Math.round(bucket.totalSeconds / bucket.count)])
}

function resolveCustomWindowDuration(start?: string, end?: string): number | null {
  const startTime = parseTimestamp(start)
  const endTime = parseTimestamp(end)
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime <= startTime) return null
  return endTime - startTime
}

function parseTimestamp(value?: string | null): number {
  if (!value) return Number.NaN
  return new Date(value).getTime()
}

function bucketTimestamp(timestamp: number, aggregation: QueueWaitAggregation): number {
  const bucket = new Date(timestamp)
  if (aggregation === 'minute') {
    bucket.setUTCSeconds(0, 0)
  } else if (aggregation === 'hour') {
    bucket.setUTCMinutes(0, 0, 0)
  } else {
    bucket.setUTCHours(0, 0, 0, 0)
  }
  return bucket.getTime()
}
