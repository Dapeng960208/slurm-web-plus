<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { ClusterTRES, JobHistoryRecord } from '@/composables/GatewayAPI'
import { formatJobExitCode, formatMemoryGB, splitJobHistoryState } from '@/composables/GatewayAPI'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import JobResources from '@/components/job/JobResources.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'
import DetailSkeletonList from '@/components/DetailSkeletonList.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import { HashtagIcon } from '@heroicons/vue/24/outline'
import { CheckIcon } from '@heroicons/vue/20/solid'
import DetailSummaryStrip from '@/components/details/DetailSummaryStrip.vue'
import { translate } from '@/i18n/translate'

const props = defineProps<{ cluster: string; id: number }>()

const route = useRoute()
const gateway = useGatewayAPI()
const { t } = useI18n()
const initialLoading = ref(true)
const error = ref<string | null>(null)
const job = ref<JobHistoryRecord | null>(null)

type HistoryField =
  | 'job-id'
  | 'name'
  | 'state-reason'
  | 'user'
  | 'group'
  | 'account'
  | 'partition'
  | 'qos'
  | 'priority'
  | 'nodes'
  | 'resources'
  | 'requested'
  | 'allocated'
  | 'tres-per-job'
  | 'tres-per-node'
  | 'gres'
  | 'max-memory'
  | 'used-cpu-cores-avg'
  | 'time-limit'
  | 'exit-code'
  | 'workdir'
  | 'command'

const allFields: HistoryField[] = [
  'job-id',
  'name',
  'state-reason',
  'user',
  'group',
  'account',
  'partition',
  'qos',
  'priority',
  'nodes',
  'resources',
  'requested',
  'allocated',
  'tres-per-job',
  'tres-per-node',
  'gres',
  'max-memory',
  'used-cpu-cores-avg',
  'time-limit',
  'exit-code',
  'workdir',
  'command'
]

type TimelineStep = {
  id: string
  label: string
  reached: boolean
  time: string | null
}

type HistoryFieldHelp = {
  title: string
  body: string
}

type HistoryFieldLayout = 'compact' | 'full'

type HistoryFieldBase = {
  id: HistoryField
  label: string
  layout: HistoryFieldLayout
  help?: HistoryFieldHelp
}

type HistoryTextField = HistoryFieldBase & {
  kind: 'text'
  value: string
  monospace?: boolean
}

type HistoryResourceField = HistoryFieldBase & {
  kind: 'resource'
  tres: ClusterTRES[] | null
  gpu: { count: number; reliable: boolean }
}

type HistoryFieldRow = HistoryTextField | HistoryResourceField

const compactFieldIds: HistoryField[] = [
  'job-id',
  'state-reason',
  'user',
  'group',
  'account',
  'partition',
  'qos',
  'priority',
  'nodes',
  'max-memory',
  'used-cpu-cores-avg',
  'time-limit',
  'exit-code'
]

function fieldLayout(id: HistoryField): HistoryFieldLayout {
  return compactFieldIds.includes(id) ? 'compact' : 'full'
}

const displayTags = ref<Record<HistoryField, { show: boolean; highlight: boolean }>>(
  Object.fromEntries(allFields.map((field) => [field, { show: false, highlight: false }])) as Record<
    HistoryField,
    { show: boolean; highlight: boolean }
  >
)

function highlightField(field: HistoryField) {
  displayTags.value[field].highlight = true
  setTimeout(() => {
    displayTags.value[field].highlight = false
  }, 2000)
}

function textField(
  id: HistoryField,
  label: string,
  value: string,
  monospace = false,
  help?: HistoryFieldHelp
): HistoryTextField {
  return { id, kind: 'text', label, layout: fieldLayout(id), value, monospace, help }
}

function resourceField(
  id: HistoryField,
  label: string,
  tres: ClusterTRES[] | null,
  gpu: { count: number; reliable: boolean }
): HistoryResourceField {
  return { id, kind: 'resource', label, layout: fieldLayout(id), tres, gpu }
}

function fmt(value: string | null | undefined) {
  return value ?? '-'
}

