<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { parseCsvList } from '@/composables/management'
import type { AccountDescription, ClusterAssociation, ClusterAccountTreeNode } from '@/composables/GatewayAPI'
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
import { createStaticSearchSource } from '@/composables/searchSelect'

const { cluster } = defineProps<{ cluster: string }>()
const route = useRoute()
const router = useRouter()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const { t } = useI18n()

const {
  data: associationsData,
  unable: associationsUnable,
  loaded: associationsLoaded,
  initialLoading: associationsInitialLoading,
  refresh: refreshAssociations
} = useClusterDataPoller<ClusterAssociation[]>(
  cluster,
  'associations',
  120000
)
const {
  data: accountsData,
  unable: accountsUnable,
  loaded: accountsLoaded,
  initialLoading: accountsInitialLoading,
  refresh: refreshAccounts
} = useClusterDataPoller<AccountDescription[]>(cluster, 'accounts', 120000)

const expandedAccounts = ref<Set<string>>(new Set())
const autoExpandedOnce = ref(false)
const MAX_AUTO_EXPANDED = 10
const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const createOpen = ref(false)
const operationBusy = ref(false)
const operationError = ref<string | null>(null)
const qosSearchSource = createStaticSearchSource(async () =>
  (await gateway.qos(cluster)).map((qos) => ({
    value: qos.name,
    label: qos.name,
    description: qos.description || qos.name
  }))
)

const canCreateAccount = computed(() => runtimeStore.hasRoutePermission(cluster, 'accounts', 'edit'))

function toggleAccount(account: string) {
  if (expandedAccounts.value.has(account)) {
    expandedAccounts.value.delete(account)
  } else {
    expandedAccounts.value.add(account)
  }
}

const unable = computed(() => associationsUnable.value || accountsUnable.value)
const loaded = computed(() => associationsLoaded.value && accountsLoaded.value)
const initialLoading = computed(() => associationsInitialLoading.value || accountsInitialLoading.value)

const accountTree = computed<ClusterAccountTreeNode[]>(() => {
  if (!accountsData.value || accountsData.value.length === 0) {
    return []
  }

  const accountMap = new Map<string, ClusterAccountTreeNode>()
  const rootAccounts: ClusterAccountTreeNode[] = []

  for (const accountEntry of accountsData.value) {
    const node: ClusterAccountTreeNode = {
      children: [],
      level: 0,
      account: accountEntry.name,
      max: {
        jobs: {
          accruing: { set: false, infinite: false, number: 0 },
          active: { set: false, infinite: false, number: 0 },
          per: {
            accruing: { set: false, infinite: false, number: 0 },
            count: { set: false, infinite: false, number: 0 },
            submitted: { set: false, infinite: false, number: 0 },
            wall_clock: { set: false, infinite: false, number: 0 }
          },
          total: { set: false, infinite: false, number: 0 }
        },
        per: {
          account: {
            wall_clock: { set: false, infinite: false, number: 0 }
          }
        },
        tres: {
          group: { active: [], minutes: [] },
          minutes: { per: { job: [] }, total: [] },
          per: { job: [], node: [] },
          total: []
        }
      },
      parent_account: accountEntry.parent_account ?? '',
      qos: accountEntry.qos ?? [],
      users: []
    }
    accountMap.set(accountEntry.name, node)
  }

  for (const association of associationsData.value ?? []) {
    const existingNode = accountMap.get(association.account)
    if (!existingNode) continue
    existingNode.max = association.max
    existingNode.parent_account = association.parent_account || existingNode.parent_account
    existingNode.qos = association.qos?.length ? association.qos : existingNode.qos
    if (association.user) {
      existingNode.users.push(association.user)
    }
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
  if (!accountsData.value) {
    return accounts
  }
  for (const accountEntry of accountsData.value) {
    accounts.add(accountEntry.name)
  }
  return accounts
})

function hasOperationErrors(result: { errors?: unknown[] } | null | undefined): boolean {
  return Array.isArray(result?.errors) && result.errors.length > 0
}

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
    const accountName = payload.name || undefined
    const parentAccount = payload.parent_account || undefined
    const qos = parseCsvList(payload.qos)
    const saveAccountResult = await gateway.save_account(cluster, {
      name: accountName,
      description: payload.description || undefined,
      organization: payload.organization || undefined,
      parent_account: parentAccount,
      qos
    })
    if (hasOperationErrors(saveAccountResult)) {
      throw new Error(t('pages.accounts.errors.createFailed'))
    }
    if (accountName && parentAccount) {
      const saveAssociationResult = await gateway.save_association(cluster, {
        associations: [
          {
            account: accountName,
            parent_account: parentAccount,
            qos
          }
        ]
      })
      if (hasOperationErrors(saveAssociationResult)) {
        throw new Error(t('pages.accounts.errors.createAssociationFailed'))
      }
    }
    await Promise.all([refreshAccounts(), refreshAssociations()])
    runtimeStore.reportInfo(
      t('pages.accounts.notifications.createRequested', { name: payload.name || '' })
    )
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
  <ClusterMainLayout
    menu-entry="accounts"
    :cluster="cluster"
    :breadcrumb="[{ title: 'shell.mainMenu.accounts' }]"
  >
    <div class="ui-page ui-page-wide ui-content-workspace">
    <PageHeader
      title="pages.accounts.title"
      description="pages.accounts.description"
      :metric-value="loaded ? availableAccounts.size : undefined"
      :metric-label="
        availableAccounts.size === 1
          ? 'pages.accounts.metricLabel'
          : 'pages.accounts.metricLabelPlural'
      "
    >
      <template #actions>
        <button
          v-if="canCreateAccount"
          type="button"
          class="ui-button-primary"
          @click="createOpen = true"
        >
          {{ t('pages.accounts.create') }}
        </button>
      </template>
    </PageHeader>
    <ErrorAlert v-if="unable"
      >{{ t('pages.accounts.unableToRetrieve', { cluster }) }}</ErrorAlert
    >
    <InfoAlert v-else-if="loaded && accountsData?.length == 0"
      >{{ t('pages.accounts.noAccounts', { cluster }) }}</InfoAlert
    >
    <div v-else class="ui-results-layout">
      <PanelSkeleton v-if="initialLoading" :rows="7" />
      <div v-else class="ui-results-workspace">
        <div class="ui-panel ui-section ui-results-card">
          <div class="ui-tree-scroll">
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
        </div>
        <div class="ui-results-dock">
          <PaginationControls
            :page="page"
            :page-size="pageSize"
            :total="accountTree.length"
            :item-label="t('common.entities.rootAccounts')"
            @update:page="updatePage"
            @update:page-size="updatePageSize"
          />
        </div>
      </div>
    </div>

    <ActionDialog
      :open="createOpen"
      title="pages.accounts.dialogs.create.title"
      description="pages.accounts.dialogs.create.description"
      submit-label="pages.accounts.dialogs.create.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'name', label: 'pages.accounts.dialogs.create.fields.name', required: true },
        {
          key: 'description',
          label: 'pages.accounts.dialogs.create.fields.description',
          type: 'textarea',
          required: true
        },
        {
          key: 'organization',
          label: 'pages.accounts.dialogs.create.fields.organization',
          required: true
        },
        { key: 'parent_account', label: 'pages.accounts.dialogs.create.fields.parentAccount' },
        {
          key: 'qos',
          label: 'pages.accounts.dialogs.create.fields.qos',
          type: 'search-multi-select',
          source: qosSearchSource
        }
      ]"
      @close="createOpen = false"
      @submit="createAccount"
    />
    </div>
  </ClusterMainLayout>
</template>
