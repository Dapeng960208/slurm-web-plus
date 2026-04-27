<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PageHeader from '@/components/PageHeader.vue'
import PercentMetric from '@/components/PercentMetric.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import { analyzeCluster } from '@/composables/ClusterAnalysis'
import { formatPercentValue } from '@/composables/percentages'
import {
  isMetricRange,
  type ClusterJob,
  type ClusterNode,
  type ClusterStats,
  type JobHistoryRecord,
  type MetricJobState,
  type MetricMemoryState,
  type MetricRange,
  type MetricResourceState,
  type MetricValue,
  useGatewayAPI
} from '@/composables/GatewayAPI'
import { extractSummaryCards, extractSummaryFields } from '@/composables/structuredDisplay'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster } = defineProps<{ cluster: string }>()

const router = useRouter()
const route = useRoute()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

const selectedRange = ref<MetricRange>('hour')
const loading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
const updatedAt = ref<string | null>(null)

const stats = ref<ClusterStats | null>(null)
const jobs = ref<ClusterJob[]>([])
const nodes = ref<ClusterNode[]>([])
const jobsMetrics = ref<Partial<Record<MetricJobState, MetricValue[]>> | null>(null)
const coreMetrics = ref<Partial<Record<MetricResourceState, MetricValue[]>> | null>(null)
const memoryMetrics = ref<Partial<Record<MetricMemoryState, MetricValue[]>> | null>(null)
const gpuMetrics = ref<Partial<Record<MetricResourceState, MetricValue[]>> | null>(null)
const historyJobs = ref<JobHistoryRecord[]>([])
const pingDetails = ref<unknown>(null)
const diagDetails = ref<unknown>(null)

const jobsUnavailable = ref(false)
const nodesUnavailable = ref(false)
const metricsUnavailable = ref(false)
const waitSamplesUnavailable = ref(false)
const pingUnavailable = ref(false)
const diagUnavailable = ref(false)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const clusterDetails = computed(() => runtimeStore.getCluster(cluster))
const metricsEnabled = computed(() => Boolean(clusterDetails.value?.metrics))
const persistenceEnabled = computed(() => Boolean(clusterDetails.value?.persistence))
const canViewJobs = computed(() => runtimeStore.hasRoutePermission(cluster, 'jobs', 'view'))
const canViewNodes = computed(() => runtimeStore.hasRoutePermission(cluster, 'resources', 'view'))
const canViewHistory = computed(
  () => persistenceEnabled.value && runtimeStore.hasRoutePermission(cluster, 'jobs-history', 'view')
)
const canViewResources = computed(() => runtimeStore.hasRoutePermission(cluster, 'resources', 'view'))

const analysis = computed(() =>
  analyzeCluster({
    stats: stats.value,
    jobs: canViewJobs.value ? jobs.value : [],
    nodes: canViewNodes.value ? nodes.value : [],
    jobsMetrics: jobsMetrics.value,
    coreMetrics: coreMetrics.value,
    memoryMetrics: memoryMetrics.value,
    gpuMetrics: gpuMetrics.value,
    historyJobs: historyJobs.value
  })
)

const updatedAtLabel = computed(() => {
  if (!updatedAt.value) return null
  return new Date(updatedAt.value).toLocaleString()
})
const pingCards = computed(() =>
  extractSummaryCards(pingDetails.value, {
    listKeys: ['pings'],
    titleKeys: ['hostname', 'host', 'name'],
    badgeKeys: ['mode'],
    preferredOrder: ['hostname', 'mode', 'latency_ms', 'status'],
    labelMap: {
      latency_ms: 'Latency (ms)'
    },
    fallbackTitle: 'Controller'
  })
)
const diagFields = computed(() => {
  const statistics =
    diagDetails.value &&
    typeof diagDetails.value === 'object' &&
    !Array.isArray(diagDetails.value) &&
    'statistics' in diagDetails.value
      ? (diagDetails.value as Record<string, unknown>).statistics
      : diagDetails.value
  return extractSummaryFields(statistics, {
    preferredOrder: [
      'jobs_submitted',
      'jobs_started',
      'jobs_completed',
      'jobs_canceled',
      'schedule_cycle_last',
      'schedule_cycle_max',
      'schedule_cycle_mean'
    ],
    labelMap: {
      jobs_submitted: 'Jobs Submitted',
      jobs_started: 'Jobs Started',
      jobs_completed: 'Jobs Completed',
      jobs_canceled: 'Jobs Canceled',
      schedule_cycle_last: 'Schedule Cycle Last',
      schedule_cycle_max: 'Schedule Cycle Max',
      schedule_cycle_mean: 'Schedule Cycle Mean'
    }
  })
})

