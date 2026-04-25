<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Component } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { RouterLink, useRoute } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { formatJobExitCode, jobRequestedGPU, jobAllocatedGPU } from '@/composables/GatewayAPI'
import type { ClusterIndividualJob } from '@/composables/GatewayAPI'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobProgress from '@/components/job/JobProgress.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import DetailSkeletonList from '@/components/DetailSkeletonList.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import { HashtagIcon } from '@heroicons/vue/24/outline'
import JobFieldRaw from '@/components/job/JobFieldRaw.vue'
import JobFieldComment from '@/components/job/JobFieldComment.vue'
import JobResources from '@/components/job/JobResources.vue'
import DetailSummaryStrip from '@/components/details/DetailSummaryStrip.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'

const { cluster, id } = defineProps<{ cluster: string; id: number }>()

const route = useRoute()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const authStore = useAuthStore()
const operationError = ref<string | null>(null)
const operationBusy = ref(false)
const editOpen = ref(false)
const cancelOpen = ref(false)

const jobsFields = [
  'user',
  'group',
  'account',
  'wckeys',
  'priority',
  'name',
  'comments',
  'submit-line',
  'script',
  'workdir',
  'exit-code',
  'nodes',
  'partition',
  'qos',
  'tres-requested',
  'tres-allocated'
] as const

type JobField = (typeof jobsFields)[number]
type JobFieldLayout = 'compact' | 'full'

type JobCompactField = {
  id: JobField
  label: string
  layout: 'compact'
  value: string
  monospace?: boolean
  to?: RouteLocationRaw
}

type JobComponentField = {
  id: JobField
  label: string
  layout: 'full'
  component: Component
  props: object
}

type JobFieldRow = JobCompactField | JobComponentField

const compactFieldIds: JobField[] = [
  'user',
  'group',
  'account',
  'wckeys',
  'priority',
  'nodes',
  'partition',
  'qos',
  'exit-code'
]

function isValidJobField(key: string): key is JobField {
  return typeof key === 'string' && jobsFields.includes(key as JobField)
}

const { data, unable, loaded, initialLoading, setCluster, setParam } =
  useClusterDataPoller<ClusterIndividualJob>(
  cluster,
  'job',
  5000,
  id
)

const displayTags = ref<Record<JobField, { show: boolean; highlight: boolean }>>({
  user: { show: false, highlight: false },
  group: { show: false, highlight: false },
  account: { show: false, highlight: false },
  wckeys: { show: false, highlight: false },
  priority: { show: false, highlight: false },
  name: { show: false, highlight: false },
  comments: { show: false, highlight: false },
  'submit-line': { show: false, highlight: false },
  script: { show: false, highlight: false },
  workdir: { show: false, highlight: false },
  'exit-code': { show: false, highlight: false },
  nodes: { show: false, highlight: false },
  partition: { show: false, highlight: false },
  qos: { show: false, highlight: false },
  'tres-allocated': { show: false, highlight: false },
  'tres-requested': { show: false, highlight: false }
})

function fieldLayout(id: JobField): JobFieldLayout {
  return compactFieldIds.includes(id) ? 'compact' : 'full'
}

function fmtField(value: string | number | null | undefined) {
  if (value == null || value === '') return '-'
  return String(value)
}

function compactField(
  id: JobField,
  label: string,
  value: string | number | null | undefined,
  to?: RouteLocationRaw
): JobCompactField {
  return { id, label, layout: fieldLayout(id) as 'compact', value: fmtField(value), to }
}

function fullField(
  id: JobField,
  label: string,
  component: Component,
  props: object
): JobComponentField {
  return { id, label, layout: fieldLayout(id) as 'full', component, props }
}

const jobFieldsContent = computed((): JobFieldRow[] => {
  if (!data.value) return []
  const account = data.value.association.account

  return [
    compactField('user', 'User', data.value.user, {
      name: 'user',
      params: { cluster, user: data.value.user }
    }),
    compactField('group', 'Group', data.value.group),
    compactField(
      'account',
      'Account',
      account,
      account ? { name: 'account', params: { cluster, account } } : undefined
    ),
    compactField('wckeys', 'Wckeys', data.value.wckey.wckey),
    compactField('priority', 'Priority', data.value.priority.number),
    compactField('nodes', 'Nodes', data.value.nodes),
    compactField('partition', 'Partition', data.value.partition),
    compactField('qos', 'QOS', data.value.qos),
    compactField('exit-code', 'Exit Code', formatJobExitCode(data.value.exit_code)),
    fullField('name', 'Name', JobFieldRaw, { field: data.value.name }),
    fullField('comments', 'Comments', JobFieldComment, { comment: data.value.comment }),
    fullField('submit-line', 'Submit line', JobFieldRaw, {
      field: data.value.submit_line,
      monospace: true
    }),
    fullField('script', 'Script', JobFieldRaw, { field: data.value.script }),
    fullField('workdir', 'Working directory', JobFieldRaw, {
      field: data.value.working_directory,
      monospace: true
    }),
    fullField('tres-requested', 'Requested', JobResources, {
      tres: data.value.tres.requested,
      gpu: jobRequestedGPU(data.value)
    }),
    fullField('tres-allocated', 'Allocated', JobResources, {
      tres: data.value.tres.allocated,
      gpu: { count: jobAllocatedGPU(data.value), reliable: true }
    })
  ]
})

