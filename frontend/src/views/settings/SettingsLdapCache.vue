<!--
  Copyright (c) 2026 Rackslab

  This file is part of Slurm-web.

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
  if (!cluster.database || !runtimeStore.hasClusterPermission(cluster.name, 'cache-view')) {
    return
  }

  if (clusterPages[cluster.name] === undefined) {
    clusterPages[cluster.name] = 1
  }
  if (clusterQueries[cluster.name] === undefined) {
    clusterQueries[cluster.name] = ''
  }

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
  if (page < 1 || page > lastPage(cluster.name) || page === currentPage(cluster.name)) {
    return
  }
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
  if ((clusterTotals[clusterName] ?? 0) === 0) {
    return 0
  }
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
  <div class="px-4 pt-16 sm:px-6 lg:px-8">
    <SettingsHeader
      title="LDAP Cache"
      description="Cached LDAP users persisted in the local database for each cluster."
    />
    <div class="mt-8 flow-root">
      <InfoAlert v-if="!runtimeConfiguration.authentication">
        LDAP authentication is disabled, so LDAP cache data is unavailable.
      </InfoAlert>
      <InfoAlert v-else-if="!pageVisible">
        No cluster has database support enabled for LDAP user caching.
      </InfoAlert>
      <div v-else class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <template v-for="cluster in clusters" :key="cluster.name">
          <div class="min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <div class="border-b border-gray-200 pb-5 dark:border-gray-600">
              <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
                Cluster {{ cluster.name }}
              </h3>
            </div>

            <InfoAlert v-if="!runtimeStore.hasClusterPermission(cluster.name, 'cache-view')">
              No permission to get LDAP cache information on this cluster.
            </InfoAlert>
            <InfoAlert v-else-if="!cluster.database">
              Database support is disabled on this cluster.
            </InfoAlert>
            <div v-else class="mt-6 space-y-6">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div class="w-full max-w-xl">
                  <label
                    :for="`ldap-cache-query-${cluster.name}`"
                    class="block text-sm font-medium text-gray-700 dark:text-gray-200"
                  >
                    Search by username
                  </label>
                  <div class="mt-2 flex flex-col gap-3 sm:flex-row">
                    <input
                      :id="`ldap-cache-query-${cluster.name}`"
                      v-model="clusterQueries[cluster.name]"
                      type="text"
                      class="block w-full rounded-md border-0 bg-white px-3 py-1.5 text-gray-900 shadow-xs ring-1 ring-gray-300 ring-inset focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-700"
                      placeholder="Search username..."
                      @keyup.enter="searchClusterUsers(cluster)"
                    />
                    <button
                      type="button"
                      class="bg-slurmweb dark:bg-slurmweb-verydark hover:bg-slurmweb-darker focus-visible:outline-slurmweb inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2"
                      @click="searchClusterUsers(cluster)"
                    >
                      Search
                    </button>
                    <button
                      type="button"
                      class="inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs ring-1 ring-gray-300 ring-inset hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-700 hover:dark:bg-gray-700"
                      @click="resetClusterUsers(cluster)"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                <div
                  v-if="!clusterLoading[cluster.name] && !clusterErrors[cluster.name]"
                  class="text-sm text-gray-600 dark:text-gray-300"
                >
                  {{ clusterTotals[cluster.name] ?? 0 }} user{{
                    (clusterTotals[cluster.name] ?? 0) === 1 ? '' : 's'
                  }}
                  found
                </div>
              </div>

              <div
                v-if="clusterLoading[cluster.name] || clusterLoaded[cluster.name] !== true"
                class="py-6 text-gray-400"
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
              <div v-else>
                <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-500">
                  <thead>
                    <tr class="text-left text-sm font-semibold text-gray-900 dark:text-gray-200">
                      <th scope="col" class="py-3.5 pr-3 sm:pl-0">Username</th>
                      <th scope="col" class="px-3 py-3.5">Full name</th>
                    </tr>
                  </thead>
                  <tbody
                    class="divide-y divide-gray-200 text-sm text-gray-500 dark:divide-gray-700 dark:text-gray-300"
                  >
                    <tr v-for="user in clusterUsers[cluster.name]" :key="user.username">
                      <td
                        class="py-4 pr-3 font-medium whitespace-nowrap text-gray-900 dark:text-gray-100"
                      >
                        {{ user.username }}
                      </td>
                      <td class="px-3 py-4 whitespace-nowrap">{{ user.fullname ?? '-' }}</td>
                    </tr>
                  </tbody>
                </table>

                <div
                  class="mt-4 flex items-center justify-between border-t border-gray-200 px-4 py-3 sm:px-6 dark:border-gray-700"
                >
                  <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                    <div>
                      <p class="text-sm text-gray-700 dark:text-gray-300">
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
                        class="isolate inline-flex -space-x-px rounded-md shadow-xs"
                        aria-label="Pagination"
                      >
                        <button
                          :class="[
                            currentPage(cluster.name) === 1
                              ? 'cursor-default bg-gray-100 text-gray-100 dark:bg-gray-900 dark:text-gray-900'
                              : 'text-gray-400 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 hover:dark:bg-gray-700',
                            'relative inline-flex items-center rounded-l-md px-2 py-2 ring-1 ring-gray-300 ring-inset focus:z-20 focus:outline-offset-0 dark:ring-gray-700'
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
                            class="relative z-10 inline-flex items-center bg-white px-4 py-2 text-xs font-semibold text-gray-600 ring-1 ring-gray-300 ring-inset dark:bg-gray-800 dark:ring-gray-700"
                          >
                            ...
                          </button>
                          <button
                            v-else
                            type="button"
                            :class="[
                              page.id === currentPage(cluster.name)
                                ? 'bg-slurmweb dark:bg-slurmweb-dark text-white'
                                : 'bg-white text-black ring-1 ring-gray-300 ring-inset hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-700 hover:dark:bg-gray-700',
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
                              ? 'cursor-default bg-gray-100 text-gray-100 dark:bg-gray-900 dark:text-gray-900'
                              : 'text-gray-400 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 hover:dark:bg-gray-700',
                            'relative inline-flex items-center rounded-r-md px-2 py-2 ring-1 ring-gray-300 ring-inset focus:z-20 focus:outline-offset-0 dark:ring-gray-700'
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
        </template>
      </div>
    </div>
  </div>
</template>
