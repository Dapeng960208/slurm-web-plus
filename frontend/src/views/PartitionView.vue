<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import { useClusterDataGetter } from '@/composables/DataGetter'
import { getMBHumanUnit, getNodeGPU } from '@/composables/GatewayAPI'
import type { ClusterNode, ClusterPartition } from '@/composables/GatewayAPI'

const { cluster, partition } = defineProps<{
  cluster: string
  partition: string
}>()

const { t } = useI18n()
const { data: partitions } = useClusterDataGetter<ClusterPartition[]>(cluster, 'partitions')
const { data: nodes } = useClusterDataGetter<ClusterNode[]>(cluster, 'nodes')

const partitionRecord = computed(() =>
  (partitions.value ?? []).find((item) => item.name === partition)
)

const partitionNodes = computed(() =>
  (nodes.value ?? []).filter((node) => node.partitions.includes(partition))
)

const totalCpu = computed(() =>
  partitionNodes.value.reduce((sum, node) => sum + node.cpus, 0)
)

const allocatedCpu = computed(() =>
  partitionNodes.value.reduce((sum, node) => sum + node.alloc_cpus, 0)
)

const totalMemory = computed(() =>
  partitionNodes.value.reduce((sum, node) => sum + node.real_memory, 0)
)

const totalGpu = computed(() =>
  partitionNodes.value.reduce(
    (sum, node) =>
      sum + getNodeGPU(node.gres).reduce((gpuTotal, item) => gpuTotal + Number(item.split(' x ')[0] ?? 0), 0),
    0
  )
)

const allocatedNodeCount = computed(() =>
  partitionNodes.value.filter((node) => node.alloc_cpus > 0).length
)

const idleNodeCount = computed(() =>
  partitionNodes.value.filter((node) => node.state.includes('IDLE')).length
)

const partitionChips = computed(() =>
  (partitionRecord.value?.node_sets ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="resources"
    :cluster="cluster"
    :breadcrumb="[
      { title: 'shell.mainMenu.resources', routeName: 'resources' },
      { title: t('common.labels.partitions') },
      { title: partition }
    ]"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <PageHeader
        kicker="common.labels.partitions"
        :title="partition"
        description="pages.partition.description"
        :metric-value="partitionNodes.length"
        metric-label="pages.resources.metricLabelPlural"
      >
        <template #actions>
          <RouterLink :to="{ name: 'resources', params: { cluster } }" class="ui-button-secondary">
            {{ t('common.navigation.back') }}
          </RouterLink>
        </template>
      </PageHeader>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
          <InfoAlert v-if="!partitionRecord">
            {{ t('pages.partition.notFound', { partition }) }}
          </InfoAlert>

          <template v-else>
            <div class="ui-summary-strip">
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.nodes') }}</div>
                <div class="ui-summary-value">{{ partitionNodes.length }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.totalCpu') }}</div>
                <div class="ui-summary-value">{{ totalCpu }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.allocatedCpu') }}</div>
                <div class="ui-summary-value">{{ allocatedCpu }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.totalMemory') }}</div>
                <div class="ui-summary-value">{{ getMBHumanUnit(totalMemory) }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.gpu') }}</div>
                <div class="ui-summary-value">{{ totalGpu }}</div>
              </div>
            </div>

            <div class="grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(18rem,1.08fr)]">
              <section class="ui-panel ui-section">
                <div class="mb-4">
                  <h2 class="ui-panel-title">{{ t('pages.partition.detailTitle') }}</h2>
                  <p class="ui-panel-description mt-2">
                    {{ t('pages.partition.detailDescription') }}
                  </p>
                </div>
                <div class="ui-detail-list">
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('common.labels.name') }}</div>
                    <div class="ui-detail-value">{{ partitionRecord.name }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.nodes') }}</div>
                    <div class="ui-detail-value">{{ partitionNodes.length }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.allocatedNodes') }}</div>
                    <div class="ui-detail-value">{{ allocatedNodeCount }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.idleNodes') }}</div>
                    <div class="ui-detail-value">{{ idleNodeCount }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.totalCpu') }}</div>
                    <div class="ui-detail-value">{{ totalCpu }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.allocatedCpu') }}</div>
                    <div class="ui-detail-value">{{ allocatedCpu }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.totalMemory') }}</div>
                    <div class="ui-detail-value">{{ getMBHumanUnit(totalMemory) }}</div>
                  </div>
                  <div class="ui-detail-row">
                    <div class="ui-detail-term">{{ t('pages.partition.summary.gpu') }}</div>
                    <div class="ui-detail-value">{{ totalGpu }}</div>
                  </div>
                </div>
              </section>

              <section class="ui-panel ui-section">
                <div class="mb-4">
                  <h2 class="ui-panel-title">{{ t('pages.partition.nodeSets') }}</h2>
                  <p class="ui-panel-description mt-2">
                    {{ t('pages.partition.nodeSetsDescription') }}
                  </p>
                </div>
                <div v-if="partitionChips.length" class="flex flex-wrap gap-2">
                  <span
                    v-for="item in partitionChips"
                    :key="item"
                    class="ui-chip"
                  >
                    {{ item }}
                  </span>
                </div>
                <p v-else class="ui-panel-description">
                  {{ t('pages.partition.nodeSetsEmpty') }}
                </p>
              </section>
            </div>
          </template>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
