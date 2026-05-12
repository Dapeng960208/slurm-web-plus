<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Component } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import PartitionLinkChip from '@/components/PartitionLinkChip.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'

const { cluster, id } = defineProps<{ cluster: string; id: number }>()

const route = useRoute()
const { t } = useI18n()
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
    compactField('group', 'pages.job.fields.group', data.value.group),
    compactField(
      'account',
      'pages.job.fields.account',
      account,
      account ? { name: 'account', params: { cluster, account } } : undefined
    ),
    compactField('user', 'pages.job.fields.user', data.value.user, {
      name: 'user',
      params: { cluster, user: data.value.user }
    }),
    compactField('wckeys', 'pages.job.fields.wckeys', data.value.wckey.wckey),
    compactField('priority', 'pages.job.fields.priority', data.value.priority.number),
    compactField('nodes', 'pages.job.fields.nodes', data.value.nodes),
    compactField(
      'partition',
      'pages.job.fields.partition',
      data.value.partition,
      data.value.partition
        ? { name: 'partition', params: { cluster, partition: data.value.partition } }
        : undefined
    ),
    compactField('qos', 'pages.job.fields.qos', data.value.qos),
    compactField(
      'exit-code',
      'pages.job.fields.exitCode',
      formatJobExitCode(data.value.exit_code)
    ),
    fullField('name', 'pages.job.fields.name', JobFieldRaw, { field: data.value.name }),
    fullField('comments', 'pages.job.fields.comments', JobFieldComment, {
      comment: data.value.comment
    }),
    fullField('submit-line', 'pages.job.fields.submitLine', JobFieldRaw, {
      field: data.value.submit_line,
      monospace: true
    }),
    fullField('script', 'pages.job.fields.script', JobFieldRaw, { field: data.value.script }),
    fullField('workdir', 'pages.job.fields.workingDirectory', JobFieldRaw, {
      field: data.value.working_directory,
      monospace: true
    }),
    fullField('tres-requested', 'pages.job.fields.requested', JobResources, {
      tres: data.value.tres.requested,
      gpu: jobRequestedGPU(data.value)
    }),
    fullField('tres-allocated', 'pages.job.fields.allocated', JobResources, {
      tres: data.value.tres.allocated,
      gpu: { count: jobAllocatedGPU(data.value), reliable: true }
    })
  ]
})

const fullFields = computed((): JobComponentField[] =>
  jobFieldsContent.value.filter((field): field is JobComponentField => field.layout === 'full')
)

const compactFields = computed((): JobCompactField[] =>
  jobFieldsContent.value.filter((field): field is JobCompactField => field.layout === 'compact')
)

