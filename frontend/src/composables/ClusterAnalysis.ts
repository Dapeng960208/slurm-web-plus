/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import {
  getNodeMainState,
  jobResourcesGPU,
  type ClusterJob,
  type ClusterNode,
  type ClusterStats,
  type JobHistoryRecord,
  type MetricJobState,
  type MetricMemoryState,
  type MetricResourceState,
  type MetricValue
} from '@/composables/GatewayAPI'

const activeJobStates = ['RUNNING', 'COMPLETING'] as const
const pendingJobStates = ['PENDING'] as const
const busyResourceStates = ['allocated', 'mixed'] as const

export interface AnalysisRecommendation {
  id: string
  title: string
  summary: string
  evidence: string
  tone: 'neutral' | 'warning' | 'danger' | 'success'
}

export interface AnalysisSummaryCard {
  id: string
  label: string
  value: string
  detail: string
  tone: 'neutral' | 'warning' | 'danger' | 'success'
}

export interface AnalysisCapacityMetric {
  id: string
  label: string
  value: number | null
  detail: string
}

export interface AnalysisReasonShare {
  reason: string
  count: number
  share: number
}

export interface AnalysisPartitionPressure {
  name: string
  pendingJobs: number
  runningJobs: number
  pendingCpu: number
  runningCpu: number
  schedulableCpu: number
  totalCpu: number
  status: 'stable' | 'hot' | 'congested'
}

export interface AnalysisWaitStats {
  samples: number
  medianMinutes: number | null
  p90Minutes: number | null
  averageMinutes: number | null
}

export interface ClusterAnalysisResult {
  score: number
  scoreLabel: string
  scoreSummary: string
  summaryCards: AnalysisSummaryCard[]
  capacityMetrics: AnalysisCapacityMetric[]
  topReasons: AnalysisReasonShare[]
  partitionPressure: AnalysisPartitionPressure[]
  recommendations: AnalysisRecommendation[]
  waitStats: AnalysisWaitStats
  latestPendingJobs: number
  latestRunningJobs: number
  pendingCpu: number
  runningCpu: number
  pendingGpu: number
  runningGpu: number
  cpuUtilization: number | null
  memoryUtilization: number | null
  gpuUtilization: number | null
  schedulableNodeRatio: number | null
  schedulableNodes: number
  totalNodes: number
  unavailableNodes: number
  unavailableCpu: number
  freeSchedulableCpu: number
  fragmentationJobs: number
  history: {
    latestPending: number | null
    peakPending: number | null
    averagePending: number | null
    latestRunning: number | null
    peakRunning: number | null
    peakBusyCores: number | null
    averageBusyCores: number | null
    peakAllocatedMemory: number | null
    peakBusyGpus: number | null
  }
}

