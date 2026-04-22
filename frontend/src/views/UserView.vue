<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PageHeader from '@/components/PageHeader.vue'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import {
  renderClusterOptionalNumber,
  renderClusterTRES,
  renderQosLabel,
  renderWalltime
} from '@/composables/GatewayAPI'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'

const { cluster, user } = defineProps<{
  cluster: string
  user: string
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

      <ErrorAlert v-if="unable">
        Unable to retrieve associations for cluster
        <span class="font-medium">{{ cluster }}</span>
      </ErrorAlert>
      <div v-else-if="!loaded" class="text-[var(--color-brand-muted)]">
        <LoadingSpinner :size="5" />
        Loading user details...
      </div>
      <InfoAlert v-else-if="!knownUser">
        User <span class="font-semibold">{{ user }}</span> has no associations on this cluster.
      </InfoAlert>
      <div v-else class="space-y-6">
        <div id="user-heading">
          <span class="sr-only">User {{ user }}</span>
          <PageHeader
            kicker="User Detail"
            :title="user"
            description="Every account association, quota boundary and scheduling policy that applies to this user."
            :metric-value="associatedAccounts.size"
            :metric-label="`account${associatedAccounts.size === 1 ? '' : 's'} associated`"
          >
            <template #actions>
              <RouterLink
                :to="{ name: 'jobs', params: { cluster }, query: { users: user } }"
                class="ui-button-primary"
              >
                View jobs
              </RouterLink>
            </template>
          </PageHeader>
        </div>

        <div class="ui-table-shell overflow-x-auto">
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
                      <div v-for="limit in jobLimits(association)" :key="limit.id" class="flex flex-wrap items-center gap-2">
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
                        <dd>{{ renderClusterOptionalNumber(limit.value) }}</dd>
                      </div>
                    </dl>
                  </td>
                  <td class="hidden px-3 py-4 align-top lg:table-cell">
                    <div v-if="resourceLimits(association).length === 0">-</div>
                    <dl v-else class="space-y-2">
                      <div v-for="limit in resourceLimits(association)" :key="limit.id" class="flex flex-wrap items-center gap-2">
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
                        <dd class="font-mono text-xs">{{ renderClusterTRES(limit.value) }}</dd>
                      </div>
                    </dl>
                  </td>
                  <td class="hidden px-3 py-4 align-top md:table-cell">
                    <div v-if="timeLimits(association).length === 0">-</div>
                    <dl v-else class="space-y-2">
                      <div v-for="limit in timeLimits(association)" :key="limit.id" class="flex flex-wrap items-center gap-2">
                        <dt class="font-semibold text-[var(--color-brand-ink-strong)]">{{ limit.label }}:</dt>
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
  </ClusterMainLayout>
</template>
