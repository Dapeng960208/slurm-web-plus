<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PageHeader from '@/components/PageHeader.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import {
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'

const { cluster, account } = defineProps<{
  cluster: string
  account: string
}>()

const router = useRouter()
const { data, unable, loaded, setCluster } = useClusterDataPoller<ClusterAssociation[]>(
  cluster,
  'associations',
  120000
)

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

const accountAssociation = computed<ClusterAssociation | undefined>(() => {
  if (!data.value) return undefined
  return data.value.find((association) => association.account === account && !association.user)
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
  if (!data.value) return false
  return data.value.some((association) => association.account === account)
})

const jobLimits = computed(() => {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    { id: 'GrpJobs', label: 'Running', value: currentAccount.max.jobs.per.count },
    { id: 'GrpSubmit', label: 'Submitted', value: currentAccount.max.jobs.per.submitted },
    { id: 'MaxJobs', label: 'Running / user', value: currentAccount.max.jobs.active },
    { id: 'MaxSubmit', label: 'Submitted / user', value: currentAccount.max.jobs.total }
  ]
})

const resourceLimits = computed(() => {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    { id: 'GrpTRES', label: 'Total', value: currentAccount.max.tres.total },
    { id: 'MaxTRES', label: 'Per job', value: currentAccount.max.tres.per.job },
    { id: 'MaxTRESPerNode', label: 'Per node', value: currentAccount.max.tres.per.node }
  ]
})

const timeLimits = computed(() => {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    { id: 'GrpWall', label: 'Total', value: currentAccount.max.per.account.wall_clock },
    { id: 'MaxWall', label: 'Per job', value: currentAccount.max.jobs.per.wall_clock }
  ]
})

