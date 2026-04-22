<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterDataPoller } from '@/composables/DataPoller'
import { getMBHumanUnit, getNodeGPU, getNodeGPUFromGres, useGatewayAPI } from '@/composables/GatewayAPI'
import type { ClusterIndividualNode, ClusterJob, NodeInstantMetrics } from '@/composables/GatewayAPI'
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
import { XCircleIcon } from '@heroicons/vue/20/solid'

const { cluster, nodeName } = defineProps<{ cluster: string; nodeName: string }>()

const runtimeStore = useRuntimeStore()
const gateway = useGatewayAPI()

const nodeMetrics = ref<NodeInstantMetrics | null>(null)
const nodeMetricsError = ref(false)
let metricsTimer: ReturnType<typeof setInterval> | null = null

async function fetchNodeMetrics() {
  if (!runtimeStore.currentCluster?.node_metrics) {
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

function startMetricsPolling() {
  if (!runtimeStore.currentCluster?.node_metrics) return
  fetchNodeMetrics()
  if (metricsTimer) clearInterval(metricsTimer)
  metricsTimer = setInterval(fetchNodeMetrics, 15000)
}

function stopMetricsPolling() {
  if (metricsTimer) {
    clearInterval(metricsTimer)
    metricsTimer = null
  }
}

function roundToDecimal(value: number, decimals = 1): number {
  return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals)
}

function formatTimestamp(set: boolean, value: number): string {
  return set ? new Date(value * 10 ** 3).toLocaleString() : 'N/A'
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
      text: `${getMBHumanUnit(node.data.value.alloc_memory)} / ${getMBHumanUnit(node.data.value.real_memory)}`,
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

watch(
  () => cluster,
  (newCluster) => {
    node.setCluster(newCluster)
    jobs?.setCluster(newCluster)
    if (runtimeStore.currentCluster?.node_metrics) {
      fetchNodeMetrics()
    }
  }
)

watch(
  () => nodeName,
  (newNodeName) => {
    node.setParam(newNodeName)
    jobs?.setParam(newNodeName)
    if (runtimeStore.currentCluster?.node_metrics) {
      nodeMetrics.value = null
      nodeMetricsError.value = false
      void fetchNodeMetrics()
    }
  }
)

watch(
  () => runtimeStore.currentCluster?.node_metrics,
  (enabled) => {
    stopMetricsPolling()
    if (enabled) {
      startMetricsPolling()
    } else {
      nodeMetrics.value = null
      nodeMetricsError.value = false
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

      <div class="space-y-6">
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
              <div class="mb-5">
                <h2 class="ui-panel-title">Node Overview</h2>
                <p class="ui-panel-description mt-2">
                  Scheduling status, hardware layout, assigned partitions and currently running jobs.
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
      <div v-else-if="node.data.value">
        <div class="ui-stat-grid">
          <div class="ui-stat-card">
            <div class="ui-stat-label">CPU Capacity</div>
            <div class="ui-stat-value">{{ node.data.value.cpus }}</div>
            <div class="ui-stat-subtle">{{ node.data.value.sockets }} sockets x {{ node.data.value.cores }} cores</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">Memory</div>
            <div class="ui-stat-value">{{ getMBHumanUnit(node.data.value.real_memory) }}</div>
            <div class="ui-stat-subtle">Allocated: {{ getMBHumanUnit(node.data.value.alloc_memory) }}</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">GPU Slots</div>
            <div class="ui-stat-value">{{ gpuAvailable }}</div>
            <div class="ui-stat-subtle">Allocated: {{ gpuAllocated }}</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">Realtime CPU</div>
            <div class="ui-stat-value">
              {{ nodeMetrics?.cpu_usage !== null && nodeMetrics?.cpu_usage !== undefined ? `${nodeMetrics.cpu_usage}%` : '--' }}
            </div>
            <div class="ui-stat-subtle">
              <template v-if="nodeMetricsError">Metrics unavailable</template>
              <template v-else-if="runtimeStore.currentCluster?.node_metrics">Updated every 15s</template>
              <template v-else>Metrics disabled</template>
            </div>
          </div>
        </div>

        <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
          <div class="ui-panel ui-section">
            <div class="mb-5">
              <h2 class="ui-panel-title">Node Overview</h2>
              <p class="ui-panel-description mt-2">
                Scheduling status, hardware layout, assigned partitions and currently running jobs.
              </p>
            </div>

            <div class="ui-detail-list">
              <dl>
                <div id="status" class="ui-detail-row">
                  <dt class="ui-detail-term">Node status</dt>
                  <dd class="ui-detail-value">
                    <div class="flex flex-wrap items-center gap-3">
                      <NodeMainState :status="node.data.value.state" />
                      <span v-if="node.data.value.reason">reason: {{ node.data.value.reason }}</span>
                    </div>
                  </dd>
                </div>

                <div id="allocation" class="ui-detail-row">
                  <dt class="ui-detail-term">Allocation status</dt>
                  <dd class="ui-detail-value space-y-4">
                    <NodeAllocationState :status="node.data.value.state" />
                    <ul class="space-y-2">
                      <li
                        v-for="detail in allocationDetails"
                        :key="detail.label"
                        class="flex flex-wrap items-center gap-2"
                      >
                        <strong class="font-semibold text-[var(--color-brand-ink-strong)]">
                          {{ detail.label }}:
                        </strong>
                        <span class="order-3 text-[var(--color-brand-muted)]">({{ detail.pct }}%)</span>
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
                          <JobStatusBadge :status="job.job_state" :label="job.job_id.toString()" />
                        </RouterLink>
                      </li>
                    </ul>
                    <span v-else>-</span>
                  </dd>
                </div>

                <div id="cpu" class="ui-detail-row">
                  <dt class="ui-detail-term">CPU layout</dt>
                  <dd class="ui-detail-value">
                    {{ node.data.value.sockets }} x {{ node.data.value.cores }} = {{ node.data.value.cpus }}
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
                  <dd class="ui-detail-value">{{ getMBHumanUnit(node.data.value.real_memory) }}</dd>
                </div>

                <div v-if="node.data.value.gres" class="ui-detail-row">
                  <dt class="ui-detail-term">GPU</dt>
                  <dd class="ui-detail-value">
                    <ul class="space-y-2">
                      <li v-for="gpu in getNodeGPU(node.data.value.gres)" :key="gpu">{{ gpu }}</li>
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
                  <dd class="ui-detail-value font-mono">{{ node.data.value.operating_system }}</dd>
                </div>

                <div class="ui-detail-row">
                  <dt class="ui-detail-term">Reboot</dt>
                  <dd class="ui-detail-value">
                    {{ formatTimestamp(node.data.value.boot_time.set, node.data.value.boot_time.number) }}
                  </dd>
                </div>

                <div class="ui-detail-row">
                  <dt class="ui-detail-term">Last busy</dt>
                  <dd class="ui-detail-value">
                    {{ formatTimestamp(node.data.value.last_busy.set, node.data.value.last_busy.number) }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          <div class="ui-panel ui-section">
            <div class="mb-5">
              <h2 class="ui-panel-title">Realtime Metrics</h2>
              <p class="ui-panel-description mt-2">
                Instant Prometheus-backed usage signals when node metrics are enabled on the cluster.
              </p>
            </div>

            <template v-if="!runtimeStore.currentCluster?.node_metrics">
              <p class="ui-panel-description">Realtime metrics are disabled for this cluster.</p>
            </template>
            <template v-else-if="nodeMetricsError">
              <ErrorAlert>Unable to retrieve realtime metrics for this node.</ErrorAlert>
            </template>
            <template v-else-if="!nodeMetrics">
              <div class="text-[var(--color-brand-muted)]">
                <LoadingSpinner :size="4" />
                Loading realtime metrics...
              </div>
            </template>
            <div v-else class="space-y-4">
              <div class="ui-panel-soft px-5 py-4">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="ui-stat-label">CPU Usage</div>
                    <div class="mt-3 text-3xl font-bold text-[var(--color-brand-ink-strong)]">
                      {{ nodeMetrics.cpu_usage !== null ? `${nodeMetrics.cpu_usage}%` : 'N/A' }}
                    </div>
                  </div>
                  <span
                    class="ui-chip"
                    :class="nodeMetrics.cpu_usage !== null && nodeMetrics.cpu_usage > 90 ? '!border-[rgba(216,75,80,0.25)] !bg-[rgba(216,75,80,0.08)] !text-[var(--color-brand-danger)]' : ''"
                  >
                    {{ nodeMetrics.cpu_usage !== null && nodeMetrics.cpu_usage > 90 ? 'High load' : 'Healthy' }}
                  </span>
                </div>
              </div>

              <div class="ui-panel-soft px-5 py-4">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="ui-stat-label">Memory Usage</div>
                    <div class="mt-3 text-3xl font-bold text-[var(--color-brand-ink-strong)]">
                      {{ nodeMetrics.memory_usage !== null ? `${nodeMetrics.memory_usage}%` : 'N/A' }}
                    </div>
                  </div>
                  <span
                    class="ui-chip"
                    :class="nodeMetrics.memory_usage !== null && nodeMetrics.memory_usage > 90 ? '!border-[rgba(216,75,80,0.25)] !bg-[rgba(216,75,80,0.08)] !text-[var(--color-brand-danger)]' : ''"
                  >
                    {{ nodeMetrics.memory_usage !== null && nodeMetrics.memory_usage > 90 ? 'High usage' : 'Stable' }}
                  </span>
                </div>
              </div>

              <div class="ui-panel-soft px-5 py-4">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="ui-stat-label">Disk Usage</div>
                    <div class="mt-3 text-3xl font-bold text-[var(--color-brand-ink-strong)]">
                      {{ nodeMetrics.disk_usage !== null ? `${nodeMetrics.disk_usage}%` : 'N/A' }}
                    </div>
                  </div>
                  <span
                    class="ui-chip"
                    :class="nodeMetrics.disk_usage !== null && nodeMetrics.disk_usage > 90 ? '!border-[rgba(216,75,80,0.25)] !bg-[rgba(216,75,80,0.08)] !text-[var(--color-brand-danger)]' : ''"
                  >
                    {{ nodeMetrics.disk_usage !== null && nodeMetrics.disk_usage > 90 ? 'Attention' : 'Nominal' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
