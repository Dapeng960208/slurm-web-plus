<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import type { JobSortCriterion, JobSortOrder } from '@/stores/runtime/jobs'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { compareClusterJobSortOrder } from '@/composables/GatewayAPI'
import type { ClusterJob } from '@/composables/GatewayAPI'
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

import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/20/solid'
import { PlusSmallIcon, WindowIcon } from '@heroicons/vue/24/outline'

const { cluster } = defineProps<{ cluster: string }>()

const route = useRoute()
const { data, unable, loaded, initialLoading, setCluster } = useClusterDataPoller<ClusterJob[]>(
  cluster,
  'jobs',
  5000
)

const router = useRouter()
const runtimeStore = useRuntimeStore()

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
  return Math.max(Math.ceil(sortedJobs.value.length / 100), 1)
})
const firstjob = computed(() => {
  return (runtimeStore.jobs.page - 1) * 100
})
const lastjob = computed(() => {
  return Math.min(firstjob.value + 100, sortedJobs.value.length)
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

function sortJobs() {
  updateQueryParameters()
}

function updateQueryParameters() {
  router.push({ name: 'jobs', query: runtimeStore.jobs.query() as LocationQueryRaw })
}

watch(
  () => runtimeStore.jobs.filters.states,
  () => updateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.users,
  () => updateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.accounts,
  () => updateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.qos,
  () => updateQueryParameters()
)
watch(
  () => runtimeStore.jobs.filters.partitions,
  () => updateQueryParameters()
)
watch(
  () => runtimeStore.jobs.page,
  () => updateQueryParameters()
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

interface Page {
  id: number
  ellipsis: boolean
}

function jobsPages(): Page[] {
  const result: Page[] = []
  let ellipsis = false
  range(1, lastpage.value, 1).forEach((page) => {
    if (
      page < 3 ||
      page > lastpage.value - 2 ||
      (page >= runtimeStore.jobs.page - 1 && page <= runtimeStore.jobs.page + 1)
    ) {
      ellipsis = false
      result.push({ id: page, ellipsis: false })
    } else if (ellipsis === false) {
      ellipsis = true
      result.push({ id: page, ellipsis: true })
    }
  })
  return result
}

const range = (start: number, stop: number, step: number) =>
  Array.from({ length: (stop - start) / step + 1 }, (_, i) => start + i * step)

onMounted(() => {
  if (
    ['sort', 'states', 'users', 'accounts', 'page', 'qos', 'partitions'].some(
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
      runtimeStore.jobs.page = parseInt(route.query.page as string)
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
      />

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

      <div class="mt-8 flow-root">
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
                  <th scope="col" class="max-w-fit py-3.5 pr-4 pl-3 sm:pr-6 lg:pr-8">
                    <span class="sr-only">View</span>
                  </th>
                </tr>
              </thead>
              <tbody
                v-if="loaded"
                class="divide-y divide-gray-200 text-sm text-gray-500 dark:divide-gray-700 dark:text-gray-300"
              >
                <tr v-for="job in sortedJobs.slice(firstjob, lastjob)" :key="job.job_id">
                  <td class="py-4 pr-3 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)] sm:pl-6 lg:pl-8">
                    {{ job.job_id }}
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">
                    <JobStatusBadge :status="job.job_state" />
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">
                    {{ job.user_name }} ({{ job.account }})
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap sm:table-cell">
                    <JobResources :job="job" />
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap xl:table-cell">
                    {{ job.partition }}
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap xl:table-cell">
                    {{ job.qos }}
                  </td>
                  <td class="hidden px-3 py-4 text-center whitespace-nowrap sm:table-cell">
                    {{ jobPriority(job) }}
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap 2xl:table-cell">
                    <template v-if="job.state_reason != 'None'">
                      {{ job.state_reason }}
                    </template>
                  </td>
                  <td class="h-full text-right font-medium">
                    <RouterLink
                      :to="{ name: 'job', params: { cluster: cluster, id: job.job_id } }"
                      class="text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
                    >
                      <WindowIcon class="mr-4 inline-block h-5 w-5 lg:mr-6" aria-hidden="true" />
                      <span class="sr-only">View {{ job.job_id }}</span>
                    </RouterLink>
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

            <div class="flex items-center justify-between border-t border-[rgba(80,105,127,0.08)] px-4 py-3 sm:px-6">
              <div class="flex flex-1 justify-between sm:hidden">
                <a href="#" class="ui-button-secondary text-sm">Previous</a>
                <a href="#" class="ui-button-secondary relative ml-3 text-sm">Next</a>
              </div>
              <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p v-if="loaded" class="text-sm text-[var(--color-brand-muted)]">
                    Showing
                    <span class="font-medium">{{ firstjob }}</span>
                    to
                    <span class="font-medium">{{ lastjob }}</span>
                    of
                    <span class="font-medium">{{ sortedJobs.length }}</span>
                    jobs
                  </p>
                  <div v-else class="h-4 w-40 animate-pulse rounded-full bg-[rgba(80,105,127,0.12)]" />
                </div>
                <div>
                  <nav
                    v-if="loaded && lastpage > 1"
                    class="isolate inline-flex -space-x-px rounded-full shadow-[var(--shadow-soft)]"
                    aria-label="Pagination"
                  >
                    <button
                      :class="[
                        runtimeStore.jobs.page == 1
                          ? 'cursor-default bg-gray-100 text-gray-100'
                          : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
                        'relative inline-flex items-center rounded-l-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
                      ]"
                      @click="runtimeStore.jobs.page > 1 && (runtimeStore.jobs.page -= 1)"
                    >
                      <span class="sr-only">Previous</span>
                      <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                    <template v-for="page in jobsPages()" :key="page.id">
                      <button
                        v-if="page.ellipsis"
                        aria-current="page"
                        class="relative z-10 inline-flex items-center bg-white px-4 py-2 text-xs font-semibold text-[var(--color-brand-muted)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20"
                      >
                        ...
                      </button>
                      <button
                        v-else
                        aria-current="page"
                        :class="[
                          page.id == runtimeStore.jobs.page
                            ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                            : 'bg-white text-[var(--color-brand-ink-strong)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset hover:bg-[rgba(182,232,44,0.12)]',
                          'relative z-10 inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20'
                        ]"
                        @click="runtimeStore.jobs.page = page.id"
                      >
                        {{ page.id }}
                      </button>
                    </template>
                    <button
                      :class="[
                        runtimeStore.jobs.page == lastpage
                          ? 'cursor-default bg-gray-100 text-gray-100'
                          : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
                        'relative inline-flex items-center rounded-r-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
                      ]"
                      @click="runtimeStore.jobs.page < lastpage && (runtimeStore.jobs.page += 1)"
                    >
                      <span class="sr-only">Next</span>
                      <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                  </nav>
                  <div
                    v-else-if="initialLoading"
                    class="h-10 w-56 animate-pulse rounded-full bg-[rgba(80,105,127,0.12)]"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
