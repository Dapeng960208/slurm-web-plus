<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type {
  DateTimeWindowQuery,
  UserMetricsHistory,
  UserToolAnalysisSummary
} from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import StatCardSkeleton from '@/components/StatCardSkeleton.vue'
import UserSubmissionHistoryChart from '@/components/user/UserSubmissionHistoryChart.vue'
import UserToolAnalysisTable from '@/components/user/UserToolAnalysisTable.vue'

const { cluster, user, enabled } = defineProps<{
  cluster: string
  user: string
  enabled: boolean
}>()

const gateway = useGatewayAPI()
const route = useRoute()
const router = useRouter()
const draftStart = ref('')
const draftEnd = ref('')
const appliedWindow = ref<DateTimeWindowQuery | null>(null)
const timeWindowError = ref<string | null>(null)
const userMetricsHistory = ref<UserMetricsHistory | null>(null)
const userToolAnalysis = ref<UserToolAnalysisSummary | null>(null)
const userToolAnalysisLoading = ref(false)
const userMetricsHistoryLoading = ref(false)
const userToolAnalysisUnavailable = ref(false)
const userMetricsHistoryUnavailable = ref(false)
let summaryTimer: ReturnType<typeof setInterval> | null = null
let historyTimer: ReturnType<typeof setInterval> | null = null

const userProfileStatusLabel = computed(() => {
  if (!userToolAnalysis.value?.profile) return null
  return userToolAnalysis.value.profile.ldap_found ? 'LDAP profile available' : 'LDAP profile unavailable'
})

const userMetricsGeneratedAtLabel = computed(() => {
  const value = userToolAnalysis.value?.generated_at
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
})

const userMetricsHistoryHasData = computed(() => {
  return Boolean(
    userMetricsHistory.value?.submissions?.length || userMetricsHistory.value?.completions?.length
  )
})

const submittedJobsInRange = computed(() => userMetricsHistory.value?.totals?.submitted_jobs ?? 0)

const completedJobsInRange = computed(() => userMetricsHistory.value?.totals?.completed_jobs ?? 0)

const averageMemoryLabel = computed(() => {
  const value = userToolAnalysis.value?.totals.avg_memory_gb
  return value != null ? formatGb(value) : '--'
})

const maxMemoryLabel = computed(() => {
  const value = userToolAnalysis.value?.totals.max_memory_gb
  return value != null ? formatGb(value) : '--'
})

const medianMemoryLabel = computed(() => {
  const value = userToolAnalysis.value?.totals.median_memory_gb
  return value != null ? formatGb(value) : '--'
})

const averageCpuLabel = computed(() => {
  const value = userToolAnalysis.value?.totals.avg_cpu_cores
  return value != null ? `${value.toFixed(1)} cores` : '--'
})

const averageRuntimeLabel = computed(() => {
  const value = userToolAnalysis.value?.totals.avg_runtime_hours
  if (value != null) return formatHours(value)
  return formatDuration(userToolAnalysis.value?.totals.avg_runtime_seconds)
})

const userMetricsReady = computed(
  () => userToolAnalysis.value !== null && !userToolAnalysisUnavailable.value
)

const shouldPoll = computed(() => {
  if (!enabled || !appliedWindow.value) return false
  return new Date(appliedWindow.value.end).getTime() >= Date.now() - 5 * 60 * 1000
})

