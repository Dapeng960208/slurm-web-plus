<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { entry } = defineProps<{ entry: string }>()
const { t } = useI18n()

const tabs = computed(() => {
  return [
    { name: 'General', labelKey: 'shell.settings.general', href: 'settings' },
    { name: 'Errors', labelKey: 'shell.settings.errors', href: 'settings-errors' },
    { name: 'Account', labelKey: 'shell.settings.account', href: 'settings-account' }
  ]
})
</script>
<template>
  <div class="ui-panel ui-section">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 class="text-base leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
          {{ t('shell.settings.tabsTitle') }}
        </h3>
        <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
          {{ t('shell.settings.tabsDescription') }}
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
            >{{ t(tab.labelKey) }}</RouterLink
          >
        </nav>
      </div>
    </div>
  </div>
</template>
