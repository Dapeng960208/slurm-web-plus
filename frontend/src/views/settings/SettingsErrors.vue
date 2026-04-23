<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { useRuntimeStore } from '@/stores/runtime'
import InfoAlert from '@/components/InfoAlert.vue'

const runtimeStore = useRuntimeStore()
</script>

<template>
  <div class="ui-section-stack">
    <SettingsTabs entry="Errors" />
    <div class="ui-panel ui-section">
      <SettingsHeader title="Errors" description="Application errors captured during the current session." />
    </div>

    <InfoAlert v-if="runtimeStore.errors.length === 0">
      No application errors have been recorded in this session.
    </InfoAlert>

    <div v-else class="ui-table-shell overflow-x-auto">
      <div class="inline-block min-w-full align-middle">
        <table class="ui-table min-w-full">
        <thead>
          <tr>
            <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Timestamp</th>
            <th scope="col" class="px-3 py-3.5 text-left">Route</th>
            <th scope="col" class="px-3 py-3.5 text-left">Message</th>
          </tr>
        </thead>
        <tbody class="text-sm text-[var(--color-brand-muted)]">
          <tr v-for="error in runtimeStore.errors" :key="`${error.timestamp.toISOString()}-${error.message}`">
            <td class="py-4 pr-3 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
              {{ error.timestamp.toLocaleString() }}
            </td>
            <td class="px-3 py-4 whitespace-nowrap">{{ error.route }}</td>
            <td class="px-3 py-4">{{ error.message }}</td>
          </tr>
        </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
