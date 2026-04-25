<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { parseCsvList } from '@/composables/management'
import type { ClusterAssociation, ClusterAccountTreeNode } from '@/composables/GatewayAPI'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import AccountTreeNode from '@/components/accounts/AccountTreeNode.vue'
import PageHeader from '@/components/PageHeader.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import PaginationControls from '@/components/PaginationControls.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import {
  DEFAULT_PAGE_SIZE,
  lastPage,
  parsePageSize,
  parsePositivePage,
  type PageSizeOption
} from '@/composables/Pagination'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster } = defineProps<{ cluster: string }>()
const route = useRoute()
const router = useRouter()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

const { data, unable, loaded, initialLoading } = useClusterDataPoller<ClusterAssociation[]>(
  cluster,
  'associations',
  120000
)

const expandedAccounts = ref<Set<string>>(new Set())
const autoExpandedOnce = ref(false)
const MAX_AUTO_EXPANDED = 10
const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const createOpen = ref(false)
const operationBusy = ref(false)
const operationError = ref<string | null>(null)

const canCreateAccount = computed(() => runtimeStore.hasRoutePermission(cluster, 'accounts', 'edit'))

function toggleAccount(account: string) {
  if (expandedAccounts.value.has(account)) {
    expandedAccounts.value.delete(account)
  } else {
    expandedAccounts.value.add(account)
  }
}

const accountTree = computed<ClusterAccountTreeNode[]>(() => {
  if (!data.value || data.value.length === 0) {
    return []
  }

  const accountMap = new Map<string, ClusterAccountTreeNode>()
  const rootAccounts: ClusterAccountTreeNode[] = []

  for (const association of data.value) {
    const existingNode = accountMap.get(association.account)
    if (existingNode) {
      if (association.user) {
        existingNode.users.push(association.user)
      }
      continue
    }
    const node: ClusterAccountTreeNode = {
      children: [],
      level: 0,
      account: association.account,
      max: association.max,
      parent_account: association.parent_account,
      qos: association.qos,
      users: association.user ? [association.user] : []
    }
    accountMap.set(association.account, node)
  }

  for (const node of accountMap.values()) {
    if (node.parent_account && accountMap.has(node.parent_account)) {
      const parent = accountMap.get(node.parent_account)!
      parent.children.push(node)
      node.level = parent.level + 1
    } else {
      rootAccounts.push(node)
    }
  }

  function sortTree(nodes: ClusterAccountTreeNode[]) {
    nodes.sort((a, b) => a.account.localeCompare(b.account))
    for (const node of nodes) {
      sortTree(node.children)
    }
  }

  sortTree(rootAccounts)
  return rootAccounts
})

const totalPages = computed(() => lastPage(accountTree.value.length, pageSize.value))
const pagedAccountTree = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return accountTree.value.slice(start, start + pageSize.value)
})

const availableAccounts = computed<Set<string>>(() => {
  const accounts = new Set<string>()
  if (!data.value) {
    return accounts
  }
  for (const association of data.value) {
    accounts.add(association.account)
  }
  return accounts
})

function autoExpandTree(nodes: ClusterAccountTreeNode[]) {
  const queue = [...nodes]
  expandedAccounts.value = new Set()
  let visibleCount = nodes.length

  if (visibleCount >= MAX_AUTO_EXPANDED) {
    return
  }

  while (queue.length > 0 && visibleCount < MAX_AUTO_EXPANDED) {
    const node = queue.shift()
    if (!node) continue
    if (node.children.length === 0 || expandedAccounts.value.has(node.account)) {
      continue
    }

    expandedAccounts.value.add(node.account)
    visibleCount += node.children.length
    queue.push(...node.children)
  }
}

function updateQueryParameters() {
  const query: LocationQueryRaw = {}
  if (page.value !== 1) query.page = page.value
  if (pageSize.value !== DEFAULT_PAGE_SIZE) query.page_size = pageSize.value
  router.push({ name: 'accounts', params: { cluster }, query })
}

function updatePage(newPage: number) {
  page.value = newPage
  updateQueryParameters()
}

function updatePageSize(newPageSize: PageSizeOption) {
  pageSize.value = newPageSize
  page.value = 1
  updateQueryParameters()
}

async function createAccount(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.save_account(cluster, {
      name: payload.name || undefined,
      description: payload.description || null,
      parent_account: payload.parent_account || undefined,
      qos: parseCsvList(payload.qos)
    })
    runtimeStore.reportInfo(`Account ${payload.name || ''} creation requested.`)
    createOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

watch(
  accountTree,
  (tree) => {
    if (!tree.length) {
      expandedAccounts.value = new Set()
      autoExpandedOnce.value = false
      return
    }

    expandedAccounts.value = new Set(
      [...expandedAccounts.value].filter((account) => availableAccounts.value.has(account))
    )

    if (!autoExpandedOnce.value) {
      autoExpandTree(tree)
      autoExpandedOnce.value = true
    }
  },
  { immediate: true }
)

watch(totalPages, (newLastPage) => {
  if (page.value > newLastPage) {
    page.value = newLastPage
    updateQueryParameters()
  }
})

if (route.query.page) {
  page.value = parsePositivePage(route.query.page)
}
if (route.query.page_size) {
  pageSize.value = parsePageSize(route.query.page_size)
}
</script>

<template>
  <ClusterMainLayout menu-entry="accounts" :cluster="cluster" :breadcrumb="[{ title: 'Accounts' }]">
    <PageHeader
      title="Accounts"
      description="Accounts defined on cluster, with hierarchy, delegated users and structure laid out in one tree."
      :metric-value="loaded ? availableAccounts.size : undefined"
      :metric-label="`account${availableAccounts.size > 1 ? 's' : ''} found`"
    >
      <template #actions>
        <button v-if="canCreateAccount" type="button" class="ui-button-primary" @click="createOpen = true">
          Create account
        </button>
      </template>
    </PageHeader>
    <ErrorAlert v-if="unable"
      >Unable to retrieve associations from cluster
      <span class="font-medium">{{ cluster }}</span></ErrorAlert
    >
    <InfoAlert v-else-if="loaded && data?.length == 0"
      >No association defined on cluster <span class="font-medium">{{ cluster }}</span></InfoAlert
    >
    <div v-else class="ui-section-stack">
      <PanelSkeleton v-if="initialLoading" :rows="7" />
      <div v-else class="ui-panel ui-section">
        <ul role="list" class="space-y-4">
          <AccountTreeNode
            v-for="(node, index) in pagedAccountTree"
            :key="node.account"
            :node="node"
            :expanded-accounts="expandedAccounts"
            :is-last="index === pagedAccountTree.length - 1"
            :cluster="cluster"
            @toggle="toggleAccount"
          />
        </ul>
      </div>
      <div v-if="!initialLoading" class="ui-panel overflow-hidden">
        <PaginationControls
          :page="page"
          :page-size="pageSize"
          :total="accountTree.length"
          item-label="root account"
          @update:page="updatePage"
          @update:page-size="updatePageSize"
        />
      </div>
    </div>

    <ActionDialog
      :open="createOpen"
      title="Create Account"
      description="Add a new SlurmDB account from the account tree workspace."
      submit-label="Create account"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'name', label: 'Account name', required: true },
        { key: 'description', label: 'Description', type: 'textarea' },
        { key: 'parent_account', label: 'Parent account' },
        { key: 'qos', label: 'QOS (comma separated)' }
      ]"
      @close="createOpen = false"
      @submit="createAccount"
    />
  </ClusterMainLayout>
</template>
