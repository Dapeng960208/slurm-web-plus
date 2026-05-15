<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { AccountDescription, ClusterAssociation } from '@/composables/GatewayAPI'
import DetailSkeletonList from '@/components/DetailSkeletonList.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import StatCardSkeleton from '@/components/StatCardSkeleton.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import {
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'
import { parseCsvList, parseOptionalCsvList, stringifyList } from '@/composables/management'
import { useRuntimeStore } from '@/stores/runtime'
import { createStaticSearchSource, createUserSearchSource } from '@/composables/searchSelect'

const { cluster, account } = defineProps<{
  cluster: string
  account: string
}>()

const router = useRouter()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const { t } = useI18n()
const editOpen = ref(false)
const deleteOpen = ref(false)
const addUserOpen = ref(false)
const editUserQosOpen = ref(false)
const deleteAssociationOpen = ref(false)
const operationBusy = ref(false)
const operationError = ref<string | null>(null)
const accountDetails = ref<AccountDescription | null>(null)
const selectedAssociation = ref<ClusterAssociation | null>(null)
const userSearchSource = createUserSearchSource(cluster)
const qosSearchSource = createStaticSearchSource(async () =>
  (await gateway.qos(cluster)).map((qos) => ({
    value: qos.name,
    label: qos.name,
    description: qos.description || qos.name
  }))
)
const {
  data,
  unable,
  loaded,
  initialLoading,
  refresh: refreshAssociations,
  setCluster
} = useClusterDataPoller<ClusterAssociation[]>(cluster, 'associations', 120000)

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

async function loadAccountDetails() {
  try {
    accountDetails.value = await gateway.account(cluster, account)
  } catch {
    accountDetails.value = null
  }
}

onMounted(loadAccountDetails)

watch(
  () => [cluster, account] as const,
  () => {
    loadAccountDetails()
  }
)

function emptyOptionalNumber() {
  return { set: false, infinite: false, number: 0 }
}

function emptyAssociationMax(): ClusterAssociation['max'] {
  return {
    jobs: {
      accruing: emptyOptionalNumber(),
      active: emptyOptionalNumber(),
      per: {
        accruing: emptyOptionalNumber(),
        count: emptyOptionalNumber(),
        submitted: emptyOptionalNumber(),
        wall_clock: emptyOptionalNumber()
      },
      total: emptyOptionalNumber()
    },
    per: {
      account: {
        wall_clock: emptyOptionalNumber()
      }
    },
    tres: {
      group: { active: [], minutes: [] },
      minutes: { per: { job: [] }, total: [] },
      per: { job: [], node: [] },
      total: []
    }
  }
}

function accountDetailsAssociation(details: AccountDescription): ClusterAssociation {
  return {
    account: details.name,
    max: emptyAssociationMax(),
    parent_account: details.parent_account ?? '',
    qos: details.qos ?? [],
    user: ''
  }
}

const accountAssociation = computed<ClusterAssociation | undefined>(() => {
  const association = (data.value ?? []).find(
    (item) => item.account === account && !item.user
  )
  if (association) return association
  if (accountDetails.value?.name === account) {
    return accountDetailsAssociation(accountDetails.value)
  }
  return undefined
})

const breadcrumbAssociations = computed<ClusterAssociation[]>(() => {
  const associations = data.value ?? []
  if (
    !accountAssociation.value ||
    associations.some((association) => association.account === account && !association.user)
  ) {
    return associations
  }
  return [...associations, accountAssociation.value]
})

const subaccounts = computed(() => {
  if (!data.value) return []
  const subaccountsList: string[] = []
  const seen = new Set<string>()

  for (const association of data.value) {
    if (!association.user && association.parent_account === account && !seen.has(association.account)) {
      subaccountsList.push(association.account)
      seen.add(association.account)
    }
  }

  return subaccountsList.sort()
})

const userAssociations = computed(() => {
  if (!data.value) return []
  return data.value
    .filter((association) => association.account === account && association.user)
    .sort((a, b) => (a.user ?? '').localeCompare(b.user ?? ''))
})

const accountKnown = computed(() => {
  return Boolean(accountDetails.value?.name)
})

const jobLimits = computed(() => {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    { id: 'GrpJobs', label: 'pages.account.limits.running', value: currentAccount.max.jobs.per.count },
    { id: 'GrpSubmit', label: 'pages.account.limits.submitted', value: currentAccount.max.jobs.per.submitted },
    { id: 'MaxJobs', label: 'pages.account.limits.runningPerUser', value: currentAccount.max.jobs.active },
    { id: 'MaxSubmit', label: 'pages.account.limits.submittedPerUser', value: currentAccount.max.jobs.total }
  ]
})

