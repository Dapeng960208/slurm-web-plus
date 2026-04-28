<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterDataPoller } from '@/composables/DataPoller'
import {
  getMBHumanUnit,
  getNodeGPU,
  getNodeGPUFromGres,
  isMetricRange,
  useGatewayAPI
} from '@/composables/GatewayAPI'
import type {
  ClusterIndividualNode,
  ClusterJob,
  DateTimeWindowQuery,
  MetricRange,
  NodeInstantMetrics,
  NodeMetricsHistory
} from '@/composables/GatewayAPI'
import NodeMainState from '@/components/resources/NodeMainState.vue'
import NodeAllocationState from '@/components/resources/NodeAllocationState.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import BackToResourcesButton from '@/components/resources/BackToResourcesButton.vue'
import PageHeader from '@/components/PageHeader.vue'
import DetailSkeletonList from '@/components/DetailSkeletonList.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import StatCardSkeleton from '@/components/StatCardSkeleton.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import NodeMetricsHistoryChart from '@/components/node/NodeMetricsHistoryChart.vue'
import PercentMetric from '@/components/PercentMetric.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { XCircleIcon } from '@heroicons/vue/20/solid'

const { cluster, nodeName } = defineProps<{ cluster: string; nodeName: string }>()

const router = useRouter()
const route = useRoute()
const runtimeStore = useRuntimeStore()
const gateway = useGatewayAPI()
const operationError = ref<string | null>(null)
const operationBusy = ref(false)
const editOpen = ref(false)
const deleteOpen = ref(false)

const nodeMetrics = ref<NodeInstantMetrics | null>(null)
const nodeMetricsHistory = ref<NodeMetricsHistory | null>(null)
const nodeMetricsError = ref(false)
const nodeMetricsHistoryError = ref(false)
const nodeMetricsHistoryLoading = ref(false)
const nodeMetricsRange = ref<MetricRange>('hour')
const nodeMetricsWindow = ref<DateTimeWindowQuery | null>(null)
const nodeMetricsStartLocal = ref('')
const nodeMetricsEndLocal = ref('')
let metricsTimer: ReturnType<typeof setInterval> | null = null
let metricsHistoryTimer: ReturnType<typeof setInterval> | null = null

const nodeMetricsEnabled = computed(() => {
  const details = runtimeStore.availableClusters.find((value) => value.name === cluster)
  return Boolean(details?.node_metrics)
})

async function fetchNodeMetrics() {
  if (!nodeMetricsEnabled.value) {
    nodeMetrics.value = null
    nodeMetricsError.value = false
    return
  }

  try {
    nodeMetrics.value = await gateway.node_metrics(cluster, nodeName)
    nodeMetricsError.value = false
  } catch {
    nodeMetricsError.value = true
  }
}

async function fetchNodeMetricsHistory() {
  if (!nodeMetricsEnabled.value) {
    nodeMetricsHistory.value = null
    nodeMetricsHistoryError.value = false
    nodeMetricsHistoryLoading.value = false
    return
  }

  nodeMetricsHistoryLoading.value = true
  try {
    nodeMetricsHistory.value = await gateway.node_metrics_history(
      cluster,
      nodeName,
      nodeMetricsWindow.value ?? nodeMetricsRange.value
    )
    nodeMetricsHistoryError.value = false
  } catch {
    nodeMetricsHistoryError.value = true
    nodeMetricsHistory.value = null
  } finally {
    nodeMetricsHistoryLoading.value = false
  }
}

function startMetricsPolling() {
  if (!nodeMetricsEnabled.value) return
  void fetchNodeMetrics()
  void fetchNodeMetricsHistory()
  if (metricsTimer) clearInterval(metricsTimer)
  if (metricsHistoryTimer) clearInterval(metricsHistoryTimer)
  metricsTimer = setInterval(fetchNodeMetrics, 15000)
  metricsHistoryTimer = setInterval(fetchNodeMetricsHistory, 60000)
}