function fmtTime(value: string | null | undefined) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function fmtDuration(minutes: number | null | undefined) {
  if (minutes == null) return '-'
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return hours > 0
    ? t('pages.jobHistoryDetail.duration.hoursMinutes', { hours, minutes: remainingMinutes })
    : t('pages.jobHistoryDetail.duration.minutes', { minutes: remainingMinutes })
}

function fmtCpuCoresAvg(value: number | null | undefined) {
  if (value == null) return '-'
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value)
}

function hasValue(value: number | null | undefined) {
  return value !== null && value !== undefined
}

function countGPUTRESRequest(tresRequest: string): number {
  let total = 0
  for (const rawTres of tresRequest.split(',')) {
    let tres = rawTres.split('(')[0]
    tres = tres.replace('=', ':')
    const items = tres.split(':')
    if (!['gpu', 'gres/gpu'].includes(items[0])) continue
    const count = items.length === 2 ? parseInt(items[1]) : parseInt(items[2])
    if (!Number.isNaN(count)) total += count
  }
  return total
}

function historyRequestedGPU(record: JobHistoryRecord): { count: number; reliable: boolean } {
  if (record.tres_per_job) {
    return { count: countGPUTRESRequest(record.tres_per_job), reliable: true }
  }
  if (record.tres_per_node && hasValue(record.node_count)) {
    return {
      count: countGPUTRESRequest(record.tres_per_node) * (record.node_count ?? 0),
      reliable: true
    }
  }
  return { count: 0, reliable: true }
}

function historyAllocatedGPU(record: JobHistoryRecord): { count: number; reliable: boolean } {
  if (!record.gres_detail) return { count: 0, reliable: true }
  return { count: countGPUTRESRequest(record.gres_detail), reliable: true }
}

function timelineSteps(record: JobHistoryRecord): TimelineStep[] {
  const states = splitJobHistoryState(record.job_state)
  const completed = states.includes('COMPLETED')
  return [
    {
      id: 'submitted',
      label: t('pages.jobHistoryDetail.timeline.submitted'),
      time: record.submit_time,
      reached: !!record.submit_time
    },
    {
      id: 'eligible',
      label: t('pages.jobHistoryDetail.timeline.eligible'),
      time: record.eligible_time,
      reached: !!record.eligible_time
    },
    {
      id: 'scheduling',
      label: t('pages.jobHistoryDetail.timeline.scheduling'),
      time: record.last_sched_evaluation_time ?? record.start_time,
      reached: !!(record.last_sched_evaluation_time ?? record.start_time)
    },
    {
      id: 'running',
      label: t('pages.jobHistoryDetail.timeline.running'),
      time: record.start_time,
      reached: !!record.start_time
    },
    {
      id: 'completed',
      label: t('pages.jobHistoryDetail.timeline.completed'),
      time: completed ? record.end_time : null,
      reached: completed && !!record.end_time
    },
    {
      id: 'terminated',
      label: t('pages.jobHistoryDetail.timeline.terminated'),
      time: record.end_time,
      reached: !!record.end_time
    }
  ]
}

