<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useRuntimeStore } from '@/stores/runtime'
import type { JobSortCriterion, JobSortOrder } from '@/stores/runtime/jobs'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { compareClusterJobSortOrder } from '@/composables/GatewayAPI'
import type { ClusterJob, JobsQuery } from '@/composables/GatewayAPI'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import JobsSorter from '@/components/jobs/JobsSorter.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import JobsFiltersPanel from '@/components/jobs/JobsFiltersPanel.vue'
import JobsFiltersBar from '@/components/jobs/JobsFiltersBar.vue'
import JobResources from '@/components/jobs/JobResources.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import TableSkeletonRows from '@/components/TableSkeletonRows.vue'
import PaginationControls from '@/components/PaginationControls.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import PartitionLinkChip from '@/components/PartitionLinkChip.vue'
import { lastPage, parsePageSize, parsePositivePage, type PageSizeOption } from '@/composables/Pagination'
import { useAuthStore } from '@/stores/auth'
import { createStaticSearchSource } from '@/composables/searchSelect'

import {
  ArrowPathIcon,
  PencilSquareIcon,
  PlusSmallIcon,
  WindowIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'

const { cluster } = defineProps<{ cluster: string }>()

const route = useRoute()
const { t } = useI18n()
const { data, unable, loaded, refreshing, refresh, setCluster, setParam } = useClusterDataPoller<ClusterJob[]>(
  cluster,
  'jobs',
  30000
)

const router = useRouter()
const runtimeStore = useRuntimeStore()
const authStore = useAuthStore()
const gateway = useGatewayAPI()
const hydratingQuery = ref(false)
const operationError = ref<string | null>(null)
const operationBusy = ref(false)
const submitOpen = ref(false)
const editOpen = ref(false)
const cancelOpen = ref(false)
const selectedJob = ref<ClusterJob | null>(null)
const partitionSearchSource = createStaticSearchSource(async () =>
  (await gateway.partitions(cluster)).map((partition) => ({
    value: partition.name,
    label: partition.name
  }))
)
const qosSearchSource = createStaticSearchSource(async () =>
  (await gateway.qos(cluster)).map((qos) => ({
    value: qos.name,
    label: qos.name,
    description: qos.description || qos.name
  }))
)

function compareClusterJob(a: ClusterJob, b: ClusterJob): number {
  return compareClusterJobSortOrder(a, b, runtimeStore.jobs.sort, runtimeStore.jobs.order)
}

function commaSeparated(values: string[]): string | undefined {
  const normalized = values.map((value) => value.trim()).filter((value) => value.length > 0)
  return normalized.length ? normalized.join(',') : undefined
}

function buildJobsQuery(): JobsQuery | undefined {
  const query: JobsQuery = {
    users: commaSeparated(runtimeStore.jobs.filters.users),
    states: commaSeparated(runtimeStore.jobs.filters.states),
    accounts: commaSeparated(runtimeStore.jobs.filters.accounts),
    qos: commaSeparated(runtimeStore.jobs.filters.qos),
    partitions: commaSeparated(runtimeStore.jobs.filters.partitions)
  }
  return Object.values(query).some((value) => value !== undefined) ? query : undefined
}

function updateJobsPollerParam() {
  setParam(buildJobsQuery())
}

const sortedJobs = computed(() => {
  if (data.value) {
    const result = [...data.value].filter((job) => runtimeStore.jobs.matchesFilters(job))
    return result.sort(compareClusterJob)
  }
  return []
})

const lastpage = computed(() => {
  return lastPage(sortedJobs.value.length, runtimeStore.jobs.pageSize)
})
const firstjob = computed(() => {
  return (runtimeStore.jobs.page - 1) * runtimeStore.jobs.pageSize
})
const lastjob = computed(() => {
  return Math.min(firstjob.value + runtimeStore.jobs.pageSize, sortedJobs.value.length)
})

function jobPriority(job: ClusterJob): string {
  if (!job.job_state.includes('PENDING')) return '-'
  if (job.priority.set) {
    if (job.priority.infinite) {
      return '∞'
    }
    return job.priority.number.toString()
  }
  return '-'
}

const canSubmitJobs = computed(
  () =>
    runtimeStore.hasRoutePermission(cluster, 'jobs', 'edit') ||
    runtimeStore.hasRoutePermission(cluster, 'jobs', 'edit', 'self')
)

function canEditJob(job: ClusterJob): boolean {
  return (
    runtimeStore.hasRoutePermission(cluster, 'jobs', 'edit') ||
    (runtimeStore.hasRoutePermission(cluster, 'jobs', 'edit', 'self') &&
      authStore.username === job.user_name)
  )
}

function canCancelJob(job: ClusterJob): boolean {
  return (
    runtimeStore.hasRoutePermission(cluster, 'jobs', 'delete') ||
    (runtimeStore.hasRoutePermission(cluster, 'jobs', 'delete', 'self') &&
      authStore.username === job.user_name)
  )
}

function openSubmitDialog() {
  operationError.value = null
  submitOpen.value = true
}

function openEditDialog(job: ClusterJob) {
  selectedJob.value = job
  operationError.value = null
  editOpen.value = true
}

function openCancelDialog(job: ClusterJob) {
  selectedJob.value = job
  operationError.value = null
  cancelOpen.value = true
}

async function submitJob(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.submit_job(cluster, {
      name: payload.name || undefined,
      script: payload.script || undefined,
      partition: payload.partition || undefined,
      account: payload.account || undefined,
      qos: payload.qos || undefined
    })
    runtimeStore.reportInfo(t('pages.jobs.notifications.submitRequested', { cluster }))
    submitOpen.value = false
    await refresh()
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function editJob(payload: Record<string, string>) {
  if (!selectedJob.value) return
  operationBusy.value = true
  operationError.value = null
  try {
    const memoryPerCpu = parsePositiveInteger(payload.memory_per_cpu_mb)
    await gateway.update_job(cluster, selectedJob.value.job_id, {
      partition: payload.partition || undefined,
      qos: payload.qos || undefined,
      priority: payload.priority ? Number(payload.priority) : null,
      time_limit: payload.time_limit || undefined,
      comment: payload.comment || undefined,
      memory_per_cpu:
        memoryPerCpu == null
          ? undefined
          : { set: true, infinite: false, number: memoryPerCpu }
    })
    runtimeStore.reportInfo(
      t('pages.jobs.notifications.updateRequested', { jobId: selectedJob.value.job_id })
    )
    editOpen.value = false
    await refresh()
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

function parsePositiveInteger(value: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(t('pages.jobs.dialogs.edit.errors.invalidMemoryPerCpu'))
  }
  return parsed
}

async function cancelJob(payload: Record<string, string>) {
  if (!selectedJob.value) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.cancel_job(cluster, selectedJob.value.job_id, {
      signal: payload.signal || undefined,
      reason: payload.reason || undefined
    })
    runtimeStore.reportInfo(
      t('pages.jobs.notifications.cancelRequested', { jobId: selectedJob.value.job_id })
    )
    cancelOpen.value = false
    await refresh()
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

function sortJobs() {
  runtimeStore.jobs.page = 1
  updateQueryParameters()
}

function resetPageAndUpdateQueryParameters() {
  if (hydratingQuery.value) return
  runtimeStore.jobs.page = 1
  updateQueryParameters()
  updateJobsPollerParam()
}

function updatePage(page: number) {
  runtimeStore.jobs.page = page
  updateQueryParameters()
}

function updatePageSize(pageSize: PageSizeOption) {
  runtimeStore.jobs.pageSize = pageSize
  runtimeStore.jobs.page = 1
  updateQueryParameters()
}

function updateQueryParameters() {
  router.push({ name: 'jobs', query: runtimeStore.jobs.query() as LocationQueryRaw })
}

watch(
  () => runtimeStore.jobs.filters.states,
  () => resetPageAndUpdateQueryParameters(),
  { deep: true }
)
watch(
  () => runtimeStore.jobs.filters.users,
  () => resetPageAndUpdateQueryParameters(),
  { deep: true }
)
watch(
  () => runtimeStore.jobs.filters.accounts,
  () => resetPageAndUpdateQueryParameters(),
  { deep: true }
)
watch(
  () => runtimeStore.jobs.filters.qos,
  () => resetPageAndUpdateQueryParameters(),
  { deep: true }
)
watch(
  () => runtimeStore.jobs.filters.partitions,
  () => resetPageAndUpdateQueryParameters(),
  { deep: true }
)
watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

watch(lastpage, (newLastPage) => {
  runtimeStore.jobs.page = Math.min(runtimeStore.jobs.page, newLastPage)
  if (route.query.page && parseInt(route.query.page as string) > newLastPage) {
    updateQueryParameters()
  }
})

onMounted(async () => {
  hydratingQuery.value = true
  if (
    ['sort', 'states', 'users', 'accounts', 'page', 'page_size', 'qos', 'partitions'].some(
      (parameter) => parameter in route.query
    )
  ) {
    runtimeStore.jobs.filters = {
      states: [],
      users: [],
      accounts: [],
      qos: [],
      partitions: []
    }

    if (route.query.sort && runtimeStore.jobs.isValidSortCriterion(route.query.sort)) {
      runtimeStore.jobs.sort = route.query.sort as JobSortCriterion
    }
    if (route.query.order && runtimeStore.jobs.isValidSortOrder(route.query.order)) {
      runtimeStore.jobs.order = route.query.order as JobSortOrder
    }
    if (route.query.page) {
      runtimeStore.jobs.page = parsePositivePage(route.query.page)
    }
    if (route.query.page_size) {
      runtimeStore.jobs.pageSize = parsePageSize(route.query.page_size)
    }
    if (route.query.states) {
      runtimeStore.jobs.filters.states = (route.query.states as string).split(',')
    }
    if (route.query.users) {
      runtimeStore.jobs.filters.users = (route.query.users as string).split(',')
    }
    if (route.query.accounts) {
      runtimeStore.jobs.filters.accounts = (route.query.accounts as string).split(',')
    }
    if (route.query.qos) {
      runtimeStore.jobs.filters.qos = (route.query.qos as string).split(',')
    }
    if (route.query.partitions) {
      runtimeStore.jobs.filters.partitions = (route.query.partitions as string).split(',')
    }
  } else {
    updateQueryParameters()
  }
  await nextTick()
  hydratingQuery.value = false
  updateJobsPollerParam()
})
</script>

<template>
  <ClusterMainLayout
    menu-entry="jobs"
    :cluster="cluster"
    :breadcrumb="[{ title: 'shell.mainMenu.jobs' }]"
  >
    <div class="ui-page ui-page-wide ui-content-workspace">
      <JobsFiltersPanel :cluster="cluster" :nb-jobs="sortedJobs.length" />

      <PageHeader
        title="pages.jobs.title"
        description="pages.jobs.description"
        :metric-value="loaded ? sortedJobs.length : undefined"
        :metric-label="
          sortedJobs.length === 1 ? 'pages.jobs.metricLabel' : 'pages.jobs.metricLabelPlural'
        "
      >
        <template #actions>
          <div class="ui-page-tools-end">
            <button
              type="button"
              class="ui-button-secondary"
              :disabled="refreshing"
              @click="refresh"
            >
              <ArrowPathIcon
                :class="['h-5 w-5', refreshing ? 'animate-spin' : '']"
                aria-hidden="true"
              />
              {{ t('common.buttons.refresh') }}
            </button>
            <button
              type="button"
              class="ui-button-secondary"
              @click="runtimeStore.jobs.openFiltersPanel = true"
            >
              <PlusSmallIcon class="h-5 w-5" aria-hidden="true" />
              {{ t('pages.jobs.addFilters') }}
            </button>
            <button
              v-if="canSubmitJobs"
              type="button"
              class="ui-button-primary"
              @click="openSubmitDialog"
            >
              {{ t('pages.jobs.submitJob') }}
            </button>
          </div>
        </template>
      </PageHeader>

      <section aria-labelledby="filter-heading" class="-mx-4 -my-2 sm:-mx-6 lg:-mx-8">
        <h2 id="filter-heading" class="sr-only">{{ t('pages.jobs.headingFilters') }}</h2>

        <div class="pb-4">
          <div class="ui-page-tools mx-auto px-4 sm:px-6 lg:px-8">
            <JobsSorter @sort="sortJobs" />
          </div>
        </div>
        <JobsFiltersBar />
      </section>

      <div class="ui-results-layout">
        <ErrorAlert v-if="unable"
          >{{ t('pages.jobs.unableToRetrieve', { cluster }) }}</ErrorAlert
        >
        <InfoAlert v-else-if="loaded && data?.length == 0"
          >{{ t('pages.jobs.noJobs', { cluster }) }}</InfoAlert
        >
        <div v-else class="ui-results-workspace">
          <div class="ui-table-shell ui-results-card">
            <div class="ui-table-scroll">
              <div class="ui-table-scroll-inner py-2">
              <table class="ui-table min-w-full">
              <thead>
                <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                  <th scope="col" class="w-12 py-3.5 pr-3 text-left sm:pl-6 lg:pl-8">#ID</th>
                  <th scope="col" class="w-16 px-3 py-3.5 text-left">
                    {{ t('tables.jobs.columns.state') }}
                  </th>
                  <th scope="col" class="px-3 py-3.5 text-left">
                    {{ t('tables.jobs.columns.userAccount') }}
                  </th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left sm:table-cell">
                    {{ t('tables.jobs.columns.resources') }}
                  </th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">
                    {{ t('tables.jobs.columns.partition') }}
                  </th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">
                    {{ t('tables.jobs.columns.qos') }}
                  </th>
                  <th scope="col" class="hidden px-3 py-3.5 text-center sm:table-cell">
                    {{ t('tables.jobs.columns.priority') }}
                  </th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left 2xl:table-cell 2xl:min-w-[100px]">
                    {{ t('tables.jobs.columns.reason') }}
                  </th>
                  <th scope="col" class="max-w-fit py-3.5 pr-4 pl-3 text-right sm:pr-6 lg:pr-8">
                    {{ t('tables.jobs.columns.actions') }}
                  </th>
                </tr>
              </thead>
              <tbody
                v-if="loaded"
                class="divide-y divide-gray-200 text-sm text-gray-500 dark:divide-gray-700 dark:text-gray-300"
              >
                <tr v-for="job in sortedJobs.slice(firstjob, lastjob)" :key="job.job_id">
                  <td class="py-3 pr-3 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)] sm:pl-6 lg:pl-8">
                    {{ job.job_id }}
                  </td>
                  <td class="px-3 py-3 whitespace-nowrap">
                    <JobStatusBadge :status="job.job_state" />
                  </td>
                  <td class="px-3 py-3 whitespace-nowrap">
                    <RouterLink
                      :to="{ name: 'user', params: { cluster, user: job.user_name } }"
                      class="ui-user-link"
                    >
                      {{ job.user_name }}
                    </RouterLink>
                    <span class="text-[var(--color-brand-muted)]">({{ job.account }})</span>
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap sm:table-cell">
                    <JobResources :job="job" />
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap xl:table-cell">
                    <PartitionLinkChip :cluster="cluster" :partition="job.partition" />
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap xl:table-cell">
                    {{ job.qos }}
                  </td>
                  <td class="hidden px-3 py-3 text-center whitespace-nowrap sm:table-cell">
                    {{ jobPriority(job) }}
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap 2xl:table-cell">
                    <template v-if="job.state_reason != 'None'">
                      {{ job.state_reason }}
                    </template>
                  </td>
                  <td class="h-full py-3 text-right font-medium">
                    <div class="flex flex-wrap items-center justify-end gap-2 pr-4 sm:pr-6 lg:pr-8">
                      <button
                        v-if="canEditJob(job)"
                        type="button"
                        class="ui-button-warning"
                        @click="openEditDialog(job)"
                      >
                        <PencilSquareIcon class="h-4 w-4" aria-hidden="true" />
                        {{ t('pages.jobs.actions.edit') }}
                      </button>
                      <button
                        v-if="canCancelJob(job)"
                        type="button"
                        class="ui-button-danger"
                        @click="openCancelDialog(job)"
                      >
                        <XMarkIcon class="h-4 w-4" aria-hidden="true" />
                        {{ t('pages.jobs.actions.cancel') }}
                      </button>
                      <RouterLink
                        :to="{ name: 'job', params: { cluster: cluster, id: job.job_id } }"
                        class="ui-button-secondary"
                      >
                        <WindowIcon class="h-4 w-4" aria-hidden="true" />
                        {{ t('pages.jobs.actions.view') }}
                      </RouterLink>
                    </div>
                  </td>
                </tr>
              </tbody>
              <TableSkeletonRows
                v-else
                :columns="9"
                :rows="8"
                first-cell-class="sm:pl-6 lg:pl-8"
                cell-class="px-3"
              />
              </table>
              </div>
            </div>
          </div>
          <div class="ui-results-dock">
            <PaginationControls
              v-if="loaded"
              :page="runtimeStore.jobs.page"
              :page-size="runtimeStore.jobs.pageSize"
              :total="sortedJobs.length"
              :item-label="t('common.entities.job')"
              @update:page="updatePage"
              @update:page-size="updatePageSize"
            />
          </div>
        </div>
      </div>
    </div>

    <ActionDialog
      :open="submitOpen"
      title="pages.jobs.dialogs.submit.title"
      description="pages.jobs.dialogs.submit.description"
      submit-label="pages.jobs.dialogs.submit.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'name', label: 'pages.jobs.dialogs.submit.fields.name', required: true },
        {
          key: 'script',
          label: 'pages.jobs.dialogs.submit.fields.script',
          type: 'textarea',
          required: true
        },
        {
          key: 'partition',
          label: 'pages.jobs.dialogs.submit.fields.partition',
          type: 'search-select',
          source: partitionSearchSource
        },
        { key: 'account', label: 'pages.jobs.dialogs.submit.fields.account' },
        {
          key: 'qos',
          label: 'pages.jobs.dialogs.submit.fields.qos',
          type: 'search-select',
          source: qosSearchSource
        }
      ]"
      @close="submitOpen = false"
      @submit="submitJob"
    />

    <ActionDialog
      :open="editOpen"
      title="pages.jobs.dialogs.edit.title"
      :description="selectedJob ? 'pages.jobs.dialogs.edit.description' : undefined"
      :description-params="selectedJob ? { jobId: selectedJob.job_id, cluster } : undefined"
      submit-label="pages.jobs.dialogs.edit.submit"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        partition: selectedJob?.partition ?? '',
        qos: selectedJob?.qos ?? '',
        priority: selectedJob?.priority?.set ? String(selectedJob.priority.number) : '',
        memory_per_cpu_mb: '',
        time_limit: '',
        comment: ''
      }"
      :fields="[
        {
          key: 'partition',
          label: 'pages.jobs.dialogs.edit.fields.partition',
          type: 'search-select',
          source: partitionSearchSource
        },
        {
          key: 'qos',
          label: 'pages.jobs.dialogs.edit.fields.qos',
          type: 'search-select',
          source: qosSearchSource
        },
        { key: 'priority', label: 'pages.jobs.dialogs.edit.fields.priority', type: 'number' },
        {
          key: 'memory_per_cpu_mb',
          label: 'pages.jobs.dialogs.edit.fields.memoryPerCpuMb',
          type: 'number',
          hint: 'pages.jobs.dialogs.edit.fields.memoryPerCpuHint',
          tooltip: 'pages.jobs.dialogs.edit.fields.memoryPerCpuTooltip'
        },
        { key: 'time_limit', label: 'pages.jobs.dialogs.edit.fields.timeLimit' },
        { key: 'comment', label: 'pages.jobs.dialogs.edit.fields.comment', type: 'textarea' }
      ]"
      @close="editOpen = false"
      @submit="editJob"
    />

    <ActionDialog
      :open="cancelOpen"
      title="pages.jobs.dialogs.cancel.title"
      :description="selectedJob ? 'pages.jobs.dialogs.cancel.description' : undefined"
      :description-params="selectedJob ? { jobId: selectedJob.job_id } : undefined"
      submit-label="pages.jobs.dialogs.cancel.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'signal', label: 'pages.jobs.dialogs.cancel.fields.signal' },
        { key: 'reason', label: 'pages.jobs.dialogs.cancel.fields.reason', type: 'textarea' }
      ]"
      @close="cancelOpen = false"
      @submit="cancelJob"
    />
  </ClusterMainLayout>
</template>
