<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'

const { entry, cluster } = defineProps<{
  entry: string
  cluster: string
}>()

const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()

const tabs = computed(() => {
  const result = []
  if (runtimeStore.hasRoutePermission(cluster, 'admin/system', 'view')) {
    result.push({ name: 'System', href: 'admin-system' })
  }
  if (runtimeStore.hasRoutePermission(cluster, 'admin/ai', 'view')) {
    result.push({ name: 'AI', href: 'admin-ai' })
  }
  if (runtimeStore.hasRoutePermission(cluster, 'admin/cache', 'view')) {
    result.push({ name: 'Cache', href: 'admin-cache' })
  }
  if (
    runtimeConfiguration.authentication &&
    runtimeStore.hasRoutePermission(cluster, 'admin/ldap-cache', 'view')
  ) {
    result.push({ name: 'LDAP Cache', href: 'admin-ldap-cache' })
  }
  if (runtimeStore.hasRoutePermission(cluster, 'admin/access-control', 'view')) {
    result.push({ name: 'Access Control', href: 'admin-access-control' })
  }
  return result
})
</script>

<template>
  <div class="ui-panel ui-section">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 class="text-base leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
          Admin
        </h3>
        <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
          Cluster-scoped administration, cache services and access controls.
        </p>
      </div>
      <div class="mt-1">
        <nav class="flex flex-wrap gap-2">
          <RouterLink
            v-for="tab in tabs"
            :key="tab.name"
            :to="{ name: tab.href, params: { cluster } }"
            :class="[
              entry == tab.name
                ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                : 'bg-[rgba(239,244,246,0.7)] text-[var(--color-brand-muted)] hover:bg-white hover:text-[var(--color-brand-ink-strong)]',
              'rounded-full px-4 py-2.5 text-sm font-medium whitespace-nowrap transition'
            ]"
            :aria-current="entry == tab.name ? 'page' : undefined"
          >
            {{ tab.name }}
          </RouterLink>
        </nav>
      </div>
    </div>
  </div>
</template>
