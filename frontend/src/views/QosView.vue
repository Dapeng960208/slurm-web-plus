<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import {
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosFlag,
  renderWalltime
} from '@/composables/GatewayAPI'
import type { ClusterQos, ClusterOptionalNumber, ClusterTRES } from '@/composables/GatewayAPI'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import QosHelpModal from '@/components/qos/QosHelpModal.vue'
import type { QosModalLimitDescription } from '@/components/qos/QosHelpModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import TableSkeletonRows from '@/components/TableSkeletonRows.vue'
import PaginationControls from '@/components/PaginationControls.vue'
import {
  DEFAULT_PAGE_SIZE,
  lastPage,
  parsePageSize,
  parsePositivePage,
  type PageSizeOption
} from '@/composables/Pagination'
import { QuestionMarkCircleIcon } from '@heroicons/vue/20/solid'

const { cluster } = defineProps<{ cluster: string }>()
const route = useRoute()
const router = useRouter()

const { data, unable, loaded, setCluster } = useClusterDataPoller<ClusterQos[]>(
  cluster,
  'qos',
  10000
)

const helpModalShow: Ref<boolean> = ref(false)
const modalQosLimit: Ref<QosModalLimitDescription | undefined> = ref()
const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)

const pagedQos = computed(() => {
  const items = data.value ?? []
  const start = (page.value - 1) * pageSize.value
  return items.slice(start, start + pageSize.value)
})
const totalPages = computed(() => lastPage(data.value?.length ?? 0, pageSize.value))

function updateQueryParameters() {
  const query: LocationQueryRaw = {}
  if (page.value !== 1) query.page = page.value
  if (pageSize.value !== DEFAULT_PAGE_SIZE) query.page_size = pageSize.value
  router.push({ name: 'qos', params: { cluster }, query })
}

function updatePage(newPage: number) {
  page.value = newPage
  updateQueryParameters()
}

function updatePageSize(newPageSize: PageSizeOption) {
  pageSize.value = newPageSize
  page.value = 1
  updateQueryParameters()
}

function openHelpModal(qos: string, limit: string, value: ClusterOptionalNumber | ClusterTRES[]) {
  modalQosLimit.value = { id: limit, qos: qos, value: value }
  helpModalShow.value = true
}

function closeHelpModal() {
  helpModalShow.value = false
  modalQosLimit.value = undefined
}

function qosJobLimits(qos: ClusterQos) {
  return [
    { id: 'GrpJobs', label: 'Global', value: qos.limits.max.active_jobs.count },
    { id: 'MaxSubmitJobsPerUser', label: 'Submit / User', value: qos.limits.max.jobs.per.user },
    {
      id: 'MaxSubmitJobsPerAccount',
      label: 'Submit / Account',
      value: qos.limits.max.jobs.per.account
    },
    { id: 'MaxJobsPerUser', label: 'Max / User', value: qos.limits.max.jobs.active_jobs.per.user },
    {
      id: 'MaxJobsPerAccount',
      label: 'Max / Account',
      value: qos.limits.max.jobs.active_jobs.per.account
    }
  ]
}

function qosResourcesLimits(qos: ClusterQos) {
  return [
    { id: 'GrpTRES', label: 'Global', value: qos.limits.max.tres.total },
    { id: 'MaxTRESPerUser', label: 'Max / User', value: qos.limits.max.tres.per.user },
    { id: 'MaxTRESPerAccount', label: 'Max / Account', value: qos.limits.max.tres.per.account },
    { id: 'MaxTRESPerJob', label: 'Max / Job', value: qos.limits.max.tres.per.job },
    { id: 'MaxTRESPerNode', label: 'Max / Node', value: qos.limits.max.tres.per.node }
  ]
}

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

watch(totalPages, (newLastPage) => {
  if (page.value > newLastPage) {
    page.value = newLastPage
    updateQueryParameters()
  }
})

if (route.query.page) {
  page.value = parsePositivePage(route.query.page)
}
if (route.query.page_size) {
  pageSize.value = parsePageSize(route.query.page_size)
}
</script>

