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
import PageHeader from '@/components/PageHeader.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import {
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster, user } = defineProps<{
  cluster: string
  user: string
}>()

const router = useRouter()
const runtimeStore = useRuntimeStore()
const { data, unable, loaded, initialLoading, setCluster } = useClusterDataPoller<
  ClusterAssociation[]
>(cluster, 'associations', 120000)

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

const userAssociations = computed(() => {
  if (!data.value) return []
  return data.value
    .filter((association) => association.user === user)
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

const clusterDetails = computed(() =>
  runtimeStore.availableClusters.find((value) => value.name === cluster)
)

const userMetricsEnabled = computed(() => Boolean(clusterDetails.value?.user_metrics))
const canViewHistoryJobs = computed(() =>
  runtimeStore.hasClusterPermission(cluster, 'view-history-jobs')
)

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
</script>

<template>
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Accounts', routeName: 'accounts' }, { title: `User ${user}` }]"
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

      <div class="ui-section-stack">
        <div id="user-heading">
          <span class="sr-only">User {{ user }}</span>
          <PageHeader
            kicker="User Detail"
            :title="user"
            description="LDAP-linked account associations, quota boundaries and shortcuts to this user's job and analytics views."
            :metric-value="loaded ? associatedAccounts.size : undefined"
            :metric-label="`account${associatedAccounts.size === 1 ? '' : 's'} associated`"
          >
            <template #actions>
              <div class="flex flex-wrap gap-3">
                <RouterLink
                  :to="{ name: 'jobs', params: { cluster }, query: { users: user } }"
                  class="ui-button-primary"
                >
                  View jobs
                </RouterLink>
                <RouterLink
                  v-if="userMetricsEnabled"
                  :to="{ name: 'user-analysis', params: { cluster, user } }"
                  class="ui-button-secondary"
                >
                  View analysis
                </RouterLink>
                <RouterLink
                  v-if="canViewHistoryJobs"
                  :to="{ name: 'jobs-history', params: { cluster }, query: { user } }"
                  class="ui-button-secondary"
                >
                  View history jobs
                </RouterLink>
              </div>
            </template>
          </PageHeader>
        </div>

        <div v-if="userMetricsEnabled || canViewHistoryJobs" class="grid gap-3 sm:grid-cols-2">
          <div v-if="userMetricsEnabled" class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">User Analytics</div>
            <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
              Analysis enabled
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Open submission trends, tool analysis and daily runtime summaries.
            </div>
          </div>
          <div v-if="canViewHistoryJobs" class="ui-panel-soft px-4 py-3">
            <div class="ui-stat-label">History Jobs</div>
            <div class="mt-2 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
              History access granted
            </div>
            <div class="mt-1.5 text-sm text-[var(--color-brand-muted)]">
              Jump directly into persisted jobs history filtered on this user.
            </div>
          </div>
        </div>

        <PanelSkeleton v-if="initialLoading && !unable" :rows="8" />

        <ErrorAlert v-if="unable">
          Unable to retrieve associations for cluster
          <span class="font-medium">{{ cluster }}</span>
        </ErrorAlert>
        <div v-else-if="loaded" class="ui-section-stack">
          <InfoAlert v-if="!knownUser">
            User <span class="font-semibold">{{ user }}</span> has no associations on this cluster.
          </InfoAlert>

          <div v-if="knownUser" class="ui-table-shell overflow-x-auto">
            <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
              <h2 class="ui-panel-title">Account Associations</h2>
              <p class="ui-panel-description mt-2">
                Each row represents one account binding and the limits attached to it.
              </p>
            </div>

            <div class="inline-block min-w-full align-middle">
              <table class="ui-table min-w-full">
                <thead>
                  <tr>
                    <th scope="col" class="py-3.5 pr-3 pl-6 text-left lg:min-w-[220px]">Account</th>
                    <th scope="col" class="hidden w-72 px-3 py-3.5 text-left sm:table-cell">
                      Job limits
                    </th>
                    <th scope="col" class="hidden w-72 px-3 py-3.5 text-left lg:table-cell">
                      Resource limits
                    </th>
                    <th scope="col" class="hidden w-72 px-3 py-3.5 text-left md:table-cell">
                      Time limits
                    </th>
                    <th scope="col" class="hidden w-48 px-3 py-3.5 text-left 2xl:table-cell">
                      QOS
                    </th>
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
      </div>
    </div>
  </ClusterMainLayout>
</template>
