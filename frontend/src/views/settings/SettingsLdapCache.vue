<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { LocationQueryRaw } from 'vue-router'
import type { CachedLdapUser, ClusterDescription } from '@/composables/GatewayAPI'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import AdminTabs from '@/components/admin/AdminTabs.vue'
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
const { t } = useI18n()
const pageSize = ref(DEFAULT_PAGE_SIZE)
const isAdminRoute = computed(() => String(route.name ?? '').startsWith('admin-'))
const tabsComponent = computed(() => (isAdminRoute.value ? AdminTabs : SettingsTabs))
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

const usersPermissionResource = computed(() =>
  isAdminRoute.value ? 'admin/ldap-users' : 'settings/ldap-users'
)

async function fetchClusterUsers(cluster: ClusterDescription) {
  if (
    !cluster.database ||
    !runtimeStore.hasRoutePermission(cluster.name, usersPermissionResource.value, 'view')
  )
    return

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
  router.push({
    name: isAdminRoute.value ? 'admin-ldap-users' : 'settings-ldap-users',
    params: isAdminRoute.value ? { cluster: runtimeStore.currentCluster?.name } : undefined,
    query
  })
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
    <component
      :is="tabsComponent"
      entry="users"
      :cluster="runtimeStore.currentCluster?.name ?? runtimeStore.availableClusters[0]?.name ?? ''"
    />

    <InfoAlert v-if="!runtimeConfiguration.authentication">
      {{ t('settings.ldapUsers.alerts.authDisabled') }}
    </InfoAlert>
    <InfoAlert v-else-if="!pageVisible">
      {{ t('settings.ldapUsers.alerts.noClusterDatabase') }}
    </InfoAlert>

    <div v-else class="ui-section-stack">
      <div v-for="cluster in clusters" :key="cluster.name" class="ui-panel ui-section">
        <InfoAlert
          v-if="
            !runtimeStore.hasRoutePermission(cluster.name, usersPermissionResource, 'view')
          "
        >
          {{ t('settings.ldapUsers.alerts.noPermission') }}
        </InfoAlert>
        <InfoAlert v-else-if="!cluster.database">
          {{ t('settings.ldapUsers.alerts.databaseDisabled') }}
        </InfoAlert>
        <div v-else class="space-y-4">
          <div class="ui-admin-search-bar">
            <div class="ui-admin-search-fields">
              <input
                :id="`ldap-users-query-${cluster.name}`"
                v-model="clusterQueries[cluster.name]"
                type="search"
                class="ui-input-field ui-admin-search-field"
                :aria-label="t('settings.ldapUsers.search.label')"
                :placeholder="t('settings.ldapUsers.search.placeholder')"
                @keyup.enter="searchClusterUsers(cluster)"
              />
            </div>
            <div class="ui-admin-search-actions">
              <button type="button" class="ui-button-primary" @click="searchClusterUsers(cluster)">
                {{ t('common.buttons.search') }}
              </button>
              <button type="button" class="ui-button-secondary" @click="resetClusterUsers(cluster)">
                {{ t('common.buttons.reset') }}
              </button>
            </div>

            <div
              v-if="!clusterLoading[cluster.name] && !clusterErrors[cluster.name]"
              class="ui-admin-search-meta"
            >
              {{
                (clusterTotals[cluster.name] ?? 0) === 1
                  ? t('settings.ldapUsers.resultsCount', { count: clusterTotals[cluster.name] ?? 0 })
                  : t('settings.ldapUsers.resultsCountPlural', { count: clusterTotals[cluster.name] ?? 0 })
              }}
            </div>
          </div>

          <div
            v-if="clusterLoading[cluster.name] || clusterLoaded[cluster.name] !== true"
            class="text-[var(--color-brand-muted)]"
          >
            <LoadingSpinner :size="5" />
            {{ t('settings.ldapUsers.loading') }}
          </div>
          <ErrorAlert v-else-if="clusterErrors[cluster.name]">
            {{ clusterErrors[cluster.name] }}
          </ErrorAlert>
          <InfoAlert v-else-if="(clusterTotals[cluster.name] ?? 0) === 0">
            {{ t('settings.ldapUsers.alerts.empty') }}
          </InfoAlert>
          <div v-else class="ui-table-shell ui-results-card">
            <div class="ui-table-scroll">
              <div class="ui-table-scroll-inner">
                <table class="ui-table min-w-full">
                  <thead>
                    <tr>
                      <th scope="col" class="py-3.5 pr-3 pl-6 text-left">{{ t('settings.ldapUsers.columns.username') }}</th>
                      <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ldapUsers.columns.fullName') }}</th>
                      <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ldapUsers.columns.shortcuts') }}</th>
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
                            {{ t('settings.ldapUsers.actions.viewUser') }}
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
                            {{ t('settings.ldapUsers.actions.openAnalysis') }}
                          </RouterLink>
                          <RouterLink
                            v-if="runtimeStore.hasRoutePermission(cluster.name, 'jobs-history', 'view')"
                            :to="{ name: 'jobs-history', params: { cluster: cluster.name }, query: { user: user.username } }"
                            class="ui-button-secondary"
                          >
                            {{ t('settings.ldapUsers.actions.viewHistoryJobs') }}
                          </RouterLink>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="mt-3">
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
