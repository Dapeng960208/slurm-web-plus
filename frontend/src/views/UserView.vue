<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { getMBHumanUnit, useGatewayAPI } from '@/composables/GatewayAPI'
import type {
  ClusterAssociation,
  MetricRange,
  UserActivitySummary,
  UserToolActivityRecord,
  UserMetricsHistory
} from '@/composables/GatewayAPI'
import {
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import StatCardSkeleton from '@/components/StatCardSkeleton.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import UserSubmissionHistoryChart from '@/components/user/UserSubmissionHistoryChart.vue'
import UserToolAnalysisChart from '@/components/user/UserToolAnalysisChart.vue'

const { cluster, user } = defineProps<{
  cluster: string
  user: string
}>()

const router = useRouter()
const runtimeStore = useRuntimeStore()
const gateway = useGatewayAPI()

const { data, unable, loaded, initialLoading, setCluster } = useClusterDataPoller<
  ClusterAssociation[]
>(cluster, 'associations', 120000)

const userMetricsRange = ref<MetricRange>('hour')
const userMetricsHistory = ref<UserMetricsHistory | null>(null)
const userMetricsSummary = ref<UserActivitySummary | null>(null)
const userMetricsLoading = ref(false)
const userMetricsHistoryLoading = ref(false)
const userMetricsUnavailable = ref(false)
const userMetricsHistoryUnavailable = ref(false)
let summaryTimer: ReturnType<typeof setInterval> | null = null
let historyTimer: ReturnType<typeof setInterval> | null = null

const userAssociations = computed(() => {
  if (!data.value) return []
  return data.value
    .filter((association) => association.user === user)
    .sort((a, b) => a.account.localeCompare(b.account))
})

const knownUser = computed(() => userAssociations.value.length > 0)

const associatedAccounts = computed(() => {
  const accounts = new Set<string>()
  for (const association of userAssociations.value) {
    accounts.add(association.account)
  }
  return accounts
})

const clusterDetails = computed(() =>
  runtimeStore.availableClusters.find((value) => value.name === cluster)
)

const userMetricsEnabled = computed(() => Boolean(clusterDetails.value?.user_metrics))
const userDescription = computed(() => {
  const parts = [
    'LDAP-linked account associations, quota boundaries and observed cluster submission behaviour for this user.'
  ]
  if (userMetricsSummary.value?.profile?.fullname) {
    parts.unshift(`Full name: ${userMetricsSummary.value.profile.fullname}.`)
  }
  return parts.join(' ')
})
const userGroupsLabel = computed(() => {
  const groups = userMetricsSummary.value?.profile?.groups ?? []
  return groups.length ? groups.join(', ') : null
})
const userMetricsGeneratedAtLabel = computed(() => {
  const value = userMetricsSummary.value?.generated_at
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
})

const userMetricsHistoryHasData = computed(() => {
  return Boolean(userMetricsHistory.value?.submissions.length)
})

const topTools = computed<UserToolActivityRecord[]>(() => {
  return (userMetricsSummary.value?.tool_breakdown ?? [])
    .slice()
    .sort((a, b) => b.jobs - a.jobs)
    .slice(0, 6)
})

const latestSubmissions = computed(
  () => userMetricsSummary.value?.totals.latest_submissions_per_minute ?? null
)

const averageMemoryLabel = computed(() => {
  const value = userMetricsSummary.value?.totals.avg_max_memory_mb
  return value != null ? getMBHumanUnit(value) : '--'
})

const averageCpuLabel = computed(() => {
  const value = userMetricsSummary.value?.totals.avg_cpu_cores
  return value != null ? `${value.toFixed(1)} cores` : '--'
})

const averageRuntimeLabel = computed(() => {
  return formatDuration(userMetricsSummary.value?.totals.avg_runtime_seconds)
})

const userMetricsReady = computed(
  () => userMetricsSummary.value !== null && !userMetricsUnavailable.value
)

const userMetricsSectionVisible = computed(() => loaded.value && userMetricsEnabled.value)
const userMetricsAvailable = computed(() => userMetricsEnabled.value)

function jobLimits(association: ClusterAssociation) {
  return [
    { id: 'MaxJobs', label: 'Running / user', value: association.max.jobs.active },
    { id: 'MaxSubmit', label: 'Submitted / user', value: association.max.jobs.total }
  ]
}

function resourceLimits(association: ClusterAssociation) {
  return [
    { id: 'GrpTRES', label: 'Total', value: association.max.tres.total },
    { id: 'MaxTRES', label: 'Per job', value: association.max.tres.per.job },
    { id: 'MaxTRESPerNode', label: 'Per node', value: association.max.tres.per.node }
  ]
}

function timeLimits(association: ClusterAssociation) {
  return [
    { id: 'GrpWall', label: 'Total', value: association.max.per.account.wall_clock },
    { id: 'MaxWall', label: 'Per job', value: association.max.jobs.per.wall_clock }
  ]
}

function formatDuration(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  if (value < 60) return `${Math.round(value)} sec`
  if (value < 3600) return `${Math.round(value / 60)} min`
  const hours = Math.floor(value / 3600)
  const minutes = Math.round((value % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function resetUserMetricsState() {
  userMetricsHistory.value = null
  userMetricsSummary.value = null
  userMetricsLoading.value = false
  userMetricsHistoryLoading.value = false
  userMetricsUnavailable.value = false
  userMetricsHistoryUnavailable.value = false
}

async function fetchUserMetricsSummary() {
  if (!userMetricsAvailable.value) return

  userMetricsLoading.value = true
  try {
    userMetricsSummary.value = await gateway.user_activity_summary(cluster, user)
    userMetricsUnavailable.value = false
  } catch {
    userMetricsUnavailable.value = true
    userMetricsSummary.value = null
  } finally {
    userMetricsLoading.value = false
  }
}

async function fetchUserMetricsHistory() {
  if (!userMetricsAvailable.value) return

  userMetricsHistoryLoading.value = true
  try {
    userMetricsHistory.value = await gateway.user_metrics_history(
      cluster,
      user,
      userMetricsRange.value
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
  await Promise.all([fetchUserMetricsSummary(), fetchUserMetricsHistory()])
}

function startUserMetricsPolling() {
  if (!userMetricsAvailable.value) return
  if (summaryTimer) clearInterval(summaryTimer)
  if (historyTimer) clearInterval(historyTimer)
  summaryTimer = setInterval(fetchUserMetricsSummary, 60000)
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

function setUserMetricsRange(range: MetricRange) {
  userMetricsRange.value = range
}

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
    if (userMetricsAvailable.value) {
      void refreshUserMetrics()
    }
  }
)

watch(
  () => user,
  () => {
    if (userMetricsAvailable.value) {
      resetUserMetricsState()
      void refreshUserMetrics()
    }
  }
)

watch(
  () => userMetricsAvailable.value,
  (available) => {
    stopUserMetricsPolling()
    if (available) {
      void refreshUserMetrics()
      startUserMetricsPolling()
      return
    }
    resetUserMetricsState()
  },
  { immediate: true }
)

watch(
  () => userMetricsRange.value,
  () => {
    if (!userMetricsAvailable.value) return
    userMetricsHistory.value = null
    userMetricsHistoryUnavailable.value = false
    void fetchUserMetricsHistory()
  }
)

onUnmounted(() => {
  stopUserMetricsPolling()
})
</script>

<template>
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Accounts', routeName: 'accounts' }, { title: `User ${user}` }]"
  >
    <div class="ui-page ui-page-readable">
      <button
        @click="router.push({ name: 'accounts', params: { cluster } })"
        type="button"
        class="ui-button-secondary self-start"
      >
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        Back to accounts
      </button>

      <div class="ui-section-stack">
        <div id="user-heading">
          <span class="sr-only">User {{ user }}</span>
          <PageHeader
            kicker="User Detail"
            :title="user"
            :description="userDescription"
            :metric-value="loaded ? associatedAccounts.size : undefined"
            :metric-label="`account${associatedAccounts.size === 1 ? '' : 's'} associated`"
          >
            <template #actions>
              <RouterLink
                :to="{ name: 'jobs', params: { cluster }, query: { users: user } }"
                class="ui-button-primary"
              >
                View jobs
              </RouterLink>
            </template>
          </PageHeader>
        </div>

        <div
          v-if="userMetricsReady || userGroupsLabel || userMetricsGeneratedAtLabel"
          class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
        >
          <div class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">Username</div>
            <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
              {{ user }}
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              LDAP
              {{
                userMetricsSummary?.profile?.ldap_found
                  ? 'profile available'
                  : 'profile unavailable'
              }}
            </div>
          </div>
          <div v-if="userGroupsLabel" class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">LDAP Groups</div>
            <div class="mt-2 text-sm font-medium text-[var(--color-brand-ink-strong)]">
              {{ userGroupsLabel }}
            </div>
          </div>
          <div v-if="userMetricsGeneratedAtLabel" class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">Metrics Updated</div>
            <div class="mt-2 text-sm font-medium text-[var(--color-brand-ink-strong)]">
              {{ userMetricsGeneratedAtLabel }}
            </div>
          </div>
        </div>

        <PanelSkeleton v-if="initialLoading && !unable" :rows="8" />

        <ErrorAlert v-if="unable">
          Unable to retrieve associations for cluster
          <span class="font-medium">{{ cluster }}</span>
        </ErrorAlert>
        <div v-else-if="loaded" class="ui-section-stack">
          <InfoAlert v-if="!knownUser">
            User <span class="font-semibold">{{ user }}</span> has no associations on this cluster.
          </InfoAlert>

          <template v-if="userMetricsSectionVisible">
            <StatCardSkeleton v-if="userMetricsLoading && !userMetricsSummary" :cards="4" />

            <div v-else-if="userMetricsReady" class="ui-stat-grid">
              <div class="ui-stat-card">
                <div class="ui-stat-label">Submitted Today</div>
                <div class="ui-stat-value">
                  {{ userMetricsSummary?.totals.submitted_jobs_today ?? 0 }}
                </div>
                <div class="ui-stat-subtle">
                  Completed: {{ userMetricsSummary?.totals.completed_jobs_today ?? 0 }}
                </div>
              </div>
              <div class="ui-stat-card">
                <div class="ui-stat-label">Live Submit Rate</div>
                <div class="ui-stat-value">{{ latestSubmissions ?? '--' }}</div>
                <div class="ui-stat-subtle">Jobs per minute in the latest bucket</div>
              </div>
              <div class="ui-stat-card">
                <div class="ui-stat-label">Active Tools</div>
                <div class="ui-stat-value">{{ userMetricsSummary?.totals.active_tools ?? 0 }}</div>
                <div class="ui-stat-subtle">
                  Top tool:
                  {{ userMetricsSummary?.totals.busiest_tool ?? '--' }}
                </div>
              </div>
              <div class="ui-stat-card">
                <div class="ui-stat-label">Average Runtime</div>
                <div class="ui-stat-value">{{ averageRuntimeLabel }}</div>
                <div class="ui-stat-subtle">Across completed jobs captured today</div>
              </div>
            </div>

            <InfoAlert v-else-if="userMetricsUnavailable">
              User activity statistics are not available for this cluster. LDAP and association
              details remain available.
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
                      Near-realtime job submissions for this user. Range switches between hour, day
                      and week views.
                    </p>
                  </div>

                  <span class="isolate inline-flex rounded-full shadow-[var(--shadow-soft)]">
                    <button
                      type="button"
                      :class="[
                        userMetricsRange == 'week'
                          ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                          : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
                        'relative inline-flex items-center rounded-l-full px-3 py-1.5 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
                      ]"
                      @click="setUserMetricsRange('week')"
                    >
                      week
                    </button>
                    <button
                      type="button"
                      :class="[
                        userMetricsRange == 'day'
                          ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                          : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
                        'relative inline-flex items-center px-3 py-1.5 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
                      ]"
                      @click="setUserMetricsRange('day')"
                    >
                      day
                    </button>
                    <button
                      type="button"
                      :class="[
                        userMetricsRange == 'hour'
                          ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                          : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
                        'relative inline-flex items-center rounded-r-full px-3 py-1.5 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
                      ]"
                      @click="setUserMetricsRange('hour')"
                    >
                      hour
                    </button>
                  </span>
                </div>

                <ErrorAlert v-if="userMetricsHistoryUnavailable">
                  Unable to retrieve submission history for this user.
                </ErrorAlert>
                <div v-else-if="userMetricsHistoryLoading" class="text-[var(--color-brand-muted)]">
                  <LoadingSpinner :size="4" />
                  Loading submission history...
                </div>
                <p v-else-if="!userMetricsHistoryHasData" class="ui-panel-description">
                  No submission history is available for this range.
                </p>
                <UserSubmissionHistoryChart v-else :history="userMetricsHistory" />
              </div>

              <div class="ui-panel ui-section">
                <div class="mb-3">
                  <h2 class="ui-panel-title">Usage Profile</h2>
                  <p class="ui-panel-description mt-2">
                    Aggregate behaviour across completed jobs collected for today.
                  </p>
                </div>

                <div class="space-y-3">
                  <div class="ui-panel-soft px-4 py-3">
                    <div class="ui-stat-label">Average Max Memory</div>
                    <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
                      {{ averageMemoryLabel }}
                    </div>
                    <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                      Per completed job across recorded tools
                    </div>
                  </div>

                  <div class="ui-panel-soft px-4 py-3">
                    <div class="ui-stat-label">Average CPU Cores</div>
                    <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
                      {{ averageCpuLabel }}
                    </div>
                    <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                      Core allocation requested by this user's tool runs
                    </div>
                  </div>

                  <div class="ui-panel-soft px-4 py-3">
                    <div class="ui-stat-label">Busiest Tool</div>
                    <div class="mt-2 text-2xl font-bold text-[var(--color-brand-ink-strong)]">
                      {{ userMetricsSummary?.totals.busiest_tool ?? '--' }}
                    </div>
                    <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                      {{ userMetricsSummary?.totals.busiest_tool_jobs ?? 0 }} completed job(s)
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
                    Tool-level completed job volume for today, with memory, CPU and runtime details
                    on hover.
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
                    Daily roll-up for the most active tools associated with this user.
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
                    <div
                      class="mt-3 grid gap-2 text-sm text-[var(--color-brand-muted)] sm:grid-cols-3"
                    >
                      <div>
                        Memory:
                        {{
                          tool.avg_max_memory_mb != null
                            ? getMBHumanUnit(tool.avg_max_memory_mb)
                            : '--'
                        }}
                      </div>
                      <div>
                        CPU:
                        {{
                          tool.avg_cpu_cores != null
                            ? `${tool.avg_cpu_cores.toFixed(1)} cores`
                            : '--'
                        }}
                      </div>
                      <div>Runtime: {{ formatDuration(tool.avg_runtime_seconds) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <div v-if="knownUser" class="ui-table-shell overflow-x-auto">
            <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
              <h2 class="ui-panel-title">Account Associations</h2>
              <p class="ui-panel-description mt-2">
                Each row represents one account binding and the limits attached to it.
              </p>
            </div>

            <div class="inline-block min-w-full align-middle">
              <table class="ui-table min-w-full">
                <thead>
                  <tr>
                    <th scope="col" class="py-3.5 pr-3 pl-6 text-left lg:min-w-[220px]">Account</th>
                    <th scope="col" class="hidden w-72 px-3 py-3.5 text-left sm:table-cell">
                      Job limits
                    </th>
                    <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">
                      Resource limits
                    </th>
                    <th scope="col" class="hidden w-72 px-3 py-3.5 text-left md:table-cell">
                      Time limits
                    </th>
                    <th scope="col" class="hidden w-48 px-3 py-3.5 text-left 2xl:table-cell">
                      QOS
                    </th>
                  </tr>
                </thead>
                <tbody class="text-sm text-[var(--color-brand-muted)]">
                  <tr
                    v-for="association in userAssociations"
                    :key="`${association.account}-${association.user}`"
                  >
                    <td class="py-4 pr-3 pl-6 align-top text-[var(--color-brand-ink-strong)]">
                      <AccountBreadcrumb
                        :cluster="cluster"
                        :account="association.account"
                        :associations="data ?? []"
                        show-current
                      />
                    </td>
                    <td class="hidden px-3 py-4 align-top sm:table-cell">
                      <div v-if="jobLimits(association).length === 0">-</div>
                      <dl v-else class="space-y-2">
                        <div
                          v-for="limit in jobLimits(association)"
                          :key="limit.id"
                          class="flex flex-wrap items-center gap-2"
                        >
                          <dt class="font-semibold text-[var(--color-brand-ink-strong)]">
                            {{ limit.label }}:
                          </dt>
                          <dd>{{ renderClusterOptionalNumber(limit.value) }}</dd>
                        </div>
                      </dl>
                    </td>
                    <td class="hidden px-3 py-4 align-top lg:table-cell">
                      <div v-if="resourceLimits(association).length === 0">-</div>
                      <dl v-else class="space-y-2">
                        <div
                          v-for="limit in resourceLimits(association)"
                          :key="limit.id"
                          class="flex flex-wrap items-center gap-2"
                        >
                          <dt class="font-semibold text-[var(--color-brand-ink-strong)]">
                            {{ limit.label }}:
                          </dt>
                          <dd class="font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                        </div>
                      </dl>
                    </td>
                    <td class="hidden px-3 py-4 align-top md:table-cell">
                      <div v-if="timeLimits(association).length === 0">-</div>
                      <dl v-else class="space-y-2">
                        <div
                          v-for="limit in timeLimits(association)"
                          :key="limit.id"
                          class="flex flex-wrap items-center gap-2"
                        >
                          <dt class="font-semibold text-[var(--color-brand-ink-strong)]">
                            {{ limit.label }}:
                          </dt>
                          <dd>{{ renderWalltime(limit.value) }}</dd>
                        </div>
                      </dl>
                    </td>
                    <td class="hidden px-3 py-4 align-top 2xl:table-cell">
                      {{ renderQosLabel(association.qos) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
