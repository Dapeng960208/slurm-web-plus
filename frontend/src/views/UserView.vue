<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import {
  IdentificationIcon,
  ShieldCheckIcon,
  UsersIcon,
  ServerStackIcon
} from '@heroicons/vue/24/outline'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import {
  normalizeClusterPermissions,
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'
import { resolveUserWorkspaceSections } from '@/composables/userWorkspace'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'
import UserAnalyticsPanels from '@/components/user/UserAnalyticsPanels.vue'

const props = withDefaults(
  defineProps<{
    cluster: string
    user?: string
    selfView?: boolean
  }>(),
  {
    user: undefined,
    selfView: false
  }
)

const route = useRoute()
const router = useRouter()
const runtimeStore = useRuntimeStore()
const authStore = useAuthStore()
const viewedUser = computed(() => props.selfView ? authStore.username ?? props.user ?? '' : props.user ?? '')
const clusterDetails = computed(() => runtimeStore.getCluster(props.cluster))
const sections = computed(() =>
  resolveUserWorkspaceSections(
    runtimeStore,
    clusterDetails.value,
    props.cluster,
    viewedUser.value,
    authStore.username
  )
)

const { data, unable, loaded, initialLoading, setCluster } = useClusterDataPoller<ClusterAssociation[]>(
  props.cluster,
  'associations',
  120000
)

watch(
  () => props.cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

const clusterPermissions = computed(() =>
  normalizeClusterPermissions(clusterDetails.value?.permissions)
)

const userAssociations = computed(() => {
  if (!data.value || !viewedUser.value) return []
  return data.value
    .filter((association) => association.user === viewedUser.value)
    .sort((a, b) => a.account.localeCompare(b.account))
})

const knownUser = computed(() => userAssociations.value.length > 0)

const associatedAccounts = computed(() => {
  const accounts = new Set<string>()
  for (const association of userAssociations.value) {
    accounts.add(association.account)
  }
  return accounts
})

const canViewHistoryJobs = computed(() =>
  runtimeStore.hasRoutePermission(props.cluster, 'jobs-history', 'view')
)

const breadcrumb = computed(() => {
  if (sections.value.self) {
    return [{ title: 'My Workspace' }, { title: viewedUser.value || 'User' }]
  }
  return [
    { title: 'Accounts', routeName: 'accounts' },
    { title: `User ${viewedUser.value || props.user}` }
  ]
})

const orderedSections = computed(() => {
  const querySection = route.query.section
  const result: Array<'profile' | 'analytics'> = []
  if (querySection === 'analysis' && sections.value.analytics) {
    result.push('analytics')
  }
  if (sections.value.profile) {
    result.push('profile')
  }
  if (sections.value.analytics && !result.includes('analytics')) {
    result.push('analytics')
  }
  return result
})

function jobLimits(association: ClusterAssociation) {
  return [
    { id: 'MaxJobs', label: 'Running / user', value: association.max.jobs.active },
    { id: 'MaxSubmit', label: 'Submitted / user', value: association.max.jobs.total }
  ]
}

function resourceLimits(association: ClusterAssociation) {
  return [
    { id: 'GrpTRES', label: 'Total', value: association.max.tres.total },
    { id: 'MaxTRES', label: 'Per job', value: association.max.tres.per.job },
    { id: 'MaxTRESPerNode', label: 'Per node', value: association.max.tres.per.node }
  ]
}

function timeLimits(association: ClusterAssociation) {
  return [
    { id: 'GrpWall', label: 'Total', value: association.max.per.account.wall_clock },
    { id: 'MaxWall', label: 'Per job', value: association.max.jobs.per.wall_clock }
  ]
}

function goBack() {
  if (sections.value.self) {
    router.push({ name: 'dashboard', params: { cluster: props.cluster } })
    return
  }
  router.push({ name: 'accounts', params: { cluster: props.cluster } })
}
</script>

<template>
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="breadcrumb"
  >
    <div class="ui-page ui-page-readable">
      <button @click="goBack" type="button" class="ui-button-secondary self-start">
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        {{ sections.self ? 'Back to dashboard' : 'Back to accounts' }}
      </button>

      <div class="ui-section-stack">
        <div id="user-heading">
          <PageHeader
            kicker="User Workspace"
            :title="viewedUser"
            :description="
              sections.self
                ? 'Personal identity, effective cluster permissions, account associations and user analytics in one workspace.'
                : 'Account associations, history shortcuts and analytics for the selected user.'
            "
            :metric-value="loaded && sections.profile ? associatedAccounts.size : undefined"
            :metric-label="sections.profile ? `account${associatedAccounts.size === 1 ? '' : 's'} associated` : undefined"
          >
            <template #actions>
              <div class="flex flex-wrap gap-3">
                <RouterLink
                  :to="{ name: 'jobs', params: { cluster }, query: { users: viewedUser } }"
                  class="ui-button-primary"
                >
                  View jobs
                </RouterLink>
                <RouterLink
                  v-if="canViewHistoryJobs"
                  :to="{ name: 'jobs-history', params: { cluster }, query: { user: viewedUser } }"
                  class="ui-button-secondary"
                >
                  View history jobs
                </RouterLink>
                <RouterLink
                  v-if="sections.self"
                  :to="{ name: 'settings-account' }"
                  class="ui-button-secondary"
                >
                  Account permissions
                </RouterLink>
              </div>
            </template>
          </PageHeader>
        </div>

        <div v-if="sections.self" class="ui-section-stack">
          <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div class="ui-stat-card">
              <div class="ui-stat-label">Username</div>
              <div class="ui-stat-value">{{ authStore.username }}</div>
              <div class="ui-stat-subtle">{{ authStore.fullname || 'No full name cached' }}</div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">Cluster</div>
              <div class="ui-stat-value">{{ cluster }}</div>
              <div class="ui-stat-subtle">Current workspace context</div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">Effective Roles</div>
              <div class="ui-stat-value">{{ clusterPermissions.roles.length }}</div>
              <div class="ui-stat-subtle">Merged policy and custom roles</div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">Effective Actions</div>
              <div class="ui-stat-value">{{ clusterPermissions.actions.length }}</div>
              <div class="ui-stat-subtle">Permissions exposed to the frontend</div>
            </div>
          </div>

          <section class="ui-panel ui-section">
            <div class="mb-4 flex items-start justify-between gap-4">
              <div>
                <p class="ui-page-kicker">Identity Summary</p>
                <h2 class="ui-panel-title">My account and permissions</h2>
                <p class="ui-panel-description mt-2">
                  Local account identity plus merged cluster-level permissions.
                </p>
              </div>
            </div>

            <div class="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
              <div class="ui-panel-soft px-5 py-5">
                <div class="flex items-center gap-3">
                  <span class="ui-user-workspace-icon">
                    <IdentificationIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">Identity</div>
                </div>
                <dl class="mt-4 space-y-3 text-sm text-[var(--color-brand-muted)]">
                  <div class="flex flex-wrap items-center gap-2">
                    <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Username:</dt>
                    <dd>{{ authStore.username }}</dd>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Full name:</dt>
                    <dd>{{ authStore.fullname || '-' }}</dd>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Groups:</dt>
                    <dd>{{ authStore.groups?.join(', ') || '-' }}</dd>
                  </div>
                </dl>
              </div>

              <div class="ui-panel-soft px-5 py-5">
                <div class="flex items-center gap-3">
                  <span class="ui-user-workspace-icon">
                    <ShieldCheckIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">Merged actions</div>
                </div>
                <div class="mt-4 flex flex-wrap gap-2">
                  <span
                    v-for="action in clusterPermissions.actions"
                    :key="`self-action-${action}`"
                    class="ui-chip"
                  >
                    {{ action }}
                  </span>
                  <span
                    v-if="clusterPermissions.actions.length === 0"
                    class="text-sm text-[var(--color-brand-muted)]"
                  >
                    No actions declared.
                  </span>
                </div>
              </div>

              <div class="ui-panel-soft px-5 py-5">
                <div class="flex items-center gap-3">
                  <span class="ui-user-workspace-icon">
                    <ShieldCheckIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">Merged rules</div>
                </div>
                <div class="mt-4 flex flex-wrap gap-2">
                  <span
                    v-for="rule in clusterPermissions.rules"
                    :key="`self-rule-${rule}`"
                    class="ui-chip"
                  >
                    {{ rule }}
                  </span>
                  <span
                    v-if="clusterPermissions.rules.length === 0"
                    class="text-sm text-[var(--color-brand-muted)]"
                  >
                    No route rules declared.
                  </span>
                </div>
              </div>
            </div>
          </section>
        </div>

        <template v-for="section in orderedSections" :key="section">
          <section v-if="section === 'profile'" class="ui-panel ui-section">
            <div class="mb-5">
              <p class="ui-page-kicker">User Profile</p>
              <h2 class="ui-panel-title">Account associations and limits</h2>
              <p class="ui-panel-description mt-2">
                LDAP-linked account associations, quota boundaries and job history shortcuts for this user.
              </p>
            </div>

            <PanelSkeleton v-if="initialLoading && !unable" :rows="8" />

            <ErrorAlert v-else-if="unable">
              Unable to retrieve associations for cluster
              <span class="font-medium">{{ cluster }}</span>
            </ErrorAlert>
            <div v-else class="ui-section-stack">
              <div v-if="canViewHistoryJobs" class="grid gap-3 sm:grid-cols-2">
                <div class="ui-panel-soft px-4 py-3">
                  <div class="ui-stat-label">History Jobs</div>
                  <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                    History access granted
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    Jump directly into persisted jobs history filtered on this user.
                  </div>
                </div>
                <div class="ui-panel-soft px-4 py-3">
                  <div class="ui-stat-label">Accounts</div>
                  <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ associatedAccounts.size }}
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    Account association{{ associatedAccounts.size === 1 ? '' : 's' }} found for this user.
                  </div>
                </div>
              </div>

              <InfoAlert v-if="loaded && !knownUser">
                User <span class="font-semibold">{{ viewedUser }}</span> has no associations on this cluster.
              </InfoAlert>

              <div v-else-if="loaded" class="ui-table-shell overflow-x-auto">
                <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
                  <h3 class="ui-panel-title">Account Associations</h3>
                  <p class="ui-panel-description mt-2">
                    Each row represents one account binding and the limits attached to it.
                  </p>
                </div>

                <div class="inline-block min-w-full align-middle">
                  <table class="ui-table min-w-full">
                    <thead>
                      <tr>
                        <th scope="col" class="py-3.5 pr-3 pl-6 text-left lg:min-w-[220px]">Account</th>
                        <th scope="col" class="hidden w-72 px-3 py-3.5 text-left sm:table-cell">Job limits</th>
                        <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">Resource limits</th>
                        <th scope="col" class="hidden w-72 px-3 py-3.5 text-left md:table-cell">Time limits</th>
                        <th scope="col" class="hidden w-48 px-3 py-3.5 text-left 2xl:table-cell">QOS</th>
                      </tr>
                    </thead>
                    <tbody class="text-sm text-[var(--color-brand-muted)]">
                      <tr
                        v-for="association in userAssociations"
                        :key="`${association.account}-${association.user}`"
                      >
                        <td class="py-4 pr-3 pl-6 align-top text-[var(--color-brand-ink-strong)]">
                          <AccountBreadcrumb
                            :cluster="cluster"
                            :account="association.account"
                            :associations="data ?? []"
                            show-current
                          />
                        </td>
                        <td class="hidden px-3 py-4 align-top sm:table-cell">
                          <div v-if="jobLimits(association).length === 0">-</div>
                          <dl v-else class="space-y-2">
                            <div
                              v-for="limit in jobLimits(association)"
                              :key="limit.id"
                              class="flex flex-wrap items-center gap-2"
                            >
                              <dt class="font-semibold text-[var(--color-brand-ink-strong)]">
                                {{ limit.label }}:
                              </dt>
                              <dd>{{ renderClusterOptionalNumber(limit.value) }}</dd>
                            </div>
                          </dl>
                        </td>
                        <td class="hidden px-3 py-4 align-top lg:table-cell">
                          <div v-if="resourceLimits(association).length === 0">-</div>
                          <dl v-else class="space-y-2">
                            <div
                              v-for="limit in resourceLimits(association)"
                              :key="limit.id"
                              class="flex flex-wrap items-center gap-2"
                            >
                              <dt class="font-semibold text-[var(--color-brand-ink-strong)]">
                                {{ limit.label }}:
                              </dt>
                              <dd class="font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                            </div>
                          </dl>
                        </td>
                        <td class="hidden px-3 py-4 align-top md:table-cell">
                          <div v-if="timeLimits(association).length === 0">-</div>
                          <dl v-else class="space-y-2">
                            <div
                              v-for="limit in timeLimits(association)"
                              :key="limit.id"
                              class="flex flex-wrap items-center gap-2"
                            >
                              <dt class="font-semibold text-[var(--color-brand-ink-strong)]">
                                {{ limit.label }}:
                              </dt>
                              <dd>{{ renderWalltime(limit.value) }}</dd>
                            </div>
                          </dl>
                        </td>
                        <td class="hidden px-3 py-4 align-top 2xl:table-cell">
                          {{ renderQosLabel(association.qos) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </section>

          <section v-else-if="section === 'analytics'" class="ui-panel ui-section" id="analysis">
            <div class="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div>
                <p class="ui-page-kicker">User Analysis</p>
                <h2 class="ui-panel-title">Submission and tool analytics</h2>
                <p class="ui-panel-description mt-2">
                  Submission trends, dual-metric tool analysis and daily execution summaries for this user.
                </p>
              </div>
              <span class="ui-chip">
                <UsersIcon class="h-4 w-4" aria-hidden="true" />
                {{ viewedUser }}
              </span>
            </div>

            <UserAnalyticsPanels :cluster="cluster" :user="viewedUser" :enabled="sections.analytics" />
          </section>
        </template>

        <section
          v-if="!sections.profile && !sections.analytics && sections.self"
          class="ui-empty-state"
        >
          <div class="ui-empty-state-icon">
            <ServerStackIcon class="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <h2 class="ui-panel-title">Additional sections are unavailable</h2>
            <p class="ui-panel-description mt-2">
              This workspace can show account associations through `user/profile:view:*` and analytics through `user/analysis:view:*` on clusters where user metrics are enabled.
            </p>
          </div>
        </section>
      </div>
    </div>
  </ClusterMainLayout>
</template>