function formatDuration(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  if (value < 60) return `${Math.round(value)} sec`
  if (value < 3600) return `${Math.round(value / 60)} min`
  const hours = Math.floor(value / 3600)
  const minutes = Math.round((value % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function formatGb(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  return `${value.toFixed(value >= 10 ? 1 : 2)} GB`
}

function formatHours(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  return `${value.toFixed(value >= 10 ? 1 : 2)} h`
}

function pad2(value: number): string {
  return value.toString().padStart(2, '0')
}

function formatDateTimeLocal(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(
    date.getHours()
  )}:${pad2(date.getMinutes())}`
}

function parseDateTimeLocal(value: string): Date | null {
  if (!value) return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed
}

function defaultWindowLocal(): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end)
  start.setHours(0, 0, 0, 0)
  return {
    start: formatDateTimeLocal(start),
    end: formatDateTimeLocal(end)
  }
}

function resolveWindowQuery(
  startQuery: unknown,
  endQuery: unknown
): { startLocal: string; endLocal: string; startUtc: string; endUtc: string } {
  const fallback = defaultWindowLocal()
  const startLocal = typeof startQuery === 'string' ? startQuery : fallback.start
  const endLocal = typeof endQuery === 'string' ? endQuery : fallback.end
  const startDate = parseDateTimeLocal(startLocal)
  const endDate = parseDateTimeLocal(endLocal)
  if (!startDate || !endDate || startDate >= endDate) {
    const fallbackStartDate = parseDateTimeLocal(fallback.start) as Date
    const fallbackEndDate = parseDateTimeLocal(fallback.end) as Date
    return {
      startLocal: fallback.start,
      endLocal: fallback.end,
      startUtc: fallbackStartDate.toISOString(),
      endUtc: fallbackEndDate.toISOString()
    }
  }
  return {
    startLocal,
    endLocal,
    startUtc: startDate.toISOString(),
    endUtc: endDate.toISOString()
  }
}

function resetUserMetricsState() {
  userMetricsHistory.value = null
  userToolAnalysis.value = null
  userToolAnalysisLoading.value = false
  userMetricsHistoryLoading.value = false
  userToolAnalysisUnavailable.value = false
  userMetricsHistoryUnavailable.value = false
}

async function fetchUserToolAnalysis() {
  if (!enabled || !appliedWindow.value) return

  userToolAnalysisLoading.value = true
  try {
    userToolAnalysis.value = await gateway.user_tools_analysis(cluster, user, appliedWindow.value)
    userToolAnalysisUnavailable.value = false
  } catch {
    userToolAnalysisUnavailable.value = true
    userToolAnalysis.value = null
  } finally {
    userToolAnalysisLoading.value = false
  }
}

async function fetchUserMetricsHistory() {
  if (!enabled || !appliedWindow.value) return

  userMetricsHistoryLoading.value = true
  try {
    userMetricsHistory.value = await gateway.user_metrics_history(
      cluster,
      user,
      appliedWindow.value
    )
    userMetricsHistoryUnavailable.value = false
  } catch {
    userMetricsHistoryUnavailable.value = true
    userMetricsHistory.value = null
  } finally {
    userMetricsHistoryLoading.value = false
  }
}

async function refreshUserMetrics() {
  await Promise.all([fetchUserToolAnalysis(), fetchUserMetricsHistory()])
}

function startUserMetricsPolling() {
  if (!shouldPoll.value) return
  if (summaryTimer) clearInterval(summaryTimer)
  if (historyTimer) clearInterval(historyTimer)
  summaryTimer = setInterval(fetchUserToolAnalysis, 60000)
  historyTimer = setInterval(fetchUserMetricsHistory, 120000)
}

function stopUserMetricsPolling() {
  if (summaryTimer) {
    clearInterval(summaryTimer)
    summaryTimer = null
  }
  if (historyTimer) {
    clearInterval(historyTimer)
    historyTimer = null
  }
}

function applyTimeWindow(window: { start: string; end: string }) {
  draftStart.value = window.start
  draftEnd.value = window.end
  timeWindowError.value = null
  const startDate = parseDateTimeLocal(draftStart.value)
  const endDate = parseDateTimeLocal(draftEnd.value)
  if (!startDate || !endDate) {
    timeWindowError.value = 'Start and end time must both be valid datetimes.'
    return
  }
  if (startDate >= endDate) {
    timeWindowError.value = 'Start time must be earlier than end time.'
    return
  }
  void router.replace({
    query: {
      ...route.query,
      start: draftStart.value,
      end: draftEnd.value
    }
  })
}

function resetTimeWindow() {
  const fallback = defaultWindowLocal()
  draftStart.value = fallback.start
  draftEnd.value = fallback.end
  timeWindowError.value = null
  void router.replace({
    query: {
      ...route.query,
      start: fallback.start,
      end: fallback.end
    }
  })
}

watch(
  () => [route.query.start, route.query.end],
  ([startQuery, endQuery]) => {
    const resolved = resolveWindowQuery(startQuery, endQuery)
    draftStart.value = resolved.startLocal
    draftEnd.value = resolved.endLocal
    appliedWindow.value = {
      start: resolved.startUtc,
      end: resolved.endUtc
    }
    if (route.query.start !== resolved.startLocal || route.query.end !== resolved.endLocal) {
      void router.replace({
        query: {
          ...route.query,
          start: resolved.startLocal,
          end: resolved.endLocal
        }
      })
    }
  },
  { immediate: true }
)

watch(
  () => [enabled, appliedWindow.value?.start, appliedWindow.value?.end, cluster, user],
  () => {
    if (!enabled || !appliedWindow.value) {
      stopUserMetricsPolling()
      resetUserMetricsState()
      return
    }
    timeWindowError.value = null
    stopUserMetricsPolling()
    void refreshUserMetrics()
    startUserMetricsPolling()
  },
  { immediate: true }
)

watch(
  () => shouldPoll.value,
  (polling) => {
    stopUserMetricsPolling()
    if (polling) startUserMetricsPolling()
  }
)

onUnmounted(() => {
  stopUserMetricsPolling()
})
</script>

<template>
  <InfoAlert v-if="!enabled"> User analytics is not enabled for this cluster. </InfoAlert>

  <div v-else class="ui-section-stack">
    <div class="user-analytics-toolbar">
      <div class="min-w-0">
        <div class="ui-stat-label">Analysis Window</div>
        <div class="mt-2 text-sm font-medium text-[var(--color-brand-ink-strong)]">
          One shared time window for activity, usage and completed tool analysis.
        </div>
        <div
          v-if="userProfileStatusLabel || userMetricsGeneratedAtLabel"
          class="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--color-brand-muted)]"
        >
          <span
            v-if="userProfileStatusLabel"
            class="user-analytics-meta-pill"
          >
            {{ userProfileStatusLabel }}
          </span>
          <span
            v-if="userMetricsGeneratedAtLabel"
            class="user-analytics-meta-pill"
          >
            Updated {{ userMetricsGeneratedAtLabel }}
          </span>
        </div>
      </div>
      <div class="user-analytics-window-control">
        <div class="user-analytics-window-label">Time Range</div>
        <MetricRangeSelector
          :model-value="'hour'"
          aria-label="Select user analytics time range"
          enable-custom-window
          :show-preset-buttons="false"
          :start-value="draftStart"
          :end-value="draftEnd"
          custom-button-label="Time range"
          reset-label="Today"
          @apply-window="applyTimeWindow"
          @reset-window="resetTimeWindow"
        />
      </div>
      <p v-if="timeWindowError" class="mt-3 text-sm text-red-600">
        {{ timeWindowError }}
      </p>
    </div>

    <StatCardSkeleton v-if="userToolAnalysisLoading && !userToolAnalysis" :cards="4" />

    <div v-else-if="userMetricsReady" class="ui-stat-grid">
      <div class="ui-stat-card">
        <div class="ui-stat-label">Submitted in Range</div>
        <div class="ui-stat-value">{{ submittedJobsInRange }}</div>
        <div class="ui-stat-subtle">Submission events captured in the selected window</div>
      </div>
      <div class="ui-stat-card">
        <div class="ui-stat-label">Completed in Range</div>
        <div class="ui-stat-value">{{ completedJobsInRange }}</div>
        <div class="ui-stat-subtle">Completed jobs captured in the selected window</div>
      </div>
      <div class="ui-stat-card">
        <div class="ui-stat-label">Active Tools</div>
        <div class="ui-stat-value">{{ userToolAnalysis?.totals.active_tools ?? 0 }}</div>
        <div class="ui-stat-subtle">
          Top tool:
          {{ userToolAnalysis?.totals.busiest_tool ?? '--' }}
        </div>
      </div>
      <div class="ui-stat-card">
        <div class="ui-stat-label">Average Runtime</div>
        <div class="ui-stat-value">{{ averageRuntimeLabel }}</div>
        <div class="ui-stat-subtle">Across completed jobs captured in the selected window</div>
      </div>
    </div>

    <InfoAlert v-else-if="userToolAnalysisUnavailable">
      User tool analysis is not available for this cluster. LDAP and association details remain
      available.
    </InfoAlert>

    <div
      v-if="userMetricsReady || userMetricsHistoryLoading || userMetricsHistoryUnavailable"
      class="user-analytics-main-grid"
    >
      <div class="ui-panel ui-section min-w-0 user-analytics-activity-panel">
        <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 class="ui-panel-title">Submission Activity</h2>
            <p class="ui-panel-description mt-2">
              Submission and completion trends in the selected time range.
            </p>
          </div>
        </div>

        <ErrorAlert v-if="userMetricsHistoryUnavailable">
          Unable to retrieve submission or completion history for this user.
        </ErrorAlert>
        <div v-else-if="userMetricsHistoryLoading" class="text-[var(--color-brand-muted)]">
          <LoadingSpinner :size="4" />
          Loading activity history...
        </div>
        <p v-else-if="!userMetricsHistoryHasData" class="ui-panel-description">
          No submission or completion history is available for this range.
        </p>
        <div v-else class="user-analytics-chart-frame">
          <UserSubmissionHistoryChart :history="userMetricsHistory" />
        </div>
      </div>

      <div class="ui-panel ui-section min-w-0 user-analytics-usage-panel">
        <div class="mb-3">
          <h2 class="ui-panel-title">Usage Profile</h2>
          <p class="ui-panel-description mt-2">
            Aggregate behaviour across completed jobs in the selected time range.
          </p>
        </div>

        <div class="user-analytics-usage-grid">
          <div class="ui-panel-soft user-analytics-metric-card px-4 py-3">
            <div class="ui-stat-label">Average Memory</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ averageMemoryLabel }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Per completed job across recorded tools in the selected window
            </div>
          </div>

          <div class="ui-panel-soft user-analytics-metric-card px-4 py-3">
            <div class="ui-stat-label">Max Memory</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ maxMemoryLabel }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Highest recorded completed-job memory across the selected window
            </div>
          </div>

          <div class="ui-panel-soft user-analytics-metric-card px-4 py-3">
            <div class="ui-stat-label">Median Memory</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ medianMemoryLabel }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Typical completed-job memory across recorded tools in the selected window
            </div>
          </div>

          <div class="ui-panel-soft user-analytics-metric-card px-4 py-3">
            <div class="ui-stat-label">Average CPU Cores</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ averageCpuLabel }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Core allocation requested by this user's tool runs in the selected window
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="userMetricsReady">
      <div class="mb-3">
        <h2 class="ui-panel-title">Completed Job Tool Analysis</h2>
        <p class="ui-panel-description mt-2">
          Tool-level analysis for completed jobs in the selected time range, combining completed
          job volume with memory, CPU and runtime averages.
        </p>
      </div>

      <p
        v-if="(userToolAnalysis?.tool_breakdown ?? []).length === 0"
        class="ui-panel-soft px-4 py-5 text-sm text-[var(--color-brand-muted)]"
      >
        No completed job tool activity has been recorded for this user yet.
      </p>
      <div v-else>
        <UserToolAnalysisTable
          :tools="userToolAnalysis?.tool_breakdown ?? []"
          :total-completed-jobs="userToolAnalysis?.totals.completed_jobs ?? 0"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-analytics-toolbar {
  display: grid;
  gap: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(240, 244, 247, 0.9)),
    linear-gradient(135deg, rgba(182, 232, 44, 0.08), transparent);
  box-shadow: var(--shadow-soft);
  padding: 1rem 1rem 1.1rem;
}

.user-analytics-meta-pill {
  border: 1px solid rgba(80, 105, 127, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  padding: 0.35rem 0.75rem;
}

.user-analytics-window-control {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0;
}

.user-analytics-window-label {
  color: var(--color-brand-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.user-analytics-main-grid {
  display: grid;
  gap: 1.25rem;
  align-items: start;
}

.user-analytics-activity-panel,
.user-analytics-usage-panel {
  min-width: 0;
}

.user-analytics-chart-frame {
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(245, 247, 249, 0.88));
  padding: 0.5rem 0.25rem 0.25rem;
}

.user-analytics-usage-grid {
  display: grid;
  gap: 0.85rem;
}

.user-analytics-metric-card {
  min-height: 0;
}

:deep([data-testid='metric-range-custom-button']) {
  border: 1px solid rgba(80, 105, 127, 0.16);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 248, 250, 0.94));
  box-shadow: var(--shadow-soft);
  color: var(--color-brand-ink-strong);
  font-size: 0.92rem;
  font-weight: 700;
  min-height: 2.9rem;
  min-width: 22rem;
  padding: 0.8rem 1rem;
}

@media (min-width: 960px) {
  .user-analytics-toolbar {
    align-items: center;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 1rem 1.1rem;
  }

  .user-analytics-window-control {
    align-items: flex-end;
    justify-self: end;
  }

  .user-analytics-main-grid {
    grid-template-columns: minmax(0, 1.35fr) minmax(22rem, 0.85fr);
  }

  .user-analytics-usage-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 959px) {
  .user-analytics-window-control {
    width: 100%;
  }

  :deep([data-testid='metric-range-custom-button']) {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
