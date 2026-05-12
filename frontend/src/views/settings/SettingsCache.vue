<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { useRoute } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsCacheStatistics from '@/components/settings/SettingsCacheStatistics.vue'
import SettingsCacheMetrics from '@/components/settings/SettingsCacheMetrics.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import AdminTabs from '@/components/admin/AdminTabs.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'

const runtimeStore = useRuntimeStore()
const route = useRoute()
const { t } = useI18n()
const isAdminRoute = computed(() => String(route.name ?? '').startsWith('admin-'))
const tabsComponent = computed(() => (isAdminRoute.value ? AdminTabs : SettingsTabs))
const headerComponent = computed(() => (isAdminRoute.value ? AdminHeader : SettingsHeader))
</script>

<template>
  <div class="ui-section-stack">
    <component
      :is="tabsComponent"
      entry="cache"
      :cluster="runtimeStore.currentCluster?.name ?? runtimeStore.availableClusters[0]?.name ?? ''"
    />
    <div class="ui-panel ui-section">
      <component
        :is="headerComponent"
        title="settings.cache.title"
        description="settings.cache.description"
      />
    </div>

    <div
      v-for="cluster in runtimeStore.availableClusters"
      :key="cluster.name"
      class="ui-panel ui-section"
    >
      <div class="mb-6">
        <p class="ui-page-kicker">{{ t('settings.cache.clusterKicker') }}</p>
        <h3 class="text-2xl font-bold text-[var(--color-brand-ink-strong)]">
          {{ t('settings.cache.clusterTitle', { cluster: cluster.name }) }}
        </h3>
      </div>

      <InfoAlert
        v-if="
          !runtimeStore.hasRoutePermission(
            cluster.name,
            isAdminRoute ? 'admin/cache' : 'settings/cache',
            'view'
          )
        "
      >
        {{ t('settings.cache.alerts.noPermission') }}
      </InfoAlert>
      <InfoAlert v-else-if="!cluster.cache">{{ t('settings.cache.alerts.disabled') }}</InfoAlert>
      <template v-else>
        <div class="ui-section-stack">
          <SettingsCacheStatistics :cluster="cluster" />
          <SettingsCacheMetrics v-if="cluster.metrics" :cluster="cluster" />
          <div
            v-else
            class="rounded-[28px] border border-[rgba(80,105,127,0.12)] bg-[rgba(244,248,251,0.86)] px-6 py-5"
          >
            <p class="ui-page-kicker">{{ t('settings.cache.metricsUnavailable.kicker') }}</p>
            <h4 class="ui-panel-title">{{ t('settings.cache.metricsUnavailable.title') }}</h4>
            <p class="ui-panel-description mt-2">
              {{ t('settings.cache.metricsUnavailable.description') }}
            </p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
