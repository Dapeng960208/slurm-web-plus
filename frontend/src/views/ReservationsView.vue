<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

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

function formatReservationDateTimeLocal(epochSeconds?: number | null): string {
  if (!epochSeconds) return ''
  const date = new Date(epochSeconds * 1000)
  const pad = (value: number) => value.toString().padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function parseReservationDateTime(value: string): number | null {
  if (!value.trim()) return null
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return null
  return Math.floor(timestamp / 1000)
}

function buildReservationTimePayload(
  payload: Record<string, string>,
  options: { requireEndTime?: boolean } = {}
) {
  const startTimestamp = parseReservationDateTime(payload.start_time ?? '')
  const endTimestamp = parseReservationDateTime(payload.end_time ?? '')

  if (!startTimestamp) {
    throw new Error(t('pages.reservations.errors.startTimeRequired'))
  }
  if (options.requireEndTime && !endTimestamp) {
    throw new Error(t('pages.reservations.errors.endTimeRequired'))
  }
  if (endTimestamp && endTimestamp <= startTimestamp) {
    throw new Error(t('pages.reservations.errors.invalidTimeRange'))
  }

  return {
    start_time: {
      set: true,
      number: startTimestamp
    },
    end_time: endTimestamp
      ? {
          set: true,
          number: endTimestamp
        }
      : undefined
  }
}

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
    const timePayload = buildReservationTimePayload(payload, { requireEndTime: true })
    await gateway.save_reservation(cluster, {
      name: payload.name || undefined,
      node_list: payload.node_list || undefined,
      partition: payload.partition || undefined,
      users: parseCsvList(payload.users),
      accounts: parseCsvList(payload.accounts),
      start_time: timePayload.start_time,
      end_time: timePayload.end_time
    })
    runtimeStore.reportInfo(
      t('pages.reservations.notifications.createRequested', { name: payload.name || '' })
    )
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
    const timePayload = buildReservationTimePayload(payload)
    await gateway.update_reservation(cluster, selectedReservation.value.name, {
      name: selectedReservation.value.name,
      node_list: payload.node_list || undefined,
      partition: payload.partition || undefined,
      users: parseCsvList(payload.users),
      accounts: parseCsvList(payload.accounts),
      start_time: timePayload.start_time,
      end_time: timePayload.end_time
    })
    runtimeStore.reportInfo(
      t('pages.reservations.notifications.updateRequested', {
        name: selectedReservation.value.name
      })
    )
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
    runtimeStore.reportInfo(
      t('pages.reservations.notifications.deleteRequested', {
        name: selectedReservation.value.name
      })
    )
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
  <ClusterMainLayout
    menu-entry="reservations"
    :cluster="cluster"
    :breadcrumb="[{ title: 'shell.mainMenu.reservations' }]"
  >
    <div class="ui-page ui-page-wide ui-content-workspace">
    <PageHeader
      title="pages.reservations.title"
      description="pages.reservations.description"
      :metric-value="loaded ? data?.length : undefined"
      metric-label="pages.reservations.metricLabel"
    >
      <template #actions>
        <button
          v-if="canCreateReservation"
          type="button"
          class="ui-button-primary"
          @click="openCreateDialog"
        >
          {{ t('pages.reservations.create') }}
        </button>
      </template>
    </PageHeader>
    <ErrorAlert v-if="unable"
      >{{ t('pages.reservations.unableToRetrieve', { cluster }) }}</ErrorAlert
    >
    <InfoAlert v-else-if="loaded && data?.length == 0"
      >{{ t('pages.reservations.noReservations', { cluster }) }}</InfoAlert
    >
    <div v-else class="ui-results-layout">
      <div class="ui-results-workspace">
        <div class="ui-table-shell ui-results-card">
          <div class="ui-table-scroll">
            <div class="ui-table-scroll-inner py-2">
            <table class="ui-table min-w-full">
            <thead>
              <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                <th scope="col" class="w-48 py-3.5 pr-3 text-left align-top sm:pl-6 lg:min-w-[150px] lg:pl-8">
                  {{ t('tables.reservations.columns.name') }}
                </th>
                <th scope="col" class="w-72 px-3 py-3.5 text-left align-top">
                  {{ t('tables.reservations.columns.nodes') }}
                </th>
                <th scope="col" class="w-72 px-3 py-3.5 text-left">
                  {{ t('tables.reservations.columns.duration') }}
                </th>
                <th scope="col" class="w-12 px-3 py-3.5 text-left">
                  {{ t('tables.reservations.columns.users') }}
                </th>
                <th scope="col" class="w-12 px-3 py-3.5 text-left">
                  {{ t('tables.reservations.columns.accounts') }}
                </th>
                <th scope="col" class="hidden w-24 px-3 py-3.5 text-left align-top 2xl:table-cell">
                  {{ t('tables.reservations.columns.flags') }}
                </th>
                <th scope="col" class="py-3.5 pr-4 pl-3 text-right sm:pr-6 lg:pr-8">
                  {{ t('tables.reservations.columns.actions') }}
                </th>
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
                      class="ui-button-warning"
                      @click="openEditDialog(reservation)"
                    >
                      {{ t('pages.reservations.actions.edit') }}
                    </button>
                    <button
                      v-if="canDeleteReservation"
                      type="button"
                      class="ui-button-danger"
                      @click="openDeleteDialog(reservation)"
                    >
                      {{ t('pages.reservations.actions.delete') }}
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
            </div>
          </div>
        </div>
        <div class="ui-results-dock">
          <PaginationControls
            v-if="loaded"
            :page="page"
            :page-size="pageSize"
            :total="data?.length ?? 0"
            :item-label="t('common.entities.reservations')"
            @update:page="updatePage"
            @update:page-size="updatePageSize"
          />
        </div>
      </div>
    </div>

    <ActionDialog
      :open="createOpen"
      title="pages.reservations.dialogs.create.title"
      description="pages.reservations.dialogs.create.description"
      submit-label="pages.reservations.dialogs.create.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'name', label: 'pages.reservations.dialogs.fields.name', required: true },
        {
          key: 'node_list',
          label: 'pages.reservations.dialogs.fields.nodeList',
          required: true,
          type: 'textarea'
        },
        {
          key: 'start_time',
          label: 'pages.reservations.dialogs.fields.startTime',
          required: true,
          type: 'datetime-local',
          hint: 'pages.reservations.dialogs.hints.startTime'
        },
        {
          key: 'end_time',
          label: 'pages.reservations.dialogs.fields.endTime',
          required: true,
          type: 'datetime-local',
          hint: 'pages.reservations.dialogs.hints.endTime'
        },
        { key: 'partition', label: 'pages.reservations.dialogs.fields.partition' },
        { key: 'users', label: 'pages.reservations.dialogs.fields.users' },
        { key: 'accounts', label: 'pages.reservations.dialogs.fields.accounts' }
      ]"
      @close="createOpen = false"
      @submit="createReservation"
    />

    <ActionDialog
      :open="editOpen"
      title="pages.reservations.dialogs.edit.title"
      :description="selectedReservation ? 'pages.reservations.dialogs.edit.description' : undefined"
      :description-params="selectedReservation ? { name: selectedReservation.name } : undefined"
      submit-label="pages.reservations.dialogs.edit.submit"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        node_list: selectedReservation?.node_list ?? '',
        start_time: formatReservationDateTimeLocal(selectedReservation?.start_time?.number),
        end_time: formatReservationDateTimeLocal(selectedReservation?.end_time?.number),
        partition: '',
        users: stringifyList(selectedReservation?.users),
        accounts: stringifyList(selectedReservation?.accounts)
      }"
      :fields="[
        {
          key: 'node_list',
          label: 'pages.reservations.dialogs.fields.nodeList',
          required: true,
          type: 'textarea'
        },
        {
          key: 'start_time',
          label: 'pages.reservations.dialogs.fields.startTime',
          required: true,
          type: 'datetime-local',
          hint: 'pages.reservations.dialogs.hints.startTime'
        },
        {
          key: 'end_time',
          label: 'pages.reservations.dialogs.fields.endTime',
          type: 'datetime-local',
          hint: 'pages.reservations.dialogs.hints.endTimeOptional'
        },
        { key: 'partition', label: 'pages.reservations.dialogs.fields.partition' },
        { key: 'users', label: 'pages.reservations.dialogs.fields.users' },
        { key: 'accounts', label: 'pages.reservations.dialogs.fields.accounts' }
      ]"
      @close="editOpen = false"
      @submit="updateReservation"
    />

    <ActionDialog
      :open="deleteOpen"
      title="pages.reservations.dialogs.delete.title"
      :description="selectedReservation ? 'pages.reservations.dialogs.delete.description' : undefined"
      :description-params="selectedReservation ? { name: selectedReservation.name } : undefined"
      submit-label="pages.reservations.dialogs.delete.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[]"
      @close="deleteOpen = false"
      @submit="deleteReservation"
    />
    </div>
  </ClusterMainLayout>
</template>