const historicalCards = computed(() => {
  const busyCoresDetail =
    analysis.value.history.averageBusyCores != null && stats.value?.resources.cores
      ? `${formatPercentValue(percent(analysis.value.history.averageBusyCores, stats.value.resources.cores), 0)}% average of declared CPU capacity`
      : 'CPU history unavailable'

  return [
    {
      id: 'peak-pending',
      label: 'Peak pending',
      value: renderNumber(analysis.value.history.peakPending, 'jobs'),
      detail: 'Largest queued backlog in the selected telemetry range.'
    },
    {
      id: 'avg-pending',
      label: 'Average pending',
      value: renderNumber(analysis.value.history.averagePending, 'jobs'),
      detail: 'Average queue depth across the selected range.'
    },
    {
      id: 'peak-running',
      label: 'Peak running',
      value: renderNumber(analysis.value.history.peakRunning, 'jobs'),
      detail: 'Maximum concurrently running jobs observed in range.'
    },
    {
      id: 'busy-cores',
      label: 'Peak busy cores',
      value: renderNumber(analysis.value.history.peakBusyCores, 'cores'),
      detail: busyCoresDetail
    }
  ]
})

function percent(value: number, total: number): number {
  if (!total) return 0
  return (value / total) * 100
}

function renderNumber(value: number | null, suffix = ''): string {
  if (value == null) return '--'
  const rounded = value >= 100 ? Math.round(value) : Math.round(value * 10) / 10
  return suffix ? `${rounded} ${suffix}` : String(rounded)
}

function renderRange(range: MetricRange) {
  selectedRange.value = range
  router.push({
    name: 'analysis',
    params: { cluster },
    query: { range } as LocationQueryRaw
  })
}

function rangeStartISO(range: MetricRange): string {
  const now = Date.now()
  const duration = {
    hour: 60 * 60 * 1000,
    day: 24 * 60 * 60 * 1000,
    week: 7 * 24 * 60 * 60 * 1000
  }[range]
  return new Date(now - duration).toISOString()
}

async function loadAnalysis() {
  refreshing.value = !loading.value
  error.value = null
  jobsUnavailable.value = false
  nodesUnavailable.value = false
  metricsUnavailable.value = false
  waitSamplesUnavailable.value = false
  pingUnavailable.value = false
  diagUnavailable.value = false

  try {
    const statsResult = await gateway.stats(cluster)
    stats.value = statsResult
  } catch (caughtError: unknown) {
    error.value = caughtError instanceof Error ? caughtError.message : String(caughtError)
    loading.value = false
    refreshing.value = false
    return
  }

  const tasks: Promise<void>[] = []

  if (canViewJobs.value) {
    tasks.push(
      gateway
        .jobs(cluster)
        .then((payload) => {
          jobs.value = payload
        })
        .catch(() => {
          jobs.value = []
          jobsUnavailable.value = true
        })
    )
  }

  if (canViewNodes.value) {
    tasks.push(
      gateway
        .nodes(cluster)
        .then((payload) => {
          nodes.value = payload
        })
        .catch(() => {
          nodes.value = []
          nodesUnavailable.value = true
        })
    )
  }

  if (metricsEnabled.value) {
    const metricsTasks: Promise<unknown>[] = []
    if (canViewJobs.value) {
      metricsTasks.push(
        gateway.metrics_jobs(cluster, selectedRange.value).then((payload) => {
          jobsMetrics.value = payload
        })
      )
    }
    if (canViewNodes.value) {
      metricsTasks.push(
        gateway.metrics_cores(cluster, selectedRange.value).then((payload) => {
          coreMetrics.value = payload
        })
      )
      metricsTasks.push(
        gateway.metrics_memory(cluster, selectedRange.value).then((payload) => {
          memoryMetrics.value = payload
        })
      )
      metricsTasks.push(
        gateway.metrics_gpus(cluster, selectedRange.value).then((payload) => {
          gpuMetrics.value = payload
        })
      )
    }

    tasks.push(
      Promise.all(metricsTasks)
        .then(() => undefined)
        .catch(() => {
          jobsMetrics.value = null
          coreMetrics.value = null
          memoryMetrics.value = null
          gpuMetrics.value = null
          metricsUnavailable.value = true
        })
    )
  } else {
    jobsMetrics.value = null
    coreMetrics.value = null
    memoryMetrics.value = null
    gpuMetrics.value = null
  }

  if (canViewHistory.value) {
    tasks.push(
      gateway
        .jobs_history(cluster, {
          state: 'COMPLETED',
          sort: 'submit_time',
          order: 'desc',
          page: 1,
          page_size: 200,
          start: rangeStartISO(selectedRange.value)
        })
        .then((payload) => {
          historyJobs.value = payload.jobs
        })
        .catch(() => {
          historyJobs.value = []
          waitSamplesUnavailable.value = true
        })
    )
  } else {
    historyJobs.value = []
  }

  tasks.push(
    gateway
      .analysis_ping(cluster)
      .then((payload) => {
        pingDetails.value = payload
      })
      .catch(() => {
        pingDetails.value = null
        pingUnavailable.value = true
      })
  )

  tasks.push(
    gateway
      .analysis_diag(cluster)
      .then((payload) => {
        diagDetails.value = payload
      })
      .catch(() => {
        diagDetails.value = null
        diagUnavailable.value = true
      })
  )

  await Promise.all(tasks)
  updatedAt.value = new Date().toISOString()
  loading.value = false
  refreshing.value = false
}

