<!--
  Copyright (c) 2023-2024 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch, ref, onMounted, onUnmounted } from 'vue'
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
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import BackToResourcesButton from '@/components/resources/BackToResourcesButton.vue'
import { XCircleIcon } from '@heroicons/vue/20/solid'

const { cluster, nodeName } = defineProps<{ cluster: string; nodeName: string }>()

const runtimeStore = useRuntimeStore()
const gateway = useGatewayAPI()

/* Real-time node metrics from Prometheus (only when node_metrics is enabled) */
const nodeMetrics = ref<NodeInstantMetrics | null>(null)
const nodeMetricsError = ref(false)
let metricsTimer: ReturnType<typeof setInterval> | null = null

async function fetchNodeMetrics() {
  if (!runtimeStore.currentCluster?.node_metrics) {
    console.log('[NodeMetrics] ⚠️ 节点实时监控功能未启用')
    return
  }
  
  console.log('[NodeMetrics] 开始获取节点实时指标...')
  console.log('[NodeMetrics] 节点名称:', nodeName)
  
  try {
    nodeMetrics.value = await gateway.node_metrics(cluster, nodeName)
    nodeMetricsError.value = false
    
    console.log('[NodeMetrics] ✅ 成功获取实时指标')
    console.log('[NodeMetrics] CPU使用率:', nodeMetrics.value.cpu_usage, '%')
    console.log('[NodeMetrics] 内存使用率:', nodeMetrics.value.memory_usage, '%')
    console.log('[NodeMetrics] 磁盘使用率:', nodeMetrics.value.disk_usage, '%')
  } catch (e) {
    console.error('[NodeMetrics] ❌ 获取实时指标失败:', e)
    nodeMetricsError.value = true
  }
}

onMounted(() => {
  console.log('='.repeat(60))
  console.log('[NodeView] 🖥️ 节点详情页面已挂载')
  console.log('[NodeView] 节点名称:', nodeName)
  console.log('[NodeView] 集群名称:', cluster)
  
  if (runtimeStore.currentCluster?.node_metrics) {
    console.log('[NodeView] ✅ 节点实时监控功能已启用')
    console.log('[NodeView] 功能说明: 从 Prometheus 获取节点实时资源使用情况')
    console.log('[NodeView] 检查项:')
    console.log('[NodeView]   1. /etc/slurm-web/agent.ini 中 [node_metrics] enabled = true')
    console.log('[NodeView]   2. prometheus_host 配置正确')
    console.log('[NodeView]   3. Prometheus 中有对应节点的 node_exporter 数据')
    console.log('[NodeView]   4. Agent 服务已重启')
    console.log('[NodeView] 刷新间隔: 15秒')
    console.log('='.repeat(60))
    
    fetchNodeMetrics()
    metricsTimer = setInterval(fetchNodeMetrics, 15000)
  } else {
    console.log('[NodeView] ⚠️ 节点实时监控功能未启用')
    console.log('[NodeView] 如需启用，请在 /etc/slurm-web/agent.ini 中配置 [node_metrics]')
    console.log('='.repeat(60))
  }
})

onUnmounted(() => {
  if (metricsTimer) clearInterval(metricsTimer)
})

function roundToDecimal(value: number, decimals: number = 1): number {
  return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals)
}

const node = useClusterDataPoller<ClusterIndividualNode>(cluster, 'node', 5000, nodeName)

/* Poll jobs on current nodes if user has permission on view-jobs action. */
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