function stopMetricsPolling() {
  if (metricsTimer) {
    clearInterval(metricsTimer)
    metricsTimer = null
  }
  if (metricsHistoryTimer) {
    clearInterval(metricsHistoryTimer)
    metricsHistoryTimer = null
  }
}

function roundToDecimal(value: number, decimals = 1): number {
  return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals)
}

function formatTimestamp(set: boolean, value: number): string {
  return set ? new Date(value * 10 ** 3).toLocaleString() : 'N/A'
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

function defaultMetricsWindowLocal(): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end.getTime() - 60 * 60 * 1000)
  return {
    start: formatDateTimeLocal(start),
    end: formatDateTimeLocal(end)
  }
}

function resolveMetricsWindowQuery(
  startQuery: unknown,
  endQuery: unknown
): { startLocal: string; endLocal: string; startUtc: string; endUtc: string } | null {
  if (typeof startQuery !== 'string' || typeof endQuery !== 'string') return null
  const startDate = parseDateTimeLocal(startQuery)
  const endDate = parseDateTimeLocal(endQuery)
  if (!startDate || !endDate || startDate >= endDate) return null
  return {
    startLocal: startQuery,
    endLocal: endQuery,
    startUtc: startDate.toISOString(),
    endUtc: endDate.toISOString()
  }
}

const node = useClusterDataPoller<ClusterIndividualNode>(cluster, 'node', 5000, nodeName)

let jobs: ClusterDataPoller<ClusterJob[]> | undefined
if (runtimeStore.hasPermission('view-jobs')) {
  jobs = useClusterDataPoller<ClusterJob[]>(cluster, 'jobs', 10000, nodeName)
}

const gpuAvailable = computed(() => {
  if (!node.data.value) return 0
  return getNodeGPUFromGres(node.data.value.gres).reduce((gpu, current) => gpu + current.count, 0)
})

const gpuAllocated = computed(() => {
  if (!node.data.value) return 0
  return getNodeGPUFromGres(node.data.value.gres_used).reduce(
    (gpu, current) => gpu + current.count,
    0
  )
})

const allocationDetails = computed(() => {
  if (!node.data.value) return []
  const details = [
    {
      label: 'CPU',
      text: `${node.data.value.alloc_cpus} / ${node.data.value.cpus}`,
      pct: roundToDecimal((node.data.value.alloc_cpus / node.data.value.cpus) * 100)
    },
    {
      label: 'Memory',
      text: `${getMBHumanUnit(node.data.value.alloc_memory)} / ${getMBHumanUnit(
        node.data.value.real_memory
      )}`,
      pct: roundToDecimal((node.data.value.alloc_memory / node.data.value.real_memory) * 100)
    }
  ]
  if (node.data.value.gres_used && gpuAvailable.value > 0) {
    details.push({
      label: 'GPU',
      text: `${gpuAllocated.value} / ${gpuAvailable.value}`,
      pct: roundToDecimal((gpuAllocated.value / gpuAvailable.value) * 100)
    })
  }
  return details
})

const actualCpuUsage = computed(() => {
  if (!node.data.value || !nodeMetrics.value || nodeMetrics.value.cpu_usage === null) return null
  return roundToDecimal((node.data.value.cpus * nodeMetrics.value.cpu_usage) / 100, 1)
})

const actualMemoryUsage = computed(() => {
  if (!node.data.value || !nodeMetrics.value || nodeMetrics.value.memory_usage === null) return null
  return roundToDecimal((node.data.value.real_memory * nodeMetrics.value.memory_usage) / 100, 0)
})

const nodeMetricsHistoryHasData = computed(() => {
  if (!nodeMetricsHistory.value) return false
  return (
    nodeMetricsHistory.value.cpu_usage.length > 0 ||
    nodeMetricsHistory.value.memory_usage.length > 0 ||
    nodeMetricsHistory.value.disk_usage.length > 0
  )
})

