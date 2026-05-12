<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { Switch } from '@headlessui/vue'
import LocaleSwitcher from '@/components/LocaleSwitcher.vue'

const runtimeStore = useRuntimeStore()
const { t } = useI18n()
</script>

<template>
  <div class="ui-section-stack">
    <SettingsTabs entry="general" />
    <div class="ui-panel ui-section">
      <SettingsHeader
        title="settings.general.title"
        description="settings.general.description"
      />
      <div class="ui-panel-soft mt-6 rounded-[24px] px-5">
        <dl class="divide-y divide-[rgba(80,105,127,0.1)] text-sm/6">
          <div class="py-6 sm:flex">
            <dt class="font-medium text-[var(--color-brand-ink-strong)] sm:w-72 sm:flex-none sm:pr-6">
              {{ t('settings.general.localeLabel') }}
            </dt>
            <dd class="mt-1 flex justify-between gap-x-6 sm:mt-0 sm:flex-auto sm:items-center">
              <p class="mt-1 text-xs text-[var(--color-brand-muted)]">
                {{ t('settings.general.localeDescription') }}
              </p>
              <LocaleSwitcher />
            </dd>
          </div>
          <div class="py-6 sm:flex">
            <dt class="font-medium text-[var(--color-brand-ink-strong)] sm:w-72 sm:flex-none sm:pr-6">
              {{ t('settings.general.showNodeNames') }}
            </dt>
            <dd class="mt-1 flex justify-between gap-x-6 sm:mt-0 sm:flex-auto">
              <p class="mt-1 text-xs text-[var(--color-brand-muted)]">
                {{ t('settings.general.showNodeNamesHint') }}
              </p>
              <Switch
                v-model="runtimeStore.resources.showNodeNames"
                :class="[
                  runtimeStore.resources.showNodeNames
                    ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))]'
                    : 'bg-[rgba(80,105,127,0.16)]',
                  'relative mt-1 inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none'
                ]"
              >
                <span class="sr-only">{{ t('shell.settings.general') }}</span>
                <span
                  :class="[
                    runtimeStore.resources.showNodeNames ? 'translate-x-5' : 'translate-x-0',
                    'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out'
                  ]"
                />
              </Switch>
            </dd>
          </div>
        </dl>
      </div>
    </div>
  </div>
</template>
