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
import { useI18n } from 'vue-i18n'

const { entry, cluster } = defineProps<{
  entry: string
  cluster: string
}>()

const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()
const { t } = useI18n()

const tabs = computed(() => {
  const result: Array<{ id: string; labelKey: string; href: string }> = []
  if (runtimeStore.hasRoutePermission(cluster, 'admin/ai', 'view')) {
    result.push({ id: 'ai', labelKey: 'components.admin.ai', href: 'admin-ai' })
  }
  if (runtimeStore.hasRoutePermission(cluster, 'admin/cache', 'view')) {
    result.push({ id: 'cache', labelKey: 'components.admin.cache', href: 'admin-cache' })
  }
  if (
    runtimeConfiguration.authentication &&
    runtimeStore.hasRoutePermission(cluster, 'admin/ldap-users', 'view')
  ) {
    result.push({ id: 'users', labelKey: 'components.admin.users', href: 'admin-ldap-users' })
  }
  if (runtimeStore.hasRoutePermission(cluster, 'admin/access-control', 'view')) {
    result.push({
      id: 'access-control',
      labelKey: 'components.admin.accessControl',
      href: 'admin-access-control'
    })
  }
  return result
})
</script>

<template>
  <div class="ui-panel ui-section">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 class="text-base leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
          {{ t('components.admin.title') }}
        </h3>
        <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
          {{ t('components.admin.description') }}
        </p>
      </div>
      <div class="mt-1">
        <nav class="flex flex-wrap gap-2">
          <RouterLink
            v-for="tab in tabs"
            :key="tab.id"
            :to="{ name: tab.href, params: { cluster } }"
            :class="[
              entry == tab.id
                ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                : 'bg-[rgba(239,244,246,0.7)] text-[var(--color-brand-muted)] hover:bg-white hover:text-[var(--color-brand-ink-strong)]',
              'rounded-full px-4 py-2.5 text-sm font-medium whitespace-nowrap transition'
            ]"
            :aria-current="entry == tab.id ? 'page' : undefined"
          >
            {{ t(tab.labelKey) }}
          </RouterLink>
        </nav>
      </div>
    </div>
  </div>
</template>
