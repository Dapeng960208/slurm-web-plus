<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import type { JobSortCriterion, JobSortOrder } from '@/stores/runtime/jobs'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { compareClusterJobSortOrder } from '@/composables/GatewayAPI'
import type { ClusterJob } from '@/composables/GatewayAPI'
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
import { lastPage, parsePageSize, parsePositivePage, type PageSizeOption } from '@/composables/Pagination'
import { useAuthStore } from '@/stores/auth'

import { PencilSquareIcon, PlusSmallIcon, WindowIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const { cluster } = defineProps<{ cluster: string }>()

const route = useRoute()
const { data, unable, loaded, setCluster } = useClusterDataPoller<ClusterJob[]>(
  cluster,
  'jobs',
  5000
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

function compareClusterJob(a: ClusterJob, b: ClusterJob): number {
  return compareClusterJobSortOrder(a, b, runtimeStore.jobs.sort, runtimeStore.jobs.order)
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
    runtimeStore.reportInfo(`Job submission requested on ${cluster}.`)
    submitOpen.value = false
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
    await gateway.update_job(cluster, selectedJob.value.job_id, {
      partition: payload.partition || undefined,
      qos: payload.qos || undefined,
      priority: payload.priority ? Number(payload.priority) : null,
      time_limit: payload.time_limit || undefined,
      comment: payload.comment || undefined
    })
    runtimeStore.reportInfo(`Job ${selectedJob.value.job_id} update requested.`)
    editOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
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
    runtimeStore.reportInfo(`Job ${selectedJob.value.job_id} cancel requested.`)
    cancelOpen.value = false
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
  () => resetPageAndUpdateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.users,
  () => resetPageAndUpdateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.accounts,
  () => resetPageAndUpdateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.qos,
  () => resetPageAndUpdateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.partitions,
  () => resetPageAndUpdateQueryParameters()
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
})
</script>

<template>
  <ClusterMainLayout menu-entry="jobs" :cluster="cluster" :breadcrumb="[{ title: 'Jobs' }]">
    <div class="ui-page ui-page-wide">
      <JobsFiltersPanel :cluster="cluster" :nb-jobs="sortedJobs.length" />

      <PageHeader
        title="Jobs"
        description="Queue visibility, active states, account context and fast drill-down into job details."
        :metric-value="loaded ? sortedJobs.length : undefined"
        :metric-label="`job${sortedJobs.length > 1 ? 's' : ''} found`"
      >
        <template #actions>
          <button v-if="canSubmitJobs" type="button" class="ui-button-primary" @click="openSubmitDialog">
            Submit job
          </button>
        </template>
      </PageHeader>

      <section aria-labelledby="filter-heading" class="-mx-4 -my-2 sm:-mx-6 lg:-mx-8">
        <h2 id="filter-heading" class="sr-only">Filters</h2>

        <div class="pb-4">
          <div class="mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-8">
            <JobsSorter @sort="sortJobs" />

            <button type="button" class="ui-button-primary" @click="runtimeStore.jobs.openFiltersPanel = true">
              <PlusSmallIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
              Add filters
            </button>
          </div>
        </div>
        <JobsFiltersBar />
      </section>

      <div class="ui-section-stack">
        <ErrorAlert v-if="unable"
          >Unable to retrieve jobs from cluster
          <span class="font-medium">{{ cluster }}</span></ErrorAlert
        >
        <InfoAlert v-else-if="loaded && data?.length == 0"
          >No jobs found on cluster <span class="font-medium">{{ cluster }}</span></InfoAlert
        >
        <div v-else class="ui-table-shell -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle">
            <table class="ui-table min-w-full">
              <thead>
                <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                  <th scope="col" class="w-12 py-3.5 pr-3 text-left sm:pl-6 lg:pl-8">#ID</th>
                  <th scope="col" class="w-16 px-3 py-3.5 text-left">State</th>
                  <th scope="col" class="px-3 py-3.5 text-left">User (account)</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left sm:table-cell">Resources</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">Partition</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">QOS</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-center sm:table-cell">Priority</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left 2xl:table-cell 2xl:min-w-[100px]">
                    Reason
                  </th>
                  <th scope="col" class="max-w-fit py-3.5 pr-4 pl-3 text-right sm:pr-6 lg:pr-8">
                    Actions
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
                    {{ job.partition }}
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
                        class="ui-button-secondary"
                        @click="openEditDialog(job)"
                      >
                        <PencilSquareIcon class="h-4 w-4" aria-hidden="true" />
                        Edit
                      </button>
                      <button
                        v-if="canCancelJob(job)"
                        type="button"
                        class="ui-button-secondary"
                        @click="openCancelDialog(job)"
                      >
                        <XMarkIcon class="h-4 w-4" aria-hidden="true" />
                        Cancel
                      </button>
                      <RouterLink
                        :to="{ name: 'job', params: { cluster: cluster, id: job.job_id } }"
                        class="ui-button-secondary"
                      >
                        <WindowIcon class="h-4 w-4" aria-hidden="true" />
                        View
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

            <PaginationControls
              v-if="loaded"
              :page="runtimeStore.jobs.page"
              :page-size="runtimeStore.jobs.pageSize"
              :total="sortedJobs.length"
              item-label="job"
              @update:page="updatePage"
              @update:page-size="updatePageSize"
            />
          </div>
        </div>
      </div>
    </div>

    <ActionDialog
      :open="submitOpen"
      title="Submit Job"
      description="Create a new Slurm job from the Jobs workspace."
      submit-label="Submit job"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'name', label: 'Job name', required: true },
        { key: 'script', label: 'Script', type: 'textarea', required: true },
        { key: 'partition', label: 'Partition' },
        { key: 'account', label: 'Account' },
        { key: 'qos', label: 'QOS' }
      ]"
      @close="submitOpen = false"
      @submit="submitJob"
    />

    <ActionDialog
      :open="editOpen"
      title="Edit Job"
      :description="selectedJob ? `Update job ${selectedJob.job_id} on ${cluster}.` : ''"
      submit-label="Save changes"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        partition: selectedJob?.partition ?? '',
        qos: selectedJob?.qos ?? '',
        priority: selectedJob?.priority?.set ? String(selectedJob.priority.number) : '',
        time_limit: '',
        comment: ''
      }"
      :fields="[
        { key: 'partition', label: 'Partition' },
        { key: 'qos', label: 'QOS' },
        { key: 'priority', label: 'Priority', type: 'number' },
        { key: 'time_limit', label: 'Time limit' },
        { key: 'comment', label: 'Comment', type: 'textarea' }
      ]"
      @close="editOpen = false"
      @submit="editJob"
    />

    <ActionDialog
      :open="cancelOpen"
      title="Cancel Job"
      :description="selectedJob ? `Cancel job ${selectedJob.job_id}. This action is destructive.` : ''"
      submit-label="Cancel job"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'signal', label: 'Signal' },
        { key: 'reason', label: 'Reason', type: 'textarea' }
      ]"
      @close="cancelOpen = false"
      @submit="cancelJob"
    />
  </ClusterMainLayout>
</template>
