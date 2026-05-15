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
import { useI18n } from 'vue-i18n'
import { HashtagIcon } from '@heroicons/vue/24/outline'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { formatJobExitCode, jobAllocatedGPU, jobRequestedGPU } from '@/composables/GatewayAPI'
import type { ClusterIndividualJob } from '@/composables/GatewayAPI'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobProgress from '@/components/job/JobProgress.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import DetailSkeletonList from '@/components/DetailSkeletonList.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import JobFieldRaw from '@/components/job/JobFieldRaw.vue'
import JobFieldComment from '@/components/job/JobFieldComment.vue'
import JobResources from '@/components/job/JobResources.vue'
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

type JobLink = {
  to: RouteLocationRaw
  kind?: 'partition' | 'default'
}

type JobTextField = {
  id: JobField
  label: string
  kind: 'text'
  value: string
  monospace?: boolean
  link?: JobLink
}

type JobComponentField = {
  id: JobField
  label: string
  kind: 'component'
  component: Component
  props: object
}

type JobFieldRow = JobTextField | JobComponentField

function isValidJobField(key: string): key is JobField {
  return typeof key === 'string' && jobsFields.includes(key as JobField)
}

const { data, unable, loaded, initialLoading, setCluster, setParam } =
  useClusterDataPoller<ClusterIndividualJob>(cluster, 'job', 5000, id)

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

function fmtField(value: string | number | null | undefined) {
  if (value == null || value === '') return '-'
  return String(value)
}

function textField(
  id: JobField,
  label: string,
  value: string | number | null | undefined,
  options?: { link?: JobLink; monospace?: boolean }
): JobTextField {
  return {
    id,
    label,
    kind: 'text',
    value: fmtField(value),
    link: options?.link,
    monospace: options?.monospace
  }
}

function componentField(
  id: JobField,
  label: string,
  component: Component,
  props: object
): JobComponentField {
  return { id, label, kind: 'component', component, props }
}

const jobFieldsContent = computed((): JobFieldRow[] => {
  if (!data.value) return []

  const account = data.value.association.account
  const partitionLink =
    data.value.partition && data.value.partition !== '-'
      ? {
          to: { name: 'partition', params: { cluster, partition: data.value.partition } },
          kind: 'partition' as const
        }
      : undefined

  return [
    textField('user', 'pages.job.fields.user', data.value.user, {
      link: data.value.user
        ? { to: { name: 'user', params: { cluster, user: data.value.user } } }
        : undefined
    }),
    textField('group', 'pages.job.fields.group', data.value.group),
    textField('account', 'pages.job.fields.account', account, {
      link: account ? { to: { name: 'account', params: { cluster, account } } } : undefined
    }),
    textField('wckeys', 'pages.job.fields.wckeys', data.value.wckey?.wckey),
    textField('priority', 'pages.job.fields.priority', data.value.priority?.number),
    textField('nodes', 'pages.job.fields.nodes', data.value.nodes),
    textField('partition', 'pages.job.fields.partition', data.value.partition, {
      link: partitionLink
    }),
    textField('qos', 'pages.job.fields.qos', data.value.qos),
    textField('exit-code', 'pages.job.fields.exitCode', formatJobExitCode(data.value.exit_code)),
    componentField('name', 'pages.job.fields.name', JobFieldRaw, { field: data.value.name }),
    componentField('comments', 'pages.job.fields.comments', JobFieldComment, {
      comment: data.value.comment
    }),
    componentField('submit-line', 'pages.job.fields.submitLine', JobFieldRaw, {
      field: data.value.submit_line,
      monospace: true
    }),
    componentField('script', 'pages.job.fields.script', JobFieldRaw, { field: data.value.script }),
    componentField('workdir', 'pages.job.fields.workingDirectory', JobFieldRaw, {
      field: data.value.working_directory,
      monospace: true
    }),
    componentField('tres-requested', 'pages.job.fields.requested', JobResources, {
      tres: data.value.tres.requested,
      gpu: jobRequestedGPU(data.value)
    }),
    componentField('tres-allocated', 'pages.job.fields.allocated', JobResources, {
      tres: data.value.tres.allocated,
      gpu: { count: jobAllocatedGPU(data.value), reliable: true }
    })
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
                  <button
                    v-if="canEdit"
                    type="button"
                    class="ui-button-warning"
                    @click="editOpen = true"
                  >
                    {{ t('pages.job.actions.edit') }}
                  </button>
                  <button
                    v-if="canCancel"
                    type="button"
                    class="ui-button-danger"
                    @click="cancelOpen = true"
                  >
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

          <ErrorAlert v-if="unable">
            {{ t('pages.job.errors.unableToRetrieve', { jobId: id, cluster }) }}
          </ErrorAlert>

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

                <div class="ui-detail-list" data-testid="job-detail-list">
                  <dl>
                    <div
                      v-for="field in jobFieldsContent"
                      :id="field.id"
                      :key="field.id"
                      :class="[
                        'ui-detail-row',
                        displayTags[field.id].highlight ? 'ui-detail-item-highlight' : ''
                      ]"
                      @mouseenter="displayTags[field.id].show = true"
                      @mouseleave="displayTags[field.id].show = false"
                    >
                      <dt class="ui-detail-term">
                        <a
                          :href="`#${field.id}`"
                          class="ui-detail-anchor"
                          @click.prevent="highlightField(field.id)"
                        >
                          <span
                            :class="[
                              displayTags[field.id].show
                                ? 'ui-detail-anchor-icon ui-detail-anchor-icon-active'
                                : 'ui-detail-anchor-icon'
                            ]"
                          >
                            <HashtagIcon class="h-3.5 w-3.5" aria-hidden="true" />
                          </span>
                          <span>{{ t(field.label) }}</span>
                        </a>
                      </dt>
                      <dd class="ui-detail-value">
                        <PartitionLinkChip
                          v-if="
                            field.kind === 'text' &&
                            field.link?.kind === 'partition' &&
                            field.value !== '-'
                          "
                          :cluster="cluster"
                          :partition="field.value"
                        />
                        <RouterLink
                          v-else-if="field.kind === 'text' && field.link?.to && field.value !== '-'"
                          :to="field.link.to"
                          class="ui-inline-link ui-detail-rich-text"
                        >
                          {{ field.value }}
                        </RouterLink>
                        <pre
                          v-else-if="field.kind === 'text' && field.monospace"
                          class="ui-detail-codeblock"
                        >{{ field.value }}</pre>
                        <p v-else-if="field.kind === 'text'" class="ui-detail-rich-text">
                          {{ field.value }}
                        </p>
                        <component v-else :is="field.component" v-bind="field.props" />
                      </dd>
                    </div>
                  </dl>
                </div>
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
