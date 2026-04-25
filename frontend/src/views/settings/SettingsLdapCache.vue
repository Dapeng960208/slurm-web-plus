<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import type { CachedLdapUser, ClusterDescription } from '@/composables/GatewayAPI'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PaginationControls from '@/components/PaginationControls.vue'
import { DEFAULT_PAGE_SIZE, parsePageSize, type PageSizeOption } from '@/composables/Pagination'

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()
const route = useRoute()
const router = useRouter()
const pageSize = ref(DEFAULT_PAGE_SIZE)

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
      page_size: pageSize.value
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
  return Math.max(Math.ceil((clusterTotals[clusterName] ?? 0) / pageSize.value), 1)
}

function updateQueryParameters() {
  const query: LocationQueryRaw = {}
  if (pageSize.value !== DEFAULT_PAGE_SIZE) {
    query.page_size = pageSize.value
  }
  router.push({ name: 'settings-ldap-cache', query })
}

function updateClusterPage(cluster: ClusterDescription, page: number) {
  if (page < 1 || page > lastPage(cluster.name) || page === currentPage(cluster.name)) return
  clusterPages[cluster.name] = page
  void fetchClusterUsers(cluster)
}

async function updatePageSize(newPageSize: PageSizeOption) {
  pageSize.value = newPageSize
  Object.keys(clusterPages).forEach((clusterName) => {
    clusterPages[clusterName] = 1
  })
  updateQueryParameters()
  await Promise.all(clusters.value.map((cluster) => fetchClusterUsers(cluster)))
}

onMounted(async () => {
  if (route.query.page_size) {
    pageSize.value = parsePageSize(route.query.page_size)
  }
  await Promise.all(clusters.value.map((cluster) => fetchClusterUsers(cluster)))
})
</script>

<template>
  <div class="ui-section-stack">
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

    <div v-else class="ui-section-stack">
      <div
        v-for="cluster in clusters"
        :key="cluster.name"
        class="ui-panel ui-section"
      >
      <div class="mb-4">
        <p class="ui-page-kicker">LDAP Cache</p>
        <h3 class="text-xl font-bold text-[var(--color-brand-ink-strong)]">
          Cluster {{ cluster.name }}
        </h3>
      </div>

      <InfoAlert v-if="!runtimeStore.hasClusterPermission(cluster.name, 'cache-view')">
        No permission to get LDAP cache information on this cluster.
      </InfoAlert>
      <InfoAlert v-else-if="!cluster.database">
        Database support is disabled on this cluster.
      </InfoAlert>
      <div v-else class="space-y-4">
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
                  <th scope="col" class="px-3 py-3.5 text-left">Shortcuts</th>
                </tr>
              </thead>
              <tbody class="text-sm text-[var(--color-brand-muted)]">
                <tr v-for="user in clusterUsers[cluster.name]" :key="user.username">
                  <td class="py-3 pr-3 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                    {{ user.username }}
                  </td>
                  <td class="px-3 py-3 whitespace-nowrap">{{ user.fullname ?? '-' }}</td>
                  <td class="px-3 py-3">
                    <div class="flex flex-wrap gap-2">
                      <RouterLink
                        :to="{ name: 'user', params: { cluster: cluster.name, user: user.username } }"
                        class="ui-button-secondary"
                      >
                        View user
                      </RouterLink>
                      <RouterLink
                        v-if="cluster.user_metrics"
                        :to="{
                          name: 'user',
                          params: { cluster: cluster.name, user: user.username },
                          query: { section: 'analysis' }
                        }"
                        class="ui-button-secondary"
                      >
                        Open analysis
                      </RouterLink>
                      <RouterLink
                        v-if="runtimeStore.hasClusterPermission(cluster.name, 'view-history-jobs')"
                        :to="{ name: 'jobs-history', params: { cluster: cluster.name }, query: { user: user.username } }"
                        class="ui-button-secondary"
                      >
                        View history jobs
                      </RouterLink>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <PaginationControls
              :page="currentPage(cluster.name)"
              :page-size="pageSize"
              :total="clusterTotals[cluster.name] ?? 0"
              item-label="user"
              @update:page="updateClusterPage(cluster, $event)"
              @update:page-size="updatePageSize"
            />
          </div>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>
