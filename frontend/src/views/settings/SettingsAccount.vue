<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'

const runtimeStore = useRuntimeStore()
const authStore = useAuthStore()
</script>

<template>
  <SettingsTabs entry="Account" />
  <div class="ui-panel ui-section">
    <SettingsHeader title="Account" description="Personal identity, group membership and cluster-level permissions." />

    <div class="ui-detail-list mt-6">
      <dl>
        <div class="ui-detail-row">
          <dt class="ui-detail-term">Username</dt>
          <dd class="ui-detail-value">{{ authStore.username }}</dd>
        </div>
        <div class="ui-detail-row">
          <dt class="ui-detail-term">Full name</dt>
          <dd class="ui-detail-value">{{ authStore.fullname }}</dd>
        </div>
        <div class="ui-detail-row">
          <dt class="ui-detail-term">Groups</dt>
          <dd class="ui-detail-value">{{ authStore.groups?.join(', ') }}</dd>
        </div>
      </dl>
    </div>
  </div>

  <div class="ui-table-shell overflow-x-auto">
    <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
      <h2 class="ui-panel-title">Cluster Permissions</h2>
      <p class="ui-panel-description mt-2">
        Roles and actions currently granted for each accessible cluster.
      </p>
    </div>

    <div class="inline-block min-w-full align-middle">
      <table class="ui-table min-w-full">
        <thead>
          <tr>
            <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Cluster</th>
            <th scope="col" class="px-3 py-3.5 text-left">Roles</th>
            <th scope="col" class="px-3 py-3.5 text-left">Actions</th>
          </tr>
        </thead>
        <tbody class="text-sm text-[var(--color-brand-muted)]">
          <tr v-for="cluster in runtimeStore.getAllowedClusters()" :key="cluster.name">
            <td class="py-4 pr-3 pl-6 align-top font-semibold text-[var(--color-brand-ink-strong)]">
              {{ cluster.name }}
            </td>
            <td class="px-3 py-4 align-top">
              <div class="flex flex-wrap gap-2">
                <span v-for="role in cluster.permissions.roles.sort()" :key="role" class="ui-chip">
                  {{ role }}
                </span>
              </div>
            </td>
            <td class="px-3 py-4 align-top">
              <div class="flex flex-wrap gap-2">
                <span v-for="action in cluster.permissions.actions.sort()" :key="action" class="ui-chip">
                  {{ action }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