const compactFields = computed((): JobCompactField[] =>
  jobFieldsContent.value.filter((field): field is JobCompactField => field.layout === 'compact')
)

const fullFields = computed((): JobComponentField[] =>
  jobFieldsContent.value.filter((field): field is JobComponentField => field.layout === 'full')
)

const summaryItems = computed(() => {
  if (!data.value) return []
  const account = data.value.association.account
  const requestedGpu = jobRequestedGPU(data.value)
  const allocatedGpu = jobAllocatedGPU(data.value)
  return [
    {
      id: 'user',
      label: 'User',
      value: fmtField(data.value.user),
      to: { name: 'user', params: { cluster, user: data.value.user } }
    },
    {
      id: 'account',
      label: 'Account',
      value: fmtField(account),
      to: account ? { name: 'account', params: { cluster, account } } : undefined
    },
    { id: 'partition', label: 'Partition', value: fmtField(data.value.partition) },
    { id: 'nodes', label: 'Nodes', value: fmtField(data.value.nodes) },
    {
      id: 'tres-requested',
      label: 'Requested',
      value: `${data.value.tres.requested.length} TRES`,
      subtle: requestedGpu.count >= 0 ? `${requestedGpu.count} GPU requested` : 'GPU request unavailable'
    },
    {
      id: 'tres-allocated',
      label: 'Allocated',
      value: `${data.value.tres.allocated.length} TRES`,
      subtle: allocatedGpu >= 0 ? `${allocatedGpu} GPU allocated` : 'GPU allocation unavailable'
    },
    { id: 'exit-code', label: 'Exit Code', value: formatJobExitCode(data.value.exit_code) },
    {
      id: 'state-reason',
      label: 'State Reason',
      value: data.value.state.reason && data.value.state.reason !== 'None' ? data.value.state.reason : '-'
    }
  ]
})

const canEdit = computed(
  () =>
    runtimeStore.hasRoutePermission(cluster, 'jobs', 'edit') ||
    (runtimeStore.hasRoutePermission(cluster, 'jobs', 'edit', 'self') &&
      data.value?.user === authStore.username)
)

const canCancel = computed(
  () =>
    runtimeStore.hasRoutePermission(cluster, 'jobs', 'delete') ||
    (runtimeStore.hasRoutePermission(cluster, 'jobs', 'delete', 'self') &&
      data.value?.user === authStore.username)
)

