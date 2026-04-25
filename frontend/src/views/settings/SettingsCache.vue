<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
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
const isAdminRoute = computed(() => String(route.name ?? '').startsWith('admin-'))
const tabsComponent = computed(() => (isAdminRoute.value ? AdminTabs : SettingsTabs))
const headerComponent = computed(() => (isAdminRoute.value ? AdminHeader : SettingsHeader))
</script>

<template>
  <div class="ui-section-stack">
    <component
      :is="tabsComponent"
      entry="Cache"
      :cluster="runtimeStore.currentCluster?.name ?? runtimeStore.availableClusters[0]?.name ?? ''"
    />
    <div class="ui-panel ui-section">
      <component
        :is="headerComponent"
        title="Cache Service"
        description="Cache availability, hit ratios and live metrics for each cluster."
      />
    </div>

    <div
      v-for="cluster in runtimeStore.availableClusters"
      :key="cluster.name"
      class="ui-panel ui-section"
    >
      <div class="mb-6">
        <p class="ui-page-kicker">Cluster Cache</p>
        <h3 class="text-2xl font-bold text-[var(--color-brand-ink-strong)]">
          Cluster {{ cluster.name }}
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
        No permission to get cache information on this cluster.
      </InfoAlert>
      <InfoAlert v-else-if="!cluster.cache">Cache is disabled on this cluster.</InfoAlert>
      <template v-else>
        <div class="ui-section-stack">
          <SettingsCacheStatistics :cluster="cluster" />
          <SettingsCacheMetrics v-if="cluster.metrics" :cluster="cluster" />
          <div
            v-else
            class="rounded-[28px] border border-[rgba(80,105,127,0.12)] bg-[rgba(244,248,251,0.86)] px-6 py-5"
          >
            <p class="ui-page-kicker">Metrics Unavailable</p>
            <h4 class="ui-panel-title">Live cache metrics are unavailable</h4>
            <p class="ui-panel-description mt-2">
              This cluster exposes cache statistics, but metrics collection is disabled, so there
              is no live cache timeline to display.
            </p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
