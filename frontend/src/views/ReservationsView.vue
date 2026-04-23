<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterReservation } from '@/composables/GatewayAPI'
import { representDuration } from '@/composables/TimeDuration'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
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
import { XMarkIcon } from '@heroicons/vue/24/outline'

const { cluster } = defineProps<{ cluster: string }>()
const route = useRoute()
const router = useRouter()

const { data, unable, loaded, setCluster } = useClusterDataPoller<ClusterReservation[]>(
  cluster,
  'reservations',
  10000
)

const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const pagedReservations = computed(() => {
  const items = data.value ?? []
  const start = (page.value - 1) * pageSize.value
  return items.slice(start, start + pageSize.value)
})
const totalPages = computed(() => lastPage(data.value?.length ?? 0, pageSize.value))

function updateQueryParameters() {
  const query: LocationQueryRaw = {}
  if (page.value !== 1) query.page = page.value
  if (pageSize.value !== DEFAULT_PAGE_SIZE) query.page_size = pageSize.value
  router.push({ name: 'reservations', params: { cluster }, query })
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
  <ClusterMainLayout menu-entry="reservations" :cluster="cluster" :breadcrumb="[{ title: 'Reservations' }]">
    <PageHeader
      title="Reservations"
      description="Advanced reservations, affected nodes and account or user access windows."
      :metric-value="loaded ? data?.length : undefined"
      metric-label="reservations"
    />
    <ErrorAlert v-if="unable"
      >Unable to retrieve reservations from cluster
      <span class="font-medium">{{ cluster }}</span></ErrorAlert
    >
    <InfoAlert v-else-if="loaded && data?.length == 0"
      >No reservation defined on cluster <span class="font-medium">{{ cluster }}</span></InfoAlert
    >
    <div v-else class="mt-5 flow-root">
      <div class="ui-table-shell -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle">
          <table class="ui-table min-w-full">
            <thead>
              <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                <th scope="col" class="w-48 py-3.5 pr-3 text-left align-top sm:pl-6 lg:min-w-[150px] lg:pl-8">
                  Name
                </th>
                <th scope="col" class="w-72 px-3 py-3.5 text-left align-top">Nodes</th>
                <th scope="col" class="w-72 px-3 py-3.5 text-left">Duration</th>
                <th scope="col" class="w-12 px-3 py-3.5 text-left">Users</th>
                <th scope="col" class="w-12 px-3 py-3.5 text-left">Accounts</th>
                <th scope="col" class="hidden w-24 px-3 py-3.5 text-left align-top 2xl:table-cell">Flags</th>
                <th scope="col" class="w-12"></th>
              </tr>
            </thead>
            <tbody v-if="loaded" class="divide-y divide-gray-200 text-[var(--color-brand-ink-strong)]">
              <tr v-for="reservation in pagedReservations" :key="reservation.name">
                <td class="pr-3 sm:pl-6 lg:pl-8">{{ reservation.name }}</td>
                <td class="hidden px-3 text-sm break-all 2xl:table-cell">
                  <p class="font-mono text-xs">{{ reservation.node_list }}</p>
                  <p class="text-[var(--color-brand-muted)]">→ {{ reservation.node_count }} nodes</p>
                </td>
                <td class="table-cell px-3 text-sm 2xl:hidden">{{ reservation.node_count }}</td>
                <td class="px-3 text-sm whitespace-nowrap">
                  <p class="hidden xl:block">
                    <template v-if="reservation.start_time.set">
                      {{ new Date(reservation.start_time.number * 10 ** 3).toLocaleString() }}
                    </template>
                    <template v-else>-</template>
                  </p>
                  <p v-if="reservation.end_time.set" class="hidden xl:block">
                    <span class="font-bold">→ </span>
                    {{ new Date(reservation.end_time.number * 10 ** 3).toLocaleString() }}
                  </p>
                  <p class="xl:text-[var(--color-brand-muted)] xl:italic">
                    {{ representDuration(reservation.start_time, reservation.end_time) }}
                  </p>
                </td>
                <td class="px-3 text-sm">
                  <XMarkIcon v-if="!reservation.users" class="mr-0.5 h-5 w-5 text-[var(--color-brand-muted)]/55" aria-hidden="true" />
                  <ul v-else class="list-disc">
                    <li v-for="user in reservation.users.split(',')" :key="user">{{ user }}</li>
                  </ul>
                </td>
                <td class="px-3 text-sm">
                  <XMarkIcon v-if="!reservation.accounts" class="mr-0.5 h-5 w-5 text-[var(--color-brand-muted)]/55" aria-hidden="true" />
                  <ul v-else class="list-disc">
                    <li v-for="account in reservation.accounts.split(',')" :key="account">{{ account }}</li>
                  </ul>
                </td>
                <td class="hidden pl-3 text-sm sm:pr-6 lg:pr-8 2xl:table-cell">
                  <span v-for="flag in reservation.flags" :key="flag" class="ui-chip m-1">{{ flag }}</span>
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
            item-label="reservation"
            @update:page="updatePage"
            @update:page-size="updatePageSize"
          />
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
