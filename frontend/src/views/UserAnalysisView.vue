<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useRuntimeStore } from '@/stores/runtime'
import UserAnalyticsPanels from '@/components/user/UserAnalyticsPanels.vue'

const { cluster, user } = defineProps<{
  cluster: string
  user: string
}>()

const router = useRouter()
const runtimeStore = useRuntimeStore()
const clusterDetails = computed(() =>
  runtimeStore.availableClusters.find((value) => value.name === cluster)
)
const userMetricsEnabled = computed(
  () =>
    Boolean(clusterDetails.value?.user_metrics) &&
    runtimeStore.hasRoutePermission(cluster, 'user/analysis', 'view')
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="[
      { title: 'Accounts', routeName: 'accounts' },
      { title: `User ${user}`, routeName: 'user' },
      { title: 'Analysis' }
    ]"
  >
    <div class="ui-page ui-page-readable">
      <button
        @click="router.push({ name: 'user', params: { cluster, user } })"
        type="button"
        class="ui-button-secondary self-start"
      >
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        Back to user detail
      </button>

      <div class="ui-section-stack">
        <PageHeader
          kicker="User Analysis"
          :title="user"
          description="Submission trends, tool usage analysis and execution summaries for this user."
        >
          <template #actions>
            <div class="flex flex-wrap gap-3">
              <RouterLink
                :to="{ name: 'user', params: { cluster, user } }"
                class="ui-button-secondary"
              >
                User detail
              </RouterLink>
              <RouterLink
                :to="{ name: 'jobs', params: { cluster }, query: { users: user } }"
                class="ui-button-primary"
              >
                View jobs
              </RouterLink>
            </div>
          </template>
        </PageHeader>

        <UserAnalyticsPanels :cluster="cluster" :user="user" :enabled="userMetricsEnabled" />
      </div>
    </div>
  </ClusterMainLayout>
</template>
