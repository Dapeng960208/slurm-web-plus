import { describe, expect, test } from 'vitest'
import {
  buildQueueWaitSeries,
  inferQueueWaitAggregation
} from '@/composables/queueWaitHistory'
import type { JobHistoryRecord } from '@/composables/GatewayAPI'

const historyJobs: JobHistoryRecord[] = [
  {
    id: 1,
    snapshot_time: '2026-04-24T10:00:00Z',
    job_id: 1,
    job_name: 'job-1',
    job_state: 'COMPLETED',
    state_reason: 'None',
    user_id: 1,
    user_name: 'alice',
    account: 'science',
    group: 'science',
    partition: 'normal',
    qos: 'normal',
    nodes: 'cn1',
    node_count: 1,
    cpus: 16,
    priority: 0,
    tres_req_str: null,
    tres_per_job: null,
    tres_per_node: null,
    gres_detail: null,
    submit_time: '2026-04-24T09:00:00Z',
    eligible_time: null,
    start_time: '2026-04-24T09:10:00Z',
    end_time: '2026-04-24T09:40:00Z',
    last_sched_evaluation_time: null,
    time_limit_minutes: 60,
    tres_requested: null,
    tres_allocated: null,
    used_memory_gb: null,
    usage_stats: null,
    used_cpu_cores_avg: null,
    exit_code: '0:0',
    working_directory: null,
    command: null
  },
  {
    id: 2,
    snapshot_time: '2026-04-24T10:00:00Z',
    job_id: 2,
    job_name: 'job-2',
    job_state: 'COMPLETED',
    state_reason: 'None',
    user_id: 2,
    user_name: 'bob',
    account: 'science',
    group: 'science',
    partition: 'normal',
    qos: 'normal',
    nodes: 'cn2',
    node_count: 1,
    cpus: 16,
    priority: 0,
    tres_req_str: null,
    tres_per_job: null,
    tres_per_node: null,
    gres_detail: null,
    submit_time: '2026-04-24T09:05:00Z',
    eligible_time: null,
    start_time: '2026-04-24T09:20:00Z',
    end_time: '2026-04-24T09:45:00Z',
    last_sched_evaluation_time: null,
    time_limit_minutes: 60,
    tres_requested: null,
    tres_allocated: null,
    used_memory_gb: null,
    usage_stats: null,
    used_cpu_cores_avg: null,
    exit_code: '0:0',
    working_directory: null,
    command: null
  },
  {
    id: 3,
    snapshot_time: '2026-04-24T11:00:00Z',
    job_id: 3,
    job_name: 'job-3',
    job_state: 'COMPLETED',
    state_reason: 'None',
    user_id: 3,
    user_name: 'carol',
    account: 'science',
    group: 'science',
    partition: 'normal',
    qos: 'normal',
    nodes: 'cn3',
    node_count: 1,
    cpus: 16,
    priority: 0,
    tres_req_str: null,
    tres_per_job: null,
    tres_per_node: null,
    gres_detail: null,
    submit_time: '2026-04-24T10:30:00Z',
    eligible_time: '2026-04-24T10:35:00Z',
    start_time: '2026-04-24T10:50:00Z',
    end_time: '2026-04-24T11:10:00Z',
    last_sched_evaluation_time: null,
    time_limit_minutes: 60,
    tres_requested: null,
    tres_allocated: null,
    used_memory_gb: null,
    usage_stats: null,
    used_cpu_cores_avg: null,
    exit_code: '0:0',
    working_directory: null,
    command: null
  }
]

describe('queueWaitHistory', () => {
  test('builds minute averages in seconds using submit time as baseline', () => {
    expect(buildQueueWaitSeries(historyJobs, 'minute')).toEqual([
      [new Date('2026-04-24T09:10:00Z').getTime(), 600],
      [new Date('2026-04-24T09:20:00Z').getTime(), 900],
      [new Date('2026-04-24T10:50:00Z').getTime(), 1200]
    ])
  })

  test('builds hourly averages in seconds using submit time as baseline', () => {
    expect(buildQueueWaitSeries(historyJobs, 'hour')).toEqual([
      [new Date('2026-04-24T09:00:00Z').getTime(), 750],
      [new Date('2026-04-24T10:00:00Z').getTime(), 1200]
    ])
  })

  test('builds daily averages in seconds using submit time as baseline', () => {
    expect(buildQueueWaitSeries(historyJobs, 'day')).toEqual([
      [new Date('2026-04-24T00:00:00Z').getTime(), 900]
    ])
  })

  test('ignores jobs without a valid submit-to-start wait sample', () => {
    expect(
      buildQueueWaitSeries(
        [
          ...historyJobs,
          { ...historyJobs[0], id: 4, job_id: 4, submit_time: null },
          {
            ...historyJobs[0],
            id: 5,
            job_id: 5,
            submit_time: '2026-04-24T09:30:00Z',
            start_time: '2026-04-24T09:20:00Z'
          }
        ],
        'day'
      )
    ).toEqual([[new Date('2026-04-24T00:00:00Z').getTime(), 900]])
  })

  test('infers default aggregation from range or custom window span', () => {
    expect(inferQueueWaitAggregation({ range: 'hour' })).toBe('minute')
    expect(inferQueueWaitAggregation({ range: 'day' })).toBe('hour')
    expect(inferQueueWaitAggregation({ range: 'week' })).toBe('day')
    expect(
      inferQueueWaitAggregation({
        range: 'day',
        start: '2026-04-24T09:00:00Z',
        end: '2026-04-24T10:00:00Z'
      })
    ).toBe('minute')
    expect(
      inferQueueWaitAggregation({
        range: 'week',
        start: '2026-04-24T00:00:00Z',
        end: '2026-04-24T12:00:00Z'
      })
    ).toBe('hour')
    expect(
      inferQueueWaitAggregation({
        range: 'hour',
        start: '2026-04-24T00:00:00Z',
        end: '2026-04-27T00:00:00Z'
      })
    ).toBe('hour')
  })
})
