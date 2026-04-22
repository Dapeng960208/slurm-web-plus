<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import type { ClusterIndividualJob } from '@/composables/GatewayAPI'
import JobProgressComment from '@/components/job/JobProgressComment.vue'
import { CheckIcon } from '@heroicons/vue/20/solid'

const { job } = defineProps<{ job: ClusterIndividualJob }>()

const current = computed((): [number, boolean] => {
  const now = new Date()
  if (job.time.end && new Date(job.time.end * 1000) < now) {
    return [5, false]
  }
  if (job.time.start) {
    if (new Date(job.time.start * 1000) < now) {
      return [2, true]
    } else {
      return [2, false]
    }
  }
  if (job.time.eligible && new Date(job.time.eligible * 1000) < now) {
    return [1, true]
  }
  if (job.time.submission && new Date(job.time.submission * 1000) < now) {
    return [0, true]
  }
  return [0, false]
})

function capitalize(step: string) {
  return step.charAt(0).toUpperCase() + step.slice(1)
}

const steps = ['submitted', 'eligible', 'scheduling', 'running', 'completing', 'terminated']
</script>

<template>
  <ol v-if="current" role="list" class="overflow-hidden">
    <li
      v-for="(step, stepIdx) in steps"
      :key="step"
      :class="[stepIdx !== steps.length - 1 ? 'pb-10' : '', 'relative']"
      :id="'step-' + step"
    >
      <template v-if="current[0] >= stepIdx">
        <div
          v-if="stepIdx !== steps.length - 1"
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
              capitalize(step)
            }}</span>
            <JobProgressComment :job="job" :step="step" />
          </span>
        </div>
      </template>
      <template v-else-if="current[0] + 1 == stepIdx && current[1]">
        <div
          v-if="stepIdx !== steps.length - 1"
          class="absolute top-4 left-4 mt-0.5 -ml-px h-full w-0.5 bg-[rgba(80,105,127,0.18)]"
          aria-hidden="true"
        />
        <div class="group relative flex items-start" aria-current="step">
          <span class="flex h-9 items-center" aria-hidden="true">
            <span
              class="relative z-10 flex h-9 w-9 items-center justify-center rounded-[16px] border border-[rgba(182,232,44,0.34)] bg-[rgba(182,232,44,0.14)] shadow-[0_12px_24px_rgba(182,232,44,0.12)]"
            >
              <span class="h-2.5 w-2.5 rounded-full bg-[var(--color-slurmweb-dark)]" />
            </span>
          </span>
          <span class="ml-4 flex min-w-0 flex-col">
            <span class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{
              capitalize(step)
            }}</span>
            <JobProgressComment :job="job" :step="step" />
          </span>
        </div>
      </template>
      <template v-else>
        <div
          v-if="stepIdx !== steps.length - 1"
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
              capitalize(step)
            }}</span>
            <JobProgressComment :job="job" :step="step" />
          </span>
        </div>
      </template>
    </li>
  </ol>
</template>
