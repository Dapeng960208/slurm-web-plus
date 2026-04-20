<!--
  Copyright (c) 2023-2024 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { ClusterTRES, JobHistoryRecord } from '@/composables/GatewayAPI'
import { splitJobHistoryState } from '@/composables/GatewayAPI'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import JobResources from '@/components/job/JobResources.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { HashtagIcon } from '@heroicons/vue/24/outline'
import { CheckIcon } from '@heroicons/vue/20/solid'

const props = defineProps<{ cluster: string; id: number }>()

const route = useRoute()
const gateway = useGatewayAPI()
const loading = ref(true)
const error = ref<string | null>(null)
const job = ref<JobHistoryRecord | null>(null)

type HistoryField =
  | 'job-id' | 'name' | 'state-reason' | 'user' | 'group' | 'account'
  | 'partition' | 'qos' | 'priority' | 'nodes' | 'resources' | 'requested'
  | 'allocated' | 'tres-per-job' | 'tres-per-node' | 'gres'
  | 'time-limit' | 'exit-code' | 'workdir' | 'command'

const ALL_FIELDS: HistoryField[] = [
  'job-id', 'name', 'state-reason', 'user', 'group', 'account',
  'partition', 'qos', 'priority', 'nodes', 'resources', 'requested',
  'allocated', 'tres-per-job', 'tres-per-node', 'gres',
  'time-limit', 'exit-code', 'workdir', 'command'
]

type TimelineStep = {
  id: string
  label: string
  reached: boolean
  time: string | null
}

type HistoryTextField = {
  id: HistoryField
  kind: 'text'
  label: string
  value: string
  monospace?: boolean
}

type HistoryResourceField = {
  id: HistoryField
  kind: 'resource'
  label: string
  tres: ClusterTRES[] | null
  gpu: { count: number; reliable: boolean }
}

type HistoryFieldRow = HistoryTextField | HistoryResourceField

const displayTags = ref<Record<HistoryField, { show: boolean; highlight: boolean }>>(
  Object.fromEntries(ALL_FIELDS.map((f) => [f, { show: false, highlight: false }])) as Record<
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
  monospace = false
): HistoryTextField {
  return { id, kind: 'text', label, value, monospace }
}

function resourceField(
  id: HistoryField,
  label: string,
  tres: ClusterTRES[] | null,
  gpu: { count: number; reliable: boolean }
): HistoryResourceField {
  return { id, kind: 'resource', label, tres, gpu }
}

function fmt(v: string | null | undefined) {
  return v ?? '-'
}

function fmtTime(v: string | null | undefined) {
  if (!v) return '-'
  return new Date(v).toLocaleString()
}

