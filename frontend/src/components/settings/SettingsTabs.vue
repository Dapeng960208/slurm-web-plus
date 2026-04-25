<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { hasClusterAIAssistant, hasClusterAccessControl } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'

const { entry } = defineProps<{ entry: string }>()
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()

const settingsCluster = computed(() => {
  if (runtimeStore.currentCluster) return runtimeStore.currentCluster
  const routeCluster = runtimeStore.beforeSettingsRoute?.params?.cluster
  if (typeof routeCluster === 'string') {
    const cluster = runtimeStore.getCluster(routeCluster)
    if (cluster) return cluster
  }
  return runtimeStore.getAllowedClusters()[0]
})

const tabs = computed(() => {
  const result = [
    { name: 'General', href: 'settings' },
    { name: 'Errors', href: 'settings-errors' },
    { name: 'Account', href: 'settings-account' }
  ]
  if (
    hasClusterAIAssistant(settingsCluster.value) &&
    settingsCluster.value &&
    runtimeStore.hasRoutePermission(settingsCluster.value.name, 'settings/ai', 'view')
  ) {
    result.push({ name: 'AI', href: 'settings-ai' })
  }
  if (
    hasClusterAccessControl(settingsCluster.value) &&
    settingsCluster.value &&
    runtimeStore.hasRoutePermission(settingsCluster.value.name, 'settings/access-control', 'view')
  ) {
    result.push({ name: 'Access Control', href: 'settings-access-control' })
  }
  if (
    settingsCluster.value &&
    runtimeStore.hasRoutePermission(settingsCluster.value.name, 'settings/cache', 'view')
  ) {
    result.push({ name: 'Cache', href: 'settings-cache' })
  }
  if (
    runtimeConfiguration.authentication &&
    runtimeStore.availableClusters.some(
      (cluster) =>
        cluster.database &&
        runtimeStore.hasRoutePermission(cluster.name, 'settings/ldap-cache', 'view')
    )
  ) {
    result.push({ name: 'LDAP Cache', href: 'settings-ldap-cache' })
  }
  return result
})
</script>
<template>
  <div class="ui-panel ui-section">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 class="text-base leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
          Settings
        </h3>
        <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
          Preferences, access and cache services in one unified workspace.
        </p>
      </div>
      <div class="mt-1">
        <nav class="flex flex-wrap gap-2">
          <RouterLink
            v-for="tab in tabs"
            :key="tab.name"
            :to="{ name: tab.href }"
            :class="[
              entry == tab.name
                ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                : 'bg-[rgba(239,244,246,0.7)] text-[var(--color-brand-muted)] hover:bg-white hover:text-[var(--color-brand-ink-strong)]',
              'rounded-full px-4 py-2.5 text-sm font-medium whitespace-nowrap transition'
            ]"
            :aria-current="entry == tab.name ? 'page' : undefined"
            >{{ tab.name }}</RouterLink
          >
        </nav>
      </div>
    </div>
  </div>
</template>