const resourceLimits = computed(() => {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    { id: 'GrpTRES', label: 'pages.account.limits.total', value: currentAccount.max.tres.total },
    { id: 'MaxTRES', label: 'pages.account.limits.perJob', value: currentAccount.max.tres.per.job },
    { id: 'MaxTRESPerNode', label: 'pages.account.limits.perNode', value: currentAccount.max.tres.per.node }
  ]
})

const timeLimits = computed(() => {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    { id: 'GrpWall', label: 'pages.account.limits.total', value: currentAccount.max.per.account.wall_clock },
    { id: 'MaxWall', label: 'pages.account.limits.perJob', value: currentAccount.max.jobs.per.wall_clock }
  ]
})

const canEditAccount = computed(() => runtimeStore.hasRoutePermission(cluster, 'accounts', 'edit'))
const canDeleteAccount = computed(() =>
  runtimeStore.hasRoutePermission(cluster, 'accounts', 'delete')
)

function associationPayload(association: {
  account: string
  user?: string
  qos?: string[]
  default_qos?: string
}) {
  const item: {
    account: string
    user?: string
    qos?: string[]
    default?: { qos: string }
  } = {
    account: association.account
  }
  if (association.user) item.user = association.user
  if (association.qos !== undefined) item.qos = association.qos
  if (association.default_qos) item.default = { qos: association.default_qos }
  return {
    associations: [item]
  }
}

function hasOperationErrors(result: { errors?: unknown[] } | null | undefined): boolean {
  return Array.isArray(result?.errors) && result.errors.length > 0
}

