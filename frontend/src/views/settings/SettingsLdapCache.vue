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

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()

const clusterUsers = reactive<Record<string, CachedLdapUser[]>>({})
const clusterErrors = reactive<Record<string, string | null>>({})
const clusterLoading = reactive<Record<string, boolean>>({})

const clusters = computed(() => runtimeStore.availableClusters)
const pageVisible = computed(
  () => runtimeConfiguration.authentication && clusters.value.some((cluster) => cluster.database)
)

async function fetchClusterUsers(cluster: ClusterDescription) {
  if (!cluster.database || !runtimeStore.hasClusterPermission(cluster.name, 'cache-view')) {
    return
  }

  clusterLoading[cluster.name] = true
  clusterErrors[cluster.name] = null

  try {
    clusterUsers[cluster.name] = await gateway.ldap_cache_users(cluster.name)
  } catch (error: unknown) {
    clusterErrors[cluster.name] = error instanceof Error ? error.message : String(error)
  } finally {
    clusterLoading[cluster.name] = false
  }
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
            <div v-else-if="clusterLoading[cluster.name]" class="py-6 text-gray-400">
              <LoadingSpinner :size="5" />
              Loading cached LDAP users...
            </div>
            <ErrorAlert v-else-if="clusterErrors[cluster.name]">
              {{ clusterErrors[cluster.name] }}
            </ErrorAlert>
            <InfoAlert v-else-if="(clusterUsers[cluster.name] ?? []).length === 0">
              No cached LDAP users found on this cluster.
            </InfoAlert>
            <div v-else class="mt-6">
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
                    <td class="py-4 pr-3 font-medium whitespace-nowrap text-gray-900 dark:text-gray-100">
                      {{ user.username }}
                    </td>
                    <td class="px-3 py-4 whitespace-nowrap">{{ user.fullname ?? '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
