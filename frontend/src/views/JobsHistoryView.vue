<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type {
  JobHistoryRecord,
  JobHistoryFilters,
  JobHistorySortCriterion,
  JobHistorySortOrder
} from '@/composables/GatewayAPI'
import { splitJobHistoryState } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobHistoryResources from '@/components/jobs/JobHistoryResources.vue'
import JobsHistoryFiltersPanel from '@/components/jobs/JobsHistoryFiltersPanel.vue'
import JobsHistoryFiltersBar from '@/components/jobs/JobsHistoryFiltersBar.vue'
import JobsHistorySorter from '@/components/jobs/JobsHistorySorter.vue'
import { WindowIcon } from '@heroicons/vue/24/outline'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/20/solid'
import { PlusSmallIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{ cluster: string }>()

const gateway = useGatewayAPI()
const router = useRouter()
const route = useRoute()
const runtimeStore = useRuntimeStore()
const historyStore = runtimeStore.jobsHistory
const { filters, page, sort, order } = storeToRefs(historyStore)

const loading = ref(false)
const error = ref<string | null>(null)
const jobs = ref<JobHistoryRecord[]>([])
const total = ref(0)
const pageSize = 50
const filtersOpen = ref(false)

async function fetchHistory() {
  loading.value = true
  error.value = null
  try {
    const payload: JobHistoryFilters = {
      ...filters.value,
      page: page.value,
      page_size: pageSize,
      sort: sort.value,
      order: order.value
    }
    ;(Object.keys(payload) as (keyof JobHistoryFilters)[]).forEach((key) => {
      if (payload[key] === '' || payload[key] === undefined) delete payload[key]
    })
    const response = await gateway.jobs_history(props.cluster, payload)
    jobs.value = response.jobs
    total.value = response.total
  } catch (caughtError: unknown) {
    error.value = caughtError instanceof Error ? caughtError.message : String(caughtError)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  updateQueryParameters()
}

function updateQueryParameters() {
  router.push({
    name: 'jobs-history',
    params: { cluster: props.cluster },
    query: historyStore.query() as LocationQueryRaw
  })
}

function sortHistory(newSort?: JobHistorySortCriterion, newOrder?: JobHistorySortOrder) {
  if (newSort) sort.value = newSort
  if (newOrder) order.value = newOrder
  page.value = 1
  updateQueryParameters()
}

const lastpage = () => Math.max(Math.ceil(total.value / pageSize), 1)

function historyJobPriority(job: JobHistoryRecord): string {
  const states = splitJobHistoryState(job.job_state)
  if (!states.includes('PENDING')) return '-'
  return job.priority != null ? String(job.priority) : '-'
}

function fmtTime(value: string | null | undefined) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function jobsPages(): { id: number; ellipsis: boolean }[] {
  const result: { id: number; ellipsis: boolean }[] = []
  let ellipsis = false
  const last = lastpage()
  for (let currentPage = 1; currentPage <= last; currentPage++) {
    if (
      currentPage < 3 ||
      currentPage > last - 2 ||
      (currentPage >= page.value - 1 && currentPage <= page.value + 1)
    ) {
      ellipsis = false
      result.push({ id: currentPage, ellipsis: false })
    } else if (!ellipsis) {
      ellipsis = true
      result.push({ id: currentPage, ellipsis: true })
    }
  }
  return result
}

watch(
  () => route.query,
  () => {
    historyStore.hydrate(route.query)
    fetchHistory()
  },
  { immediate: true }
)

watch(
  () => props.cluster,
  () => {
    fetchHistory()
  }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="jobs-history"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Jobs History' }]"
  >
    <div class="ui-page ui-page-wide">
      <JobsHistoryFiltersPanel
        :open="filtersOpen"
        :filters="filters"
        :total="total"
        @close="filtersOpen = false"
        @search="applyFilters"
      />

      <PageHeader
        title="Jobs History"
        description="Historical job records with scheduler context, state transitions and searchable execution metadata."
        :metric-value="loading || error ? undefined : total"
        :metric-label="`record${total === 1 ? '' : 's'} found`"
      />

      <section aria-labelledby="history-filter-heading" class="-mx-4 -my-2 sm:-mx-6 lg:-mx-8">
        <h2 id="history-filter-heading" class="sr-only">Filters</h2>
        <div class="pb-4">
          <div class="mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-8">
            <JobsHistorySorter
              :sort="sort"
              :order="order"
              @update:sort="sortHistory($event)"
              @update:order="sortHistory(undefined, $event)"
            />
            <button type="button" class="ui-button-primary" @click="filtersOpen = true">
              <PlusSmallIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
              Add filters
            </button>
          </div>
        </div>
        <JobsHistoryFiltersBar :filters="filters" @search="applyFilters" />
      </section>

      <div class="mt-8 flow-root">
        <ErrorAlert v-if="error">{{ error }}</ErrorAlert>
        <div v-else-if="loading" class="text-[var(--color-brand-muted)] sm:pl-6 lg:pl-8">
          <LoadingSpinner :size="5" />
          Loading job history...
        </div>
        <InfoAlert v-else-if="jobs.length === 0">
          No job history records found on cluster <span class="font-medium">{{ cluster }}</span>
        </InfoAlert>
        <div v-else class="ui-table-shell -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle">
            <table class="ui-table min-w-full">
              <thead>
                <tr>
                  <th scope="col" class="w-12 py-3.5 pr-3 text-left sm:pl-6 lg:pl-8">#ID</th>
                  <th scope="col" class="min-w-[11rem] px-3 py-3.5 text-left">Submit Time</th>
                  <th scope="col" class="w-16 px-3 py-3.5 text-left">State</th>
                  <th scope="col" class="px-3 py-3.5 text-left">User (account)</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left sm:table-cell">Resources</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">Partition</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">QOS</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-center sm:table-cell">Priority</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left 2xl:table-cell">Reason</th>
                  <th scope="col" class="py-3.5 pr-4 pl-3 sm:pr-6 lg:pr-8">
                    <span class="sr-only">View</span>
                  </th>
                </tr>
              </thead>
              <tbody class="text-sm text-[var(--color-brand-muted)]">
                <tr v-for="job in jobs" :key="job.id">
                  <td class="py-4 pr-3 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)] sm:pl-6 lg:pl-8">
                    {{ job.job_id }}
                  </td>
                  <td class="px-3 py-4 text-xs tabular-nums whitespace-nowrap">
                    {{ fmtTime(job.submit_time) }}
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">
                    <JobStatusBadge :status="splitJobHistoryState(job.job_state)" />
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">
                    {{ job.user_name ?? '-' }} ({{ job.account ?? '-' }})
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap sm:table-cell">
                    <JobHistoryResources :job="job" />
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap xl:table-cell">
                    {{ job.partition ?? '-' }}
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap xl:table-cell">
                    {{ job.qos ?? '-' }}
                  </td>
                  <td class="hidden px-3 py-4 text-center whitespace-nowrap sm:table-cell">
                    {{ historyJobPriority(job) }}
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap 2xl:table-cell">
                    <template v-if="job.state_reason != 'None'">
                      {{ job.state_reason }}
                    </template>
                  </td>
                  <td class="h-full text-right font-medium">
                    <RouterLink
                      :to="{ name: 'job-history', params: { cluster: cluster, id: job.id } }"
                      class="text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
                    >
                      <WindowIcon class="mr-4 inline-block h-5 w-5 lg:mr-6" aria-hidden="true" />
                      <span class="sr-only">View {{ job.job_id }}</span>
                    </RouterLink>
                  </td>
                </tr>
              </tbody>
            </table>

            <div class="flex items-center justify-between border-t border-[rgba(80,105,127,0.08)] px-4 py-3 sm:px-6">
              <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm text-[var(--color-brand-muted)]">
                    Showing
                    <span class="font-medium">{{ (page - 1) * pageSize + 1 }}</span>
                    to
                    <span class="font-medium">{{ Math.min(page * pageSize, total) }}</span>
                    of
                    <span class="font-medium">{{ total }}</span>
                    records
                  </p>
                </div>
                <div>
                  <nav
                    v-if="lastpage() > 1"
                    class="isolate inline-flex -space-x-px rounded-full shadow-[var(--shadow-soft)]"
                    aria-label="Pagination"
                  >
                    <button
                      :class="[
                        page === 1
                          ? 'cursor-default bg-gray-100 text-gray-100'
                          : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
                        'relative inline-flex items-center rounded-l-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
                      ]"
                      @click="page > 1 && (page--, updateQueryParameters())"
                    >
                      <span class="sr-only">Previous</span>
                      <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                    <template v-for="historyPage in jobsPages()" :key="historyPage.id">
                      <button
                        v-if="historyPage.ellipsis"
                        class="relative z-10 inline-flex items-center bg-white px-4 py-2 text-xs font-semibold text-[var(--color-brand-muted)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20"
                      >
                        ...
                      </button>
                      <button
                        v-else
                        :class="[
                          historyPage.id === page
                            ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                            : 'bg-white text-[var(--color-brand-ink-strong)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset hover:bg-[rgba(182,232,44,0.12)]',
                          'relative z-10 inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20'
                        ]"
                        @click="page = historyPage.id; updateQueryParameters()"
                      >
                        {{ historyPage.id }}
                      </button>
                    </template>
                    <button
                      :class="[
                        page === lastpage()
                          ? 'cursor-default bg-gray-100 text-gray-100'
                          : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
                        'relative inline-flex items-center rounded-r-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
                      ]"
                      @click="page < lastpage() && (page++, updateQueryParameters())"
                    >
                      <span class="sr-only">Next</span>
                      <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
