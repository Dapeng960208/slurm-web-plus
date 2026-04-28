<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMBHumanUnit, useGatewayAPI } from '@/composables/GatewayAPI'
import type {
  DateTimeWindowQuery,
  UserMetricsHistory,
  UserToolActivityRecord,
  UserToolAnalysisSummary
} from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import StatCardSkeleton from '@/components/StatCardSkeleton.vue'
import UserSubmissionHistoryChart from '@/components/user/UserSubmissionHistoryChart.vue'
import UserToolAnalysisChart from '@/components/user/UserToolAnalysisChart.vue'

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

const userGroupsLabel = computed(() => {
  const groups = userToolAnalysis.value?.profile?.groups ?? []
  return groups.length ? groups.join(', ') : null
})

const userFullnameLabel = computed(() => userToolAnalysis.value?.profile?.fullname ?? null)

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

const topTools = computed<UserToolActivityRecord[]>(() => {
  return (userToolAnalysis.value?.tool_breakdown ?? [])
    .slice()
    .sort((a, b) => (b.avg_max_memory_mb ?? 0) - (a.avg_max_memory_mb ?? 0) || b.jobs - a.jobs)
    .slice(0, 6)
})

const submittedJobsInRange = computed(() => userMetricsHistory.value?.totals?.submitted_jobs ?? 0)

const completedJobsInRange = computed(() => userMetricsHistory.value?.totals?.completed_jobs ?? 0)

const averageMemoryLabel = computed(() => {
  const gbValue = userToolAnalysis.value?.totals.avg_max_memory_gb
  if (gbValue != null) return formatGb(gbValue)
  const value = userToolAnalysis.value?.totals.avg_max_memory_mb
  return value != null ? getMBHumanUnit(value) : '--'
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
  }
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
    <div class="ui-panel-soft px-4 py-4">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div class="min-w-0">
          <div class="ui-stat-label">Analysis Window</div>
          <div class="mt-2 text-sm text-[var(--color-brand-muted)]">
            Use one shared window for submissions, usage profile, tool analysis and top tools.
          </div>
          <div
            v-if="userFullnameLabel || userGroupsLabel || userProfileStatusLabel || userMetricsGeneratedAtLabel"
            class="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--color-brand-muted)]"
          >
            <span
              v-if="userFullnameLabel"
              class="rounded-full border border-[rgba(80,105,127,0.12)] bg-white/80 px-3 py-1 font-medium text-[var(--color-brand-ink-strong)]"
            >
              {{ userFullnameLabel }}
            </span>
            <span
              v-if="userProfileStatusLabel"
              class="rounded-full border border-[rgba(80,105,127,0.12)] bg-white/80 px-3 py-1"
            >
              {{ userProfileStatusLabel }}
            </span>
            <span
              v-if="userGroupsLabel"
              class="rounded-full border border-[rgba(80,105,127,0.12)] bg-white/80 px-3 py-1"
            >
              Groups: {{ userGroupsLabel }}
            </span>
            <span
              v-if="userMetricsGeneratedAtLabel"
              class="rounded-full border border-[rgba(80,105,127,0.12)] bg-white/80 px-3 py-1"
            >
              Updated {{ userMetricsGeneratedAtLabel }}
            </span>
          </div>
        </div>
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
      class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]"
    >
      <div class="ui-panel ui-section">
        <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 class="ui-panel-title">Submission Activity</h2>
            <p class="ui-panel-description mt-2">
              Submission and completion trends for this user within the selected time range.
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
        <UserSubmissionHistoryChart v-else :history="userMetricsHistory" />
      </div>

      <div class="ui-panel ui-section">
        <div class="mb-3">
          <h2 class="ui-panel-title">Usage Profile</h2>
          <p class="ui-panel-description mt-2">
            Aggregate behaviour across completed jobs in the selected time range.
          </p>
        </div>

        <div class="space-y-3">
          <div class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">Average Max Memory</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ averageMemoryLabel }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Per completed job across recorded tools in the selected window
            </div>
          </div>

          <div class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">Average CPU Cores</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ averageCpuLabel }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Core allocation requested by this user's tool runs in the selected window
            </div>
          </div>

          <div class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">Busiest Tool</div>
            <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
              {{ userToolAnalysis?.totals.busiest_tool ?? '--' }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              {{ userToolAnalysis?.totals.busiest_tool_jobs ?? 0 }} completed job(s)
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="userMetricsReady"
      class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.86fr)]"
    >
      <div class="ui-panel ui-section">
        <div class="mb-3">
          <h2 class="ui-panel-title">Tool Analysis</h2>
          <p class="ui-panel-description mt-2">
            Dual horizontal bars compare average memory footprint and completed job volume for the
            most active tools recorded in the selected time range.
          </p>
        </div>

        <p
          v-if="topTools.length === 0"
          class="ui-panel-soft px-4 py-5 text-sm text-[var(--color-brand-muted)]"
        >
          No tool activity has been recorded for this user yet.
        </p>
        <UserToolAnalysisChart v-else :tools="topTools" />
      </div>

      <div class="ui-panel ui-section">
        <div class="mb-3">
          <h2 class="ui-panel-title">Top Tools</h2>
          <p class="ui-panel-description mt-2">
            Tool roll-up for memory, CPU, runtime and completed jobs in the selected time range.
          </p>
        </div>

        <div class="space-y-3">
          <div v-for="tool in topTools" :key="tool.tool" class="ui-panel-soft px-4 py-3">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ tool.tool }}
                </div>
                <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
                  {{ tool.jobs }} completed job(s)
                </div>
              </div>
              <span class="ui-chip">{{ tool.jobs }} jobs</span>
            </div>
            <div class="mt-3 grid gap-2 text-sm text-[var(--color-brand-muted)] sm:grid-cols-3">
              <div>
                Memory:
                {{
                  tool.avg_max_memory_gb != null
                    ? formatGb(tool.avg_max_memory_gb)
                    : tool.avg_max_memory_mb != null
                      ? getMBHumanUnit(tool.avg_max_memory_mb)
                      : '--'
                }}
              </div>
              <div>
                CPU:
                {{ tool.avg_cpu_cores != null ? `${tool.avg_cpu_cores.toFixed(1)} cores` : '--' }}
              </div>
              <div>
                Runtime:
                {{
                  tool.avg_runtime_hours != null
                    ? formatHours(tool.avg_runtime_hours)
                    : formatDuration(tool.avg_runtime_seconds)
                }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