const fields = (record: JobHistoryRecord): HistoryFieldRow[] => [
  textField('job-id', 'pages.jobHistoryDetail.fields.jobId', String(record.job_id)),
  textField('name', 'pages.jobHistoryDetail.fields.name', fmt(record.job_name)),
  textField('state-reason', 'pages.jobHistoryDetail.fields.stateReason', fmt(record.state_reason)),
  textField('user', 'pages.jobHistoryDetail.fields.user', fmt(record.user_name)),
  textField('group', 'pages.jobHistoryDetail.fields.group', fmt(record.group)),
  textField('account', 'pages.jobHistoryDetail.fields.account', fmt(record.account)),
  textField('partition', 'pages.jobHistoryDetail.fields.partition', fmt(record.partition)),
  textField('qos', 'pages.jobHistoryDetail.fields.qos', fmt(record.qos)),
  textField('priority', 'pages.jobHistoryDetail.fields.priority', record.priority != null ? String(record.priority) : '-'),
  textField('nodes', 'pages.jobHistoryDetail.fields.nodes', fmt(record.nodes)),
  textField(
    'resources',
    'pages.jobHistoryDetail.fields.resources',
    [
      hasValue(record.node_count)
        ? t(
            record.node_count === 1
              ? 'pages.jobHistoryDetail.resourcesLabel.nodes'
              : 'pages.jobHistoryDetail.resourcesLabel.nodesPlural',
            { count: record.node_count }
          )
        : null,
      hasValue(record.cpus)
        ? t(
            record.cpus === 1
              ? 'pages.jobHistoryDetail.resourcesLabel.cpus'
              : 'pages.jobHistoryDetail.resourcesLabel.cpusPlural',
            { count: record.cpus }
          )
        : null,
      record.tres_req_str ?? null
    ]
      .filter(Boolean)
      .join(', ') || '-'
  ),
  resourceField('requested', 'pages.jobHistoryDetail.fields.requested', record.tres_requested, historyRequestedGPU(record)),
  resourceField('allocated', 'pages.jobHistoryDetail.fields.allocated', record.tres_allocated, historyAllocatedGPU(record)),
  textField('tres-per-job', 'pages.jobHistoryDetail.fields.tresPerJob', fmt(record.tres_per_job)),
  textField('tres-per-node', 'pages.jobHistoryDetail.fields.tresPerNode', fmt(record.tres_per_node)),
  textField('gres', 'pages.jobHistoryDetail.fields.gres', fmt(record.gres_detail)),
  textField('max-memory', 'pages.jobHistoryDetail.fields.maxMemory', formatMemoryGB(record.used_memory_gb)),
  textField(
    'used-cpu-cores-avg',
    'pages.jobHistoryDetail.fields.avgCpuCores',
    fmtCpuCoresAvg(record.used_cpu_cores_avg),
    false,
    {
      title: t('pages.jobHistoryDetail.helps.avgCpuCoresTitle'),
      body: t('pages.jobHistoryDetail.helps.avgCpuCoresBody')
    }
  ),
  textField('time-limit', 'pages.jobHistoryDetail.fields.timeLimit', fmtDuration(record.time_limit_minutes)),
  textField('exit-code', 'pages.jobHistoryDetail.fields.exitCode', formatJobExitCode(record.exit_code)),
  textField('workdir', 'pages.jobHistoryDetail.fields.workdir', fmt(record.working_directory), true),
  textField('command', 'pages.jobHistoryDetail.fields.command', fmt(record.command), true)
]

const timeline = computed(() => (job.value ? timelineSteps(job.value) : []))
const fullFields = computed(() =>
  job.value ? fields(job.value).filter((field) => field.layout === 'full') : []
)

const summaryItems = computed(() => {
  if (!job.value) return []
  return [
    { id: 'job-id', label: 'pages.jobHistoryDetail.summary.jobId', value: String(job.value.job_id) },
    { id: 'user', label: 'pages.jobHistoryDetail.summary.user', value: fmt(job.value.user_name) },
    { id: 'account', label: 'pages.jobHistoryDetail.summary.account', value: fmt(job.value.account) },
    { id: 'partition', label: 'pages.jobHistoryDetail.summary.partition', value: fmt(job.value.partition) },
    { id: 'nodes', label: 'pages.jobHistoryDetail.summary.nodes', value: fmt(job.value.nodes) },
    {
      id: 'max-memory',
      label: 'pages.jobHistoryDetail.summary.maxMemory',
      value: formatMemoryGB(job.value.used_memory_gb)
    },
    {
      id: 'used-cpu-cores-avg',
      label: 'pages.jobHistoryDetail.summary.avgCpuCores',
      value: fmtCpuCoresAvg(job.value.used_cpu_cores_avg),
      subtle: 'pages.jobHistoryDetail.summary.avgCpuCoresSubtle'
    },
    { id: 'exit-code', label: 'pages.jobHistoryDetail.summary.exitCode', value: formatJobExitCode(job.value.exit_code) }
  ]
})

async function loadJobHistory() {
  try {
    job.value = await gateway.job_history_detail(props.cluster, props.id)
    if (!route.hash) return
    const field = route.hash.slice(1) as HistoryField
    if (allFields.includes(field)) {
      highlightField(field)
    }
  } catch (caughtError: unknown) {
    error.value = caughtError instanceof Error ? caughtError.message : String(caughtError)
  } finally {
    initialLoading.value = false
  }
}