function fmtDuration(minutes: number | null | undefined) {
  if (minutes == null) return '-'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
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

function historyRequestedGPU(j: JobHistoryRecord): { count: number; reliable: boolean } {
  if (j.tres_per_job) {
    return { count: countGPUTRESRequest(j.tres_per_job), reliable: true }
  }
  if (j.tres_per_node && hasValue(j.node_count)) {
    return { count: countGPUTRESRequest(j.tres_per_node) * (j.node_count ?? 0), reliable: true }
  }
  return { count: 0, reliable: true }
}

function historyAllocatedGPU(j: JobHistoryRecord): { count: number; reliable: boolean } {
  if (!j.gres_detail) return { count: 0, reliable: true }
  return { count: countGPUTRESRequest(j.gres_detail), reliable: true }
}

function timelineSteps(j: JobHistoryRecord): TimelineStep[] {
  const states = splitJobHistoryState(j.job_state)
  const completed = states.includes('COMPLETED')
  return [
    { id: 'submitted', label: 'Submitted', time: j.submit_time, reached: !!j.submit_time },
    { id: 'eligible', label: 'Eligible', time: j.eligible_time, reached: !!j.eligible_time },
    {
      id: 'scheduling',
      label: 'Scheduling',
      time: j.last_sched_evaluation_time ?? j.start_time,
      reached: !!(j.last_sched_evaluation_time ?? j.start_time)
    },
    { id: 'running', label: 'Running', time: j.start_time, reached: !!j.start_time },
    {
      id: 'completed',
      label: 'Completed',
      time: completed ? j.end_time : null,
      reached: completed && !!j.end_time
    },
    {
      id: 'terminated',
      label: 'Terminated',
      time: j.end_time,
      reached: !!j.end_time
    }
  ]
}

const fields = (j: JobHistoryRecord): HistoryFieldRow[] => [
  textField('job-id', 'Job ID', String(j.job_id)),
  textField('name', 'Name', fmt(j.job_name)),
  textField('state-reason', 'State Reason', fmt(j.state_reason)),
  textField('user', 'User', fmt(j.user_name)),
  textField('group', 'Group', fmt(j.group)),
  textField('account', 'Account', fmt(j.account)),
  textField('partition', 'Partition', fmt(j.partition)),
  textField('qos', 'QOS', fmt(j.qos)),
  textField('priority', 'Priority', j.priority != null ? String(j.priority) : '-'),
  textField('nodes', 'Nodes', fmt(j.nodes)),
  textField(
    'resources',
    'Resources',
    [
      hasValue(j.node_count) ? `${j.node_count} node${j.node_count > 1 ? 's' : ''}` : null,
      hasValue(j.cpus) ? `${j.cpus} CPU${j.cpus > 1 ? 's' : ''}` : null,
      j.tres_req_str ?? null
    ]
      .filter(Boolean)
      .join(', ') || '-'
  ),
  resourceField('requested', 'Requested', j.tres_requested, historyRequestedGPU(j)),
  resourceField('allocated', 'Allocated', j.tres_allocated, historyAllocatedGPU(j)),
  textField('tres-per-job', 'TRES/Job', fmt(j.tres_per_job)),
  textField('tres-per-node', 'TRES/Node', fmt(j.tres_per_node)),
  textField('gres', 'GRES', fmt(j.gres_detail)),
  textField('time-limit', 'Time Limit', fmtDuration(j.time_limit_minutes)),
  textField('exit-code', 'Exit Code', fmt(j.exit_code)),
  textField('workdir', 'Working Directory', fmt(j.working_directory), true),
  textField('command', 'Command', fmt(j.command), true)
]

const timeline = computed(() => (job.value ? timelineSteps(job.value) : []))

onMounted(async () => {
  try {
    job.value = await gateway.job_history_detail(props.cluster, props.id)
    if (route.hash) {
      const field = route.hash.slice(1) as HistoryField
      if (ALL_FIELDS.includes(field)) {
        highlightField(field)
      }
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <ClusterMainLayout
    menu-entry="jobs-history"
    :cluster="cluster"
    :breadcrumb="[
      { title: 'Jobs History', routeName: 'jobs-history' },
      { title: `Job ${job?.job_id ?? id}` }
    ]"
  >
    <JobBackButton :cluster="cluster" route-name="jobs-history" />

    <ErrorAlert v-if="error">Unable to retrieve job history record {{ id }}: {{ error }}</ErrorAlert>

    <div v-else-if="loading" class="text-gray-400 sm:pl-6 lg:pl-8">
      <LoadingSpinner :size="5" />
      Loading job history record {{ id }}...
    </div>

    <div v-else-if="job">
      <div class="flex justify-between">
        <div class="px-4 pb-8 sm:px-0">
          <h3 class="text-base leading-7 font-semibold text-gray-900 dark:text-gray-100">
            Job {{ job.job_id }}
          </h3>
          <p class="mt-1 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-300">
            Historical job record
          </p>
        </div>
        <div>
          <JobStatusBadge :status="splitJobHistoryState(job.job_state)" :large="true" />
        </div>
      </div>

      <div class="flex flex-wrap">
        <div class="w-full lg:w-1/3">
          <ol role="list" class="overflow-hidden">
            <li
              v-for="(step, idx) in timeline"
              :key="step.id"
              :id="`step-${step.id}`"
              :class="[idx !== timeline.length - 1 ? 'pb-10' : '', 'relative']"
            >
              <div
                v-if="idx !== timeline.length - 1"
                :class="[
                  step.reached
                    ? 'bg-slurmweb dark:bg-slurmweb-dark'
                    : 'bg-gray-300 dark:bg-gray-700',
                  'absolute top-4 left-4 mt-0.5 -ml-px h-full w-0.5'
                ]"
                aria-hidden="true"
              />
              <template v-if="step.reached">
                <div class="group relative flex items-start">
                  <span class="flex h-9 items-center">
                    <span
                      class="bg-slurmweb dark:bg-slurmweb-dark relative z-10 flex h-8 w-8 items-center justify-center rounded-full"
                    >
                      <CheckIcon class="h-5 w-5 text-white" aria-hidden="true" />
                    </span>
                  </span>
                  <span class="ml-4 flex min-w-0 flex-col">
                    <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{
                      step.label
                    }}</span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">{{
                      fmtTime(step.time)
                    }}</span>
                  </span>
                </div>
              </template>
              <template v-else>
                <div class="group relative flex items-start">
                  <span class="flex h-9 items-center" aria-hidden="true">
                    <span
                      class="relative z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 border-gray-300 bg-white dark:border-gray-700 dark:bg-gray-900"
                    >
                      <span class="h-2.5 w-2.5 rounded-full bg-transparent" />
                    </span>
                  </span>
                  <span class="ml-4 flex min-w-0 flex-col">
                    <span class="text-sm font-medium text-gray-500 dark:text-gray-600">{{
                      step.label
                    }}</span>
                    <span class="text-xs text-gray-400 dark:text-gray-500">-</span>
                  </span>
                </div>
              </template>
            </li>
          </ol>
        </div>

        <div class="w-full lg:w-2/3">
          <div class="border-t border-gray-100 dark:border-gray-700">
            <dl class="divide-y divide-gray-100 dark:divide-gray-700">
              <div
                v-for="field in fields(job)"
                :key="field.id"
                :id="field.id"
                :class="[
                  displayTags[field.id as HistoryField].highlight
                    ? 'bg-slurmweb-light dark:bg-slurmweb-dark'
                    : '',
                  'px-4 py-2 transition-colors duration-700 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-0'
                ]"
                @mouseenter="displayTags[field.id as HistoryField].show = true"
                @mouseleave="displayTags[field.id as HistoryField].show = false"
              >
                <dt class="text-sm leading-6 font-medium text-gray-900 dark:text-gray-100">
                  <a
                    :href="`#${field.id}`"
                    @click.prevent="highlightField(field.id as HistoryField)"
                  >
                    <span class="flex items-center">
                      <HashtagIcon
                        :class="[
                          displayTags[field.id as HistoryField].show ? 'opacity-100' : 'opacity-0',
                          'mr-2 -ml-5 h-3 w-3 text-gray-500 transition-opacity'
                        ]"
                        aria-hidden="true"
                      />
                      {{ field.label }}
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
                  class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300"
                >
                  -
                </dd>
                <dd
                  v-else
                  :class="[
                    field.monospace
                        ? 'font-mono text-xs break-all'
                        : 'text-sm',
                    'mt-1 leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300'
                  ]"
                >
                  {{ field.value }}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>
