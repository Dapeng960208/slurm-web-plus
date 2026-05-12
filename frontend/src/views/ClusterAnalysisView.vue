<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
const { t, locale } = useI18n()

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

const analysis = computed(() => {
  return analyzeCluster({
    locale: locale.value,
    stats: stats.value,
    jobs: canViewJobs.value ? jobs.value : [],
    nodes: canViewNodes.value ? nodes.value : [],
    jobsMetrics: jobsMetrics.value,
    coreMetrics: coreMetrics.value,
    memoryMetrics: memoryMetrics.value,
    gpuMetrics: gpuMetrics.value,
    historyJobs: historyJobs.value
  })
})

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
      latency_ms: t('analysis.labels.latencyMs')
    },
    fallbackTitle: t('pages.analysis.health.fallbackController')
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
      jobs_submitted: t('analysis.labels.jobsSubmitted'),
      jobs_started: t('analysis.labels.jobsStarted'),
      jobs_completed: t('analysis.labels.jobsCompleted'),
      jobs_canceled: t('analysis.labels.jobsCanceled'),
      schedule_cycle_last: t('analysis.labels.scheduleCycleLast'),
      schedule_cycle_max: t('analysis.labels.scheduleCycleMax'),
      schedule_cycle_mean: t('analysis.labels.scheduleCycleMean')
    }
  })
})