const canEditNode = computed(() => runtimeStore.hasRoutePermission(cluster, 'resources', 'edit'))
const canDeleteNode = computed(() =>
  runtimeStore.hasRoutePermission(cluster, 'resources', 'delete')
)

async function saveNode(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.update_node(cluster, nodeName, {
      state: payload.state || undefined,
      reason: payload.reason || undefined
    })
    runtimeStore.reportInfo(`Node ${nodeName} update requested.`)
    editOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function removeNode() {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.delete_node(cluster, nodeName)
    runtimeStore.reportInfo(`Node ${nodeName} delete requested.`)
    deleteOpen.value = false
    void router.push({ name: 'resources', params: { cluster } })
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

function confirmDeleteNode(payload: Record<string, string>) {
  if (payload.confirmation !== 'DELETE') {
    operationError.value = 'Type DELETE to confirm.'
    return
  }
  void removeNode()
}

function setMetricsRange(range: MetricRange) {
  if (
    nodeMetricsRange.value === range &&
    route.query.range === range &&
    !route.query.start &&
    !route.query.end
  ) {
    return
  }
  const { start, end, ...query } = route.query
  void start
  void end
  void router.replace({
    query: {
      ...query,
      range
    }
  })
}

function applyMetricsWindow(window: { start: string; end: string }) {
  const startDate = parseDateTimeLocal(window.start)
  const endDate = parseDateTimeLocal(window.end)
  if (!startDate || !endDate || startDate >= endDate) return
  void router.replace({
    query: {
      ...route.query,
      start: window.start,
      end: window.end
    }
  })
}

function resetMetricsWindow() {
  const { start, end, ...query } = route.query
  void start
  void end
  void router.replace({
    query: {
      ...query,
      range: 'hour'
    }
  })
}

watch(
  () => [route.query.range, route.query.start, route.query.end],
  ([range, startQuery, endQuery]) => {
    nodeMetricsRange.value = isMetricRange(range) ? range : 'hour'
    const resolved = resolveMetricsWindowQuery(startQuery, endQuery)
    if (resolved) {
      nodeMetricsStartLocal.value = resolved.startLocal
      nodeMetricsEndLocal.value = resolved.endLocal
      nodeMetricsWindow.value = {
        start: resolved.startUtc,
        end: resolved.endUtc
      }
      return
    }
    nodeMetricsWindow.value = null
    const fallback = defaultMetricsWindowLocal()
    nodeMetricsStartLocal.value = fallback.start
    nodeMetricsEndLocal.value = fallback.end
  },
  { immediate: true }
)

watch(
  () => cluster,
  (newCluster) => {
    node.setCluster(newCluster)
    jobs?.setCluster(newCluster)
    if (nodeMetricsEnabled.value) {
      void fetchNodeMetrics()
      void fetchNodeMetricsHistory()
    }
  }
)

watch(
  () => nodeName,
  (newNodeName) => {
    node.setParam(newNodeName)
    jobs?.setParam(newNodeName)
    if (nodeMetricsEnabled.value) {
      nodeMetrics.value = null
      nodeMetricsHistory.value = null
      nodeMetricsError.value = false
      nodeMetricsHistoryError.value = false
      void fetchNodeMetrics()
      void fetchNodeMetricsHistory()
    }
  }
)

watch(
  () => nodeMetricsEnabled.value,
  (enabled) => {
    stopMetricsPolling()
    if (enabled) {
      startMetricsPolling()
    } else {
      nodeMetrics.value = null
      nodeMetricsHistory.value = null
      nodeMetricsError.value = false
      nodeMetricsHistoryError.value = false
      nodeMetricsHistoryLoading.value = false
    }
  }
)

watch(
  () => [
    nodeMetricsRange.value,
    nodeMetricsWindow.value?.start ?? null,
    nodeMetricsWindow.value?.end ?? null
  ],
  () => {
    if (nodeMetricsEnabled.value) {
      nodeMetricsHistory.value = null
      nodeMetricsHistoryError.value = false
      void fetchNodeMetricsHistory()
    }
  }
)

onMounted(() => {
  startMetricsPolling()
})

onUnmounted(() => {
  stopMetricsPolling()
})
</script>

<template>
  <ClusterMainLayout
    menu-entry="resources"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Resources', routeName: 'resources' }, { title: `Node ${nodeName}` }]"
  >
    <div class="ui-page ui-page-readable">
      <BackToResourcesButton :cluster="cluster" />

      <div class="ui-section-stack">
        <PageHeader
          kicker="Node Detail"
          :title="`Node ${nodeName}`"
          description="Live allocation status, hardware profile and workload occupancy for the selected node."
        >
          <template #actions>
            <div class="flex flex-wrap items-center justify-end gap-3">
              <template v-if="node.data.value">
                <NodeMainState :status="node.data.value.state" />
                <NodeAllocationState :status="node.data.value.state" />
                <span
                  v-if="node.data.value.reason"
                  class="ui-chip border-[rgba(216,75,80,0.16)] bg-[rgba(216,75,80,0.08)] text-[var(--color-brand-danger)]"
                >
                  {{ node.data.value.reason }}
                </span>
                <button
                  v-if="canEditNode"
                  type="button"
                  class="ui-button-warning"
                  title="Edit the node state and set a scheduler-visible reason."
                  @click="editOpen = true"
                >
                  Edit
                </button>
                <button
                  v-if="canDeleteNode"
                  type="button"
                  class="ui-button-danger"
                  title="Delete this node definition from the cluster."
                  @click="deleteOpen = true"
                >
                  Delete
                </button>
              </template>
              <div
                v-else-if="node.initialLoading.value"
                class="h-10 w-32 animate-pulse rounded-full bg-[rgba(80,105,127,0.12)]"
              />
            </div>
          </template>
        </PageHeader>

        <template v-if="node.initialLoading.value && !node.unable.value">
          <StatCardSkeleton :cards="4" />
          <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
            <div class="ui-panel ui-section">
              <div class="mb-3">
                <h2 class="ui-panel-title">Node Overview</h2>
                <p class="ui-panel-description mt-2">
                  Scheduling status, hardware layout, assigned partitions and currently running
                  jobs.
                </p>
              </div>
              <DetailSkeletonList :rows="10" />
            </div>
            <PanelSkeleton :rows="4" />
          </div>
        </template>

        <ErrorAlert v-if="node.unable.value"
          >Unable to retrieve node {{ nodeName }} from cluster
          <span class="font-medium">{{ cluster }}</span></ErrorAlert
        >
        <div v-else-if="node.data.value" class="ui-section-stack">
          <div class="ui-stat-grid">
            <div class="ui-stat-card">
              <div class="ui-stat-label">CPU Capacity</div>
              <div class="ui-stat-value">{{ node.data.value.cpus }}</div>
              <div class="ui-stat-subtle">
                {{ node.data.value.sockets }} sockets x {{ node.data.value.cores }} cores
              </div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">Memory</div>
              <div class="ui-stat-value">{{ getMBHumanUnit(node.data.value.real_memory) }}</div>
              <div class="ui-stat-subtle">
                Allocated: {{ getMBHumanUnit(node.data.value.alloc_memory) }}
              </div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">GPU Slots</div>
              <div class="ui-stat-value">{{ gpuAvailable }}</div>
              <div class="ui-stat-subtle">Allocated: {{ gpuAllocated }}</div>
            </div>
            <div v-if="nodeMetricsEnabled" class="ui-stat-card">
              <div class="ui-stat-label">Realtime CPU</div>
              <div class="mt-3">
                <PercentMetric :value="nodeMetrics?.cpu_usage" size="lg" />
              </div>
              <div class="ui-stat-subtle">
                <template v-if="nodeMetricsError">Metrics unavailable</template>
                <template v-else-if="actualCpuUsage !== null"
                  >{{ actualCpuUsage }} / {{ node.data.value.cpus }} cores</template
                >
                <template v-else>Updated every 15s</template>
              </div>
            </div>
          </div>

          <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
            <div class="ui-panel ui-section" :class="{ 'xl:col-span-2': !nodeMetricsEnabled }">
              <div class="mb-3">
                <h2 class="ui-panel-title">Node Overview</h2>
                <p class="ui-panel-description mt-2">
                  Scheduling status, hardware layout, assigned partitions and currently running
                  jobs.
                </p>
              </div>

              <div class="ui-detail-list">
                <dl>
                  <div id="status" class="ui-detail-row">
                    <dt class="ui-detail-term">Node status</dt>
                    <dd class="ui-detail-value">
                      <div class="flex flex-wrap items-center gap-3">
                        <NodeMainState :status="node.data.value.state" />
                        <span v-if="node.data.value.reason"
                          >reason: {{ node.data.value.reason }}</span
                        >
                      </div>
                    </dd>
                  </div>

                  <div id="allocation" class="ui-detail-row">
                    <dt class="ui-detail-term">Allocation status</dt>
                    <dd class="ui-detail-value space-y-2">
                      <NodeAllocationState :status="node.data.value.state" />
                      <ul class="space-y-1.5">
                        <li
                          v-for="detail in allocationDetails"
                          :key="detail.label"
                          class="flex flex-wrap items-center gap-2"
                        >
                          <strong class="font-semibold text-[var(--color-brand-ink-strong)]">
                            {{ detail.label }}:
                          </strong>
                          <span class="order-3">
                            <PercentMetric :value="detail.pct" size="sm" />
                          </span>
                          <span class="order-2">{{ detail.text }}</span>
                        </li>
                      </ul>
                    </dd>
                  </div>

                  <div v-if="jobs" id="jobs" class="ui-detail-row">
                    <dt class="ui-detail-term">Current jobs</dt>
                    <dd class="ui-detail-value">
                      <div
                        v-if="jobs.unable.value"
                        class="flex items-center gap-2 text-[var(--color-brand-muted)]"
                      >
                        <XCircleIcon class="h-5 w-5" aria-hidden="true" />
                        Unable to retrieve jobs
                      </div>
                      <div v-else-if="!jobs.loaded.value" class="text-[var(--color-brand-muted)]">
                        <LoadingSpinner :size="4" />
                        Loading jobs...
                      </div>
                      <ul v-else-if="jobs.data.value?.length" class="flex flex-wrap gap-2">
                        <li v-for="job in jobs.data.value" :key="job.job_id">
                          <RouterLink
                            :to="{
                              name: 'job',
                              params: { cluster: cluster, id: job.job_id },
                              query: { returnTo: 'node', nodeName: nodeName }
                            }"
                          >
                            <JobStatusBadge
                              :status="job.job_state"
                              :label="job.job_id.toString()"
                            />
                          </RouterLink>
                        </li>
                      </ul>
                      <span v-else>-</span>
                    </dd>
                  </div>

                  <div id="cpu" class="ui-detail-row">
                    <dt class="ui-detail-term">CPU layout</dt>
                    <dd class="ui-detail-value">
                      {{ node.data.value.sockets }} x {{ node.data.value.cores }} =
                      {{ node.data.value.cpus }}
                    </dd>
                  </div>

                  <div class="ui-detail-row">
                    <dt class="ui-detail-term">Threads/core</dt>
                    <dd class="ui-detail-value">{{ node.data.value.threads }}</dd>
                  </div>

                  <div id="arch" class="ui-detail-row">
                    <dt class="ui-detail-term">Architecture</dt>
                    <dd class="ui-detail-value font-mono">{{ node.data.value.architecture }}</dd>
                  </div>

                  <div id="memory" class="ui-detail-row">
                    <dt class="ui-detail-term">Memory</dt>
                    <dd class="ui-detail-value">
                      {{ getMBHumanUnit(node.data.value.real_memory) }}
                    </dd>
                  </div>

                  <div v-if="node.data.value.gres" class="ui-detail-row">
                    <dt class="ui-detail-term">GPU</dt>
                    <dd class="ui-detail-value">
                      <ul class="space-y-2">
                        <li v-for="gpu in getNodeGPU(node.data.value.gres)" :key="gpu">
                          {{ gpu }}
                        </li>
                      </ul>
                    </dd>
                  </div>

                  <div id="partitions" class="ui-detail-row">
                    <dt class="ui-detail-term">Partitions</dt>
                    <dd class="ui-detail-value">
                      <div class="flex flex-wrap gap-2">
                        <span
                          v-for="partition in node.data.value.partitions"
                          :key="partition"
                          class="ui-chip"
                        >
                          {{ partition }}
                        </span>
                      </div>
                    </dd>
                  </div>

                  <div class="ui-detail-row">
                    <dt class="ui-detail-term">OS Kernel</dt>
                    <dd class="ui-detail-value font-mono">
                      {{ node.data.value.operating_system }}
                    </dd>
                  </div>

                  <div class="ui-detail-row">
                    <dt class="ui-detail-term">Reboot</dt>
                    <dd class="ui-detail-value">
                      {{
                        formatTimestamp(
                          node.data.value.boot_time.set,
                          node.data.value.boot_time.number
                        )
                      }}
                    </dd>
                  </div>

                  <div class="ui-detail-row">
                    <dt class="ui-detail-term">Last busy</dt>
                    <dd class="ui-detail-value">
                      {{
                        formatTimestamp(
                          node.data.value.last_busy.set,
                          node.data.value.last_busy.number
                        )
                      }}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>

            <div v-if="nodeMetricsEnabled" class="ui-panel ui-section">
              <div class="mb-3">
                <h2 class="ui-panel-title">Realtime Metrics</h2>
                <p class="ui-panel-description mt-2">
                  Prometheus-backed realtime and historical usage signals for this node.
                </p>
              </div>

              <template v-if="nodeMetricsError">
                <ErrorAlert>Unable to retrieve realtime metrics for this node.</ErrorAlert>
              </template>
              <template v-else-if="!nodeMetrics">
                <div class="text-[var(--color-brand-muted)]">
                  <LoadingSpinner :size="4" />
                  Loading realtime metrics...
                </div>
              </template>
              <div v-else class="space-y-3">
                <div class="ui-panel-soft px-4 py-3">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <div class="ui-stat-label">CPU Usage</div>
                      <div class="mt-2">
                        <PercentMetric :value="nodeMetrics.cpu_usage" />
                      </div>
                      <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                        Actual: {{ actualCpuUsage !== null ? `${actualCpuUsage} cores` : 'N/A' }}
                      </div>
                    </div>
                    <span
                      class="ui-chip"
                      :class="
                        nodeMetrics.cpu_usage !== null && nodeMetrics.cpu_usage > 90
                          ? '!border-[rgba(216,75,80,0.25)] !bg-[rgba(216,75,80,0.08)] !text-[var(--color-brand-danger)]'
                          : ''
                      "
                    >
                      {{
                        nodeMetrics.cpu_usage !== null && nodeMetrics.cpu_usage > 90
                          ? 'High load'
                          : 'Healthy'
                      }}
                    </span>
                  </div>
                </div>

                <div class="ui-panel-soft px-4 py-3">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <div class="ui-stat-label">Memory Usage</div>
                      <div class="mt-2">
                        <PercentMetric :value="nodeMetrics.memory_usage" />
                      </div>
                      <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                        Actual:
                        {{ actualMemoryUsage !== null ? getMBHumanUnit(actualMemoryUsage) : 'N/A' }}
                      </div>
                    </div>
                    <span
                      class="ui-chip"
                      :class="
                        nodeMetrics.memory_usage !== null && nodeMetrics.memory_usage > 90
                          ? '!border-[rgba(216,75,80,0.25)] !bg-[rgba(216,75,80,0.08)] !text-[var(--color-brand-danger)]'
                          : ''
                      "
                    >
                      {{
                        nodeMetrics.memory_usage !== null && nodeMetrics.memory_usage > 90
                          ? 'High usage'
                          : 'Stable'
                      }}
                    </span>
                  </div>
                </div>

                <div class="ui-panel-soft px-4 py-3">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <div class="ui-stat-label">Disk Usage</div>
                      <div class="mt-2">
                        <PercentMetric :value="nodeMetrics.disk_usage" />
                      </div>
                    </div>
                    <span
                      class="ui-chip"
                      :class="
                        nodeMetrics.disk_usage !== null && nodeMetrics.disk_usage > 90
                          ? '!border-[rgba(216,75,80,0.25)] !bg-[rgba(216,75,80,0.08)] !text-[var(--color-brand-danger)]'
                          : ''
                      "
                    >
                      {{
                        nodeMetrics.disk_usage !== null && nodeMetrics.disk_usage > 90
                          ? 'Attention'
                          : 'Nominal'
                      }}
                    </span>
                  </div>
                </div>

                <div class="ui-panel-soft px-4 py-3">
                  <div class="flex flex-wrap items-end justify-between gap-3">
                    <div>
                      <div class="ui-stat-label">Usage History</div>
                      <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                        CPU, memory and disk usage trends across the selected interval.
                      </div>
                    </div>

                    <MetricRangeSelector
                      :model-value="nodeMetricsRange"
                      aria-label="Select node metrics range"
                      enable-custom-window
                      :start-value="nodeMetricsStartLocal"
                      :end-value="nodeMetricsEndLocal"
                      custom-button-label="Custom"
                      reset-label="Last hour"
                      @update:model-value="setMetricsRange"
                      @apply-window="applyMetricsWindow"
                      @reset-window="resetMetricsWindow"
                    />
                  </div>

                  <div class="mt-3">
                    <ErrorAlert v-if="nodeMetricsHistoryError">
                      Unable to retrieve metrics history for this node.
                    </ErrorAlert>
                    <div
                      v-else-if="nodeMetricsHistoryLoading"
                      class="text-[var(--color-brand-muted)]"
                    >
                      <LoadingSpinner :size="4" />
                      Loading history...
                    </div>
                    <p v-else-if="!nodeMetricsHistoryHasData" class="ui-panel-description">
                      No metrics history is available for this range.
                    </p>
                    <NodeMetricsHistoryChart v-else :history="nodeMetricsHistory" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ActionDialog
      :open="editOpen"
      title="Edit Node"
      :description="`Update node ${nodeName} on ${cluster}.`"
      submit-label="Save changes"
      submit-variant="warning"
      submit-tooltip="Apply the edited node state and optional reason to the selected cluster node."
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        state: node.data.value?.state?.join(',') ?? '',
        reason: node.data.value?.reason ?? ''
      }"
      :fields="[
        {
          key: 'state',
          label: 'State',
          required: true,
          hint: 'Comma-separated Slurm state flags to apply to this node.',
          tooltip:
            'Examples include DRAIN, RESUME or UNDRAIN depending on the desired scheduler action.'
        },
        {
          key: 'reason',
          label: 'Reason',
          type: 'textarea',
          hint: 'Optional audit note shown with the node state inside the cluster UI and scheduler output.',
          tooltip: 'Use this when draining or changing node behavior so operators understand why.'
        }
      ]"
      @close="editOpen = false"
      @submit="saveNode"
    />

    <ActionDialog
      :open="deleteOpen"
      title="Delete Node"
      :description="`Delete node ${nodeName}. This action is destructive.`"
      submit-label="Delete node"
      submit-variant="danger"
      submit-tooltip="Permanently remove the node definition after confirmation."
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        {
          key: 'confirmation',
          label: 'Type DELETE to confirm',
          required: true,
          hint: 'Enter DELETE exactly to unlock this destructive action.',
          tooltip: 'This safeguard prevents accidental node removal.'
        }
      ]"
      @close="deleteOpen = false"
      @submit="confirmDeleteNode"
    />
  </ClusterMainLayout>
</template>
