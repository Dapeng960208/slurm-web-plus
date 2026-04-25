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
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { representDuration } from '@/composables/TimeDuration'
import { parseCsvList, stringifyList } from '@/composables/management'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import TableSkeletonRows from '@/components/TableSkeletonRows.vue'
import PaginationControls from '@/components/PaginationControls.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import {
  DEFAULT_PAGE_SIZE,
  lastPage,
  parsePageSize,
  parsePositivePage,
  type PageSizeOption
} from '@/composables/Pagination'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster } = defineProps<{ cluster: string }>()
const route = useRoute()
const router = useRouter()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

const { data, unable, loaded, setCluster } = useClusterDataPoller<ClusterReservation[]>(
  cluster,
  'reservations',
  10000
)

const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const operationBusy = ref(false)
const operationError = ref<string | null>(null)
const createOpen = ref(false)
const editOpen = ref(false)
const deleteOpen = ref(false)
const selectedReservation = ref<ClusterReservation | null>(null)

const pagedReservations = computed(() => {
  const items = data.value ?? []
  const start = (page.value - 1) * pageSize.value
  return items.slice(start, start + pageSize.value)
})
const totalPages = computed(() => lastPage(data.value?.length ?? 0, pageSize.value))

const canCreateReservation = computed(() =>
  runtimeStore.hasRoutePermission(cluster, 'reservations', 'edit')
)
const canEditReservation = computed(() =>
  runtimeStore.hasRoutePermission(cluster, 'reservations', 'edit')
)
const canDeleteReservation = computed(() =>
  runtimeStore.hasRoutePermission(cluster, 'reservations', 'delete')
)

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

function openCreateDialog() {
  operationError.value = null
  createOpen.value = true
}

function openEditDialog(reservation: ClusterReservation) {
  selectedReservation.value = reservation
  operationError.value = null
  editOpen.value = true
}

function openDeleteDialog(reservation: ClusterReservation) {
  selectedReservation.value = reservation
  operationError.value = null
  deleteOpen.value = true
}

async function createReservation(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.save_reservation(cluster, {
      name: payload.name || undefined,
      node_list: payload.node_list || undefined,
      partition: payload.partition || undefined,
      users: parseCsvList(payload.users),
      accounts: parseCsvList(payload.accounts)
    })
    runtimeStore.reportInfo(`Reservation ${payload.name || ''} creation requested.`)
    createOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function updateReservation(payload: Record<string, string>) {
  if (!selectedReservation.value) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.update_reservation(cluster, selectedReservation.value.name, {
      name: selectedReservation.value.name,
      node_list: payload.node_list || undefined,
      partition: payload.partition || undefined,
      users: parseCsvList(payload.users),
      accounts: parseCsvList(payload.accounts)
    })
    runtimeStore.reportInfo(`Reservation ${selectedReservation.value.name} update requested.`)
    editOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function deleteReservation() {
  if (!selectedReservation.value) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.delete_reservation(cluster, selectedReservation.value.name)
    runtimeStore.reportInfo(`Reservation ${selectedReservation.value.name} deletion requested.`)
    deleteOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
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
    >
      <template #actions>
        <button
          v-if="canCreateReservation"
          type="button"
          class="ui-button-primary"
          @click="openCreateDialog"
        >
          Create reservation
        </button>
      </template>
    </PageHeader>
    <ErrorAlert v-if="unable"
      >Unable to retrieve reservations from cluster
      <span class="font-medium">{{ cluster }}</span></ErrorAlert
    >
    <InfoAlert v-else-if="loaded && data?.length == 0"
      >No reservation defined on cluster <span class="font-medium">{{ cluster }}</span></InfoAlert
    >
    <div v-else class="ui-section-stack">
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
                <th scope="col" class="py-3.5 pr-4 pl-3 text-right sm:pr-6 lg:pr-8">Actions</th>
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
                <td class="py-4 pl-3 text-right whitespace-nowrap sm:pr-6 lg:pr-8">
                  <div class="flex flex-wrap items-center justify-end gap-2">
                    <button
                      v-if="canEditReservation"
                      type="button"
                      class="ui-button-secondary"
                      @click="openEditDialog(reservation)"
                    >
                      Edit
                    </button>
                    <button
                      v-if="canDeleteReservation"
                      type="button"
                      class="ui-button-secondary"
                      @click="openDeleteDialog(reservation)"
                    >
                      Delete
                    </button>
                  </div>
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

    <ActionDialog
      :open="createOpen"
      title="Create Reservation"
      description="Create a new reservation on this cluster."
      submit-label="Create reservation"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'name', label: 'Reservation name', required: true },
        { key: 'node_list', label: 'Node list', required: true, type: 'textarea' },
        { key: 'partition', label: 'Partition' },
        { key: 'users', label: 'Users (comma separated)' },
        { key: 'accounts', label: 'Accounts (comma separated)' }
      ]"
      @close="createOpen = false"
      @submit="createReservation"
    />

    <ActionDialog
      :open="editOpen"
      title="Edit Reservation"
      :description="selectedReservation ? `Update reservation ${selectedReservation.name}.` : ''"
      submit-label="Save changes"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        node_list: selectedReservation?.node_list ?? '',
        partition: '',
        users: stringifyList(selectedReservation?.users),
        accounts: stringifyList(selectedReservation?.accounts)
      }"
      :fields="[
        { key: 'node_list', label: 'Node list', required: true, type: 'textarea' },
        { key: 'partition', label: 'Partition' },
        { key: 'users', label: 'Users (comma separated)' },
        { key: 'accounts', label: 'Accounts (comma separated)' }
      ]"
      @close="editOpen = false"
      @submit="updateReservation"
    />

    <ActionDialog
      :open="deleteOpen"
      title="Delete Reservation"
      :description="selectedReservation ? `Delete reservation ${selectedReservation.name}. This action is destructive.` : ''"
      submit-label="Delete reservation"
      :loading="operationBusy"
      :error="operationError"
      :fields="[]"
      @close="deleteOpen = false"
      @submit="deleteReservation"
    />
  </ClusterMainLayout>
</template>