watch(
  () => cluster,
  (new_cluster) => {
    node.setCluster(new_cluster)
  }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="resources"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Resources', routeName: 'resources' }, { title: `Node ${nodeName}` }]"
  >
    <BackToResourcesButton :cluster="cluster" />
    <ErrorAlert v-if="node.unable.value"
      >Unable to retrieve node {{ nodeName }} from cluster
      <span class="font-medium">{{ cluster }}</span></ErrorAlert
    >
    <div v-else-if="!node.loaded" class="text-gray-400 sm:pl-6 lg:pl-8">
      <LoadingSpinner :size="5" />
      Loading node {{ nodeName }}
    </div>
    <div v-else-if="node.data.value">
      <div class="flex justify-between">
        <div class="px-4 pb-8 sm:px-0">
          <h3 class="text-base leading-7 font-semibold text-gray-900 dark:text-gray-100">
            Node {{ nodeName }}
          </h3>
          <p class="mt-1 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-300">
            All node statuses
          </p>
        </div>
      </div>
      <div class="flex flex-wrap">
        <div class="w-full">
          <div class="border-t border-gray-100 dark:border-gray-700">
            <dl class="divide-y divide-gray-100 dark:divide-gray-700">
              <div id="status" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Node status
                </dt>
                <dd class="mt-1 text-sm leading-6 sm:col-span-2 sm:mt-0">
                  <NodeMainState :status="node.data.value.state" />
                  <span v-if="node.data.value.reason" class="pl-4 text-gray-500"
                    >reason: {{ node.data.value.reason }}</span
                  >
                </dd>
              </div>
              <div id="allocation" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Allocation status
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  <NodeAllocationState :status="node.data.value.state" />
                  <ul class="list-disc pt-4 pl-4">
                    <li>
                      CPU: {{ node.data.value.alloc_cpus }} / {{ node.data.value.cpus }}
                      <span class="text-gray-400 italic dark:text-gray-500"
                        >({{
                          roundToDecimal((node.data.value.alloc_cpus / node.data.value.cpus) * 100)
                        }}%)</span
                      >
                    </li>
                    <li>
                      Memory: {{ getMBHumanUnit(node.data.value.alloc_memory) }} /
                      {{ getMBHumanUnit(node.data.value.real_memory) }}
                      <span class="text-gray-400 italic dark:text-gray-600"
                        >({{
                          roundToDecimal(
                            (node.data.value.alloc_memory / node.data.value.real_memory) * 100
                          )
                        }}%)</span
                      >
                    </li>
                    <li v-if="node.data.value.gres_used">
                      GPU: {{ gpuAllocated }} / {{ gpuAvailable }}
                      <span class="text-gray-400 italic dark:text-gray-600"
                        >({{ roundToDecimal((gpuAllocated / gpuAvailable) * 100) }}%)</span
                      >
                    </li>
                  </ul>
                </dd>
              </div>
              <div v-if="jobs" id="jobs" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Current Jobs
                  <span
                    v-if="jobs.data.value"
                    class="text-slurmweb dark:text-slurmweb-light dark:bg-slurmweb-verydark ml-1 hidden rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium md:inline-block"
                    >{{ jobs.data.value.length }}</span
                  >
                </dt>
                <dd class="text-sm leading-6 sm:col-span-2">
                  <div
                    v-if="jobs.unable.value"
                    class="flex items-center gap-x-1 text-gray-400 dark:text-gray-600"
                  >
                    <XCircleIcon class="h-5 w-5" aria-hidden="true" />
                    Unable to retrieve jobs
                  </div>
                  <div v-else-if="!jobs.loaded.value" class="text-gray-400 dark:text-gray-600">
                    <LoadingSpinner :size="4" />
                    Loading jobs...
                  </div>
                  <template v-else-if="jobs.data.value">
                    <ul v-if="jobs.data.value.length">
                      <li v-for="job in jobs.data.value" :key="job.job_id" class="inline">
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
                            class="mr-1"
                          />
                        </RouterLink>
                      </li>
                    </ul>
                    <span v-else class="text-gray-400 dark:text-gray-600">∅</span>
                  </template>
                </dd>
              </div>
              <div id="cpu" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  CPU (socket x cores/socket)
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  {{ node.data.value.sockets }} x {{ node.data.value.cores }} =
                  {{ node.data.value.cpus }}
                </dd>
              </div>
              <div id="threads" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Threads/core
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  {{ node.data.value.threads }}
                </dd>
              </div>
              <div id="arch" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Architecture
                </dt>
                <dd
                  class="mt-1 font-mono text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  {{ node.data.value.architecture }}
                </dd>
              </div>
              <div id="memory" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Memory
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  {{ getMBHumanUnit(node.data.value.real_memory) }}
                </dd>
              </div>
              <div
                v-if="node.data.value.gres"
                id="memory"
                class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0"
              >
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">GPU</dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  <ul class="list-disc pl-4">
                    <li v-for="gpu in getNodeGPU(node.data.value.gres)" :key="gpu">{{ gpu }}</li>
                  </ul>
                </dd>
              </div>
              <div id="partitions" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Partitions
                </dt>
                <dd class="mt-1 text-sm leading-6 sm:col-span-2 sm:mt-0">
                  <span
                    v-for="partition in node.data.value.partitions"
                    :key="partition"
                    class="rounded-sm bg-gray-500 px-2 py-1 font-medium text-white"
                    >{{ partition }}</span
                  >
                </dd>
              </div>
              <div id="kernel" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  OS Kernel
                </dt>
                <dd
                  class="mt-1 font-mono text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  {{ node.data.value.operating_system }}
                </dd>
              </div>
              <div id="reboot" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Reboot
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  <template v-if="node.data.value.boot_time.set">
                    {{ new Date(node.data.value.boot_time.number * 10 ** 3).toLocaleString() }}
                  </template>
                  <template v-else>N/A</template>
                </dd>
              </div>
              <div id="last" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Last busy
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  <template v-if="node.data.value.last_busy.set">
                    {{ new Date(node.data.value.last_busy.number * 10 ** 3).toLocaleString() }}
                  </template>
                  <template v-else>N/A</template>
                </dd>
              </div>
              <!-- Real-time metrics from Prometheus -->
              <div
                v-if="runtimeStore.currentCluster?.node_metrics"
                id="realtime-metrics"
                class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0"
              >
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  Real-time Metrics
                </dt>
                <dd
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  <span v-if="nodeMetricsError" class="text-red-500 text-xs">
                    Unable to retrieve metrics
                  </span>
                  <span v-else-if="!nodeMetrics" class="text-gray-400 text-xs">Loading…</span>
                  <ul v-else class="list-disc pl-4 space-y-1">
                    <li>
                      CPU usage:
                      <span :class="nodeMetrics.cpu_usage !== null && nodeMetrics.cpu_usage > 90 ? 'text-red-500 font-semibold' : ''">
                        {{ nodeMetrics.cpu_usage !== null ? nodeMetrics.cpu_usage + '%' : 'N/A' }}
                      </span>
                    </li>
                    <li>
                      Memory usage:
                      <span :class="nodeMetrics.memory_usage !== null && nodeMetrics.memory_usage > 90 ? 'text-red-500 font-semibold' : ''">
                        {{ nodeMetrics.memory_usage !== null ? nodeMetrics.memory_usage + '%' : 'N/A' }}
                      </span>
                    </li>
                    <li>
                      Disk usage (root):
                      <span :class="nodeMetrics.disk_usage !== null && nodeMetrics.disk_usage > 90 ? 'text-red-500 font-semibold' : ''">
                        {{ nodeMetrics.disk_usage !== null ? nodeMetrics.disk_usage + '%' : 'N/A' }}
                      </span>
                    </li>
                  </ul>
                </dd>
              </div>
              <!--
                <div v-for="(value, property) in data" class="px-4 py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0">
                  <dt class="text-sm font-medium leading-6 text-gray-900">{{  property }}</dt>
                  <dd class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0"> {{ value }}</dd>
                </div>
              -->
            </dl>
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