function startPolling() {
  stopPolling()
  refreshTimer = setInterval(() => {
    void loadAnalysis()
  }, 60000)
}

function stopPolling() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

watch(
  () => route.query.range,
  () => {
    if (route.query.range && isMetricRange(route.query.range)) {
      selectedRange.value = route.query.range
    } else {
      selectedRange.value = 'hour'
    }
  },
  { immediate: true }
)

watch(
  () => `${cluster}/${selectedRange.value}`,
  () => {
    loading.value = true
    void loadAnalysis()
    startPolling()
  },
  { immediate: true }
)

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <ClusterMainLayout menu-entry="analysis" :cluster="cluster" :breadcrumb="[{ title: 'Analysis' }]">
    <div class="ui-page ui-page-wide">
      <PageHeader
        kicker="Capacity Analysis"
        title="Cluster Efficiency"
        :description="analysis.scoreSummary"
        :metric-value="loading ? undefined : `${analysis.score}/100`"
        metric-label="operational score"
      >
        <template #actions>
          <div class="flex flex-wrap gap-3">
            <RouterLink :to="{ name: 'dashboard', params: { cluster } }" class="ui-button-secondary">
              Live dashboard
            </RouterLink>
            <RouterLink
              v-if="canViewJobs"
              :to="{ name: 'jobs', params: { cluster } }"
              class="ui-button-primary"
            >
              Inspect queue
            </RouterLink>
            <RouterLink
              v-if="canViewResources"
              :to="{ name: 'resources', params: { cluster } }"
              class="ui-button-secondary"
            >
              Open resources
            </RouterLink>
          </div>
        </template>
      </PageHeader>

      <ErrorAlert v-if="error">{{ error }}</ErrorAlert>

      <template v-else-if="loading">
        <div class="ui-panel ui-section">
          <div class="flex items-center gap-3 text-[var(--color-brand-muted)]">
            <LoadingSpinner :size="4" />
            Building the cluster analysis workspace...
          </div>
        </div>
      </template>

      <template v-else>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap gap-2">
            <span class="ui-chip">Status: {{ analysis.scoreLabel }}</span>
            <span v-if="updatedAtLabel" class="ui-chip">Updated {{ updatedAtLabel }}</span>
            <span v-if="refreshing" class="ui-chip">Refreshing</span>
          </div>

          <MetricRangeSelector
            :model-value="selectedRange"
            aria-label="Select cluster analysis range"
            @update:model-value="renderRange"
          />
        </div>

        <div class="ui-summary-strip">
          <div v-for="card in analysis.summaryCards" :key="card.id" class="ui-summary-item">
            <div class="ui-summary-label">{{ card.label }}</div>
            <div class="ui-summary-value">{{ card.value }}</div>
            <div class="ui-summary-subtle">{{ card.detail }}</div>
          </div>
        </div>

        <div class="grid gap-6 xl:grid-cols-[minmax(0,1.18fr)_minmax(320px,0.82fr)]">
          <section class="ui-panel ui-section">
            <div class="mb-4">
              <h2 class="ui-panel-title">Capacity Envelope</h2>
              <p class="ui-panel-description mt-2">
                Current utilization and schedulable headroom across the cluster.
              </p>
            </div>

            <div class="space-y-4">
              <div
                v-for="metric in analysis.capacityMetrics"
                :key="metric.id"
                class="ui-analysis-meter"
              >
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="ui-stat-label">{{ metric.label }}</div>
                    <div class="mt-2 text-sm text-[var(--color-brand-muted)]">
                      {{ metric.detail }}
                    </div>
                  </div>
                  <div class="text-right">
                    <PercentMetric :value="metric.value" :maximum-fraction-digits="0" />
                  </div>
                </div>
                <div class="ui-analysis-meter-track">
                  <div
                    class="ui-analysis-meter-fill"
                    :style="{ width: `${metric.value ?? 0}%` }"
                  />
                </div>
              </div>
            </div>
          </section>

          <section class="ui-panel ui-section">
            <div class="mb-4">
              <h2 class="ui-panel-title">Queue Blockers</h2>
              <p class="ui-panel-description mt-2">
                Why jobs are waiting, and whether the queue is blocked by capacity, policy or packing.
              </p>
            </div>

            <div class="space-y-3">
              <div v-if="!canViewJobs" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
                Job visibility is required to analyze queue blockers.
              </div>
              <div v-else-if="jobsUnavailable" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
                Job queue data is currently unavailable.
              </div>
              <div
                v-else-if="analysis.topReasons.length === 0"
                class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]"
              >
                No pending jobs are currently blocking the queue.
              </div>
              <div v-for="reason in analysis.topReasons" :key="reason.reason" class="ui-analysis-reason">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ reason.reason }}
                    </div>
                    <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
                      {{ reason.count }} pending job(s)
                    </div>
                  </div>
                  <PercentMetric
                    :value="Math.round(reason.share * 100)"
                    size="sm"
                    :maximum-fraction-digits="0"
                  />
                </div>
                <div class="ui-analysis-meter-track mt-3">
                  <div
                    class="ui-analysis-meter-fill"
                    :style="{ width: `${Math.round(reason.share * 100)}%` }"
                  />
                </div>
              </div>

              <div class="ui-panel-soft px-4 py-4">
                <div class="ui-stat-label">Packing signal</div>
                <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
                  {{ analysis.fragmentationJobs }}
                </div>
                <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                  pending single-node job(s) appear blocked by fragmentation while
                  {{ analysis.freeSchedulableCpu }} schedulable CPU(s) remain free.
                </div>
              </div>
            </div>
          </section>
        </div>

        <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.92fr)]">
          <section class="ui-panel ui-section">
            <div class="mb-4">
              <h2 class="ui-panel-title">Partition Hotspots</h2>
              <p class="ui-panel-description mt-2">
                Partition-level pressure helps decide whether to expand hardware, rebalance jobs or adjust QOS.
              </p>
            </div>

            <div v-if="!canViewJobs || !canViewNodes" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
              Both job and node visibility are required for partition pressure analysis.
            </div>
            <div v-else-if="analysis.partitionPressure.length === 0" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
              No partition-level pressure is currently visible.
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="partition in analysis.partitionPressure"
                :key="partition.name"
                class="ui-analysis-partition"
              >
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ partition.name }}
                    </div>
                    <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
                      {{ partition.pendingJobs }} pending, {{ partition.runningJobs }} active
                    </div>
                  </div>
                  <span class="ui-chip">CPU {{ partition.runningCpu }}/{{ partition.schedulableCpu || partition.totalCpu }}</span>
                </div>
                <div class="mt-3 grid gap-2 text-sm text-[var(--color-brand-muted)] sm:grid-cols-3">
                  <div>Pending CPU: {{ partition.pendingCpu }}</div>
                  <div>Total CPU: {{ partition.totalCpu }}</div>
                  <div>Schedulable CPU: {{ partition.schedulableCpu }}</div>
                </div>
              </div>
            </div>
          </section>

          <section class="ui-panel ui-section">
            <div class="mb-4">
              <h2 class="ui-panel-title">Historical Pressure</h2>
              <p class="ui-panel-description mt-2">
                Fast historical snapshots show whether capacity pressure is steady, bursty or policy-driven.
              </p>
            </div>

            <InfoAlert v-if="!metricsEnabled">
              Metrics collection is disabled for this cluster. Live analysis remains available.
            </InfoAlert>
            <InfoAlert v-else-if="metricsUnavailable">
              Historical metrics are temporarily unavailable.
            </InfoAlert>
            <div v-else class="grid gap-3 sm:grid-cols-2">
              <div v-for="card in historicalCards" :key="card.id" class="ui-panel-soft px-4 py-3">
                <div class="ui-stat-label">{{ card.label }}</div>
                <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
                  {{ card.value }}
                </div>
                <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                  {{ card.detail }}
                </div>
              </div>
            </div>

            <div class="mt-4 space-y-3">
              <div class="ui-panel-soft px-4 py-3">
                <div class="ui-stat-label">Latest telemetry</div>
                <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ renderNumber(analysis.history.latestPending, 'pending') }} /
                  {{ renderNumber(analysis.history.latestRunning, 'running') }}
                </div>
                <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                  Jobs at the most recent metric sample in the selected range.
                </div>
              </div>

              <div class="ui-panel-soft px-4 py-3">
                <div class="ui-stat-label">Wait samples</div>
                <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                  {{
                    analysis.waitStats.medianMinutes == null
                      ? '--'
                      : `${analysis.waitStats.medianMinutes} min median`
                  }}
                </div>
                <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                  <template v-if="analysis.waitStats.samples > 0">
                    p90 {{ analysis.waitStats.p90Minutes }} min from {{ analysis.waitStats.samples }}
                    recent completed jobs.
                  </template>
                  <template v-else-if="waitSamplesUnavailable">
                    Job history samples are unavailable for this cluster or time range.
                  </template>
                  <template v-else>
                    Historical wait samples are not enabled on this cluster.
                  </template>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section class="ui-panel ui-section">
          <div class="mb-4">
            <h2 class="ui-panel-title">Recommended Actions</h2>
            <p class="ui-panel-description mt-2">
              The list below is generated from live telemetry to help reduce queue time and increase job throughput.
            </p>
          </div>

          <div class="grid gap-4 xl:grid-cols-3">
            <article
              v-for="recommendation in analysis.recommendations"
              :key="recommendation.id"
              class="ui-analysis-recommendation"
            >
              <div class="ui-stat-label">{{ recommendation.tone }}</div>
              <h3 class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                {{ recommendation.title }}
              </h3>
              <p class="mt-3 text-sm leading-6 text-[var(--color-brand-muted)]">
                {{ recommendation.summary }}
              </p>
              <p class="mt-4 border-t border-[rgba(80,105,127,0.12)] pt-4 text-sm leading-6 text-[var(--color-brand-blue)]">
                {{ recommendation.evidence }}
              </p>
            </article>
          </div>
        </section>

        <section class="ui-panel ui-section">
          <div class="mb-4">
            <h2 class="ui-panel-title">Controller Health</h2>
            <p class="ui-panel-description mt-2">
              Lightweight controller status checks from the Slurm `ping` and `diag` endpoints.
            </p>
          </div>

          <div class="grid gap-4 xl:grid-cols-2">
            <article class="ui-panel-soft px-4 py-4">
              <div class="flex items-center justify-between gap-3">
                <div class="ui-stat-label">Ping</div>
                <span class="ui-chip">{{ pingUnavailable ? 'Unavailable' : 'Ready' }}</span>
              </div>
              <InfoAlert v-if="pingUnavailable" class="mt-4">
                Ping data is currently unavailable for this cluster.
              </InfoAlert>
              <div v-else-if="pingCards.length" class="mt-4 grid gap-3">
                <div
                  v-for="card in pingCards"
                  :key="card.title"
                  class="rounded-[20px] border border-[rgba(80,105,127,0.12)] bg-white/84 px-4 py-3"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ card.title }}
                    </div>
                    <span v-if="card.badge" class="ui-chip">{{ card.badge }}</span>
                  </div>
                  <div class="ui-detail-list mt-3">
                    <dl>
                      <div v-for="field in card.fields" :key="field.key" class="ui-detail-row">
                        <dt class="ui-detail-term">{{ field.label }}</dt>
                        <dd class="ui-detail-value">{{ field.value }}</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              </div>
              <p v-else class="ui-panel-description mt-4">
                No controller ping fields are available in the current response.
              </p>
            </article>

            <article class="ui-panel-soft px-4 py-4">
              <div class="flex items-center justify-between gap-3">
                <div class="ui-stat-label">Diag</div>
                <span class="ui-chip">{{ diagUnavailable ? 'Unavailable' : 'Ready' }}</span>
              </div>
              <InfoAlert v-if="diagUnavailable" class="mt-4">
                Diagnostic data is currently unavailable for this cluster.
              </InfoAlert>
              <div v-else-if="diagFields.length" class="ui-detail-list mt-4">
                <dl>
                  <div v-for="field in diagFields" :key="field.key" class="ui-detail-row">
                    <dt class="ui-detail-term">{{ field.label }}</dt>
                    <dd class="ui-detail-value">{{ field.value }}</dd>
                  </div>
                </dl>
              </div>
              <p v-else class="ui-panel-description mt-4">
                No diagnostic summary fields are available in the current response.
              </p>
            </article>
          </div>
        </section>
      </template>
    </div>
  </ClusterMainLayout>
</template>