watch(
  () => [props.cluster, props.id],
  () => {
    job.value = null
    error.value = null
    initialLoading.value = true
    void loadJobHistory()
  },
  { immediate: true }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="jobs-history"
    :cluster="cluster"
    :breadcrumb="[
      { title: 'shell.mainMenu.jobsHistory', routeName: 'jobs-history' },
      { title: `Job ${job?.job_id ?? id}` }
    ]"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <JobBackButton :cluster="cluster" route-name="jobs-history" />

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
          <PageHeader
            kicker="pages.jobHistoryDetail.kicker"
            :title="`Job ${job?.job_id ?? id}`"
            description="pages.jobHistoryDetail.description"
          >
            <template #actions>
              <div v-if="job" class="flex flex-wrap items-center justify-end gap-3">
                <JobStatusBadge
                  :status="splitJobHistoryState(job.job_state)"
                  :large="true"
                />
                <RouterLink
                  :to="{ name: 'job', params: { cluster, id: job.job_id } }"
                  class="ui-button-secondary"
                >
                  {{ t('pages.jobHistoryDetail.liveJob') }}
                </RouterLink>
              </div>
              <div
                v-else-if="initialLoading"
                class="h-10 w-28 animate-pulse rounded-full bg-[rgba(80,105,127,0.12)]"
              />
            </template>
          </PageHeader>
          <DetailSummaryStrip v-if="job" :items="summaryItems" />

        <div
          v-if="initialLoading && !error"
          class="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)]"
        >
          <PanelSkeleton :rows="4" />
          <div class="ui-panel ui-section">
            <div class="mb-5">
              <h2 class="ui-panel-title">{{ t('pages.jobHistoryDetail.recordedFieldsTitle') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('pages.jobHistoryDetail.recordedFieldsDescription') }}
              </p>
            </div>
            <DetailSkeletonList :rows="8" />
          </div>
        </div>

      <ErrorAlert v-if="error">
        {{ t('pages.jobHistoryDetail.errors.unableToRetrieve', { id, error }) }}
      </ErrorAlert>
      <div v-else-if="job">
        <div class="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)]">
          <div class="ui-panel ui-section">
            <div class="mb-5">
              <h2 class="ui-panel-title">{{ t('pages.jobHistoryDetail.executionTimelineTitle') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('pages.jobHistoryDetail.executionTimelineDescription') }}
              </p>
            </div>

            <ol role="list" class="overflow-hidden" data-testid="job-history-timeline-list">
              <li
                v-for="(step, idx) in timeline"
                :key="step.id"
                :id="`step-${step.id}`"
                :data-state="step.reached ? 'complete' : 'pending'"
                :class="[idx !== timeline.length - 1 ? 'pb-10' : '', 'relative']"
              >
                <template v-if="step.reached">
                  <div
                    v-if="idx !== timeline.length - 1"
                    class="absolute top-4 left-4 mt-0.5 -ml-px h-full w-0.5 bg-[linear-gradient(180deg,rgba(182,232,44,0.95),rgba(152,201,31,0.9))]"
                    aria-hidden="true"
                  />
                  <div class="group relative flex items-start">
                    <span class="flex h-9 items-center">
                      <span
                        class="relative z-10 flex h-9 w-9 items-center justify-center rounded-[16px] border border-white/70 bg-[linear-gradient(135deg,rgba(182,232,44,0.96),rgba(152,201,31,0.92))] shadow-[0_16px_30px_rgba(182,232,44,0.2)]"
                      >
                        <CheckIcon class="h-5 w-5 text-[var(--color-brand-deep)]" aria-hidden="true" />
                      </span>
                    </span>
                    <span class="ml-4 flex min-w-0 flex-col">
                      <span class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{
                        step.label
                      }}</span>
                      <span class="text-xs text-[var(--color-brand-muted)]">{{ fmtTime(step.time) }}</span>
                    </span>
                  </div>
                </template>
                <template v-else>
                  <div
                    v-if="idx !== timeline.length - 1"
                    class="absolute top-4 left-4 mt-0.5 -ml-px h-full w-0.5 bg-[rgba(80,105,127,0.18)]"
                    aria-hidden="true"
                  />
                  <div class="group relative flex items-start">
                    <span class="flex h-9 items-center" aria-hidden="true">
                      <span
                        class="relative z-10 flex h-9 w-9 items-center justify-center rounded-[16px] border border-[rgba(80,105,127,0.14)] bg-[rgba(239,244,246,0.9)] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]"
                      >
                        <span class="h-2.5 w-2.5 rounded-full bg-[rgba(80,105,127,0.16)]" />
                      </span>
                    </span>
                    <span class="ml-4 flex min-w-0 flex-col">
                      <span class="text-sm font-medium text-[var(--color-brand-muted)]">{{
                        step.label
                      }}</span>
                      <span class="text-xs text-[var(--color-brand-muted)]">-</span>
                    </span>
                  </div>
                </template>
              </li>
            </ol>
          </div>

          <div class="ui-panel ui-section">
            <div class="mb-5">
              <h2 class="ui-panel-title">{{ t('pages.jobHistoryDetail.recordedFieldsTitle') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('pages.jobHistoryDetail.recordedFieldsDescription') }}
              </p>
            </div>
            <section class="space-y-6">
              <div>
                <div class="mb-4">
                  <h3 class="ui-panel-title">{{ t('pages.jobHistoryDetail.detailedTitle') }}</h3>
                  <p class="ui-panel-description mt-1">
                    {{ t('pages.jobHistoryDetail.detailedDescription') }}
                  </p>
                </div>
                <div class="ui-detail-list" data-testid="job-history-detail-list">
                  <dl>
                    <div
                      v-for="field in fullFields"
                      :key="field.id"
                      :id="field.id"
                      :class="[
                        displayTags[field.id as HistoryField].highlight
                          ? 'rounded-[18px] bg-[rgba(182,232,44,0.16)] px-4 sm:px-5'
                          : '',
                        'px-4 py-3 transition-colors duration-700 sm:grid sm:grid-cols-3 sm:gap-5 sm:px-0'
                      ]"
                      @mouseenter="displayTags[field.id as HistoryField].show = true"
                      @mouseleave="displayTags[field.id as HistoryField].show = false"
                    >
                      <dt class="text-sm leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
                        <a
                          :href="`#${field.id}`"
                          @click.prevent="highlightField(field.id as HistoryField)"
                        >
                          <span class="group inline-flex items-center gap-2 rounded-full px-1.5 py-1 transition-colors hover:bg-[rgba(182,232,44,0.12)]">
                            <span
                              :class="[
                                displayTags[field.id as HistoryField].show
                                  ? 'border-[rgba(182,232,44,0.38)] bg-[rgba(182,232,44,0.18)] text-[var(--color-brand-blue)] shadow-[0_8px_16px_rgba(182,232,44,0.14)]'
                                  : 'border-transparent bg-transparent text-[var(--color-brand-muted)]/70',
                                'inline-flex h-6 w-6 items-center justify-center rounded-full border transition-all duration-200'
                              ]"
                            >
                              <HashtagIcon class="h-3.5 w-3.5" aria-hidden="true" />
                            </span>
                            <span>{{ translate(field.label) }}</span>
                          </span>
                        </a>
                      </dt>
                      <JobResources
                        v-if="field.kind === 'resource' && field.tres && field.tres.length > 0"
                        :tres="field.tres"
                        :gpu="field.gpu"
                      />
                      <dd
                        v-else-if="field.kind === 'resource'"
                        class="mt-1 text-sm leading-6 text-[var(--color-brand-muted)] sm:col-span-2 sm:mt-0"
                      >
                        -
                      </dd>
                      <dd
                        v-else-if="field.id === 'user' && field.value !== '-'"
                        class="mt-1 text-sm leading-6 sm:col-span-2 sm:mt-0"
                      >
                        <RouterLink
                          :to="{ name: 'user', params: { cluster, user: field.value } }"
                          class="ui-user-link"
                        >
                          {{ field.value }}
                        </RouterLink>
                      </dd>
                      <dd
                        v-else
                        :class="[
                          field.monospace ? 'font-mono text-xs break-all' : 'text-sm',
                          'mt-1 leading-6 text-[var(--color-brand-muted)] sm:col-span-2 sm:mt-0'
                        ]"
                      >
                        {{ field.value }}
                      </dd>
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
  </ClusterMainLayout>
</template>
