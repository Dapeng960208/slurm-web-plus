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
import { translate } from '@/i18n/translate'

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
  locale?: string
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

function formatMemoryGb(valueMb: number): string {
  return `${round(valueMb / 1024, 1)} GB`
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
  if (score >= 85) return translate('pages.analysis.status.efficient')
  if (score >= 70) return translate('pages.analysis.status.stable')
  if (score >= 55) return translate('pages.analysis.status.pressured')
  return translate('pages.analysis.status.constrained')
}

function computeScoreSummary(
  scoreLabel: string,
  pendingJobs: number,
  unavailableNodes: number,
  fragmentationJobs: number
): string {
  if (scoreLabel === translate('pages.analysis.status.efficient')) {
    return translate('analysis.scoreSummary.efficient')
  }
  if (unavailableNodes > 0) {
    return translate('analysis.scoreSummary.recoverCapacity')
  }
  if (fragmentationJobs > 0) {
    return translate('analysis.scoreSummary.fragmentation')
  }
  if (pendingJobs > 0) {
    return translate('analysis.scoreSummary.backlog')
  }
  return translate('analysis.scoreSummary.steady')
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
      title: translate('analysis.recommendations.recoverCapacity.title'),
      summary: translate('analysis.recommendations.recoverCapacity.summary'),
      evidence: translate('analysis.recommendations.recoverCapacity.evidence', {
        nodes: input.unavailableNodes,
        cpu: input.unavailableCpu
      }),
      tone: input.unavailableNodes > 1 ? 'danger' : 'warning'
    })
  }

  if (input.fragmentationJobs > 0) {
    recommendations.push({
      id: 'reduce-fragmentation',
      title: translate('analysis.recommendations.fragmentation.title'),
      summary: translate('analysis.recommendations.fragmentation.summary'),
      evidence: translate('analysis.recommendations.fragmentation.evidence', {
        count: input.fragmentationJobs
      }),
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
      title: translate('analysis.recommendations.expandBusy.title'),
      summary: translate('analysis.recommendations.expandBusy.summary'),
      evidence: translate('analysis.recommendations.expandBusy.evidence', {
        share: Math.round(resourceReason.share * 100),
        cpu: Math.round(input.cpuUtilization ?? 0)
      }),
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
      title: translate('analysis.recommendations.priority.title'),
      summary: translate('analysis.recommendations.priority.summary'),
      evidence: translate('analysis.recommendations.priority.evidence', {
        share: Math.round(priorityReason.share * 100),
        cpu: Math.round(input.cpuUtilization ?? 0)
      }),
      tone: 'neutral'
    })
  }

  if (input.pendingGpu > 0 && (input.gpuUtilization ?? 0) >= 70) {
    recommendations.push({
      id: 'protect-gpu-throughput',
      title: translate('analysis.recommendations.gpu.title'),
      summary: translate('analysis.recommendations.gpu.summary'),
      evidence: translate('analysis.recommendations.gpu.evidence', {
        gpu: input.pendingGpu,
        occupancy: Math.round(input.gpuUtilization ?? 0)
      }),
      tone: 'warning'
    })
  }

  if (
    input.waitStats.medianMinutes != null &&
    input.waitStats.medianMinutes >= 15
  ) {
    recommendations.push({
      id: 'reduce-wait-time',
      title: translate('analysis.recommendations.waitTime.title'),
      summary: translate('analysis.recommendations.waitTime.summary'),
      evidence: translate('analysis.recommendations.waitTime.evidence', {
        minutes: input.waitStats.medianMinutes,
        samples: input.waitStats.samples
      }),
      tone: input.waitStats.medianMinutes >= 60 ? 'danger' : 'warning'
    })
  }

  if (recommendations.length < 3) {
    recommendations.push({
      id: 'keep-balance',
      title: translate('analysis.recommendations.balance.title'),
      summary: translate('analysis.recommendations.balance.summary'),
      evidence: translate('analysis.recommendations.balance.evidence', {
        pending: pendingCount,
        running: runningCount,
        cpu: input.freeSchedulableCpu
      }),
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
      label: translate('analysis.summary.cpuOccupancy.label'),
      value: cpuUtilization != null ? `${Math.round(cpuUtilization)}%` : '--',
      detail:
        totalCpu > 0
          ? translate('analysis.summary.cpuOccupancy.detail', {
              busy: allocatedCpu || runningCpu,
              total: totalCpu
            })
          : translate('analysis.summary.cpuOccupancy.unavailable'),
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
      label: translate('analysis.summary.queuePressure.label'),
      value: pendingJobs.length ? `${round(queueRatio, 1)}x` : translate('analysis.summary.queuePressure.low'),
      detail: translate('analysis.summary.queuePressure.detail', {
        pending: pendingJobs.length,
        running: runningJobs.length
      }),
      tone: pendingJobs.length === 0 ? 'success' : queueRatio > 2 ? 'danger' : queueRatio > 1 ? 'warning' : 'neutral'
    },
    {
      id: 'wait-sample',
      label: translate('analysis.summary.waitSample.label'),
      value:
        waitStats.medianMinutes != null
          ? translate('analysis.summary.waitSample.value', { minutes: waitStats.medianMinutes })
          : translate('analysis.summary.waitSample.proxy'),
      detail:
        waitStats.samples > 0
          ? translate('analysis.summary.waitSample.detail', { samples: waitStats.samples })
          : translate('analysis.summary.waitSample.fallback'),
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
      label: translate('analysis.summary.recovery.label'),
      value: unavailableCpu > 0 ? `${unavailableCpu} CPU` : `${freeSchedulableCpu} CPU`,
      detail:
        unavailableCpu > 0
          ? translate('analysis.summary.recovery.unavailable')
          : translate('analysis.summary.recovery.available'),
      tone: unavailableCpu > 0 ? 'warning' : 'success'
    }
  ]

  const capacityMetrics: AnalysisCapacityMetric[] = [
    {
      id: 'cpu',
      label: translate('analysis.capacity.cpu.label'),
      value: cpuUtilization,
      detail:
        totalCpu > 0
          ? translate('analysis.capacity.cpu.detail', {
              busy: allocatedCpu || runningCpu,
              total: totalCpu
            })
          : translate('analysis.capacity.cpu.unavailable')
    },
    {
      id: 'memory',
      label: translate('analysis.capacity.memory.label'),
      value: memoryUtilization,
      detail:
        memoryAllocated != null && totalMemory > 0
          ? translate('analysis.capacity.memory.detail', {
              committed: formatMemoryGb(memoryAllocated),
              total: formatMemoryGb(totalMemory)
            })
          : translate('analysis.capacity.memory.unavailable')
    },
    {
      id: 'gpu',
      label: translate('analysis.capacity.gpu.label'),
      value: totalGpu > 0 ? gpuUtilization : null,
      detail:
        totalGpu > 0
          ? translate('analysis.capacity.gpu.detail', {
              running: runningGpu,
              total: totalGpu
            })
          : translate('analysis.capacity.gpu.unavailable')
    },
    {
      id: 'nodes',
      label: translate('analysis.capacity.nodes.label'),
      value: schedulableNodeRatio,
      detail:
        totalNodes > 0
          ? translate('analysis.capacity.nodes.detail', {
              schedulable: schedulableNodes,
              total: totalNodes
            })
          : translate('analysis.capacity.nodes.unavailable')
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
