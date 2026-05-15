<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import {
  normalizeClusterPermissions,
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'
import { parseOptionalCsvList, stringifyList } from '@/composables/management'
import { resolveUserWorkspaceSections } from '@/composables/userWorkspace'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'
import UserAnalyticsPanels from '@/components/user/UserAnalyticsPanels.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { createStaticSearchSource } from '@/composables/searchSelect'

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
const gateway = useGatewayAPI()
const { t } = useI18n()
const editOpen = ref(false)
const deleteOpen = ref(false)
const operationBusy = ref(false)
const operationError = ref<string | null>(null)
const qosSearchSource = createStaticSearchSource(async () =>
  (await gateway.qos(props.cluster)).map((qos) => ({
    value: qos.name,
    label: qos.name,
    description: qos.description || qos.name
  }))
)
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

const { data, unable, loaded, initialLoading, refresh, setCluster } = useClusterDataPoller<ClusterAssociation[]>(
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
const canManageUser = computed(() =>
  runtimeStore.hasRoutePermission(props.cluster, 'users-admin', 'edit')
)
const canDeleteUser = computed(() =>
  runtimeStore.hasRoutePermission(props.cluster, 'users-admin', 'delete')
)

const breadcrumb = computed(() => {
  if (sections.value.self) {
    return [
      { title: t('pages.user.breadcrumb.myWorkspace') },
      { title: viewedUser.value || t('common.labels.user') }
    ]
  }
  return [
    { title: 'shell.mainMenu.accounts', routeName: 'accounts' },
    { title: t('pages.user.breadcrumb.userPrefix', { user: viewedUser.value || props.user || '' }) }
  ]
})

const orderedSections = computed(() => {
  const querySection = route.query.section
  const result: Array<'profile' | 'analytics'> = []
  if (sections.value.analytics && querySection !== 'profile') {
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
    { id: 'MaxJobs', label: 'pages.user.limits.runningPerUser', value: association.max.jobs.active },
    { id: 'MaxSubmit', label: 'pages.user.limits.submittedPerUser', value: association.max.jobs.total }
  ]
}

function resourceLimits(association: ClusterAssociation) {
  return [
    { id: 'GrpTRES', label: 'pages.user.limits.total', value: association.max.tres.total },
    { id: 'MaxTRES', label: 'pages.user.limits.perJob', value: association.max.tres.per.job },
    { id: 'MaxTRESPerNode', label: 'pages.user.limits.perNode', value: association.max.tres.per.node }
  ]
}

function timeLimits(association: ClusterAssociation) {
  return [
    { id: 'GrpWall', label: 'pages.user.limits.total', value: association.max.per.account.wall_clock },
    { id: 'MaxWall', label: 'pages.user.limits.perJob', value: association.max.jobs.per.wall_clock }
  ]
}

function goBack() {
  if (sections.value.self) {
    router.push({ name: 'dashboard', params: { cluster: props.cluster } })
    return
  }
  router.push({ name: 'accounts', params: { cluster: props.cluster } })
}

async function saveUser(payload: Record<string, string>) {
  if (!viewedUser.value) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.save_user(props.cluster, {
      name: viewedUser.value,
      description: payload.description || null,
      default_account: payload.default_account || undefined,
      default_qos: payload.default_qos || undefined,
      qos: parseOptionalCsvList(payload.qos),
      default_wckey: payload.default_wckey || undefined,
      admin_level: payload.admin_level || undefined
    })
    runtimeStore.reportInfo(t('pages.user.notifications.updateRequested', { user: viewedUser.value }))
    await refresh()
    editOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function removeUser() {
  if (!viewedUser.value) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.delete_user(props.cluster, viewedUser.value)
    runtimeStore.reportInfo(t('pages.user.notifications.deleteRequested', { user: viewedUser.value }))
    await refresh()
    deleteOpen.value = false
    goBack()
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}
</script>

<template>
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="breadcrumb"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <button @click="goBack" type="button" class="ui-button-secondary self-start shrink-0">
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        {{ sections.self ? t('pages.user.backToDashboard') : t('pages.user.backToAccounts') }}
      </button>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
        <div id="user-heading">
          <PageHeader
            kicker="pages.user.kicker"
            :title="viewedUser"
            :description="
              sections.self
                ? 'pages.user.selfDescription'
                : 'pages.user.description'
            "
            :metric-value="loaded && sections.profile ? associatedAccounts.size : undefined"
            :metric-label="
              sections.profile
                ? associatedAccounts.size === 1
                  ? 'pages.user.metricLabel'
                  : 'pages.user.metricLabelPlural'
                : undefined
            "
          >
            <template #actions>
              <div class="flex flex-wrap gap-3">
                <RouterLink
                  :to="{ name: 'jobs', params: { cluster }, query: { users: viewedUser } }"
                  class="ui-button-primary"
                >
                  {{ t('pages.user.actions.viewJobs') }}
                </RouterLink>
                <RouterLink
                  v-if="canViewHistoryJobs"
                  :to="{ name: 'jobs-history', params: { cluster }, query: { user: viewedUser } }"
                  class="ui-button-secondary"
                >
                  {{ t('pages.user.actions.viewHistoryJobs') }}
                </RouterLink>
                <RouterLink
                  v-if="sections.self"
                  :to="{ name: 'settings-account' }"
                  class="ui-button-secondary"
                >
                  {{ t('pages.user.actions.accountPermissions') }}
                </RouterLink>
                <button
                  v-if="canManageUser"
                  type="button"
                  class="ui-button-warning"
                  @click="editOpen = true"
                >
                  {{ t('pages.user.actions.editUser') }}
                </button>
                <button
                  v-if="canDeleteUser"
                  type="button"
                  class="ui-button-danger"
                  @click="deleteOpen = true"
                >
                  {{ t('pages.user.actions.deleteUser') }}
                </button>
              </div>
            </template>
          </PageHeader>
        </div>

        <div v-if="sections.self" class="ui-section-stack">
          <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div class="ui-stat-card">
              <div class="ui-stat-label">{{ t('pages.user.selfStats.username') }}</div>
              <div class="ui-stat-value">{{ authStore.username }}</div>
              <div class="ui-stat-subtle">{{ authStore.fullname || t('pages.user.selfStats.noFullName') }}</div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">{{ t('pages.user.selfStats.cluster') }}</div>
              <div class="ui-stat-value">{{ cluster }}</div>
              <div class="ui-stat-subtle">{{ t('pages.user.selfStats.currentWorkspaceContext') }}</div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">{{ t('pages.user.selfStats.effectiveRoles') }}</div>
              <div class="ui-stat-value">{{ clusterPermissions.roles.length }}</div>
              <div class="ui-stat-subtle">{{ t('pages.user.selfStats.mergedPolicyAndCustomRoles') }}</div>
            </div>
            <div class="ui-stat-card">
              <div class="ui-stat-label">{{ t('pages.user.selfStats.effectiveActions') }}</div>
              <div class="ui-stat-value">{{ clusterPermissions.actions.length }}</div>
              <div class="ui-stat-subtle">{{ t('pages.user.selfStats.permissionsExposed') }}</div>
            </div>
          </div>

          <section class="ui-panel ui-section">
            <div class="mb-4 flex items-start justify-between gap-4">
              <div>
                <p class="ui-page-kicker">{{ t('pages.user.identity.summaryKicker') }}</p>
                <h2 class="ui-panel-title">{{ t('pages.user.identity.summaryTitle') }}</h2>
                <p class="ui-panel-description mt-2">
                  {{ t('pages.user.identity.summaryDescription') }}
                </p>
              </div>
            </div>

            <div class="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
              <div class="ui-panel-soft px-5 py-5">
                <div class="flex items-center gap-3">
                  <span class="ui-user-workspace-icon">
                    <IdentificationIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t('pages.user.identity.identity') }}</div>
                </div>
                <dl class="mt-4 space-y-3 text-sm text-[var(--color-brand-muted)]">
                  <div class="flex flex-wrap items-center gap-2">
                    <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t('pages.user.identity.username') }}</dt>
                    <dd>{{ authStore.username }}</dd>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t('pages.user.identity.fullName') }}</dt>
                    <dd>{{ authStore.fullname || '-' }}</dd>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t('pages.user.identity.groups') }}</dt>
                    <dd>{{ authStore.groups?.join(', ') || '-' }}</dd>
                  </div>
                </dl>
              </div>

              <div class="ui-panel-soft px-5 py-5">
                <div class="flex items-center gap-3">
                  <span class="ui-user-workspace-icon">
                    <ShieldCheckIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t('pages.user.identity.mergedActions') }}</div>
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
                    {{ t('pages.user.identity.noActions') }}
                  </span>
                </div>
              </div>

              <div class="ui-panel-soft px-5 py-5">
                <div class="flex items-center gap-3">
                  <span class="ui-user-workspace-icon">
                    <ShieldCheckIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t('pages.user.identity.mergedRules') }}</div>
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
                    {{ t('pages.user.identity.noRules') }}
                  </span>
                </div>
              </div>
            </div>
          </section>
        </div>

        <template v-for="section in orderedSections" :key="section">
          <section v-if="section === 'profile'" class="ui-panel ui-section">
            <div class="mb-5">
              <p class="ui-page-kicker">{{ t('pages.user.profile.kicker') }}</p>
              <h2 class="ui-panel-title">{{ t('pages.user.profile.title') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('pages.user.profile.description') }}
              </p>
            </div>

            <PanelSkeleton v-if="initialLoading && !unable" :rows="8" />

            <ErrorAlert v-else-if="unable">
              {{ t('pages.account.errors.unableToRetrieve', { cluster }) }}
            </ErrorAlert>
            <div v-else class="ui-section-stack">
              <div v-if="canViewHistoryJobs" class="grid gap-3 sm:grid-cols-2">
                <div class="ui-panel-soft px-4 py-3">
                  <div class="ui-stat-label">{{ t('pages.user.profile.historyJobs') }}</div>
                  <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ t('pages.user.profile.historyAccessGranted') }}
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    {{ t('pages.user.profile.historyShortcut') }}
                  </div>
                </div>
                <div class="ui-panel-soft px-4 py-3">
                  <div class="ui-stat-label">{{ t('pages.user.profile.accounts') }}</div>
                  <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ associatedAccounts.size }}
                  </div>
                  <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
                    {{
                      associatedAccounts.size === 1
                        ? t('pages.user.profile.accountAssociationsFound')
                        : t('pages.user.profile.accountAssociationsFoundPlural', { count: associatedAccounts.size })
                    }}
                  </div>
                </div>
              </div>

              <InfoAlert v-if="loaded && !knownUser">
                {{ t('pages.user.profile.noAssociations', { user: viewedUser }) }}
              </InfoAlert>

              <div v-else-if="loaded" class="ui-table-shell overflow-x-auto">
                <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
                  <h3 class="ui-panel-title">{{ t('pages.user.profile.accountAssociationsTitle') }}</h3>
                  <p class="ui-panel-description mt-2">
                    {{ t('pages.user.profile.accountAssociationsDescription') }}
                  </p>
                </div>

                <div class="inline-block min-w-full align-middle">
                  <table class="ui-table min-w-full">
                    <thead>
                      <tr>
                        <th scope="col" class="py-3.5 pr-3 pl-6 text-left lg:min-w-[220px]">{{ t('tables.userAssociations.columns.account') }}</th>
                        <th scope="col" class="hidden w-72 px-3 py-3.5 text-left sm:table-cell">{{ t('tables.userAssociations.columns.jobLimits') }}</th>
                        <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">{{ t('tables.userAssociations.columns.resourceLimits') }}</th>
                        <th scope="col" class="hidden w-72 px-3 py-3.5 text-left md:table-cell">{{ t('tables.userAssociations.columns.timeLimits') }}</th>
                        <th scope="col" class="hidden w-48 px-3 py-3.5 text-left 2xl:table-cell">{{ t('tables.userAssociations.columns.qos') }}</th>
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
                                {{ t(limit.label) }}:
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
                                {{ t(limit.label) }}:
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
                                {{ t(limit.label) }}:
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
            <h2 class="ui-panel-title">{{ t('pages.user.emptyState.title') }}</h2>
            <p class="ui-panel-description mt-2">
              {{ t('pages.user.emptyState.description') }}
            </p>
          </div>
        </section>
        </div>
      </div>
    </div>

    <ActionDialog
      :open="editOpen"
      :title="knownUser ? 'pages.user.dialogs.edit.title' : 'pages.user.dialogs.create.title'"
      :title-params="viewedUser ? { user: viewedUser } : undefined"
      :description="viewedUser ? (knownUser ? 'pages.user.dialogs.edit.description' : 'pages.user.dialogs.create.description') : ''"
      :description-params="viewedUser ? { user: viewedUser } : undefined"
      :submit-label="knownUser ? 'pages.user.dialogs.edit.submit' : 'pages.user.dialogs.create.submit'"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        default_account: userAssociations[0]?.account ?? '',
        default_qos: userAssociations.find((association) => association.default?.qos)?.default?.qos ?? '',
        qos: stringifyList([...new Set(userAssociations.flatMap((association) => association.qos ?? []))])
      }"
      :fields="[
        { key: 'description', label: 'pages.user.dialogs.fields.description', type: 'textarea' },
        { key: 'default_account', label: 'pages.user.dialogs.fields.defaultAccount' },
        {
          key: 'default_qos',
          label: 'pages.user.dialogs.fields.defaultQos',
          type: 'search-select',
          source: qosSearchSource
        },
        {
          key: 'qos',
          label: 'pages.user.dialogs.fields.assignedQosCsv',
          type: 'search-multi-select',
          source: qosSearchSource
        },
        { key: 'default_wckey', label: 'pages.user.dialogs.fields.defaultWckey' },
        { key: 'admin_level', label: 'pages.user.dialogs.fields.adminLevel' }
      ]"
      @close="editOpen = false"
      @submit="saveUser"
    />

    <ActionDialog
      :open="deleteOpen"
      title="pages.user.dialogs.delete.title"
      :title-params="viewedUser ? { user: viewedUser } : undefined"
      :description="viewedUser ? 'pages.user.dialogs.delete.description' : ''"
      :description-params="viewedUser ? { user: viewedUser } : undefined"
      submit-label="pages.user.dialogs.delete.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[]"
      @close="deleteOpen = false"
      @submit="removeUser"
    />
  </ClusterMainLayout>
</template>