export interface ClusterAnalysisInput {
  stats?: ClusterStats | null
  jobs?: ClusterJob[] | null
  nodes?: ClusterNode[] | null
  jobsMetrics?: Partial<Record<MetricJobState, MetricValue[]>> | null
  coreMetrics?: Partial<Record<MetricResourceState, MetricValue[]>> | null
  memoryMetrics?: Partial<Record<MetricMemoryState, MetricValue[]>> | null
  gpuMetrics?: Partial<Record<MetricResourceState, MetricValue[]>> | null
  historyJobs?: JobHistoryRecord[] | null
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function percent(value: number, total: number): number {
  if (!total) return 0
  return clamp((value / total) * 100, 0, 100)
}

function round(value: number, digits = 1): number {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

function countJobsInStates(jobs: ClusterJob[], states: readonly string[]): ClusterJob[] {
  return jobs.filter((job) => job.job_state.some((state) => states.includes(state)))
}

function sumRequestedCpu(jobs: ClusterJob[]): number {
  return jobs.reduce((total, job) => {
    if (!job.cpus.set || job.cpus.infinite) return total
    return total + job.cpus.number
  }, 0)
}

function sumRequestedGpu(jobs: ClusterJob[]): number {
  return jobs.reduce((total, job) => total + jobResourcesGPU(job).count, 0)
}

function buildReasonShares(jobs: ClusterJob[]): AnalysisReasonShare[] {
  const counts = new Map<string, number>()
  for (const job of jobs) {
    const reason = job.state_reason && job.state_reason !== 'None' ? job.state_reason : 'Unknown'
    counts.set(reason, (counts.get(reason) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([reason, count]) => ({
      reason,
      count,
      share: jobs.length ? count / jobs.length : 0
    }))
    .sort((left, right) => right.count - left.count)
}

function buildPartitionPressure(
  jobs: ClusterJob[],
  nodes: ClusterNode[]
): AnalysisPartitionPressure[] {
  const partitions = new Map<string, AnalysisPartitionPressure>()

  for (const node of nodes) {
    for (const partitionName of node.partitions) {
      if (!partitions.has(partitionName)) {
        partitions.set(partitionName, {
          name: partitionName,
          pendingJobs: 0,
          runningJobs: 0,
          pendingCpu: 0,
          runningCpu: 0,
          schedulableCpu: 0,
          totalCpu: 0,
          status: 'stable'
        })
      }
      const partition = partitions.get(partitionName)!
      partition.totalCpu += node.cpus
      if (getNodeMainState(node.state) === 'up') {
        partition.schedulableCpu += node.cpus
      }
    }
  }

  for (const job of jobs) {
    if (!partitions.has(job.partition)) {
      partitions.set(job.partition, {
        name: job.partition,
        pendingJobs: 0,
        runningJobs: 0,
        pendingCpu: 0,
        runningCpu: 0,
        schedulableCpu: 0,
        totalCpu: 0,
        status: 'stable'
      })
    }
    const partition = partitions.get(job.partition)!
    const jobCpu = job.cpus.set && !job.cpus.infinite ? job.cpus.number : 0
    if (job.job_state.includes('PENDING')) {
      partition.pendingJobs += 1
      partition.pendingCpu += jobCpu
    }
    if (job.job_state.includes('RUNNING') || job.job_state.includes('COMPLETING')) {
      partition.runningJobs += 1
      partition.runningCpu += jobCpu
    }
  }

  return [...partitions.values()]
    .map((partition) => {
      const pendingPressure =
        partition.schedulableCpu > 0 ? partition.pendingCpu / partition.schedulableCpu : 0
      const busyPressure =
        partition.schedulableCpu > 0 ? partition.runningCpu / partition.schedulableCpu : 0
      if (partition.pendingJobs > 0 && (pendingPressure > 0.4 || partition.pendingJobs > partition.runningJobs)) {
        partition.status = 'congested'
      } else if (busyPressure > 0.72 || partition.pendingJobs > 0) {
        partition.status = 'hot'
      } else {
        partition.status = 'stable'
      }
      return partition
    })
    .sort((left, right) => {
      if (right.pendingCpu !== left.pendingCpu) return right.pendingCpu - left.pendingCpu
      return right.pendingJobs - left.pendingJobs
    })
}

function extractTimeline<T extends string>(
  metrics: Partial<Record<T, MetricValue[]>> | null | undefined,
  states: readonly T[]
): number[] {
  if (!metrics) return []
  const maxLength = Math.max(0, ...states.map((state) => metrics[state]?.length ?? 0))
  return Array.from({ length: maxLength }, (_, index) =>
    states.reduce((total, state) => total + (metrics[state]?.[index]?.[1] ?? 0), 0)
  )
}

function latestValue(values: number[]): number | null {
  if (!values.length) return null
  return values[values.length - 1] ?? null
}

function peakValue(values: number[]): number | null {
  if (!values.length) return null
  return Math.max(...values)
}

function averageValue(values: number[]): number | null {
  if (!values.length) return null
  return values.reduce((total, value) => total + value, 0) / values.length
}

function computeWaitStats(historyJobs: JobHistoryRecord[] | null | undefined): AnalysisWaitStats {
  const waits = (historyJobs ?? [])
    .map((job) => {
      const start = job.start_time ? new Date(job.start_time).getTime() : NaN
      const eligible = job.eligible_time ? new Date(job.eligible_time).getTime() : NaN
      const submit = job.submit_time ? new Date(job.submit_time).getTime() : NaN
      const baseline = Number.isFinite(eligible) ? eligible : submit
      if (!Number.isFinite(start) || !Number.isFinite(baseline) || start < baseline) {
        return null
      }
      return (start - baseline) / 60000
    })
    .filter((value): value is number => value != null)
    .sort((left, right) => left - right)

  if (!waits.length) {
    return {
      samples: 0,
      medianMinutes: null,
      p90Minutes: null,
      averageMinutes: null
    }
  }

  const medianIndex = Math.floor((waits.length - 1) / 2)
  const p90Index = Math.floor((waits.length - 1) * 0.9)

  return {
    samples: waits.length,
    medianMinutes: round(waits[medianIndex], 1),
    p90Minutes: round(waits[p90Index], 1),
    averageMinutes: round(
      waits.reduce((total, value) => total + value, 0) / waits.length,
      1
    )
  }
}

function computeFragmentationJobs(
  pendingJobs: ClusterJob[],
  freeSchedulableCpu: number,
  maxFreeCpuOnNode: number
): number {
  return pendingJobs.filter((job) => {
    if (job.state_reason !== 'Resources') return false
    if (!job.cpus.set || job.cpus.infinite) return false
    if (!job.node_count.set || job.node_count.infinite || job.node_count.number !== 1) return false
    return freeSchedulableCpu >= job.cpus.number && maxFreeCpuOnNode < job.cpus.number
  }).length
}

function computeScoreLabel(score: number): string {
  if (score >= 85) return 'Efficient'
  if (score >= 70) return 'Stable'
  if (score >= 55) return 'Pressured'
  return 'Constrained'
}

function computeScoreSummary(
  scoreLabel: string,
  pendingJobs: number,
  unavailableNodes: number,
  fragmentationJobs: number
): string {
  if (scoreLabel === 'Efficient') {
    return 'Resources are well used and queue pressure is currently contained.'
  }
  if (unavailableNodes > 0) {
    return 'Cluster throughput is being reduced by unavailable capacity that should be recovered first.'
  }
  if (fragmentationJobs > 0) {
    return 'Idle capacity exists, but job shape and node packing are preventing fast starts.'
  }
  if (pendingJobs > 0) {
    return 'Backlog is building faster than the scheduler can admit work.'
  }
  return 'The cluster is operating steadily with limited queue friction.'
}

function buildRecommendations(input: {
  totalCpu: number
  unavailableNodes: number
  unavailableCpu: number
  pendingJobs: ClusterJob[]
  runningJobs: ClusterJob[]
  topReasons: AnalysisReasonShare[]
  fragmentationJobs: number
  cpuUtilization: number | null
  gpuUtilization: number | null
  pendingGpu: number
  waitStats: AnalysisWaitStats
  freeSchedulableCpu: number
}): AnalysisRecommendation[] {
  const recommendations: AnalysisRecommendation[] = []
  const pendingCount = input.pendingJobs.length
  const runningCount = input.runningJobs.length
  const queueRatio = runningCount > 0 ? pendingCount / runningCount : pendingCount
  const resourceReason = input.topReasons.find((reason) => reason.reason === 'Resources')
  const priorityReason = input.topReasons.find((reason) => reason.reason === 'Priority')

  if (input.unavailableNodes > 0 && input.unavailableCpu > 0) {
    recommendations.push({
      id: 'recover-capacity',
      title: 'Recover unavailable nodes before planning expansion',
      summary: 'The fastest capacity gain comes from returning drained or down nodes to service.',
      evidence: `${input.unavailableNodes} node(s) and ${input.unavailableCpu} CPU(s) are currently unavailable.`,
      tone: input.unavailableNodes > 1 ? 'danger' : 'warning'
    })
  }

  if (input.fragmentationJobs > 0) {
    recommendations.push({
      id: 'reduce-fragmentation',
      title: 'Mitigate CPU fragmentation for single-node jobs',
      summary:
        'Backfill smaller jobs, reduce oversized single-node requests or rebalance partitions to turn idle cores into admitted work.',
      evidence: `${input.fragmentationJobs} pending job(s) can fit in cluster-wide free CPU but not on any single schedulable node.`,
      tone: 'warning'
    })
  }

  if (
    resourceReason &&
    resourceReason.share >= 0.3 &&
    (input.cpuUtilization ?? 0) >= 70
  ) {
    recommendations.push({
      id: 'expand-busy-partitions',
      title: 'Expand or rebalance the busiest capacity pool',
      summary:
        'Resource-bound jobs dominate the queue while active capacity is already heavily occupied.',
      evidence: `${Math.round(resourceReason.share * 100)}% of pending jobs are blocked on resources at ${Math.round(input.cpuUtilization ?? 0)}% CPU occupancy.`,
      tone: 'danger'
    })
  }

  if (
    priorityReason &&
    priorityReason.share >= 0.25 &&
    (input.cpuUtilization ?? 0) < 75
  ) {
    recommendations.push({
      id: 'review-priority-policy',
      title: 'Review QOS and priority policy before adding hardware',
      summary:
        'Queue delay appears to be policy-bound rather than purely capacity-bound.',
      evidence: `${Math.round(priorityReason.share * 100)}% of pending jobs are blocked by priority while CPU occupancy is ${Math.round(input.cpuUtilization ?? 0)}%.`,
      tone: 'neutral'
    })
  }

  if (input.pendingGpu > 0 && (input.gpuUtilization ?? 0) >= 70) {
    recommendations.push({
      id: 'protect-gpu-throughput',
      title: 'Protect GPU throughput with tighter GPU queue classes',
      summary:
        'GPU demand is building while accelerator capacity is already hot.',
      evidence: `${input.pendingGpu} GPU(s) are requested by pending jobs and active GPU occupancy is ${Math.round(input.gpuUtilization ?? 0)}%.`,
      tone: 'warning'
    })
  }

  if (
    input.waitStats.medianMinutes != null &&
    input.waitStats.medianMinutes >= 15
  ) {
    recommendations.push({
      id: 'reduce-wait-time',
      title: 'Reduce queue wait with shorter walltime classes and backfill',
      summary:
        'Observed wait samples show users are spending meaningful time in queue before admission.',
      evidence: `Median sampled queue wait is ${input.waitStats.medianMinutes} min across ${input.waitStats.samples} completed jobs.`,
      tone: input.waitStats.medianMinutes >= 60 ? 'danger' : 'warning'
    })
  }

  if (recommendations.length < 3) {
    recommendations.push({
      id: 'keep-balance',
      title: 'Keep admission balanced across job sizes',
      summary:
        'Track partition pressure and promote smaller backfill windows to keep the cluster full without starving large jobs.',
      evidence: `${pendingCount} pending job(s), ${runningCount} active job(s) and ${input.freeSchedulableCpu} schedulable free CPU(s) are in play right now.`,
      tone: queueRatio > 1 ? 'warning' : 'success'
    })
  }

  return recommendations.slice(0, 4)
}

export function analyzeCluster(input: ClusterAnalysisInput): ClusterAnalysisResult {
  const jobs = input.jobs ?? []
  const nodes = input.nodes ?? []
  const pendingJobs = countJobsInStates(jobs, pendingJobStates)
  const runningJobs = countJobsInStates(jobs, activeJobStates)
  const topReasons = buildReasonShares(pendingJobs)
  const waitStats = computeWaitStats(input.historyJobs)

  const totalCpuFromNodes = nodes.reduce((total, node) => total + node.cpus, 0)
  const totalCpu = totalCpuFromNodes || input.stats?.resources.cores || 0
  const allocatedCpu = nodes.reduce((total, node) => total + node.alloc_cpus, 0)
  const totalNodes = nodes.length || input.stats?.resources.nodes || 0
  const schedulableNodes = nodes.filter((node) => getNodeMainState(node.state) === 'up').length
  const unavailableNodes = Math.max(totalNodes - schedulableNodes, 0)
  const unavailableCpu = nodes
    .filter((node) => getNodeMainState(node.state) !== 'up')
    .reduce((total, node) => total + node.cpus, 0)
  const freeSchedulableCpu = nodes
    .filter((node) => getNodeMainState(node.state) === 'up')
    .reduce((total, node) => total + Math.max(node.cpus - node.alloc_cpus, 0), 0)
  const maxFreeCpuOnNode = nodes
    .filter((node) => getNodeMainState(node.state) === 'up')
    .reduce((current, node) => Math.max(current, Math.max(node.cpus - node.alloc_cpus, 0)), 0)
  const fragmentationJobs = computeFragmentationJobs(
    pendingJobs,
    freeSchedulableCpu,
    maxFreeCpuOnNode
  )

  const totalMemory = input.stats?.resources.memory ?? nodes.reduce((total, node) => total + node.real_memory, 0)
  const memoryAllocated =
    input.stats?.resources.memory_allocated ??
    (input.stats?.resources.memory_available != null
      ? input.stats.resources.memory - input.stats.resources.memory_available
      : null)
  const totalGpu = input.stats?.resources.gpus ?? 0
  const pendingCpu = sumRequestedCpu(pendingJobs)
  const runningCpu = sumRequestedCpu(runningJobs)
  const pendingGpu = sumRequestedGpu(pendingJobs)
  const runningGpu = sumRequestedGpu(runningJobs)

  const cpuUtilization =
    totalCpu > 0 ? percent(allocatedCpu || runningCpu, totalCpu) : null
  const memoryUtilization =
    memoryAllocated != null && totalMemory > 0 ? percent(memoryAllocated, totalMemory) : null
  const gpuUtilization = totalGpu > 0 ? percent(runningGpu, totalGpu) : null
  const schedulableNodeRatio = totalNodes > 0 ? percent(schedulableNodes, totalNodes) : null

  const pendingTimeline = extractTimeline(input.jobsMetrics, ['pending'])
  const runningTimeline = extractTimeline(input.jobsMetrics, ['running'])
  const busyCoresTimeline = extractTimeline(input.coreMetrics, busyResourceStates)
  const allocatedMemoryTimeline = extractTimeline(input.memoryMetrics, ['allocated'])
  const busyGpuTimeline = extractTimeline(input.gpuMetrics, busyResourceStates)

  let score = 100
  const queueRatio = runningJobs.length > 0 ? pendingJobs.length / runningJobs.length : pendingJobs.length
  if (cpuUtilization != null) {
    if (cpuUtilization < 35) score -= 16
    else if (cpuUtilization < 55) score -= 8
    else if (cpuUtilization > 92) score -= 5
  }
  if (queueRatio > 4) score -= 24
  else if (queueRatio > 2) score -= 16
  else if (queueRatio > 1) score -= 8
  if (schedulableNodeRatio != null) {
    if (schedulableNodeRatio < 70) score -= 18
    else if (schedulableNodeRatio < 85) score -= 9
  }
  if (fragmentationJobs > 0) score -= Math.min(12, fragmentationJobs * 3)
  if (waitStats.medianMinutes != null) {
    if (waitStats.medianMinutes >= 60) score -= 16
    else if (waitStats.medianMinutes >= 20) score -= 8
  }
  score = clamp(Math.round(score), 25, 97)
  const scoreLabel = computeScoreLabel(score)
  const scoreSummary = computeScoreSummary(
    scoreLabel,
    pendingJobs.length,
    unavailableNodes,
    fragmentationJobs
  )

  const summaryCards: AnalysisSummaryCard[] = [
    {
      id: 'cpu-occupancy',
      label: 'CPU occupancy',
      value: cpuUtilization != null ? `${Math.round(cpuUtilization)}%` : '--',
      detail:
        totalCpu > 0
          ? `${allocatedCpu || runningCpu} of ${totalCpu} CPU(s) are currently busy.`
          : 'CPU occupancy is not available.',
      tone:
        cpuUtilization == null
          ? 'neutral'
          : cpuUtilization >= 75
            ? 'success'
            : cpuUtilization >= 55
              ? 'neutral'
              : 'warning'
    },
    {
      id: 'queue-pressure',
      label: 'Queue pressure',
      value: pendingJobs.length ? `${round(queueRatio, 1)}x` : 'Low',
      detail: `${pendingJobs.length} pending job(s) versus ${runningJobs.length} active job(s).`,
      tone: pendingJobs.length === 0 ? 'success' : queueRatio > 2 ? 'danger' : queueRatio > 1 ? 'warning' : 'neutral'
    },
    {
      id: 'wait-sample',
      label: 'Queue wait',
      value: waitStats.medianMinutes != null ? `${waitStats.medianMinutes} min` : 'Proxy',
      detail:
        waitStats.samples > 0
          ? `Median wait from ${waitStats.samples} recent completed jobs.`
          : 'Using live backlog as the queue delay proxy because history samples are unavailable.',
      tone:
        waitStats.medianMinutes == null
          ? 'neutral'
          : waitStats.medianMinutes >= 60
            ? 'danger'
            : waitStats.medianMinutes >= 20
              ? 'warning'
              : 'success'
    },
    {
      id: 'capacity-recovery',
      label: 'Recovery potential',
      value: unavailableCpu > 0 ? `${unavailableCpu} CPU` : `${freeSchedulableCpu} CPU`,
      detail:
        unavailableCpu > 0
          ? 'Recovering unavailable capacity will immediately increase admission throughput.'
          : 'Schedulable free CPU currently available for backfill and smaller jobs.',
      tone: unavailableCpu > 0 ? 'warning' : 'success'
    }
  ]

  const capacityMetrics: AnalysisCapacityMetric[] = [
    {
      id: 'cpu',
      label: 'CPU busy',
      value: cpuUtilization,
      detail:
        totalCpu > 0
          ? `${allocatedCpu || runningCpu}/${totalCpu} CPU(s) allocated or requested by active jobs.`
          : 'CPU totals are unavailable.'
    },
    {
      id: 'memory',
      label: 'Memory committed',
      value: memoryUtilization,
      detail:
        memoryAllocated != null && totalMemory > 0
          ? `${memoryAllocated} MB committed out of ${totalMemory} MB.`
          : 'Memory commitment is unavailable in current telemetry.'
    },
    {
      id: 'gpu',
      label: 'GPU busy',
      value: totalGpu > 0 ? gpuUtilization : null,
      detail:
        totalGpu > 0
          ? `${runningGpu}/${totalGpu} GPU(s) are actively in use.`
          : 'No GPU capacity is declared for this cluster.'
    },
    {
      id: 'nodes',
      label: 'Schedulable nodes',
      value: schedulableNodeRatio,
      detail:
        totalNodes > 0
          ? `${schedulableNodes}/${totalNodes} node(s) are currently schedulable.`
          : 'Node inventory is unavailable.'
    }
  ]

  const recommendations = buildRecommendations({
    totalCpu,
    unavailableNodes,
    unavailableCpu,
    pendingJobs,
    runningJobs,
    topReasons,
    fragmentationJobs,
    cpuUtilization,
    gpuUtilization,
    pendingGpu,
    waitStats,
    freeSchedulableCpu
  })

  return {
    score,
    scoreLabel,
    scoreSummary,
    summaryCards,
    capacityMetrics,
    topReasons: topReasons.slice(0, 5),
    partitionPressure: buildPartitionPressure(jobs, nodes).slice(0, 6),
    recommendations,
    waitStats,
    latestPendingJobs: pendingJobs.length,
    latestRunningJobs: runningJobs.length,
    pendingCpu,
    runningCpu,
    pendingGpu,
    runningGpu,
    cpuUtilization,
    memoryUtilization,
    gpuUtilization,
    schedulableNodeRatio,
    schedulableNodes,
    totalNodes,
    unavailableNodes,
    unavailableCpu,
    freeSchedulableCpu,
    fragmentationJobs,
    history: {
      latestPending: latestValue(pendingTimeline),
      peakPending: peakValue(pendingTimeline),
      averagePending: averageValue(pendingTimeline),
      latestRunning: latestValue(runningTimeline),
      peakRunning: peakValue(runningTimeline),
      peakBusyCores: peakValue(busyCoresTimeline),
      averageBusyCores: averageValue(busyCoresTimeline),
      peakAllocatedMemory: peakValue(allocatedMemoryTimeline),
      peakBusyGpus: peakValue(busyGpuTimeline)
    }
  }
}
