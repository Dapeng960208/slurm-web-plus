<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { AccessControlSourceName } from '@/composables/GatewayAPI'
import { normalizeClusterPermissions } from '@/composables/GatewayAPI'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'

const runtimeStore = useRuntimeStore()
const authStore = useAuthStore()

const permissionSources: Array<{
  key: AccessControlSourceName
  title: string
  description: string
}> = [
  {
    key: 'policy',
    title: 'Policy',
    description: 'Base RBAC roles and actions from the active policy.'
  },
  {
    key: 'custom',
    title: 'Custom',
    description: 'Site-specific additions or overrides.'
  },
  {
    key: 'merged',
    title: 'Merged',
    description: 'Effective permissions exposed to the application.'
  }
]

const clusters = computed(() =>
  runtimeStore.getAllowedClusters().map((cluster) => ({
    ...cluster,
    permissions: normalizeClusterPermissions(cluster.permissions)
  }))
)

function sortedValues(values: string[]) {
  return [...values].sort()
}
</script>

<template>
  <div class="ui-section-stack">
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

    <div class="ui-section-stack">
      <div
        v-for="cluster in clusters"
        :key="cluster.name"
        class="ui-panel ui-section"
      >
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p class="ui-page-kicker">Cluster Permissions</p>
            <h2 class="ui-panel-title">{{ cluster.name }}</h2>
            <p class="ui-panel-description mt-2">
              Policy, custom overrides and merged permissions resolved for this cluster.
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <RouterLink
              :to="{ name: 'user', params: { cluster: cluster.name, user: authStore.username } }"
              class="ui-button-secondary"
            >
              View my user
            </RouterLink>
            <RouterLink
              v-if="cluster.user_metrics"
              :to="{ name: 'user-analysis', params: { cluster: cluster.name, user: authStore.username } }"
              class="ui-button-secondary"
            >
              View my analysis
            </RouterLink>
            <RouterLink
              v-if="runtimeStore.hasClusterPermission(cluster.name, 'view-history-jobs')"
              :to="{ name: 'jobs-history', params: { cluster: cluster.name }, query: { user: authStore.username } }"
              class="ui-button-secondary"
            >
              View my history jobs
            </RouterLink>
          </div>
        </div>

        <div class="mt-6 grid gap-4 xl:grid-cols-3">
          <section
            v-for="source in permissionSources"
            :key="`${cluster.name}-${source.key}`"
            class="rounded-[26px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-5"
          >
            <p class="ui-page-kicker">{{ source.title }}</p>
            <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
              {{ source.title }} Roles & Actions
            </h3>
            <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
              {{ source.description }}
            </p>

            <div class="mt-5 space-y-5">
              <div>
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">Roles</p>
                <div
                  v-if="cluster.permissions.sources?.[source.key]?.roles.length"
                  class="mt-3 flex flex-wrap gap-2"
                >
                  <span
                    v-for="role in sortedValues(cluster.permissions.sources?.[source.key]?.roles ?? [])"
                    :key="`${cluster.name}-${source.key}-role-${role}`"
                    class="ui-chip"
                  >
                    {{ role }}
                  </span>
                </div>
                <p v-else class="mt-3 text-sm text-[var(--color-brand-muted)]">No roles declared.</p>
              </div>

              <div>
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">Actions</p>
                <div
                  v-if="cluster.permissions.sources?.[source.key]?.actions.length"
                  class="mt-3 flex flex-wrap gap-2"
                >
                  <span
                    v-for="action in sortedValues(cluster.permissions.sources?.[source.key]?.actions ?? [])"
                    :key="`${cluster.name}-${source.key}-action-${action}`"
                    class="ui-chip"
                  >
                    {{ action }}
                  </span>
                </div>
                <p v-else class="mt-3 text-sm text-[var(--color-brand-muted)]">
                  No actions declared.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>
