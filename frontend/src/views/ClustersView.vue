<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useGatewayAPI, type ClusterDescription } from '@/composables/GatewayAPI'
import { AuthenticationError } from '@/composables/HTTPErrors'
import { useErrorsHandler } from '@/composables/ErrorsHandler'
import ClusterListItem from '@/components/clusters/ClustersListItem.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import BrandLogo from '@/components/BrandLogo.vue'
import PageHeader from '@/components/PageHeader.vue'
import { ArrowRightOnRectangleIcon } from '@heroicons/vue/24/outline'

const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()
const gateway = useGatewayAPI()
const { reportAuthenticationError, reportServerError } = useErrorsHandler()
const router = useRouter()

const clusters = ref<ClusterDescription[]>([])
const loaded = ref(false)
const unable = ref(false)
const awaitingAutoRedirect = ref(false)
const awaitingClusterName = ref<string | null>(null)

const clusterCount = computed(() => clusters.value?.length ?? 0)
const clusterWithError = computed(() => clusters.value.find((cluster) => cluster.error))

async function getClustersDescriptions() {
  try {
    const clusterList = await gateway.clusters()
    clusters.value = Array.isArray(clusterList) ? clusterList : []
    runtimeStore.availableClusters = []
    clusters.value.forEach((cluster) => {
      cluster.error = false
      runtimeStore.addCluster(cluster)
    })
    loaded.value = true

    const clustersWithPermissions = clusters.value.filter(
      (cluster) =>
        (cluster.permissions.actions?.length ?? 0) > 0 ||
        (cluster.permissions.rules?.length ?? 0) > 0
    )
    if (clustersWithPermissions.length === 1) {
      awaitingAutoRedirect.value = true
      awaitingClusterName.value = clustersWithPermissions[0].name
    }
  } catch (error) {
    if (error instanceof AuthenticationError) {
      reportAuthenticationError(error)
    } else if (error instanceof Error) {
      reportServerError(error)
      unable.value = true
    }
  }
}

function handleClusterPing(cluster: ClusterDescription) {
  if (!awaitingAutoRedirect.value || awaitingClusterName.value !== cluster.name) {
    return
  }

  if (cluster.error) {
    loaded.value = true
    return
  }

  router.push({ name: 'dashboard', params: { cluster: cluster.name } })
}

onMounted(() => {
  void getClustersDescriptions()
})
</script>

<template>
  <main class="ui-public-shell">
    <RouterLink
      v-if="runtimeConfiguration.authentication"
      :to="{ name: 'signout' }"
      custom
      v-slot="{ navigate }"
    >
      <button
        @click="navigate"
        role="link"
        class="absolute top-4 right-4 z-20 flex items-center gap-2 rounded-full border border-white/70 bg-white/80 px-4 py-2 text-sm font-semibold text-[var(--color-brand-ink)] shadow-[var(--shadow-soft)] backdrop-blur-lg transition hover:bg-white"
      >
        Signout
        <ArrowRightOnRectangleIcon class="h-6 w-6" />
      </button>
    </RouterLink>

    <section class="ui-public-grid">
      <aside class="ui-public-aside">
        <div class="space-y-6">
          <BrandLogo size="lg" />
          <div class="space-y-4">
            <p class="ui-page-kicker">Cluster Gateway</p>
            <h1 class="text-4xl font-bold text-white md:text-5xl">Select a cluster</h1>
            <p class="max-w-xl text-sm leading-7 text-white/72 md:text-base">
              Compare visible environments, inspect availability and jump straight into the shared
              operations console.
            </p>
          </div>
        </div>
        <div class="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <div class="rounded-[22px] border border-white/10 bg-white/6 p-4">
            <p class="text-xs font-semibold tracking-[0.14em] text-white/50 uppercase">Clusters</p>
            <p class="mt-2 text-3xl font-bold text-white">{{ clusterCount }}</p>
            <p class="mt-1 text-sm text-white/70">Visible to this session.</p>
          </div>
          <div class="rounded-[22px] border border-white/10 bg-white/6 p-4">
            <p class="text-xs font-semibold tracking-[0.14em] text-white/50 uppercase">Routing</p>
            <p class="mt-2 text-sm text-white/80">
              Permission-aware entry and single-cluster auto redirect.
            </p>
          </div>
          <div class="rounded-[22px] border border-white/10 bg-white/6 p-4">
            <p class="text-xs font-semibold tracking-[0.14em] text-white/50 uppercase">Signals</p>
            <p class="mt-2 text-sm text-white/80">
              Status, version and runtime context before you enter.
            </p>
          </div>
        </div>
      </aside>

      <div class="ui-public-panel px-5 py-6 sm:px-8">
        <PageHeader
          kicker="Cluster Entry"
          title="Select a cluster"
          description="Pick an available environment to open the control surface."
          :metric-value="clusterCount"
          metric-label="clusters visible"
        />

        <div v-if="unable" class="mt-6">
          <ErrorAlert :show-errors-link="false">
            <strong>Unable to load cluster list</strong>
            <br />
            Try to refresh…
          </ErrorAlert>
        </div>
        <div
          v-else-if="!loaded"
          class="ui-panel-soft mt-6 flex min-h-28 items-center justify-center gap-3 rounded-[24px] px-5 text-sm text-[var(--color-brand-muted)]"
        >
          <LoadingSpinner :size="5" />
          <span>Loading clusters…</span>
        </div>
        <div v-else-if="clusterCount === 0" class="mt-6">
          <InfoAlert>
            <strong>Empty cluster list</strong>
            <br />
            Try to refresh…
          </InfoAlert>
        </div>
        <div v-else v-show="!awaitingAutoRedirect || clusterWithError" class="mt-6">
          <h1 class="sr-only">Select a cluster</h1>
          <ul role="list" class="ui-table-shell divide-y divide-[rgba(80,105,127,0.08)]">
            <ClusterListItem
              v-for="clusterItem in clusters"
              :key="clusterItem.name"
              :cluster-name="clusterItem.name"
              @pinged="handleClusterPing"
            />
          </ul>
        </div>
      </div>
    </section>
  </main>
</template>
