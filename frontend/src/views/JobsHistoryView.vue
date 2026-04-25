<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
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
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobHistoryResources from '@/components/jobs/JobHistoryResources.vue'
import JobsHistoryFiltersPanel from '@/components/jobs/JobsHistoryFiltersPanel.vue'
import JobsHistoryFiltersBar from '@/components/jobs/JobsHistoryFiltersBar.vue'
import JobsHistorySorter from '@/components/jobs/JobsHistorySorter.vue'
import TableSkeletonRows from '@/components/TableSkeletonRows.vue'
import { WindowIcon } from '@heroicons/vue/24/outline'
import { PlusSmallIcon } from '@heroicons/vue/24/outline'
import PaginationControls from '@/components/PaginationControls.vue'
import { lastPage, type PageSizeOption } from '@/composables/Pagination'

const props = defineProps<{ cluster: string }>()

const gateway = useGatewayAPI()
const router = useRouter()
const route = useRoute()
const runtimeStore = useRuntimeStore()
const historyStore = runtimeStore.jobsHistory
const { filters, page, pageSize, sort, order } = storeToRefs(historyStore)

const initialLoading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
const jobs = ref<JobHistoryRecord[]>([])
const total = ref(0)
const filtersOpen = ref(false)
const totalPages = computed(() => lastPage(total.value, pageSize.value))

async function fetchHistory() {
  refreshing.value = !initialLoading.value
  error.value = null
  try {
    const payload: JobHistoryFilters = {
      ...filters.value,
      page: page.value,
      page_size: pageSize.value,
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
    initialLoading.value = false
    refreshing.value = false
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

function historyJobPriority(job: JobHistoryRecord): string {
  const states = splitJobHistoryState(job.job_state)
  if (!states.includes('PENDING')) return '-'
  return job.priority != null ? String(job.priority) : '-'
}

function fmtTime(value: string | null | undefined) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
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

watch(
  () => route.query,
  () => {
    historyStore.hydrate(route.query)
    void fetchHistory()
  },
  { immediate: true }
)

watch(
  () => props.cluster,
  () => {
    jobs.value = []
    total.value = 0
    initialLoading.value = true
    refreshing.value = false
    void fetchHistory()
  }
)

watch(totalPages, (newLastPage) => {
  if (page.value > newLastPage) {
    page.value = newLastPage
    updateQueryParameters()
  }
})
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
        :metric-value="initialLoading || error ? undefined : total"
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

      <div class="ui-section-stack">
        <ErrorAlert v-if="error">{{ error }}</ErrorAlert>
        <InfoAlert v-else-if="!initialLoading && jobs.length === 0">
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
              <tbody v-if="!initialLoading" class="text-sm text-[var(--color-brand-muted)]">
                <tr v-for="job in jobs" :key="job.id">
                  <td class="py-3 pr-3 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)] sm:pl-6 lg:pl-8">
                    {{ job.job_id }}
                  </td>
                  <td class="px-3 py-3 text-xs tabular-nums whitespace-nowrap">
                    {{ fmtTime(job.submit_time) }}
                  </td>
                  <td class="px-3 py-3 whitespace-nowrap">
                    <JobStatusBadge :status="splitJobHistoryState(job.job_state)" />
                  </td>
                  <td class="px-3 py-3 whitespace-nowrap">
                    <RouterLink
                      v-if="job.user_name"
                      :to="{ name: 'user', params: { cluster, user: job.user_name } }"
                      class="ui-user-link"
                    >
                      {{ job.user_name }}
                    </RouterLink>
                    <span v-else>-</span>
                    <span class="text-[var(--color-brand-muted)]">({{ job.account ?? '-' }})</span>
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap sm:table-cell">
                    <JobHistoryResources :job="job" />
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap xl:table-cell">
                    {{ job.partition ?? '-' }}
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap xl:table-cell">
                    {{ job.qos ?? '-' }}
                  </td>
                  <td class="hidden px-3 py-3 text-center whitespace-nowrap sm:table-cell">
                    {{ historyJobPriority(job) }}
                  </td>
                  <td class="hidden px-3 py-3 whitespace-nowrap 2xl:table-cell">
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
              <TableSkeletonRows
                v-else
                :columns="10"
                :rows="8"
                first-cell-class="sm:pl-6 lg:pl-8"
                cell-class="px-3"
              />
            </table>

            <PaginationControls
              v-if="!initialLoading"
              :page="page"
              :page-size="pageSize"
              :total="total"
              item-label="record"
              @update:page="updatePage"
              @update:page-size="updatePageSize"
            />
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
