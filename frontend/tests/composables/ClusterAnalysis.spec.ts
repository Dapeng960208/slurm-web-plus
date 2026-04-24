import { describe, expect, test } from 'vitest'
import { analyzeCluster } from '@/composables/ClusterAnalysis'
import type { ClusterJob, ClusterNode, ClusterStats, JobHistoryRecord } from '@/composables/GatewayAPI'

function buildOptionalNumber(number: number) {
  return { set: true, infinite: false, number }
}

describe('ClusterAnalysis', () => {
  test('summarizes backlog, fragmentation and wait samples', () => {
    const stats: ClusterStats = {
      resources: {
        nodes: 4,
        cores: 128,
        memory: 524288,
        memory_allocated: 196608,
        memory_available: 327680,
        gpus: 8
      },
      jobs: {
        running: 2,
        total: 5
      }
    }

    const nodes: ClusterNode[] = [
      {
        alloc_cpus: 48,
        alloc_idle_cpus: 0,
        cores: 24,
        cpus: 48,
        gres: '',
        gres_used: '',
        name: 'cpu-a',
        partitions: ['normal'],
        real_memory: 131072,
        sockets: 2,
        state: ['ALLOCATED'],
        reason: ''
      },
      {
        alloc_cpus: 16,
        alloc_idle_cpus: 16,
        cores: 24,
        cpus: 32,
        gres: '',
        gres_used: '',
        name: 'cpu-b',
        partitions: ['normal'],
        real_memory: 131072,
        sockets: 2,
        state: ['MIXED'],
        reason: ''
      },
      {
        alloc_cpus: 0,
        alloc_idle_cpus: 16,
        cores: 16,
        cpus: 16,
        gres: '',
        gres_used: '',
        name: 'cpu-c',
        partitions: ['normal'],
        real_memory: 131072,
        sockets: 1,
        state: ['IDLE'],
        reason: ''
      },
      {
        alloc_cpus: 0,
        alloc_idle_cpus: 0,
        cores: 24,
        cpus: 48,
        gres: '',
        gres_used: '',
        name: 'cpu-d',
        partitions: ['normal'],
        real_memory: 131072,
        sockets: 2,
        state: ['DOWN'],
        reason: 'network'
      }
    ]

    const jobs: ClusterJob[] = [
      {
        account: 'science',
        cpus: buildOptionalNumber(32),
        gres_detail: [],
        job_id: 11,
        job_state: ['RUNNING'],
        node_count: buildOptionalNumber(1),
        nodes: 'cpu-a',
        partition: 'normal',
        priority: buildOptionalNumber(1000),
        qos: 'normal',
        sockets_per_node: { set: false, infinite: false, number: 0 },
        state_reason: 'None',
        tasks: buildOptionalNumber(32),
        tres_per_job: '',
        tres_per_node: '',
        tres_per_socket: '',
        tres_per_task: '',
        user_name: 'alice'
      },
      {
        account: 'science',
        cpus: buildOptionalNumber(16),
        gres_detail: [],
        job_id: 12,
        job_state: ['COMPLETING'],
        node_count: buildOptionalNumber(1),
        nodes: 'cpu-b',
        partition: 'normal',
        priority: buildOptionalNumber(980),
        qos: 'normal',
        sockets_per_node: { set: false, infinite: false, number: 0 },
        state_reason: 'None',
        tasks: buildOptionalNumber(16),
        tres_per_job: '',
        tres_per_node: '',
        tres_per_socket: '',
        tres_per_task: '',
        user_name: 'bob'
      },
      {
        account: 'science',
        cpus: buildOptionalNumber(24),
        gres_detail: [],
        job_id: 13,
        job_state: ['PENDING'],
        node_count: buildOptionalNumber(1),
        nodes: '',
        partition: 'normal',
        priority: buildOptionalNumber(970),
        qos: 'normal',
        sockets_per_node: { set: false, infinite: false, number: 0 },
        state_reason: 'Resources',
        tasks: buildOptionalNumber(24),
        tres_per_job: '',
        tres_per_node: '',
        tres_per_socket: '',
        tres_per_task: '',
        user_name: 'carol'
      },
      {
        account: 'science',
        cpus: buildOptionalNumber(8),
        gres_detail: [],
        job_id: 14,
        job_state: ['PENDING'],
        node_count: buildOptionalNumber(1),
        nodes: '',
        partition: 'normal',
        priority: buildOptionalNumber(960),
        qos: 'normal',
        sockets_per_node: { set: false, infinite: false, number: 0 },
        state_reason: 'Priority',
        tasks: buildOptionalNumber(8),
        tres_per_job: '',
        tres_per_node: '',
        tres_per_socket: '',
        tres_per_task: '',
        user_name: 'dave'
      }
    ]

    const historyJobs: JobHistoryRecord[] = [
      {
        id: 1,
        snapshot_time: '2026-04-24T10:00:00Z',
        job_id: 1,
        job_name: 'j1',
        job_state: 'COMPLETED',
        state_reason: 'None',
        user_id: 1,
        user_name: 'alice',
        account: 'science',
        group: 'science',
        partition: 'normal',
        qos: 'normal',
        nodes: 'cpu-a',
        node_count: 1,
        cpus: 16,
        priority: 0,
        tres_req_str: null,
        tres_per_job: null,
        tres_per_node: null,
        gres_detail: null,
        submit_time: '2026-04-24T09:00:00Z',
        eligible_time: null,
        start_time: '2026-04-24T09:15:00Z',
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
        id: 2,
        snapshot_time: '2026-04-24T11:00:00Z',
        job_id: 2,
        job_name: 'j2',
        job_state: 'COMPLETED',
        state_reason: 'None',
        user_id: 1,
        user_name: 'bob',
        account: 'science',
        group: 'science',
        partition: 'normal',
        qos: 'normal',
        nodes: 'cpu-b',
        node_count: 1,
        cpus: 8,
        priority: 0,
        tres_req_str: null,
        tres_per_job: null,
        tres_per_node: null,
        gres_detail: null,
        submit_time: '2026-04-24T10:00:00Z',
        eligible_time: '2026-04-24T10:05:00Z',
        start_time: '2026-04-24T10:25:00Z',
        end_time: '2026-04-24T10:55:00Z',
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

    const result = analyzeCluster({
      stats,
      jobs,
      nodes,
      historyJobs
    })

    expect(result.unavailableNodes).toBe(1)
    expect(result.fragmentationJobs).toBe(1)
    expect(result.topReasons[0]).toMatchObject({ reason: 'Resources', count: 1 })
    expect(result.waitStats.medianMinutes).toBe(15)
    expect(result.partitionPressure[0]).toMatchObject({
      name: 'normal',
      pendingJobs: 2,
      runningJobs: 2
    })
    expect(result.recommendations.map((item) => item.id)).toContain('recover-capacity')
    expect(result.recommendations.map((item) => item.id)).toContain('reduce-fragmentation')
  })
})