async function saveJobEdits(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.update_job(cluster, id, {
      partition: payload.partition || undefined,
      qos: payload.qos || undefined,
      priority: payload.priority ? Number(payload.priority) : null,
      time_limit: payload.time_limit || undefined,
      comment: payload.comment || undefined
    })
    runtimeStore.reportInfo(`Job ${id} update requested.`)
    editOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

async function cancelJob(payload: Record<string, string>) {
  operationBusy.value = true
  operationError.value = null
  try {
    await gateway.cancel_job(cluster, id, {
      signal: payload.signal || undefined,
      reason: payload.reason || undefined
    })
    runtimeStore.reportInfo(`Job ${id} cancel requested.`)
    cancelOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

function highlightField(field: JobField) {
  displayTags.value[field].highlight = true
  setTimeout(() => {
    displayTags.value[field].highlight = false
  }, 2000)
}

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
)

watch(
  () => id,
  (newId) => {
    setParam(newId)
  }
)

watch(
  () => route.hash,
  (hash) => {
    if (!hash) return
    const field = hash.slice(1)
    if (isValidJobField(field)) {
      highlightField(field)
    }
  },
  { immediate: true }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="jobs"
    :cluster="cluster"
    :breadcrumb="[{ title: 'Jobs', routeName: 'jobs' }, { title: `Job ${id}` }]"
  >
    <div class="ui-page ui-page-readable">
      <JobBackButton :cluster="cluster" />

      <div class="ui-section-stack">
        <PageHeader
          kicker="Job Detail"
          :title="`Job ${id}`"
          description="Execution state, request metadata and allocated resources for the selected job."
        >
          <template #actions>
            <div class="flex flex-wrap items-center justify-end gap-3">
              <template v-if="data">
                <JobStatusBadge :status="data.state.current" :large="true" />
                <span
                  v-if="data.state.reason != 'None'"
                  class="ui-chip border-[rgba(216,75,80,0.18)] bg-[rgba(216,75,80,0.08)] text-[var(--color-brand-danger)]"
                >
                  {{ data.state.reason }}
                </span>
                <button v-if="canEdit" type="button" class="ui-button-secondary" @click="editOpen = true">
                  Edit
                </button>
                <button v-if="canCancel" type="button" class="ui-button-secondary" @click="cancelOpen = true">
                  Cancel
                </button>
              </template>
              <div
                v-else-if="initialLoading"
                class="h-10 w-28 animate-pulse rounded-full bg-[rgba(80,105,127,0.12)]"
              />
            </div>
          </template>
        </PageHeader>
        <DetailSummaryStrip v-if="data" :items="summaryItems" />

        <div
          v-if="!loaded && !unable"
          class="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)]"
        >
          <PanelSkeleton :rows="5" />
          <div class="ui-panel ui-section">
            <div class="mb-5">
              <h2 class="ui-panel-title">Job Configuration</h2>
              <p class="ui-panel-description mt-2">
                Core identity, command context and requested versus allocated resources.
              </p>
            </div>
            <DetailSkeletonList :rows="8" />
          </div>
        </div>

        <ErrorAlert v-if="unable"
          >Unable to retrieve job {{ id }} from cluster
          <span class="font-medium">{{ cluster }}</span></ErrorAlert
        >
        <div v-else-if="data">
          <div class="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)]">
            <div class="ui-panel ui-section">
              <div class="mb-5">
                <h2 class="ui-panel-title">Execution Timeline</h2>
                <p class="ui-panel-description mt-2">
                  Submission, scheduling and runtime milestones for this job.
                </p>
              </div>
              <JobProgress :job="data" />
            </div>

            <div class="ui-panel ui-section">
              <div class="mb-5">
                <h2 class="ui-panel-title">Job Configuration</h2>
                <p class="ui-panel-description mt-2">
                  Core identity, command context and requested versus allocated resources.
                </p>
              </div>
              <section class="space-y-6">
                <div>
                  <div class="mb-4">
                    <h3 class="ui-panel-title">Detailed Resources & Commands</h3>
                    <p class="ui-panel-description mt-1">
                      Longer fields stay expanded for readability and copy-friendly access.
                    </p>
                  </div>
                  <div class="ui-detail-list" data-testid="job-detail-list">
                    <dl>
                      <div
                        v-for="field in fullFields"
                        :key="field.id"
                        :id="field.id"
                        :class="[
                          displayTags[field.id].highlight
                            ? 'rounded-[18px] bg-[rgba(182,232,44,0.16)] px-4 sm:px-5'
                            : '',
                          'px-4 py-3 transition-colors duration-700 sm:grid sm:grid-cols-3 sm:gap-5 sm:px-0'
                        ]"
                        @mouseenter="displayTags[field.id].show = true"
                        @mouseleave="displayTags[field.id].show = false"
                      >
                        <dt class="text-sm leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
                        <a :href="`#${field.id}`" @click.prevent="highlightField(field.id)">
                            <span class="group inline-flex items-center gap-2 rounded-full px-1.5 py-1 transition-colors hover:bg-[rgba(182,232,44,0.12)]">
                              <span
                                :class="[
                                  displayTags[field.id].show
                                    ? 'border-[rgba(182,232,44,0.38)] bg-[rgba(182,232,44,0.18)] text-[var(--color-brand-blue)] shadow-[0_8px_16px_rgba(182,232,44,0.14)]'
                                    : 'border-transparent bg-transparent text-[var(--color-brand-muted)]/70',
                                  'inline-flex h-6 w-6 items-center justify-center rounded-full border transition-all duration-200'
                                ]"
                              >
                                <HashtagIcon class="h-3.5 w-3.5" aria-hidden="true" />
                              </span>
                              <span>{{ field.label }}</span>
                            </span>
                          </a>
                        </dt>
                        <component :is="field.component" v-bind="field.props" />
                      </div>
                    </dl>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ActionDialog
      :open="editOpen"
      title="Edit Job"
      :description="`Update job ${id} on ${cluster}.`"
      submit-label="Save changes"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        partition: data?.partition ?? '',
        qos: data?.qos ?? '',
        priority: data?.priority?.set ? String(data.priority.number) : '',
        time_limit: '',
        comment: data?.comment?.administrator || data?.comment?.job || ''
      }"
      :fields="[
        { key: 'partition', label: 'Partition' },
        { key: 'qos', label: 'QOS' },
        { key: 'priority', label: 'Priority', type: 'number' },
        { key: 'time_limit', label: 'Time limit' },
        { key: 'comment', label: 'Comment', type: 'textarea' }
      ]"
      @close="editOpen = false"
      @submit="saveJobEdits"
    />

    <ActionDialog
      :open="cancelOpen"
      title="Cancel Job"
      :description="`Cancel job ${id}. This action is destructive.`"
      submit-label="Cancel job"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'signal', label: 'Signal' },
        { key: 'reason', label: 'Reason', type: 'textarea' }
      ]"
      @close="cancelOpen = false"
      @submit="cancelJob"
    />
  </ClusterMainLayout>
</template>
