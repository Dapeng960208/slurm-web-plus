<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import AdminTabs from '@/components/admin/AdminTabs.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const { cluster } = defineProps<{ cluster: string }>()

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

const loading = ref(false)
const error = ref<string | null>(null)
const licenses = ref<unknown>(null)
const shares = ref<unknown>(null)
const slurmdbDiag = ref<unknown>(null)
const slurmdbConfig = ref<unknown>(null)
const instances = ref<unknown>(null)
const tres = ref<unknown>(null)

const canEditSystem = computed(() => runtimeStore.hasRoutePermission(cluster, 'admin/system', 'edit'))

async function loadSystemPanels() {
  if (!runtimeStore.hasRoutePermission(cluster, 'admin/system', 'view')) return
  loading.value = true
  error.value = null
  try {
    const results = await Promise.allSettled([
      gateway.admin_licenses(cluster),
      gateway.admin_shares(cluster),
      gateway.admin_slurmdb_diag(cluster),
      gateway.admin_slurmdb_config(cluster),
      gateway.admin_slurmdb_instances(cluster),
      gateway.admin_slurmdb_tres(cluster)
    ])
    licenses.value = results[0].status === 'fulfilled' ? results[0].value : null
    shares.value = results[1].status === 'fulfilled' ? results[1].value : null
    slurmdbDiag.value = results[2].status === 'fulfilled' ? results[2].value : null
    slurmdbConfig.value = results[3].status === 'fulfilled' ? results[3].value : null
    instances.value = results[4].status === 'fulfilled' ? results[4].value : null
    tres.value = results[5].status === 'fulfilled' ? results[5].value : null
  } catch (caughtError: unknown) {
    error.value = caughtError instanceof Error ? caughtError.message : String(caughtError)
  } finally {
    loading.value = false
  }
}

async function reconfigureCluster() {
  if (!canEditSystem.value) return
  try {
    await gateway.admin_reconfigure(cluster)
    runtimeStore.reportInfo(`Cluster ${cluster} reconfigure requested.`)
  } catch (caughtError: unknown) {
    runtimeStore.reportError(
      caughtError instanceof Error ? caughtError.message : String(caughtError)
    )
  }
}

watch(
  () => cluster,
  () => {
    void loadSystemPanels()
  }
)

onMounted(async () => {
  await loadSystemPanels()
})
</script>

<template>
  <div class="ui-section-stack">
    <AdminTabs entry="System" :cluster="cluster" />
    <div class="ui-panel ui-section">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <AdminHeader
          title="System Control"
          description="System-wide cluster administration, diagnostics snapshots and database-backed control surfaces."
        />
        <div class="flex flex-wrap gap-2">
          <button type="button" class="ui-button-secondary" :disabled="loading" @click="loadSystemPanels">
            Refresh
          </button>
          <button
            type="button"
            class="ui-button-primary"
            :disabled="!canEditSystem"
            @click="reconfigureCluster"
          >
            Reconfigure
          </button>
        </div>
      </div>
    </div>

    <ErrorAlert v-if="error">{{ error }}</ErrorAlert>
    <InfoAlert v-if="!canEditSystem">
      This workspace is visible, but cluster reconfigure requires `admin/system:edit:*`.
    </InfoAlert>

    <div v-if="loading" class="ui-panel ui-section text-[var(--color-brand-muted)]">
      <LoadingSpinner :size="5" />
      Loading admin system panels...
    </div>

    <template v-else>
      <section class="ui-panel ui-section">
        <div class="mb-4">
          <p class="ui-page-kicker">Slurm Services</p>
          <h2 class="ui-panel-title">Control Surfaces</h2>
          <p class="ui-panel-description mt-2">
            Read-only snapshots from licenses, shares and SlurmDB system endpoints.
          </p>
        </div>

        <div class="grid gap-4 lg:grid-cols-2">
          <article class="ui-panel-soft px-4 py-4">
            <div class="ui-stat-label">Licenses</div>
            <pre class="mt-3 overflow-x-auto text-xs text-[var(--color-brand-ink-strong)]">{{ JSON.stringify(licenses, null, 2) }}</pre>
          </article>
          <article class="ui-panel-soft px-4 py-4">
            <div class="ui-stat-label">Shares</div>
            <pre class="mt-3 overflow-x-auto text-xs text-[var(--color-brand-ink-strong)]">{{ JSON.stringify(shares, null, 2) }}</pre>
          </article>
          <article class="ui-panel-soft px-4 py-4">
            <div class="ui-stat-label">SlurmDB Diag</div>
            <pre class="mt-3 overflow-x-auto text-xs text-[var(--color-brand-ink-strong)]">{{ JSON.stringify(slurmdbDiag, null, 2) }}</pre>
          </article>
          <article class="ui-panel-soft px-4 py-4">
            <div class="ui-stat-label">SlurmDB Config</div>
            <pre class="mt-3 overflow-x-auto text-xs text-[var(--color-brand-ink-strong)]">{{ JSON.stringify(slurmdbConfig, null, 2) }}</pre>
          </article>
          <article class="ui-panel-soft px-4 py-4">
            <div class="ui-stat-label">Instances</div>
            <pre class="mt-3 overflow-x-auto text-xs text-[var(--color-brand-ink-strong)]">{{ JSON.stringify(instances, null, 2) }}</pre>
          </article>
          <article class="ui-panel-soft px-4 py-4">
            <div class="ui-stat-label">TRES</div>
            <pre class="mt-3 overflow-x-auto text-xs text-[var(--color-brand-ink-strong)]">{{ JSON.stringify(tres, null, 2) }}</pre>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>
