<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { isFiltersClusterNodeMainState } from '@/stores/runtime/resources'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { getMBHumanUnit, getNodeGPU } from '@/composables/GatewayAPI'
import type { ClusterNode } from '@/composables/GatewayAPI'
import ResourcesDiagramThumbnail from '@/components/resources/ResourcesDiagramThumbnail.vue'
import NodeMainState from '@/components/resources/NodeMainState.vue'
import NodeAllocationState from '@/components/resources/NodeAllocationState.vue'
import NodeGPU from '@/components/resources/NodeGPU.vue'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import ResourcesFiltersPanel from '@/components/resources/ResourcesFiltersPanel.vue'
import ResourcesFiltersBar from '@/components/resources/ResourcesFiltersBar.vue'
import { foldNodeset, expandNodeset } from '@/composables/Nodeset'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import TableSkeletonRows from '@/components/TableSkeletonRows.vue'
import PaginationControls from '@/components/PaginationControls.vue'
import { lastPage, parsePageSize, parsePositivePage, type PageSizeOption } from '@/composables/Pagination'
import { ChevronRightIcon, MagnifyingGlassPlusIcon } from '@heroicons/vue/20/solid'
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'

const { cluster } = defineProps<{ cluster: string }>()

const foldedNodesShow: Ref<Record<string, boolean>> = ref({})
const runtimeStore = useRuntimeStore()
const route = useRoute()
const router = useRouter()
const hydratingQuery = ref(false)
const { data, unable, loaded, initialLoading, setCluster } = useClusterDataPoller<ClusterNode[]>(
  cluster,
  'nodes',
  10000
)

function arraysEqual<CType>(a: Array<CType>, b: Array<CType>): boolean {
  if (a === b) return true
  if (a == null || b == null) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; ++i) {
    if (a[i] !== b[i]) return false
  }
  return true
}

interface FoldedClusterNode extends ClusterNode {
  number: number
}

const filteredNodes: Ref<ClusterNode[]> = computed(() => {
  if (!data.value) {
    return []
  }
  return [...data.value].filter((node) => runtimeStore.resources.matchesFilters(node))
})

const clusterSupportsRacksdb = computed(() => {
  return Boolean(runtimeStore.getCluster(cluster)?.racksdb)
})

const foldedNodes: Ref<FoldedClusterNode[]> = computed(() => {
  let previousNode: FoldedClusterNode | undefined = undefined
  let similarNodes: string[] = []
  const result: FoldedClusterNode[] = []

  function finishSet() {
    if (previousNode) {
      previousNode.name = foldNodeset(similarNodes)
    }
  }

  for (const currentNode of filteredNodes.value) {
    if (
      previousNode &&
      previousNode.sockets == currentNode.sockets &&
      previousNode.cores == currentNode.cores &&
      previousNode.real_memory == currentNode.real_memory &&
      getNodeGPU(previousNode.gres).join(',') == getNodeGPU(currentNode.gres).join(',') &&
      arraysEqual<string>(previousNode.state, currentNode.state) &&
      arraysEqual<string>(previousNode.partitions, currentNode.partitions)
    ) {
      previousNode.number += 1
      similarNodes.push(currentNode.name)
    } else {
      finishSet()
      previousNode = { ...currentNode, number: 1 }
      similarNodes = [currentNode.name]
      result.push(previousNode)
    }
  }
  finishSet()
  return result
})

const totalPages = computed(() => lastPage(foldedNodes.value.length, runtimeStore.resources.pageSize))
const pagedFoldedNodes = computed(() => {
  const start = (runtimeStore.resources.page - 1) * runtimeStore.resources.pageSize
  const end = start + runtimeStore.resources.pageSize
  return foldedNodes.value.slice(start, end)
})

function updateQueryParameters() {
  router.push({ name: 'resources', query: runtimeStore.resources.query() as LocationQueryRaw })
}

function resetPageAndUpdateQueryParameters() {
  if (hydratingQuery.value) return
  runtimeStore.resources.page = 1
  updateQueryParameters()
}

function updatePage(page: number) {
  runtimeStore.resources.page = page
  updateQueryParameters()
}

function updatePageSize(pageSize: PageSizeOption) {
  runtimeStore.resources.pageSize = pageSize
  runtimeStore.resources.page = 1
  updateQueryParameters()
}

