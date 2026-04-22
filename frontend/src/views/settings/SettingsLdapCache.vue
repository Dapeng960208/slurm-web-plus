<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import type { CachedLdapUser, ClusterDescription } from '@/composables/GatewayAPI'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/20/solid'

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()
const pageSize = 20

const clusterUsers = reactive<Record<string, CachedLdapUser[]>>({})
const clusterTotals = reactive<Record<string, number>>({})
const clusterPages = reactive<Record<string, number>>({})
const clusterQueries = reactive<Record<string, string>>({})
const clusterErrors = reactive<Record<string, string | null>>({})
const clusterLoading = reactive<Record<string, boolean>>({})
const clusterLoaded = reactive<Record<string, boolean>>({})

const clusters = computed(() => runtimeStore.availableClusters)
const pageVisible = computed(
  () => runtimeConfiguration.authentication && clusters.value.some((cluster) => cluster.database)
)

async function fetchClusterUsers(cluster: ClusterDescription) {
  if (!cluster.database || !runtimeStore.hasClusterPermission(cluster.name, 'cache-view')) return

  if (clusterPages[cluster.name] === undefined) clusterPages[cluster.name] = 1
  if (clusterQueries[cluster.name] === undefined) clusterQueries[cluster.name] = ''

  clusterLoading[cluster.name] = true
  clusterErrors[cluster.name] = null

  try {
    const response = await gateway.ldap_cache_users(cluster.name, {
      username: clusterQueries[cluster.name] || undefined,
      page: clusterPages[cluster.name],
      page_size: pageSize
    })
    if (Array.isArray(response)) {
      clusterUsers[cluster.name] = response
      clusterTotals[cluster.name] = response.length
      clusterPages[cluster.name] = currentPage(cluster.name)
    } else {
      clusterUsers[cluster.name] = response.items
      clusterTotals[cluster.name] = response.total
      clusterPages[cluster.name] = response.page
    }
  } catch (error: unknown) {
    clusterErrors[cluster.name] = error instanceof Error ? error.message : String(error)
  } finally {
    clusterLoading[cluster.name] = false
    clusterLoaded[cluster.name] = true
  }
}

function searchClusterUsers(cluster: ClusterDescription) {
  clusterPages[cluster.name] = 1
  fetchClusterUsers(cluster)
}

function resetClusterUsers(cluster: ClusterDescription) {
  clusterQueries[cluster.name] = ''
  clusterPages[cluster.name] = 1
  fetchClusterUsers(cluster)
}

function currentPage(clusterName: string): number {
  return clusterPages[clusterName] ?? 1
}

function lastPage(clusterName: string): number {
  return Math.max(Math.ceil((clusterTotals[clusterName] ?? 0) / pageSize), 1)
}

function changePage(cluster: ClusterDescription, page: number) {
  if (page < 1 || page > lastPage(cluster.name) || page === currentPage(cluster.name)) return
  clusterPages[cluster.name] = page
  fetchClusterUsers(cluster)
}

function pages(clusterName: string): { id: number; ellipsis: boolean }[] {
  const result: { id: number; ellipsis: boolean }[] = []
  let ellipsis = false
  const last = lastPage(clusterName)
  for (let page = 1; page <= last; page++) {
    if (
      page < 3 ||
      page > last - 2 ||
      (page >= currentPage(clusterName) - 1 && page <= currentPage(clusterName) + 1)
    ) {
      ellipsis = false
      result.push({ id: page, ellipsis: false })
    } else if (!ellipsis) {
      ellipsis = true
      result.push({ id: page, ellipsis: true })
    }
  }
  return result
}

function firstItem(clusterName: string): number {
  if ((clusterTotals[clusterName] ?? 0) === 0) return 0
  return (currentPage(clusterName) - 1) * pageSize + 1
}

function lastItem(clusterName: string): number {
  return Math.min(currentPage(clusterName) * pageSize, clusterTotals[clusterName] ?? 0)
}

onMounted(async () => {
  await Promise.all(clusters.value.map((cluster) => fetchClusterUsers(cluster)))
})
</script>