async function saveAccount(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.save_account(cluster, {
      name: account,
      description: payload.description || null,
      organization: payload.organization || undefined,
      parent_account: payload.parent_account || undefined,
      qos: parseCsvList(payload.qos)
    })
    await refreshAssociations()
    runtimeStore.reportInfo(t('pages.account.notifications.updateRequested', { account }))
    await loadAccountDetails()
    editOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function addUserAssociation(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    const saveUserResult = await gateway.save_user(cluster, {
      name: payload.user,
      default_account: account,
      default_qos: payload.default_qos || null,
      qos: parseOptionalCsvList(payload.qos)
    })
    if (hasOperationErrors(saveUserResult)) {
      throw new Error(t('pages.account.errors.addUserFailed'))
    }

    const saveAssociationResult = await gateway.save_association(
      cluster,
      associationPayload({
        account,
        user: payload.user,
        qos: parseOptionalCsvList(payload.qos),
        default_qos: payload.default_qos
      })
    )
    if (hasOperationErrors(saveAssociationResult)) {
      throw new Error(t('pages.account.errors.addUserFailed'))
    }
    await refreshAssociations()
    const associationVisible = (data.value ?? []).some(
      (association) => association.account === account && association.user === payload.user
    )
    if (!associationVisible) {
      throw new Error(
        t('pages.account.errors.addUserAssociationMissing', {
          user: payload.user,
          account
        })
      )
    }
    runtimeStore.reportInfo(
      t('pages.account.notifications.addUserRequested', { user: payload.user, account })
    )
    addUserOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function saveUserAssociationQos(payload: Record<string, string>) {
  if (!selectedAssociation.value?.user) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.save_association(
      cluster,
      associationPayload({
        account,
        user: selectedAssociation.value.user,
        qos: parseOptionalCsvList(payload.qos),
        default_qos: payload.default_qos
      })
    )
    await refreshAssociations()
    runtimeStore.reportInfo(
      t('pages.account.notifications.updateQosRequested', {
        user: selectedAssociation.value.user,
        account
      })
    )
    editUserQosOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function removeUserAssociation() {
  if (!selectedAssociation.value?.user) return
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.delete_association(
      cluster,
      associationPayload({
        account,
        user: selectedAssociation.value.user
      })
    )
    await refreshAssociations()
    runtimeStore.reportInfo(
      t('pages.account.notifications.removeUserRequested', {
        user: selectedAssociation.value.user,
        account
      })
    )
    deleteAssociationOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function removeAccount() {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.delete_account(cluster, account)
    runtimeStore.reportInfo(t('pages.account.notifications.deleteRequested', { account }))
    deleteOpen.value = false
    router.push({ name: 'accounts', params: { cluster } })
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

function openEditAssociationDialog(association: ClusterAssociation) {
  selectedAssociation.value = association
  operationError.value = null
  editUserQosOpen.value = true
}

function openDeleteAssociationDialog(association: ClusterAssociation) {
  selectedAssociation.value = association
  operationError.value = null
  deleteAssociationOpen.value = true
}

function userJobLimits(association: ClusterAssociation) {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    {
      id: 'MaxJobs',
      label: 'pages.account.limits.runningPerUser',
      value: association.max.jobs.active,
      different: !compareOptionalNumber(association.max.jobs.active, currentAccount.max.jobs.active)
    },
    {
      id: 'MaxSubmit',
      label: 'pages.account.limits.submittedPerUser',
      value: association.max.jobs.total,
      different: !compareOptionalNumber(association.max.jobs.total, currentAccount.max.jobs.total)
    }
  ]
}

function userResourceLimits(association: ClusterAssociation) {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    {
      id: 'GrpTRES',
      label: 'pages.account.limits.total',
      value: association.max.tres.total,
      different: !compareTRES(association.max.tres.total, currentAccount.max.tres.total, true)
    },
    {
      id: 'MaxTRES',
      label: 'pages.account.limits.perJob',
      value: association.max.tres.per.job,
      different: !compareTRES(association.max.tres.per.job, currentAccount.max.tres.per.job)
    },
    {
      id: 'MaxTRESPerNode',
      label: 'pages.account.limits.perNode',
      value: association.max.tres.per.node,
      different: !compareTRES(association.max.tres.per.node, currentAccount.max.tres.per.node)
    }
  ]
}

function userTimeLimits(association: ClusterAssociation) {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    {
      id: 'GrpWall',
      label: 'pages.account.limits.total',
      value: association.max.per.account.wall_clock,
      different: !compareOptionalNumber(
        association.max.per.account.wall_clock,
        currentAccount.max.per.account.wall_clock,
        true
      )
    },
    {
      id: 'MaxWall',
      label: 'pages.account.limits.perJob',
      value: association.max.jobs.per.wall_clock,
      different: !compareOptionalNumber(
        association.max.jobs.per.wall_clock,
        currentAccount.max.jobs.per.wall_clock
      )
    }
  ]
}

function compareOptionalNumber(
  a: ClusterAssociation['max']['jobs']['total'],
  b: ClusterAssociation['max']['jobs']['total'],
  acceptUnset = false
): boolean {
  if (a.set !== b.set) return acceptUnset
  if (!a.set && !b.set) return true
  if (a.infinite !== b.infinite) return false
  if (a.infinite && b.infinite) return true
  return a.number === b.number
}

function compareTRES(
  a: ClusterAssociation['max']['tres']['total'],
  b: ClusterAssociation['max']['tres']['total'],
  acceptAZero = false
): boolean {
  if (a.length === 0 && b.length !== 0) return acceptAZero
  if (a.length !== b.length) return false
  const aMap = new Map<string, number>()
  const bMap = new Map<string, number>()
  for (const tres of a) aMap.set(tres.type, tres.count)
  for (const tres of b) bMap.set(tres.type, tres.count)
  if (aMap.size !== bMap.size) return false
  for (const [key, value] of aMap) {
    if (bMap.get(key) !== value) return false
  }
  return true
}

function hasDifferentQos(userAssociation: ClusterAssociation): boolean {
  if (!accountAssociation.value) return true

  const accountQos = new Set(accountAssociation.value.qos || [])
  const userQos = new Set(userAssociation.qos || [])

  if (accountQos.size !== userQos.size) return true
  for (const qos of accountQos) {
    if (!userQos.has(qos)) return true
  }
  return false
}
</script>

<template>
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="[{ title: 'shell.mainMenu.accounts', routeName: 'accounts' }, { title: `${account}` }]"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <button
        @click="router.push({ name: 'accounts', params: { cluster } })"
        type="button"
        class="ui-button-secondary self-start shrink-0"
      >
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        {{ t('pages.account.back') }}
      </button>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
          <div id="account-heading">
            <PageHeader
              kicker="pages.account.kicker"
              :title="account"
              description="pages.account.description"
              :metric-value="loaded && accountAssociation ? userAssociations.length : undefined"
              :metric-label="
                userAssociations.length === 1
                  ? 'pages.account.metricLabel'
                  : 'pages.account.metricLabelPlural'
              "
            >
              <template #actions>
                <div class="flex flex-wrap gap-3">
                  <RouterLink
                    :to="{ name: 'jobs', params: { cluster }, query: { accounts: account } }"
                    class="ui-button-primary"
                  >
                    {{ t('pages.account.actions.viewJobs') }}
                  </RouterLink>
                  <button
                    v-if="canEditAccount"
                    type="button"
                    class="ui-button-warning"
                    @click="editOpen = true"
                  >
                    {{ t('pages.account.actions.edit') }}
                  </button>
                  <button
                    v-if="canDeleteAccount"
                    type="button"
                    class="ui-button-danger"
                    @click="deleteOpen = true"
                  >
                    {{ t('pages.account.actions.delete') }}
                  </button>
                </div>
              </template>
            </PageHeader>
          </div>

        <template v-if="initialLoading && !unable">
          <StatCardSkeleton :cards="4" />
          <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div class="ui-panel ui-section">
              <div class="mb-5">
                <h2 class="ui-panel-title">{{ t('pages.account.overviewTitle') }}</h2>
                <p class="ui-panel-description mt-2">
                  {{ t('pages.account.overviewDescription') }}
                </p>
              </div>
              <DetailSkeletonList :rows="6" />
            </div>
            <PanelSkeleton :rows="8" />
          </div>
        </template>

      <ErrorAlert v-if="unable">
        {{ t('pages.account.errors.unableToRetrieve', { cluster }) }}
      </ErrorAlert>
      <InfoAlert v-else-if="loaded && !accountKnown">
        {{ t('pages.account.noAccount', { account }) }}
      </InfoAlert>
      <div v-else-if="accountKnown" class="ui-section-stack">
        <div class="ui-stat-grid">
          <div class="ui-stat-card">
            <div class="ui-stat-label">{{ t('pages.account.stats.parentChain') }}</div>
            <div class="ui-stat-value">{{ subaccounts.length }}</div>
            <div class="ui-stat-subtle">{{ t('pages.account.stats.directSubaccounts') }}</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">{{ t('pages.account.stats.qosScope') }}</div>
            <div class="mt-3 text-lg font-bold text-[var(--color-brand-ink-strong)]">
              {{ renderQosLabel(accountAssociation?.qos ?? []) }}
            </div>
            <div class="ui-stat-subtle">{{ t('pages.account.stats.appliedAtAccountLevel') }}</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">{{ t('pages.account.stats.jobLimits') }}</div>
            <div class="ui-stat-value">{{ jobLimits.length }}</div>
            <div class="ui-stat-subtle">{{ t('pages.account.stats.configuredLimitEntries') }}</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">{{ t('pages.account.stats.timeLimits') }}</div>
            <div class="ui-stat-value">{{ timeLimits.length }}</div>
            <div class="ui-stat-subtle">{{ t('pages.account.stats.walltimePolicies') }}</div>
          </div>
        </div>

        <div class="ui-panel ui-section">
          <div class="mb-5">
            <h2 class="ui-panel-title">{{ t('pages.account.overviewTitle') }}</h2>
            <p class="ui-panel-description mt-2">
              {{ t('pages.account.overviewDescription') }}
            </p>
          </div>

          <div class="ui-detail-list">
            <dl>
              <div id="parents" class="ui-detail-row">
                <dt class="ui-detail-term">{{ t('pages.account.detail.parentAccounts') }}</dt>
                <dd class="ui-detail-value">
                  <AccountBreadcrumb :cluster="cluster" :account="account" :associations="breadcrumbAssociations" />
                </dd>
              </div>

              <div id="subaccounts" class="ui-detail-row">
                <dt class="ui-detail-term">{{ t('pages.account.detail.subaccounts') }}</dt>
                <dd class="ui-detail-value">
                  <div v-if="subaccounts.length === 0">∅</div>
                  <div v-else class="flex flex-wrap gap-2">
                    <RouterLink
                      v-for="subaccount in subaccounts"
                      :key="subaccount"
                      :to="{ name: 'account', params: { cluster, account: subaccount } }"
                      class="ui-chip"
                    >
                      {{ subaccount }}
                    </RouterLink>
                  </div>
                </dd>
              </div>

              <div id="qos" class="ui-detail-row">
                <dt class="ui-detail-term">{{ t('pages.account.detail.qos') }}</dt>
                <dd class="ui-detail-value">{{ renderQosLabel(accountAssociation?.qos ?? []) }}</dd>
              </div>

              <div id="limits-jobs" class="ui-detail-row">
                <dt class="ui-detail-term">{{ t('pages.account.detail.jobLimits') }}</dt>
                <dd class="ui-detail-value">
                  <div v-if="jobLimits.length === 0">-</div>
                  <dl v-else class="space-y-2">
                    <div v-for="limit in jobLimits" :key="limit.id" class="flex flex-wrap items-center gap-2">
                      <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t(limit.label) }}:</dt>
                      <dd>{{ renderClusterOptionalNumber(limit.value) }}</dd>
                    </div>
                  </dl>
                </dd>
              </div>

              <div id="limits-resources" class="ui-detail-row">
                <dt class="ui-detail-term">{{ t('pages.account.detail.resourceLimits') }}</dt>
                <dd class="ui-detail-value">
                  <div v-if="resourceLimits.length === 0">-</div>
                  <dl v-else class="space-y-2">
                    <div v-for="limit in resourceLimits" :key="limit.id" class="flex flex-wrap items-center gap-2">
                      <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t(limit.label) }}:</dt>
                      <dd class="font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                    </div>
                  </dl>
                </dd>
              </div>

              <div id="limits-time" class="ui-detail-row">
                <dt class="ui-detail-term">{{ t('pages.account.detail.timeLimits') }}</dt>
                <dd class="ui-detail-value">
                  <div v-if="timeLimits.length === 0">-</div>
                  <dl v-else class="space-y-2">
                    <div v-for="limit in timeLimits" :key="limit.id" class="flex flex-wrap items-center gap-2">
                      <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t(limit.label) }}:</dt>
                      <dd>{{ renderWalltime(limit.value) }}</dd>
                    </div>
                  </dl>
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <InfoAlert v-if="userAssociations.length === 0">
          {{ t('pages.account.noAssociations', { account }) }}
        </InfoAlert>

        <div class="ui-table-shell overflow-x-auto">
          <div class="flex flex-wrap items-start justify-between gap-3 border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
            <div>
              <h2 class="ui-panel-title">{{ t('pages.account.userAssociationsTitle') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('pages.account.userAssociationsDescription') }}
              </p>
            </div>
            <button
              v-if="canEditAccount"
              type="button"
              class="ui-button-primary"
              @click="addUserOpen = true"
            >
              {{ t('pages.account.actions.addUser') }}
            </button>
          </div>

          <InfoAlert v-if="userAssociations.length === 0" class="m-6">
            {{ t('pages.account.noAssociationsYet', { account }) }}
          </InfoAlert>

          <div v-else class="inline-block min-w-full align-middle">
            <table class="ui-table min-w-full">
              <thead>
                <tr>
                  <th scope="col" class="py-3.5 pr-3 pl-6 text-left lg:min-w-[250px]">{{ t('tables.userAssociations.columns.user') }}</th>
                  <th scope="col" class="hidden w-72 px-3 py-3.5 text-left sm:table-cell">{{ t('tables.userAssociations.columns.jobLimits') }}</th>
                  <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">{{ t('tables.userAssociations.columns.resourceLimits') }}</th>
                  <th scope="col" class="hidden w-72 px-3 py-3.5 text-left md:table-cell">{{ t('tables.userAssociations.columns.timeLimits') }}</th>
                  <th scope="col" class="hidden w-48 px-3 py-3.5 text-left 2xl:table-cell">{{ t('tables.userAssociations.columns.qos') }}</th>
                  <th scope="col" class="py-3.5 pr-6 pl-3 text-right">{{ t('tables.userAssociations.columns.actions') }}</th>
                </tr>
              </thead>
              <tbody class="text-sm text-[var(--color-brand-muted)]">
                <tr
                  v-for="association in userAssociations"
                  :key="`${association.account}-${association.user}`"
                >
                  <td class="py-4 pr-3 pl-6 align-top font-semibold text-[var(--color-brand-ink-strong)]">
                    <RouterLink
                      v-if="association.user"
                      :to="{ name: 'user', params: { cluster, user: association.user } }"
                      class="ui-user-link"
                    >
                      {{ association.user }}
                    </RouterLink>
                  </td>
                  <td class="hidden px-3 py-4 align-top sm:table-cell">
                    <div v-if="userJobLimits(association).length === 0">-</div>
                    <dl v-else class="space-y-2">
                      <div
                        v-for="limit in userJobLimits(association)"
                        :key="limit.id"
                        :class="limit.different ? '' : 'opacity-40'"
                        class="flex flex-wrap items-center gap-2"
                      >
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t(limit.label) }}:</dt>
                        <dd>{{ renderClusterOptionalNumber(limit.value) }}</dd>
                      </div>
                    </dl>
                  </td>
                  <td class="hidden px-3 py-4 align-top lg:table-cell">
                    <div v-if="userResourceLimits(association).length === 0">-</div>
                    <dl v-else class="space-y-2">
                      <div
                        v-for="limit in userResourceLimits(association)"
                        :key="limit.id"
                        :class="limit.different ? '' : 'opacity-40'"
                        class="flex flex-wrap items-center gap-2"
                      >
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t(limit.label) }}:</dt>
                        <dd class="font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                      </div>
                    </dl>
                  </td>
                  <td class="hidden px-3 py-4 align-top md:table-cell">
                    <div v-if="userTimeLimits(association).length === 0">-</div>
                    <dl v-else class="space-y-2">
                      <div
                        v-for="limit in userTimeLimits(association)"
                        :key="limit.id"
                        :class="limit.different ? '' : 'opacity-40'"
                        class="flex flex-wrap items-center gap-2"
                      >
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ t(limit.label) }}:</dt>
                        <dd>{{ renderWalltime(limit.value) }}</dd>
                      </div>
                    </dl>
                  </td>
                  <td class="hidden px-3 py-4 align-top 2xl:table-cell">
                    <span :class="hasDifferentQos(association) ? '' : 'opacity-40'">
                      {{ renderQosLabel(association.qos) }}
                      <span v-if="association.default?.qos" class="block text-xs">
                        {{ t('pages.account.tables.defaultQos', { qos: association.default.qos }) }}
                      </span>
                    </span>
                  </td>
                  <td class="py-4 pr-6 pl-3 align-top text-right">
                    <div class="flex flex-wrap justify-end gap-2">
                      <button
                        v-if="canEditAccount"
                        type="button"
                        class="ui-button-warning"
                        @click="openEditAssociationDialog(association)"
                      >
                        {{ t('pages.account.actions.editQos') }}
                      </button>
                      <button
                        v-if="canDeleteAccount"
                        type="button"
                        class="ui-button-danger"
                        @click="openDeleteAssociationDialog(association)"
                      >
                        {{ t('pages.account.actions.delete') }}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
        </div>
      </div>
    </div>

    <ActionDialog
      :open="editOpen"
      title="pages.account.dialogs.edit.title"
      :description="'pages.account.dialogs.edit.description'"
      :description-params="{ account }"
      submit-label="pages.account.dialogs.edit.submit"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        description: accountDetails?.description ?? '',
        organization: accountDetails?.organization ?? '',
        parent_account: accountAssociation?.parent_account ?? '',
        qos: stringifyList(accountAssociation?.qos)
      }"
      :fields="[
        { key: 'description', label: 'pages.account.dialogs.fields.description', type: 'textarea' },
        { key: 'organization', label: 'pages.account.dialogs.fields.organization', required: true },
        { key: 'parent_account', label: 'pages.account.dialogs.fields.parentAccount' },
        {
          key: 'qos',
          label: 'pages.account.dialogs.fields.qosCsv',
          type: 'search-multi-select',
          source: qosSearchSource
        }
      ]"
      @close="editOpen = false"
      @submit="saveAccount"
    />

    <ActionDialog
      :open="addUserOpen"
      title="pages.account.dialogs.addUserAssociation.title"
      :description="'pages.account.dialogs.addUserAssociation.description'"
      :description-params="{ account }"
      submit-label="pages.account.dialogs.addUserAssociation.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        {
          key: 'user',
          label: 'pages.account.dialogs.fields.username',
          required: true,
          type: 'search-select',
          source: userSearchSource,
          minQueryLength: 1
        },
        {
          key: 'qos',
          label: 'pages.account.dialogs.fields.assignedQosCsv',
          type: 'search-multi-select',
          source: qosSearchSource
        },
        {
          key: 'default_qos',
          label: 'pages.account.dialogs.fields.defaultQos',
          type: 'search-select',
          source: qosSearchSource
        }
      ]"
      @close="addUserOpen = false"
      @submit="addUserAssociation"
    />

    <ActionDialog
      :open="editUserQosOpen"
      title="pages.account.dialogs.editUserQos.title"
      :description="selectedAssociation?.user ? 'pages.account.dialogs.editUserQos.description' : ''"
      :description-params="selectedAssociation?.user ? { user: selectedAssociation.user, account } : undefined"
      submit-label="pages.account.dialogs.editUserQos.submit"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        qos: stringifyList(selectedAssociation?.qos),
        default_qos: selectedAssociation?.default?.qos ?? ''
      }"
      :fields="[
        {
          key: 'qos',
          label: 'pages.account.dialogs.fields.assignedQosCsv',
          type: 'search-multi-select',
          source: qosSearchSource
        },
        {
          key: 'default_qos',
          label: 'pages.account.dialogs.fields.defaultQos',
          type: 'search-select',
          source: qosSearchSource
        }
      ]"
      @close="editUserQosOpen = false"
      @submit="saveUserAssociationQos"
    />

    <ActionDialog
      :open="deleteOpen"
      title="pages.account.dialogs.delete.title"
      :description="'pages.account.dialogs.delete.description'"
      :description-params="{ account }"
      submit-label="pages.account.dialogs.delete.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[]"
      @close="deleteOpen = false"
      @submit="removeAccount"
    />

    <ActionDialog
      :open="deleteAssociationOpen"
      title="pages.account.dialogs.deleteAssociation.title"
      :description="selectedAssociation?.user ? 'pages.account.dialogs.deleteAssociation.description' : ''"
      :description-params="selectedAssociation?.user ? { user: selectedAssociation.user, account } : undefined"
      submit-label="pages.account.dialogs.deleteAssociation.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[]"
      @close="deleteAssociationOpen = false"
      @submit="removeUserAssociation"
    />
  </ClusterMainLayout>
</template>