watch(
  () => runtimeStore.resources.filters.states,
  () => resetPageAndUpdateQueryParameters()
)
watch(
  () => runtimeStore.resources.filters.partitions,
  () => resetPageAndUpdateQueryParameters()
)
watch(
  () => foldedNodes.value,
  () => {
    const newFoldedNodesShow: Record<string, boolean> = {}
    for (const foldedNodeset of foldedNodes.value) {
      if (foldedNodesShow.value && foldedNodeset.name in foldedNodesShow.value) {
        newFoldedNodesShow[foldedNodeset.name] = foldedNodesShow.value[foldedNodeset.name]
      } else {
        newFoldedNodesShow[foldedNodeset.name] = false
      }
    }
    foldedNodesShow.value = newFoldedNodesShow
  }
)

watch(
  () => cluster,
  (newCluster) => {
    runtimeStore.resources.showRackDiagram = false
    setCluster(newCluster)
  }
)

onMounted(async () => {
  hydratingQuery.value = true
  runtimeStore.resources.showRackDiagram = false
  if (['states', 'partitions', 'page', 'page_size'].some((parameter) => parameter in route.query)) {
    if (route.query.states) {
      runtimeStore.resources.filters.states = []
      ;(route.query.states as string).split(',').forEach((state: string) => {
        if (isFiltersClusterNodeMainState(state)) runtimeStore.resources.filters.states.push(state)
      })
    }
    if (route.query.partitions) {
      runtimeStore.resources.filters.partitions = (route.query.partitions as string).split(',')
    }
    if (route.query.page) {
      runtimeStore.resources.page = parsePositivePage(route.query.page)
    }
    if (route.query.page_size) {
      runtimeStore.resources.pageSize = parsePageSize(route.query.page_size)
    }
  } else {
    updateQueryParameters()
  }
  await nextTick()
  hydratingQuery.value = false
})

watch(totalPages, (newLastPage) => {
  if (runtimeStore.resources.page > newLastPage) {
    runtimeStore.resources.page = newLastPage
    updateQueryParameters()
  }
})
</script>

