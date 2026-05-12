<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()
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
      { title: 'shell.mainMenu.accounts', routeName: 'accounts' },
      { title: t('pages.user.breadcrumb.userPrefix', { user }), routeName: 'user' },
      { title: 'shell.mainMenu.analysis' }
    ]"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <button
        @click="router.push({ name: 'user', params: { cluster, user } })"
        type="button"
        class="ui-button-secondary self-start shrink-0"
      >
        <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
        {{ t('pages.user.analytics.backToUser') }}
      </button>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
          <PageHeader
            kicker="pages.user.analytics.kicker"
            :title="user"
            description="pages.user.analytics.description"
          >
            <template #actions>
              <div class="flex flex-wrap gap-3">
                <RouterLink
                  :to="{ name: 'user', params: { cluster, user } }"
                  class="ui-button-secondary"
                >
                  {{ t('pages.user.analytics.userDetail') }}
                </RouterLink>
                <RouterLink
                  :to="{ name: 'jobs', params: { cluster }, query: { users: user } }"
                  class="ui-button-primary"
                >
                  {{ t('pages.user.actions.viewJobs') }}
                </RouterLink>
              </div>
            </template>
          </PageHeader>

          <UserAnalyticsPanels :cluster="cluster" :user="user" :enabled="userMetricsEnabled" />
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