function userJobLimits(association: ClusterAssociation) {
  if (!accountAssociation.value) return []
  const currentAccount = accountAssociation.value
  return [
    {
      id: 'MaxJobs',
      label: 'Running / user',
      value: association.max.jobs.active,
      different: !compareOptionalNumber(association.max.jobs.active, currentAccount.max.jobs.active)
    },
    {
      id: 'MaxSubmit',
      label: 'Submitted / user',
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
      label: 'Total',
      value: association.max.tres.total,
      different: !compareTRES(association.max.tres.total, currentAccount.max.tres.total, true)
    },
    {
      id: 'MaxTRES',
      label: 'Per job',
      value: association.max.tres.per.job,
      different: !compareTRES(association.max.tres.per.job, currentAccount.max.tres.per.job)
    },
    {
      id: 'MaxTRESPerNode',
      label: 'Per node',
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
      label: 'Total',
      value: association.max.per.account.wall_clock,
      different: !compareOptionalNumber(
        association.max.per.account.wall_clock,
        currentAccount.max.per.account.wall_clock,
        true
      )
    },
    {
      id: 'MaxWall',
      label: 'Per job',
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
    :breadcrumb="[{ title: 'Accounts', routeName: 'accounts' }, { title: `${account}` }]"
  >
    <div class="ui-page ui-page-readable">
      <button
        @click="router.push({ name: 'accounts', params: { cluster } })"
        type="button"
        class="ui-button-secondary self-start"
      >
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        Back to accounts
      </button>

      <ErrorAlert v-if="unable">
        Unable to retrieve associations for cluster
        <span class="font-medium">{{ cluster }}</span>
      </ErrorAlert>
      <div v-else-if="!loaded" class="text-[var(--color-brand-muted)]">
        <LoadingSpinner :size="5" />
        Loading account details...
      </div>
      <InfoAlert v-else-if="!accountKnown">
        Account <span class="font-semibold">{{ account }}</span> does not exist on this cluster.
      </InfoAlert>
      <div v-else-if="accountAssociation" class="space-y-6">
        <div id="account-heading">
          <span class="sr-only">Account {{ account }}</span>
          <PageHeader
            kicker="Account Detail"
            :title="account"
            description="Hierarchy, inherited policy and per-user overrides for the selected Slurm account."
            :metric-value="userAssociations.length"
            :metric-label="`user association${userAssociations.length === 1 ? '' : 's'}`"
          >
            <template #actions>
              <RouterLink
                :to="{ name: 'jobs', params: { cluster }, query: { accounts: account } }"
                class="ui-button-primary"
              >
                View jobs
              </RouterLink>
            </template>
          </PageHeader>
        </div>

        <div class="ui-stat-grid">
          <div class="ui-stat-card">
            <div class="ui-stat-label">Parent Chain</div>
            <div class="ui-stat-value">{{ subaccounts.length }}</div>
            <div class="ui-stat-subtle">Direct subaccounts</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">QoS Scope</div>
            <div class="mt-3 text-lg font-bold text-[var(--color-brand-ink-strong)]">
              {{ renderQosLabel(accountAssociation.qos) }}
            </div>
            <div class="ui-stat-subtle">Applied at account level</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">Job Limits</div>
            <div class="ui-stat-value">{{ jobLimits.length }}</div>
            <div class="ui-stat-subtle">Configured limit entries</div>
          </div>
          <div class="ui-stat-card">
            <div class="ui-stat-label">Time Limits</div>
            <div class="ui-stat-value">{{ timeLimits.length }}</div>
            <div class="ui-stat-subtle">Walltime policies</div>
          </div>
        </div>

        <div class="ui-panel ui-section">
          <div class="mb-5">
            <h2 class="ui-panel-title">Account Overview</h2>
            <p class="ui-panel-description mt-2">
              Parent hierarchy, scoped QoS and inherited account-wide limits.
            </p>
          </div>

          <div class="ui-detail-list">
            <dl>
              <div id="parents" class="ui-detail-row">
                <dt class="ui-detail-term">Parent accounts</dt>
                <dd class="ui-detail-value">
                  <AccountBreadcrumb :cluster="cluster" :account="account" :associations="data ?? []" />
                </dd>
              </div>

              <div id="subaccounts" class="ui-detail-row">
                <dt class="ui-detail-term">Subaccounts</dt>
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
                <dt class="ui-detail-term">QoS</dt>
                <dd class="ui-detail-value">{{ renderQosLabel(accountAssociation.qos) }}</dd>
              </div>

              <div id="limits-jobs" class="ui-detail-row">
                <dt class="ui-detail-term">Job limits</dt>
                <dd class="ui-detail-value">
                  <div v-if="jobLimits.length === 0">-</div>
                  <dl v-else class="space-y-2">
                    <div v-for="limit in jobLimits" :key="limit.id" class="flex flex-wrap items-center gap-2">
                      <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
                      <dd>{{ renderClusterOptionalNumber(limit.value) }}</dd>
                    </div>
                  </dl>
                </dd>
              </div>

              <div id="limits-resources" class="ui-detail-row">
                <dt class="ui-detail-term">Resource limits</dt>
                <dd class="ui-detail-value">
                  <div v-if="resourceLimits.length === 0">-</div>
                  <dl v-else class="space-y-2">
                    <div v-for="limit in resourceLimits" :key="limit.id" class="flex flex-wrap items-center gap-2">
                      <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
                      <dd class="font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                    </div>
                  </dl>
                </dd>
              </div>

              <div id="limits-time" class="ui-detail-row">
                <dt class="ui-detail-term">Time limits</dt>
                <dd class="ui-detail-value">
                  <div v-if="timeLimits.length === 0">-</div>
                  <dl v-else class="space-y-2">
                    <div v-for="limit in timeLimits" :key="limit.id" class="flex flex-wrap items-center gap-2">
                      <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
                      <dd>{{ renderWalltime(limit.value) }}</dd>
                    </div>
                  </dl>
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <InfoAlert v-if="userAssociations.length === 0">
          Account <span class="font-semibold">{{ account }}</span> has no end-user associations.
        </InfoAlert>

        <div v-else class="ui-table-shell overflow-x-auto">
          <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
            <h2 class="ui-panel-title">User Associations</h2>
            <p class="ui-panel-description mt-2">
              User associations attached to this account, with inherited values visually de-emphasized.
            </p>
          </div>

          <div class="inline-block min-w-full align-middle">
            <table class="ui-table min-w-full">
              <thead>
                <tr>
                  <th scope="col" class="py-3.5 pr-3 pl-6 text-left lg:min-w-[250px]">User</th>
                  <th scope="col" class="hidden w-72 px-3 py-3.5 text-left sm:table-cell">Job limits</th>
                  <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">Resource limits</th>
                  <th scope="col" class="hidden w-72 px-3 py-3.5 text-left md:table-cell">Time limits</th>
                  <th scope="col" class="hidden w-48 px-3 py-3.5 text-left 2xl:table-cell">QoS</th>
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
                      class="text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
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
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
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
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
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
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
                        <dd>{{ renderWalltime(limit.value) }}</dd>
                      </div>
                    </dl>
                  </td>
                  <td class="hidden px-3 py-4 align-top 2xl:table-cell">
                    <span :class="hasDifferentQos(association) ? '' : 'opacity-40'">
                      {{ renderQosLabel(association.qos) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