<template>
  <ClusterMainLayout
    menu-entry="resources"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Resources' }]"
  >
    <div class="ui-page ui-page-wide">
      <ResourcesFiltersPanel :cluster="cluster" :nbNodes="filteredNodes.length" />

      <PageHeader
        title="Nodes"
        description="Current node state, allocation pressure and partition visibility across the cluster."
        :metric-value="loaded ? filteredNodes.length : undefined"
        :metric-label="`node${filteredNodes.length > 1 ? 's' : ''} found`"
      >
        <template #actions>
          <button
            v-if="clusterSupportsRacksdb"
            type="button"
            class="ui-button-secondary"
            @click="
              runtimeStore.resources.showRackDiagram = !runtimeStore.resources.showRackDiagram
            "
          >
            <EyeSlashIcon
              v-if="runtimeStore.resources.showRackDiagram"
              class="h-4 w-4"
              aria-hidden="true"
            />
            <EyeIcon v-else class="h-4 w-4" aria-hidden="true" />
            {{ runtimeStore.resources.showRackDiagram ? 'Hide Rack Diagram' : 'Show Rack Diagram' }}
          </button>
        </template>
      </PageHeader>

      <ResourcesDiagramThumbnail
        v-if="clusterSupportsRacksdb && runtimeStore.resources.showRackDiagram"
        :cluster="cluster"
        :nodes="filteredNodes"
        :loading="initialLoading"
      />
      <ResourcesFiltersBar />

      <ErrorAlert v-if="unable"
        >Unable to retrieve nodes from cluster
        <span class="font-medium">{{ cluster }}</span></ErrorAlert
      >
      <div v-else class="ui-section-stack">
        <div class="ui-table-shell -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div class="inline-block min-w-full py-2 align-middle">
            <table class="ui-table min-w-full">
              <thead>
                <tr class="text-sm font-semibold text-gray-900 dark:text-gray-200">
                  <th scope="col" colspan="2" class="w-12 py-3.5 pr-3 text-left sm:pl-6 lg:pl-8">
                    Nodename
                  </th>
                  <th scope="col" class="w-12 px-3 py-3.5 text-left">State</th>
                  <th scope="col" class="w-12 px-3 py-3.5 text-left">Allocation</th>
                  <th scope="col" class="px-3 py-3.5 text-left">CPU</th>
                  <th scope="col" class="px-3 py-3.5 text-left">Memory</th>
                  <th scope="col" class="px-3 py-3.5 text-left">GPU</th>
                  <th scope="col" class="px-3 py-3.5 text-left">Partitions</th>
                </tr>
              </thead>
              <tbody
                v-if="loaded"
                class="divide-y divide-gray-200 text-sm text-gray-500 dark:divide-gray-700 dark:text-gray-300"
              >
                <template v-for="node in pagedFoldedNodes" :key="node.name">
                  <tr>
                    <td class="w-4">
                      <button
                        v-if="node.number > 1"
                        class="-mr-2 flex h-10 w-10 items-center justify-center rounded-full p-2 text-[var(--color-brand-muted)] transition hover:bg-[rgba(182,232,44,0.12)]"
                        @click="foldedNodesShow[node.name] = !foldedNodesShow[node.name]"
                      >
                        <span class="sr-only">Toggle folded nodes {{ node.name }}</span>
                        <ChevronRightIcon
                          class="h-6 w-6"
                          aria-hidden="true"
                          :class="[foldedNodesShow[node.name] ? 'rotate-90' : '', 'transition']"
                        />
                      </button>
                    </td>
                    <td class="py-3 text-sm whitespace-nowrap">
                      <RouterLink
                        v-if="node.number == 1"
                        class="inline-flex text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
                        :to="{
                          name: 'node',
                          params: { cluster: cluster, nodeName: node.name },
                          query: { returnTo: 'resources' }
                        }"
                      >
                        <span class="pr-4 font-mono text-[var(--color-brand-ink-strong)]">{{
                          node.name
                        }}</span>
                        <MagnifyingGlassPlusIcon class="h-4 w-4" />
                      </RouterLink>
                      <button
                        v-else
                        @click="foldedNodesShow[node.name] = !foldedNodesShow[node.name]"
                        class="transition hover:text-[var(--color-brand-ink-strong)]"
                      >
                        <span class="sr-only">Toggle folded nodes {{ node.name }}</span>
                        <span class="font-mono text-[var(--color-brand-ink-strong)]">{{
                          node.name
                        }}</span>
                        <span class="px-1 font-normal text-[var(--color-brand-muted)] italic"
                          >({{ node.number }})</span
                        >
                      </button>
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      <NodeMainState :status="node.state" />
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      <NodeAllocationState :status="node.state" />
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      {{ node.sockets }} x {{ node.cores }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      {{ getMBHumanUnit(node.real_memory) }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      <NodeGPU :node="node" />
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      <span
                        v-for="partition in node.partitions"
                        :key="partition"
                        class="ui-chip mr-1"
                      >
                        {{ partition }}
                      </span>
                    </td>
                  </tr>
                  <template v-if="node.number > 1">
                    <Transition
                      enter-active-class="duration-100 ease-out"
                      enter-from-class="-translate-y-6 opacity-0"
                      enter-to-class="opacity-100"
                      leave-active-class="duration-100 ease-out"
                      leave-from-class="opacity-100"
                      leave-to-class="-translate-y-6 opacity-0"
                    >
                      <tr v-show="foldedNodesShow[node.name]">
                        <td colspan="8" class="z-0 bg-[rgba(239,244,246,0.92)]">
                          <ul
                            role="list"
                            class="m-4 grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-4 md:grid-cols-4 xl:grid-cols-8 2xl:grid-cols-16"
                          >
                            <li
                              v-for="_node in expandNodeset(node.name)"
                              :key="_node"
                              class="col-span-1 divide-y divide-[rgba(80,105,127,0.08)] rounded-[18px] border border-white/70 bg-white text-left font-mono text-xs shadow-[var(--shadow-soft)] transition-transform hover:scale-[1.03]"
                            >
                              <button
                                class="flex w-full items-center justify-between space-x-6 px-4 py-3 text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
                                @click="
                                  router.push({
                                    name: 'node',
                                    params: { cluster: $props.cluster, nodeName: _node },
                                    query: { returnTo: 'resources' }
                                  })
                                "
                              >
                                <span
                                  class="visible mr-0 grow text-left text-[var(--color-brand-ink-strong)]"
                                  >{{ _node }}</span
                                >
                                <MagnifyingGlassPlusIcon class="h-4 w-4" />
                              </button>
                            </li>
                          </ul>
                        </td>
                      </tr>
                    </Transition>
                  </template>
                </template>
              </tbody>
              <TableSkeletonRows
                v-else
                :columns="8"
                :rows="8"
                first-cell-class="sm:pl-6 lg:pl-8"
                cell-class="px-3"
              />
            </table>
            <PaginationControls
              v-if="loaded"
              :page="runtimeStore.resources.page"
              :page-size="runtimeStore.resources.pageSize"
              :total="foldedNodes.length"
              item-label="node group"
              @update:page="updatePage"
              @update:page-size="updatePageSize"
            />
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
