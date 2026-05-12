<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { AccessControlSourceName } from '@/composables/GatewayAPI'
import { normalizeClusterPermissions } from '@/composables/GatewayAPI'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'

const runtimeStore = useRuntimeStore()
const authStore = useAuthStore()
const { t } = useI18n()

const permissionSources: Array<{
  key: AccessControlSourceName
  titleKey: string
  descriptionKey: string
}> = [
  {
    key: 'policy',
    titleKey: 'settings.account.permissionSources.policy.title',
    descriptionKey: 'settings.account.permissionSources.policy.description'
  },
  {
    key: 'custom',
    titleKey: 'settings.account.permissionSources.custom.title',
    descriptionKey: 'settings.account.permissionSources.custom.description'
  },
  {
    key: 'merged',
    titleKey: 'settings.account.permissionSources.merged.title',
    descriptionKey: 'settings.account.permissionSources.merged.description'
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
    <SettingsTabs entry="account" />
    <div class="ui-panel ui-section">
      <SettingsHeader
        title="settings.account.title"
        description="settings.account.description"
      />

      <div class="ui-detail-list mt-6">
        <dl>
          <div class="ui-detail-row">
            <dt class="ui-detail-term">{{ t('settings.account.username') }}</dt>
            <dd class="ui-detail-value">{{ authStore.username }}</dd>
          </div>
          <div class="ui-detail-row">
            <dt class="ui-detail-term">{{ t('settings.account.fullName') }}</dt>
            <dd class="ui-detail-value">{{ authStore.fullname }}</dd>
          </div>
          <div class="ui-detail-row">
            <dt class="ui-detail-term">{{ t('settings.account.groups') }}</dt>
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
            <p class="ui-page-kicker">{{ t('settings.account.clusterPermissions') }}</p>
            <h2 class="ui-panel-title">{{ cluster.name }}</h2>
            <p class="ui-panel-description mt-2">
              {{ t('settings.account.clusterDescription') }}
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <RouterLink
              :to="{ name: 'my-profile', params: { cluster: cluster.name } }"
              class="ui-button-secondary"
            >
              {{ t('settings.account.actions.openWorkspace') }}
            </RouterLink>
            <RouterLink
              v-if="cluster.user_metrics"
              :to="{
                name: 'my-profile',
                params: { cluster: cluster.name },
                query: { section: 'analysis' }
              }"
              class="ui-button-secondary"
            >
              {{ t('settings.account.actions.openAnalysis') }}
            </RouterLink>
            <RouterLink
              v-if="runtimeStore.hasRoutePermission(cluster.name, 'jobs-history', 'view')"
              :to="{ name: 'jobs-history', params: { cluster: cluster.name }, query: { user: authStore.username } }"
              class="ui-button-secondary"
            >
              {{ t('settings.account.actions.viewHistoryJobs') }}
            </RouterLink>
          </div>
        </div>

        <div class="mt-6 grid gap-4 xl:grid-cols-3">
          <section
            v-for="source in permissionSources"
            :key="`${cluster.name}-${source.key}`"
            class="rounded-[26px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-5"
          >
            <p class="ui-page-kicker">{{ t(source.titleKey) }}</p>
            <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
              {{ t('settings.account.sourceSummary', { title: t(source.titleKey) }) }}
            </h3>
            <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
              {{ t(source.descriptionKey) }}
            </p>

            <div class="mt-5 space-y-5">
              <div>
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ t('settings.account.roles') }}
                </p>
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
                <p v-else class="mt-3 text-sm text-[var(--color-brand-muted)]">
                  {{ t('settings.account.emptyRoles') }}
                </p>
              </div>

              <div>
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ t('settings.account.actionsLabel') }}
                </p>
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
                  {{ t('settings.account.emptyActions') }}
                </p>
              </div>

              <div>
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ t('settings.account.rules') }}
                </p>
                <div
                  v-if="cluster.permissions.sources?.[source.key]?.rules.length"
                  class="mt-3 flex flex-wrap gap-2"
                >
                  <span
                    v-for="rule in sortedValues(cluster.permissions.sources?.[source.key]?.rules ?? [])"
                    :key="`${cluster.name}-${source.key}-rule-${rule}`"
                    class="ui-chip"
                  >
                    {{ rule }}
                  </span>
                </div>
                <p v-else class="mt-3 text-sm text-[var(--color-brand-muted)]">
                  {{ t('settings.account.emptyRules') }}
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>
