<!--
  Copyright (c) 2023-2024 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { JobHistoryRecord } from '@/composables/GatewayAPI'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
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
  | 'partition' | 'qos' | 'priority' | 'nodes' | 'resources'
  | 'tres-per-job' | 'tres-per-node' | 'gres' | 'time-limit' | 'exit-code'
  | 'workdir' | 'command' | 'submit-time' | 'start-time' | 'end-time' | 'snapshot-time'

const ALL_FIELDS: HistoryField[] = [
  'job-id', 'name', 'state-reason', 'user', 'group', 'account',
  'partition', 'qos', 'priority', 'nodes', 'resources',
  'tres-per-job', 'tres-per-node', 'gres', 'time-limit', 'exit-code',
  'workdir', 'command', 'submit-time', 'start-time', 'end-time', 'snapshot-time'
]

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

function fmt(v: string | null | undefined) {
  return v ?? '-'
}

function fmtTime(v: string | null | undefined) {
  if (!v) return '-'
  return new Date(v).toLocaleString()
}

function fmtDuration(minutes: number | null | undefined) {
  if (!minutes) return '-'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

/** Build a simple timeline from the history record timestamps */
function timelineSteps(j: JobHistoryRecord) {
  const steps = [
    { label: 'Submitted', time: j.submit_time },
    { label: 'Started', time: j.start_time },
    { label: 'Terminated', time: j.end_time }
  ]
  const now = new Date()
  let reached = 0
  for (let i = 0; i < steps.length; i++) {
    if (steps[i].time && new Date(steps[i].time as string) <= now) reached = i + 1
  }
  return { steps, reached }
}

const fields = (j: JobHistoryRecord) => [
  { id: 'job-id', label: 'Job ID', value: String(j.job_id) },
  { id: 'name', label: 'Name', value: fmt(j.job_name) },
  { id: 'state-reason', label: 'State Reason', value: fmt(j.state_reason) },
  { id: 'user', label: 'User', value: fmt(j.user_name) },
  { id: 'group', label: 'Group', value: fmt(j.group) },
  { id: 'account', label: 'Account', value: fmt(j.account) },
  { id: 'partition', label: 'Partition', value: fmt(j.partition) },
  { id: 'qos', label: 'QOS', value: fmt(j.qos) },
  { id: 'priority', label: 'Priority', value: j.priority != null ? String(j.priority) : '-' },
  { id: 'nodes', label: 'Nodes', value: fmt(j.nodes) },
  {
    id: 'resources',
    label: 'Resources',
    value: [
      j.node_count ? `${j.node_count} node${j.node_count > 1 ? 's' : ''}` : null,
      j.cpus ? `${j.cpus} CPU${j.cpus > 1 ? 's' : ''}` : null,
      j.tres_req_str ?? null
    ]
      .filter(Boolean)
      .join(', ') || '-'
  },
  { id: 'tres-per-job', label: 'TRES/Job', value: fmt(j.tres_per_job) },
  { id: 'tres-per-node', label: 'TRES/Node', value: fmt(j.tres_per_node) },
  { id: 'gres', label: 'GRES', value: fmt(j.gres_detail) },
  { id: 'time-limit', label: 'Time Limit', value: fmtDuration(j.time_limit_minutes) },
  { id: 'exit-code', label: 'Exit Code', value: fmt(j.exit_code) },
  { id: 'workdir', label: 'Working Directory', value: fmt(j.working_directory), monospace: true },
  { id: 'command', label: 'Command', value: fmt(j.command), monospace: true },
  { id: 'submit-time', label: 'Submit Time', value: fmtTime(j.submit_time) },
  { id: 'start-time', label: 'Start Time', value: fmtTime(j.start_time) },
  { id: 'end-time', label: 'End Time', value: fmtTime(j.end_time) },
  { id: 'snapshot-time', label: 'Snapshot Time', value: fmtTime(j.snapshot_time) }
]

onMounted(async () => {
  try {
    job.value = await gateway.job_history_detail(props.cluster, props.id)
    /* If a field id is in route hash, highlight it after load */
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
      Loading job history record {{ id }}…
    </div>

    <div v-else-if="job">
      <!-- Title row -->
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
          <JobStatusBadge :status="job.job_state ? [job.job_state] : ['UNKNOWN']" :large="true" />
        </div>
      </div>

      <div class="flex flex-wrap">
        <!-- Timeline (left column) -->
        <div class="w-full lg:w-1/3">
          <ol role="list" class="overflow-hidden">
            <li
              v-for="(step, idx) in timelineSteps(job).steps"
              :key="step.label"
              :class="[idx !== timelineSteps(job).steps.length - 1 ? 'pb-10' : '', 'relative']"
            >
              <!-- connector line -->
              <div
                v-if="idx !== timelineSteps(job).steps.length - 1"
                :class="[
                  idx < timelineSteps(job).reached
                    ? 'bg-slurmweb dark:bg-slurmweb-dark'
                    : 'bg-gray-300 dark:bg-gray-700',
                  'absolute top-4 left-4 mt-0.5 -ml-px h-full w-0.5'
                ]"
                aria-hidden="true"
              />
              <!-- completed step -->
              <template v-if="idx < timelineSteps(job).reached">
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
              <!-- future step -->
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

        <!-- Fields (right column) -->
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
                <dd
                  :class="[
                    field.monospace ? 'font-mono text-xs break-all' : 'text-sm',
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