const historicalCards = computed(() => {
  const busyCoresDetail =
    analysis.value.history.averageBusyCores != null && stats.value?.resources.cores
      ? t('analysis.historyCards.busyCores.detail', {
          percent: formatPercentValue(
            percent(analysis.value.history.averageBusyCores, stats.value.resources.cores),
            0
          )
        })
      : t('analysis.historyCards.busyCores.unavailable')

  return [
    {
      id: 'peak-pending',
      label: t('analysis.historyCards.peakPending.label'),
      value: renderNumber(analysis.value.history.peakPending, t('common.entities.jobs')),
      detail: t('analysis.historyCards.peakPending.detail')
    },
    {
      id: 'avg-pending',
      label: t('analysis.historyCards.averagePending.label'),
      value: renderNumber(analysis.value.history.averagePending, t('common.entities.jobs')),
      detail: t('analysis.historyCards.averagePending.detail')
    },
    {
      id: 'peak-running',
      label: t('analysis.historyCards.peakRunning.label'),
      value: renderNumber(analysis.value.history.peakRunning, t('common.entities.jobs')),
      detail: t('analysis.historyCards.peakRunning.detail')
    },
    {
      id: 'busy-cores',
      label: t('analysis.historyCards.busyCores.label'),
      value: renderNumber(analysis.value.history.peakBusyCores, t('pages.dashboard.stats.cores')),
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
  <ClusterMainLayout
    menu-entry="analysis"
    :cluster="cluster"
    :breadcrumb="[{ title: 'shell.mainMenu.analysis' }]"
  >
    <div class="ui-page ui-page-wide ui-content-workspace">
      <PageHeader
        kicker="pages.analysis.kicker"
        title="pages.analysis.title"
        :description="analysis.scoreSummary"
        :metric-value="loading ? undefined : `${analysis.score}/100`"
        metric-label="pages.analysis.metricLabel"
      >
        <template #actions>
          <div class="flex flex-wrap gap-3">
            <RouterLink :to="{ name: 'dashboard', params: { cluster } }" class="ui-button-secondary">
              {{ t('pages.analysis.actions.liveDashboard') }}
            </RouterLink>
            <RouterLink
              v-if="canViewJobs"
              :to="{ name: 'jobs', params: { cluster } }"
              class="ui-button-primary"
            >
              {{ t('pages.analysis.actions.inspectQueue') }}
            </RouterLink>
            <RouterLink
              v-if="canViewResources"
              :to="{ name: 'resources', params: { cluster } }"
              class="ui-button-secondary"
            >
              {{ t('pages.analysis.actions.openResources') }}
            </RouterLink>
          </div>
        </template>
      </PageHeader>

      <ErrorAlert v-if="error">{{ error }}</ErrorAlert>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div v-if="loading" class="ui-section-stack pb-2">
          <div class="ui-panel ui-section">
            <div class="flex items-center gap-3 text-[var(--color-brand-muted)]">
              <LoadingSpinner :size="4" />
              {{ t('pages.analysis.loading') }}
            </div>
          </div>
        </div>

        <div v-else class="ui-section-stack pb-2">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap gap-2">
              <span class="ui-chip">{{ t('pages.analysis.status.prefix') }} {{ analysis.scoreLabel }}</span>
              <span v-if="updatedAtLabel" class="ui-chip">
                {{ t('pages.analysis.status.updated', { time: updatedAtLabel }) }}
              </span>
              <span v-if="refreshing" class="ui-chip">{{ t('pages.analysis.status.refreshing') }}</span>
            </div>

            <MetricRangeSelector
              :model-value="selectedRange"
              :aria-label="t('pages.analysis.toolbar.selectRange')"
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
                <h2 class="ui-panel-title">{{ t('pages.analysis.sections.capacityTitle') }}</h2>
                <p class="ui-panel-description mt-2">{{ t('pages.analysis.sections.capacityDescription') }}</p>
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
                <h2 class="ui-panel-title">{{ t('pages.analysis.sections.blockersTitle') }}</h2>
                <p class="ui-panel-description mt-2">{{ t('pages.analysis.sections.blockersDescription') }}</p>
              </div>

              <div class="space-y-3">
                <div v-if="!canViewJobs" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
                  {{ t('pages.analysis.blockers.noJobPermission') }}
                </div>
                <div v-else-if="jobsUnavailable" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
                  {{ t('pages.analysis.blockers.jobsUnavailable') }}
                </div>
                <div
                  v-else-if="analysis.topReasons.length === 0"
                  class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]"
                >
                  {{ t('pages.analysis.blockers.none') }}
                </div>
                <div v-for="reason in analysis.topReasons" :key="reason.reason" class="ui-analysis-reason">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                        {{ reason.reason }}
                      </div>
                      <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
                        {{ t('pages.analysis.blockers.pendingJobs', { count: reason.count }) }}
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

                <div class="ui-metric-surface px-4 py-4">
                  <div class="ui-stat-label">{{ t('pages.analysis.blockers.packingSignal') }}</div>
                  <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
                    {{ analysis.fragmentationJobs }}
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    {{
                      t('pages.analysis.blockers.packingDetail', {
                        count: analysis.fragmentationJobs,
                        cpu: analysis.freeSchedulableCpu
                      })
                    }}
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.92fr)]">
            <section class="ui-panel ui-section">
              <div class="mb-4">
                <h2 class="ui-panel-title">{{ t('pages.analysis.sections.partitionTitle') }}</h2>
                <p class="ui-panel-description mt-2">{{ t('pages.analysis.sections.partitionDescription') }}</p>
              </div>

              <div v-if="!canViewJobs || !canViewNodes" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
                {{ t('pages.analysis.partition.noPermission') }}
              </div>
              <div v-else-if="analysis.partitionPressure.length === 0" class="ui-panel-soft px-4 py-4 text-sm text-[var(--color-brand-muted)]">
                {{ t('pages.analysis.partition.none') }}
              </div>
              <div v-else class="space-y-3">
                <div
                  v-for="partition in analysis.partitionPressure"
                  :key="partition.name"
                  class="ui-metric-surface px-4 py-4"
                >
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                        {{ partition.name }}
                      </div>
                      <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
                        {{
                          t('pages.analysis.partition.pendingActive', {
                            pending: partition.pendingJobs,
                            running: partition.runningJobs
                          })
                        }}
                      </div>
                    </div>
                    <span class="ui-chip">
                      {{
                        t('pages.analysis.partition.cpuChip', {
                          running: partition.runningCpu,
                          total: partition.schedulableCpu || partition.totalCpu
                        })
                      }}
                    </span>
                  </div>
                  <div class="mt-3 grid gap-2 text-sm text-[var(--color-brand-muted)] sm:grid-cols-3">
                    <div>{{ t('pages.analysis.partition.pendingCpu', { value: partition.pendingCpu }) }}</div>
                    <div>{{ t('pages.analysis.partition.totalCpu', { value: partition.totalCpu }) }}</div>
                    <div>{{ t('pages.analysis.partition.schedulableCpu', { value: partition.schedulableCpu }) }}</div>
                  </div>
                </div>
              </div>
            </section>

            <section class="ui-panel ui-section">
              <div class="mb-4">
                <h2 class="ui-panel-title">{{ t('pages.analysis.sections.historicalTitle') }}</h2>
                <p class="ui-panel-description mt-2">{{ t('pages.analysis.sections.historicalDescription') }}</p>
              </div>

              <InfoAlert v-if="!metricsEnabled">
                {{ t('pages.analysis.historical.metricsDisabled') }}
              </InfoAlert>
              <InfoAlert v-else-if="metricsUnavailable">
                {{ t('pages.analysis.historical.metricsUnavailable') }}
              </InfoAlert>
              <div v-else class="grid gap-3 sm:grid-cols-2">
                <div v-for="card in historicalCards" :key="card.id" class="ui-metric-surface px-4 py-3">
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
                <div class="ui-metric-surface px-4 py-3">
                  <div class="ui-stat-label">{{ t('pages.analysis.historical.latestTelemetry') }}</div>
                  <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ renderNumber(analysis.history.latestPending, t('filters.states.pending')) }} /
                    {{ renderNumber(analysis.history.latestRunning, t('filters.states.running')) }}
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    {{ t('pages.analysis.historical.latestTelemetryDetail') }}
                  </div>
                </div>

                <div class="ui-metric-surface px-4 py-3">
                  <div class="ui-stat-label">{{ t('pages.analysis.historical.waitSamples') }}</div>
                  <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                    {{
                      analysis.waitStats.medianMinutes == null
                        ? '--'
                        : t('pages.analysis.historical.waitMedian', {
                            minutes: analysis.waitStats.medianMinutes
                          })
                    }}
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    <template v-if="analysis.waitStats.samples > 0">
                      {{
                        t('pages.analysis.historical.waitP90', {
                          p90: analysis.waitStats.p90Minutes,
                          samples: analysis.waitStats.samples
                        })
                      }}
                    </template>
                    <template v-else-if="waitSamplesUnavailable">
                      {{ t('pages.analysis.historical.waitUnavailable') }}
                    </template>
                    <template v-else>
                      {{ t('pages.analysis.historical.waitDisabled') }}
                    </template>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <section class="ui-panel ui-section">
            <div class="mb-4">
              <h2 class="ui-panel-title">{{ t('pages.analysis.sections.actionsTitle') }}</h2>
              <p class="ui-panel-description mt-2">{{ t('pages.analysis.sections.actionsDescription') }}</p>
            </div>

            <div class="grid gap-4 xl:grid-cols-3">
              <article
                v-for="recommendation in analysis.recommendations"
                :key="recommendation.id"
                class="ui-analysis-recommendation"
              >
                <div class="ui-stat-label">{{ t(`pages.analysis.status.${recommendation.tone}`) }}</div>
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
              <h2 class="ui-panel-title">{{ t('pages.analysis.sections.healthTitle') }}</h2>
              <p class="ui-panel-description mt-2">{{ t('pages.analysis.sections.healthDescription') }}</p>
            </div>

            <div class="grid gap-4 xl:grid-cols-2">
              <article class="ui-panel-soft px-4 py-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="ui-stat-label">{{ t('pages.analysis.health.ping') }}</div>
                  <span class="ui-chip">
                    {{ pingUnavailable ? t('common.status.unavailable') : t('pages.analysis.status.ready') }}
                  </span>
                </div>
                <InfoAlert v-if="pingUnavailable" class="mt-4">
                  {{ t('pages.analysis.health.pingUnavailable') }}
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
                  {{ t('pages.analysis.health.pingEmpty') }}
                </p>
              </article>

              <article class="ui-panel-soft px-4 py-4">
                <div class="flex items-center justify-between gap-3">
                  <div class="ui-stat-label">{{ t('pages.analysis.health.diag') }}</div>
                  <span class="ui-chip">
                    {{ diagUnavailable ? t('common.status.unavailable') : t('pages.analysis.status.ready') }}
                  </span>
                </div>
                <InfoAlert v-if="diagUnavailable" class="mt-4">
                  {{ t('pages.analysis.health.diagUnavailable') }}
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
                  {{ t('pages.analysis.health.diagEmpty') }}
                </p>
              </article>
            </div>
          </section>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