<template>
  <ClusterMainLayout menu-entry="qos" :cluster="cluster" :breadcrumb="[{ title: 'QOS' }]">
    <PageHeader
      title="QOS"
      description="Quality-of-service policies, resource ceilings and scheduling constraints defined on this cluster."
      :metric-value="loaded ? data?.length : undefined"
      metric-label="qos policies"
    />
    <QosHelpModal
      :help-modal-show="helpModalShow"
      :limit="modalQosLimit"
      @close-help-modal="closeHelpModal"
    />
    <ErrorAlert v-if="unable"
      >Unable to retrieve qos from cluster
      <span class="font-medium">{{ cluster }}</span></ErrorAlert
    >
    <InfoAlert v-else-if="loaded && data?.length == 0"
      >No qos defined on cluster <span class="font-medium">{{ cluster }}</span></InfoAlert
    >
    <div v-else class="ui-section-stack">
      <div class="ui-table-shell -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle">
          <table class="ui-table min-w-full">
            <thead>
              <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                <th scope="col" class="py-3.5 pr-3 text-left align-top sm:pl-6 lg:min-w-[250px] lg:pl-8">
                  Name
                </th>
                <th scope="col" class="w-24 px-3 py-3.5 text-left align-top">Priority</th>
                <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">Jobs</th>
                <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">Resources</th>
                <th scope="col" class="w-12 px-3 py-3.5 text-left">Time</th>
                <th scope="col" class="hidden w-12 px-3 py-3.5 text-left align-top 2xl:table-cell">Flags</th>
                <th scope="col" class="w-12"></th>
              </tr>
            </thead>
            <tbody
              v-if="loaded"
              class="divide-y divide-gray-200 text-sm text-gray-600 dark:divide-gray-700 dark:text-gray-300"
            >
              <tr v-for="qos in pagedQos" :key="qos.name">
                <td class="py-3 pr-3 whitespace-nowrap text-[var(--color-brand-ink-strong)] sm:pl-6 lg:pl-8">
                  <p class="text-base font-medium">{{ qos.name }}</p>
                  <p class="text-gray-500 text-[var(--color-brand-muted)]">{{ qos.description }}</p>
                </td>
                <td class="px-3 py-3 whitespace-nowrap">{{ qos.priority.number }}</td>
                <td class="hidden px-3 py-3 whitespace-nowrap lg:table-cell">
                  <dl>
                    <div
                      v-for="limit in qosJobLimits(qos)"
                      :key="limit.id"
                      :class="[limit.value.set ? '' : 'text-[var(--color-brand-muted)]/35', 'invisible flex leading-relaxed hover:visible']"
                    >
                      <button @click="openHelpModal(qos.name, limit.id, limit.value)" class="mr-1 -ml-5">
                        <QuestionMarkCircleIcon class="h-5 w-5 text-[var(--color-slurmweb-dark)]" />
                      </button>
                      <dt class="visible">{{ limit.label }}:</dt>
                      <dd class="visible ml-2">{{ renderClusterOptionalNumber(limit.value) }}</dd>
                    </div>
                  </dl>
                </td>
                <td class="hidden px-3 py-3 whitespace-nowrap lg:table-cell">
                  <dl>
                    <div
                      v-for="limit in qosResourcesLimits(qos)"
                      :key="limit.id"
                      :class="[limit.value.length > 0 ? '' : 'text-[var(--color-brand-muted)]/35', 'invisible flex items-baseline leading-relaxed hover:visible']"
                    >
                      <button @click="openHelpModal(qos.name, limit.id, limit.value)" class="mr-1 -ml-5 self-center">
                        <QuestionMarkCircleIcon class="h-5 w-5 text-[var(--color-slurmweb-dark)]" />
                      </button>
                      <dt class="visible">{{ limit.label }}:</dt>
                      <dd class="visible ml-2 font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                    </div>
                  </dl>
                </td>
                <td class="px-3 py-3 whitespace-nowrap">
                  <div
                    :class="[
                      qos.limits.max.wall_clock.per.job.set ? '' : 'text-[var(--color-brand-muted)]/35',
                      'invisible flex items-baseline leading-relaxed hover:visible'
                    ]"
                  >
                    <button
                      @click="openHelpModal(qos.name, 'MaxWall', qos.limits.max.wall_clock.per.job)"
                      class="mr-1 -ml-5 self-center"
                    >
                      <QuestionMarkCircleIcon class="h-5 w-5 text-[var(--color-slurmweb-dark)]" />
                    </button>
                    <span class="visible">{{ renderWalltime(qos.limits.max.wall_clock.per.job) }}</span>
                  </div>
                </td>
                <td class="hidden px-3 py-3 2xl:table-cell">
                  <span v-for="flag in qos.flags" :key="flag" class="ui-chip m-1">{{ renderQosFlag(flag) }}</span>
                </td>
                <td class="py-4 pl-3 text-right whitespace-nowrap sm:pr-6 lg:pr-8">
                  <RouterLink
                    :to="{ name: 'jobs', params: { cluster: cluster }, query: { qos: qos.name } }"
                    class="font-bold text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
                    >View jobs</RouterLink
                  >
                </td>
              </tr>
            </tbody>
            <TableSkeletonRows
              v-else
              :columns="7"
              :rows="6"
              first-cell-class="sm:pl-6 lg:pl-8"
              cell-class="px-3"
            />
            </table>
            <PaginationControls
              v-if="loaded"
              :page="page"
              :page-size="pageSize"
              :total="data?.length ?? 0"
              item-label="qos policy"
              @update:page="updatePage"
              @update:page-size="updatePageSize"
            />
          </div>
        </div>
      </div>
  </ClusterMainLayout>
</template>