<template>
  <SettingsTabs entry="LDAP Cache" />
  <div class="ui-panel ui-section">
    <SettingsHeader
      title="LDAP Cache"
      description="Cached LDAP users persisted in the local database for each cluster."
    />
  </div>

  <InfoAlert v-if="!runtimeConfiguration.authentication">
    LDAP authentication is disabled, so LDAP cache data is unavailable.
  </InfoAlert>
  <InfoAlert v-else-if="!pageVisible">
    No cluster has database support enabled for LDAP user caching.
  </InfoAlert>

  <div v-else class="space-y-6">
    <div
      v-for="cluster in clusters"
      :key="cluster.name"
      class="ui-panel ui-section"
    >
      <div class="mb-6">
        <p class="ui-page-kicker">LDAP Cache</p>
        <h3 class="text-2xl font-bold text-[var(--color-brand-ink-strong)]">
          Cluster {{ cluster.name }}
        </h3>
      </div>

      <InfoAlert v-if="!runtimeStore.hasClusterPermission(cluster.name, 'cache-view')">
        No permission to get LDAP cache information on this cluster.
      </InfoAlert>
      <InfoAlert v-else-if="!cluster.database">
        Database support is disabled on this cluster.
      </InfoAlert>
      <div v-else class="space-y-6">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div class="w-full max-w-xl">
            <label
              :for="`ldap-cache-query-${cluster.name}`"
              class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]"
            >
              Search by username
            </label>
            <div class="flex flex-col gap-3 sm:flex-row">
              <input
                :id="`ldap-cache-query-${cluster.name}`"
                v-model="clusterQueries[cluster.name]"
                type="text"
                class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                placeholder="Search username..."
                @keyup.enter="searchClusterUsers(cluster)"
              />
              <button type="button" class="ui-button-primary" @click="searchClusterUsers(cluster)">
                Search
              </button>
              <button type="button" class="ui-button-secondary" @click="resetClusterUsers(cluster)">
                Reset
              </button>
            </div>
          </div>

          <div
            v-if="!clusterLoading[cluster.name] && !clusterErrors[cluster.name]"
            class="text-sm text-[var(--color-brand-muted)]"
          >
            {{ clusterTotals[cluster.name] ?? 0 }} user{{ (clusterTotals[cluster.name] ?? 0) === 1 ? '' : 's' }} found
          </div>
        </div>

        <div
          v-if="clusterLoading[cluster.name] || clusterLoaded[cluster.name] !== true"
          class="text-[var(--color-brand-muted)]"
        >
          <LoadingSpinner :size="5" />
          Loading cached LDAP users...
        </div>
        <ErrorAlert v-else-if="clusterErrors[cluster.name]">
          {{ clusterErrors[cluster.name] }}
        </ErrorAlert>
        <InfoAlert v-else-if="(clusterTotals[cluster.name] ?? 0) === 0">
          No cached LDAP users found on this cluster.
        </InfoAlert>
        <div v-else class="ui-table-shell overflow-x-auto">
          <div class="inline-block min-w-full align-middle">
            <table class="ui-table min-w-full">
              <thead>
                <tr>
                  <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Username</th>
                  <th scope="col" class="px-3 py-3.5 text-left">Full name</th>
                </tr>
              </thead>
              <tbody class="text-sm text-[var(--color-brand-muted)]">
                <tr v-for="user in clusterUsers[cluster.name]" :key="user.username">
                  <td class="py-4 pr-3 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                    {{ user.username }}
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap">{{ user.fullname ?? '-' }}</td>
                </tr>
              </tbody>
            </table>

            <div class="flex items-center justify-between border-t border-[rgba(80,105,127,0.08)] px-4 py-3 sm:px-6">
              <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm text-[var(--color-brand-muted)]">
                    Showing
                    <span class="font-medium">{{ firstItem(cluster.name) }}</span>
                    to
                    <span class="font-medium">{{ lastItem(cluster.name) }}</span>
                    of
                    <span class="font-medium">{{ clusterTotals[cluster.name] ?? 0 }}</span>
                    users
                  </p>
                </div>
                <div>
                  <nav
                    v-if="lastPage(cluster.name) > 1"
                    class="isolate inline-flex -space-x-px rounded-full shadow-[var(--shadow-soft)]"
                    aria-label="Pagination"
                  >
                    <button
                      :class="[
                        currentPage(cluster.name) === 1
                          ? 'cursor-default bg-gray-100 text-gray-100'
                          : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
                        'relative inline-flex items-center rounded-l-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
                      ]"
                      @click="changePage(cluster, currentPage(cluster.name) - 1)"
                    >
                      <span class="sr-only">Previous</span>
                      <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                    <template v-for="page in pages(cluster.name)" :key="page.id">
                      <button
                        v-if="page.ellipsis"
                        type="button"
                        class="relative z-10 inline-flex items-center bg-white px-4 py-2 text-xs font-semibold text-[var(--color-brand-muted)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset"
                      >
                        ...
                      </button>
                      <button
                        v-else
                        type="button"
                        :class="[
                          page.id === currentPage(cluster.name)
                            ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                            : 'bg-white text-[var(--color-brand-ink-strong)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset hover:bg-[rgba(182,232,44,0.12)]',
                          'relative z-10 inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20'
                        ]"
                        @click="changePage(cluster, page.id)"
                      >
                        {{ page.id }}
                      </button>
                    </template>
                    <button
                      :class="[
                        currentPage(cluster.name) === lastPage(cluster.name)
                          ? 'cursor-default bg-gray-100 text-gray-100'
                          : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
                        'relative inline-flex items-center rounded-r-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
                      ]"
                      @click="changePage(cluster, currentPage(cluster.name) + 1)"
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
  </div>
</template>
