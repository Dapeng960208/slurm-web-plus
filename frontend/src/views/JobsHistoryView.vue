<!--
  Copyright (c) 2023-2024 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { JobHistoryRecord, JobHistoryFilters } from '@/composables/GatewayAPI'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobsHistoryFiltersPanel from '@/components/jobs/JobsHistoryFiltersPanel.vue'
import JobsHistoryFiltersBar from '@/components/jobs/JobsHistoryFiltersBar.vue'
import { WindowIcon } from '@heroicons/vue/24/outline'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/20/solid'
import { PlusSmallIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{ cluster: string }>()

const gateway = useGatewayAPI()

const loading = ref(false)
const error = ref<string | null>(null)
const jobs = ref<JobHistoryRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 50
const filtersOpen = ref(false)

const filters = reactive<JobHistoryFilters>({
  user: '',
  account: '',
  partition: '',
  qos: '',
  state: '',
  job_id: undefined,
  start: '',
  end: '',
  page: 1,
  page_size: pageSize
})

async function fetchHistory() {
  loading.value = true
  error.value = null
  try {
    const f: JobHistoryFilters = { ...filters, page: page.value, page_size: pageSize }
    // strip empty values
    ;(Object.keys(f) as (keyof JobHistoryFilters)[]).forEach((k) => {
      if (f[k] === '' || f[k] === undefined) delete f[k]
    })
    const resp = await gateway.jobs_history(props.cluster, f)
    jobs.value = resp.jobs
    total.value = resp.total
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  fetchHistory()
}

const lastpage = () => Math.max(Math.ceil(total.value / pageSize), 1)

function jobsPages(): { id: number; ellipsis: boolean }[] {
  const result: { id: number; ellipsis: boolean }[] = []
  let ellipsis = false
  const last = lastpage()
  for (let p = 1; p <= last; p++) {
    if (p < 3 || p > last - 2 || (p >= page.value - 1 && p <= page.value + 1)) {
      ellipsis = false
      result.push({ id: p, ellipsis: false })
    } else if (!ellipsis) {
      ellipsis = true
      result.push({ id: p, ellipsis: true })
    }
  }
  return result
}

onMounted(() => fetchHistory())
</script>

<template>
  <ClusterMainLayout
    menu-entry="jobs-history"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Jobs History' }]"
  >
    <div>
      <!-- Filters side panel -->
      <JobsHistoryFiltersPanel
        :open="filtersOpen"
        :filters="filters"
        :total="total"
        @close="filtersOpen = false"
        @search="applyFilters"
      />

      <!-- Header -->
      <div class="mx-auto flex items-center justify-between">
        <div class="px-4 py-16 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            Jobs History
          </h1>
          <p class="mt-4 max-w-xl text-sm font-light text-gray-600 dark:text-gray-300">
            Historical job records from cluster
          </p>
        </div>
        <div v-if="!loading && !error" class="mt-4 text-right text-gray-600 dark:text-gray-300">
          <div class="text-5xl font-bold">{{ total }}</div>
          <div class="text-sm font-light">record{{ total !== 1 ? 's' : '' }} found</div>
        </div>
        <div v-else-if="loading" class="flex animate-pulse space-x-4">
          <div class="h-14 w-14 rounded-2xl bg-slate-200 dark:bg-slate-800"></div>
        </div>
      </div>

      <!-- Filter toolbar — same layout as JobsView -->
      <section aria-labelledby="history-filter-heading" class="-mx-4 -my-2 sm:-mx-6 lg:-mx-8">
        <h2 id="history-filter-heading" class="sr-only">Filters</h2>
        <div class="border-gray-200 pb-4">
          <div class="mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-8">
            <!-- left side: intentionally empty (no sorter for history) -->
            <div />
            <button
              type="button"
              class="bg-slurmweb dark:bg-slurmweb-verydark hover:bg-slurmweb-darker focus-visible:outline-slurmweb inline-flex items-center gap-x-1.5 rounded-md px-3 py-2 text-sm font-semibold text-white shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2"
              @click="filtersOpen = true"
            >
              <PlusSmallIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
              Add filters
            </button>
          </div>
        </div>
        <JobsHistoryFiltersBar :filters="filters" @search="applyFilters" />
      </section>

      <!-- Content -->
      <div class="mt-8 flow-root">
        <ErrorAlert v-if="error">{{ error }}</ErrorAlert>
        <div v-else-if="loading" class="text-gray-400 sm:pl-6 lg:pl-8">
          <LoadingSpinner :size="5" />
          Loading job history…
        </div>
        <InfoAlert v-else-if="jobs.length === 0">
          No job history records found on cluster <span class="font-medium">{{ cluster }}</span>
        </InfoAlert>
        <div v-else class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle">
            <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-500">
              <thead>
                <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                  <th scope="col" class="w-12 py-3.5 pr-3 text-left sm:pl-6 lg:pl-8">#ID</th>
                  <th scope="col" class="w-16 px-3 py-3.5 text-left">State</th>
                  <th scope="col" class="px-3 py-3.5 text-left">User (account)</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left sm:table-cell">Resources</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">Partition</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left xl:table-cell">Submit Time</th>
                  <th scope="col" class="hidden px-3 py-3.5 text-left 2xl:table-cell">End Time</th>
                  <th scope="col" class="py-3.5 pr-4 pl-3 sm:pr-6 lg:pr-8">
                    <span class="sr-only">View</span>
                  </th>
                </tr>
              </thead>
              <tbody
                class="divide-y divide-gray-200 text-sm text-gray-500 dark:divide-gray-700 dark:text-gray-300"
              >
                <tr v-for="job in jobs" :key="job.id">
                  <td
                    class="py-4 pr-3 font-medium whitespace-nowrap text-gray-900 sm:pl-6 lg:pl-8 dark:text-gray-100"
                  >
                    {{ job.job_id }}
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">
                    <JobStatusBadge :status="job.job_state ? [job.job_state] : ['UNKNOWN']" />
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">
                    {{ job.user_name ?? '-' }} ({{ job.account ?? '-' }})
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap sm:table-cell">
                    <span v-if="job.node_count"
                      >{{ job.node_count }} node{{ job.node_count > 1 ? 's' : '' }}</span
                    >
                    <span v-if="job.node_count && job.cpus">, </span>
                    <span v-if="job.cpus">{{ job.cpus }} CPU{{ job.cpus > 1 ? 's' : '' }}</span>
                    <span v-if="!job.node_count && !job.cpus">-</span>
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap xl:table-cell">
                    {{ job.partition ?? '-' }}
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap xl:table-cell">
                    {{ job.submit_time ? new Date(job.submit_time).toLocaleString() : '-' }}
                  </td>
                  <td class="hidden px-3 py-4 whitespace-nowrap 2xl:table-cell">
                    {{ job.end_time ? new Date(job.end_time).toLocaleString() : '-' }}
                  </td>
                  <td class="h-full text-right font-medium">
                    <RouterLink
                      :to="{ name: 'job-history', params: { cluster: cluster, id: job.id } }"
                      class="hover:text-slurmweb-dark hover:dark:text-slurmweb"
                    >
                      <WindowIcon class="mr-4 inline-block h-5 w-5 lg:mr-6" aria-hidden="true" />
                      <span class="sr-only">View {{ job.job_id }}</span>
                    </RouterLink>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Pagination -->
            <div
              class="flex items-center justify-between border-t border-gray-200 px-4 py-3 sm:px-6 dark:border-gray-700"
            >
              <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm text-gray-700 dark:text-gray-300">
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
                    class="isolate inline-flex -space-x-px rounded-md shadow-xs"
                    aria-label="Pagination"
                  >
                    <button
                      :class="[
                        page === 1
                          ? 'cursor-default bg-gray-100 text-gray-100 dark:bg-gray-900 dark:text-gray-900'
                          : 'text-gray-400 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 hover:dark:bg-gray-700',
                        'relative inline-flex items-center rounded-l-md px-2 py-2 ring-1 ring-gray-300 ring-inset focus:z-20 focus:outline-offset-0 dark:ring-gray-700'
                      ]"
                      @click="page > 1 && (page--, fetchHistory())"
                    >
                      <span class="sr-only">Previous</span>
                      <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                    <template v-for="p in jobsPages()" :key="p.id">
                      <button
                        v-if="p.ellipsis"
                        class="relative z-10 inline-flex items-center bg-white px-4 py-2 text-xs font-semibold text-gray-600 ring-1 ring-gray-300 ring-inset dark:bg-gray-800 dark:ring-gray-700"
                      >
                        …
                      </button>
                      <button
                        v-else
                        :class="[
                          p.id === page
                            ? 'bg-slurmweb dark:bg-slurmweb-dark text-white'
                            : 'bg-white text-black ring-1 ring-gray-300 ring-inset hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-700 hover:dark:bg-gray-700',
                          'relative z-10 inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20'
                        ]"
                        @click="page = p.id; fetchHistory()"
                      >
                        {{ p.id }}
                      </button>
                    </template>
                    <button
                      :class="[
                        page === lastpage()
                          ? 'cursor-default bg-gray-100 text-gray-100 dark:bg-gray-900 dark:text-gray-900'
                          : 'text-gray-400 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 hover:dark:bg-gray-700',
                        'relative inline-flex items-center rounded-r-md px-2 py-2 ring-1 ring-gray-300 ring-inset focus:z-20 focus:outline-offset-0 dark:ring-gray-700'
                      ]"
                      @click="page < lastpage() && (page++, fetchHistory())"
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