const summaryItems = computed(() => {
  if (!data.value) return []
  const account = data.value.association.account
  const requestedGpu = jobRequestedGPU(data.value)
  const allocatedGpu = jobAllocatedGPU(data.value)
  return [
    {
      id: 'user',
      label: 'pages.job.summary.user',
      value: fmtField(data.value.user),
      to: { name: 'user', params: { cluster, user: data.value.user } }
    },
    {
      id: 'account',
      label: 'pages.job.summary.account',
      value: fmtField(account),
      to: account ? { name: 'account', params: { cluster, account } } : undefined
    },
    {
      id: 'partition',
      label: 'pages.job.summary.partition',
      value: fmtField(data.value.partition),
      to: data.value.partition
        ? { name: 'partition', params: { cluster, partition: data.value.partition } }
        : undefined
    },
    { id: 'nodes', label: 'pages.job.summary.nodes', value: fmtField(data.value.nodes) },
    {
      id: 'tres-requested',
      label: 'pages.job.summary.requested',
      value: `${data.value.tres.requested.length} TRES`,
      subtle:
        requestedGpu.count >= 0
          ? t('pages.job.summary.requestedSubtle', { count: requestedGpu.count })
          : t('pages.job.summary.requestedUnavailable'),
      translateSubtle: false
    },
    {
      id: 'tres-allocated',
      label: 'pages.job.summary.allocated',
      value: `${data.value.tres.allocated.length} TRES`,
      subtle:
        allocatedGpu >= 0
          ? t('pages.job.summary.allocatedSubtle', { count: allocatedGpu })
          : t('pages.job.summary.allocatedUnavailable'),
      translateSubtle: false
    },
    {
      id: 'exit-code',
      label: 'pages.job.summary.exitCode',
      value: formatJobExitCode(data.value.exit_code)
    },
    {
      id: 'state-reason',
      label: 'pages.job.summary.stateReason',
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
    const memoryPerCpu = parsePositiveInteger(payload.memory_per_cpu_mb)
    await gateway.update_job(cluster, id, {
      partition: payload.partition || undefined,
      qos: payload.qos || undefined,
      priority: payload.priority ? Number(payload.priority) : null,
      time_limit: payload.time_limit || undefined,
      comment: payload.comment || undefined,
      memory_per_cpu:
        memoryPerCpu == null
          ? undefined
          : { set: true, infinite: false, number: memoryPerCpu }
    })
    runtimeStore.reportInfo(t('pages.job.notifications.updateRequested', { jobId: id }))
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
    runtimeStore.reportInfo(t('pages.job.notifications.cancelRequested', { jobId: id }))
    cancelOpen.value = false
  } catch (error: unknown) {
    operationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationBusy.value = false
  }
}

function parsePositiveInteger(value: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(t('pages.jobs.dialogs.edit.errors.invalidMemoryPerCpu'))
  }
  return parsed
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
    :breadcrumb="[
      { title: 'shell.mainMenu.jobs', routeName: 'jobs' },
      { title: t('pages.job.title', { jobId: id }) }
    ]"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <JobBackButton :cluster="cluster" />

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
        <PageHeader
          kicker="pages.job.kicker"
          title="pages.job.title"
          :title-params="{ jobId: id }"
          description="pages.job.description"
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
                <button v-if="canEdit" type="button" class="ui-button-warning" @click="editOpen = true">
                  {{ t('pages.job.actions.edit') }}
                </button>
                <button v-if="canCancel" type="button" class="ui-button-danger" @click="cancelOpen = true">
                  {{ t('pages.job.actions.cancel') }}
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
              <h2 class="ui-panel-title">{{ t('pages.job.panels.configurationTitle') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('pages.job.panels.configurationDescription') }}
              </p>
            </div>
            <DetailSkeletonList :rows="8" />
          </div>
        </div>

        <ErrorAlert v-if="unable"
          >{{ t('pages.job.errors.unableToRetrieve', { jobId: id, cluster }) }}</ErrorAlert
        >
        <div v-else-if="data">
          <div class="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)]">
            <div class="ui-panel ui-section">
              <div class="mb-5">
                <h2 class="ui-panel-title">{{ t('pages.job.panels.executionTimelineTitle') }}</h2>
                <p class="ui-panel-description mt-2">
                  {{ t('pages.job.panels.executionTimelineDescription') }}
                </p>
              </div>
              <JobProgress :job="data" />
            </div>

            <div class="ui-panel ui-section">
              <div class="mb-5">
                <h2 class="ui-panel-title">{{ t('pages.job.panels.configurationTitle') }}</h2>
                <p class="ui-panel-description mt-2">
                  {{ t('pages.job.panels.configurationDescription') }}
                </p>
              </div>
              <section class="space-y-6">
                <div>
                  <div class="mb-4">
                    <h3 class="ui-panel-title">{{ t('pages.job.panels.detailedTitle') }}</h3>
                    <p class="ui-panel-description mt-1">
                      {{ t('pages.job.panels.detailedDescription') }}
                    </p>
                  </div>
                  <div class="ui-detail-compact-grid" data-testid="job-detail-compact-grid">
                    <div
                      v-for="field in compactFields"
                      :key="field.id"
                      class="ui-detail-compact-card"
                    >
                      <div class="ui-detail-compact-label">{{ t(field.label) }}</div>
                      <div class="ui-detail-compact-value">
                        <PartitionLinkChip
                          v-if="field.id === 'partition' && field.value !== '-'"
                          :cluster="cluster"
                          :partition="field.value"
                        />
                        <RouterLink
                          v-else-if="field.to && field.value !== '-'"
                          :to="field.to"
                          class="ui-inline-link"
                        >
                          {{ field.value }}
                        </RouterLink>
                        <template v-else>
                          {{ field.value }}
                        </template>
                      </div>
                    </div>
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
                              <span>{{ t(field.label) }}</span>
                            </span>
                          </a>
                        </dt>
                        <dd
                          v-if="field.id === 'partition' && data?.partition"
                          class="mt-1 sm:col-span-2 sm:mt-0"
                        >
                          <PartitionLinkChip :cluster="cluster" :partition="data.partition" />
                        </dd>
                        <component v-else :is="field.component" v-bind="field.props" />
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
    </div>

    <ActionDialog
      :open="editOpen"
      title="pages.job.dialogs.edit.title"
      description="pages.job.dialogs.edit.description"
      :description-params="{ jobId: id, cluster }"
      submit-label="pages.job.dialogs.edit.submit"
      :loading="operationBusy"
      :error="operationError"
      :initial-values="{
        partition: data?.partition ?? '',
        qos: data?.qos ?? '',
        priority: data?.priority?.set ? String(data.priority.number) : '',
        memory_per_cpu_mb: '',
        time_limit: '',
        comment: data?.comment?.administrator || data?.comment?.job || ''
      }"
      :fields="[
        { key: 'partition', label: 'pages.jobs.dialogs.edit.fields.partition' },
        { key: 'qos', label: 'pages.jobs.dialogs.edit.fields.qos' },
        { key: 'priority', label: 'pages.jobs.dialogs.edit.fields.priority', type: 'number' },
        {
          key: 'memory_per_cpu_mb',
          label: 'pages.jobs.dialogs.edit.fields.memoryPerCpuMb',
          type: 'number',
          hint: 'pages.jobs.dialogs.edit.fields.memoryPerCpuHint',
          tooltip: 'pages.jobs.dialogs.edit.fields.memoryPerCpuTooltip'
        },
        { key: 'time_limit', label: 'pages.jobs.dialogs.edit.fields.timeLimit' },
        { key: 'comment', label: 'pages.jobs.dialogs.edit.fields.comment', type: 'textarea' }
      ]"
      @close="editOpen = false"
      @submit="saveJobEdits"
    />

    <ActionDialog
      :open="cancelOpen"
      title="pages.job.dialogs.cancel.title"
      description="pages.job.dialogs.cancel.description"
      :description-params="{ jobId: id }"
      submit-label="pages.job.dialogs.cancel.submit"
      :loading="operationBusy"
      :error="operationError"
      :fields="[
        { key: 'signal', label: 'pages.jobs.dialogs.cancel.fields.signal' },
        { key: 'reason', label: 'pages.jobs.dialogs.cancel.fields.reason', type: 'textarea' }
      ]"
      @close="cancelOpen = false"
      @submit="cancelJob"
    />
  </ClusterMainLayout>
</template>
