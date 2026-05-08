<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import type { UserToolActivityRecord } from '@/composables/GatewayAPI'

const props = defineProps<{
  tools: UserToolActivityRecord[]
  totalCompletedJobs?: number
}>()

const sortedTools = computed(() =>
  [...props.tools].sort(
    (left, right) =>
      right.jobs - left.jobs ||
      (right.max_memory_gb ?? 0) - (left.max_memory_gb ?? 0) ||
      left.tool.localeCompare(right.tool)
  )
)

const completedJobsTotal = computed(() => {
  if ((props.totalCompletedJobs ?? 0) > 0) return props.totalCompletedJobs ?? 0
  return sortedTools.value.reduce((total, tool) => total + tool.jobs, 0)
})

const maxJobs = computed(() => Math.max(...sortedTools.value.map((tool) => tool.jobs), 0))

function formatGb(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  return `${value.toFixed(value >= 10 ? 1 : 2)} GB`
}

function formatCpu(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  return `${value.toFixed(1)} cores`
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return '--'
  if (seconds < 60) return `${Math.round(seconds)} sec`
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function formatHours(hours: number | null | undefined): string {
  if (hours == null || Number.isNaN(hours)) return '--'
  return `${hours.toFixed(hours >= 10 ? 1 : 2)} h`
}

function formatRuntime(tool: UserToolActivityRecord): string {
  if (tool.avg_runtime_hours != null) return formatHours(tool.avg_runtime_hours)
  return formatDuration(tool.avg_runtime_seconds)
}

function shareLabel(tool: UserToolActivityRecord): string {
  if (!completedJobsTotal.value) return '0%'
  return `${Math.round((tool.jobs / completedJobsTotal.value) * 100)}%`
}

function jobsBarWidth(tool: UserToolActivityRecord): string {
  if (!maxJobs.value) return '0%'
  return `${(tool.jobs / maxJobs.value) * 100}%`
}

function memorySpread(tool: UserToolActivityRecord): string {
  const parts: string[] = []
  if (tool.avg_memory_gb != null) parts.push(`avg ${formatGb(tool.avg_memory_gb)}`)
  if (tool.max_memory_gb != null) parts.push(`peak ${formatGb(tool.max_memory_gb)}`)
  if (tool.median_memory_gb != null) parts.push(`median ${formatGb(tool.median_memory_gb)}`)
  return parts.join(' / ') || 'No memory sample'
}
</script>

<template>
  <div class="ui-table-shell overflow-x-auto" data-testid="user-tool-analysis-table">
    <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
      <div class="flex flex-wrap justify-end gap-2">
        <div class="flex flex-wrap gap-2">
          <span class="ui-chip">{{ sortedTools.length }} tool{{ sortedTools.length === 1 ? '' : 's' }}</span>
          <span class="ui-chip">{{ completedJobsTotal }} completed job{{ completedJobsTotal === 1 ? '' : 's' }}</span>
        </div>
      </div>
    </div>

    <div class="inline-block min-w-full align-middle">
      <table class="ui-table min-w-[1100px]">
        <thead>
          <tr>
            <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Tool</th>
            <th scope="col" class="px-3 py-3.5 text-left">Workload</th>
            <th scope="col" class="px-3 py-3.5 text-left">Avg Memory</th>
            <th scope="col" class="px-3 py-3.5 text-left">Max Memory</th>
            <th scope="col" class="px-3 py-3.5 text-left">Median Memory</th>
            <th scope="col" class="px-3 py-3.5 text-left">Avg Runtime</th>
            <th scope="col" class="px-3 py-3.5 text-left">Avg CPU</th>
            <th scope="col" class="px-3 py-3.5 text-left">Jobs</th>
          </tr>
        </thead>
        <tbody class="text-sm text-[var(--color-brand-muted)]">
          <tr
            v-for="(tool, index) in sortedTools"
            :key="tool.tool"
            :data-testid="`tool-analysis-row-${tool.tool}`"
          >
            <td class="py-4 pr-3 pl-6 align-top">
              <div class="flex items-start gap-3">
                <span
                  class="inline-flex h-8 min-w-8 items-center justify-center rounded-full bg-[rgba(196,120,53,0.14)] px-2 text-xs font-semibold text-[var(--color-brand-ink-strong)]"
                >
                  {{ index + 1 }}
                </span>
                <div class="min-w-0">
                  <div class="font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ tool.tool }}
                  </div>
                  <div class="mt-1 text-xs text-[var(--color-brand-muted)]">
                    {{ memorySpread(tool) }}
                  </div>
                </div>
              </div>
            </td>
            <td class="px-3 py-4 align-top">
              <div class="min-w-[180px]">
                <div class="flex items-center justify-between gap-3 text-xs font-semibold text-[var(--color-brand-ink-strong)]">
                  <span>{{ shareLabel(tool) }}</span>
                  <span>{{ tool.jobs }} job{{ tool.jobs === 1 ? '' : 's' }}</span>
                </div>
                <div class="mt-2 h-2.5 overflow-hidden rounded-full bg-[rgba(80,105,127,0.12)]">
                  <div
                    class="h-full rounded-full bg-[linear-gradient(90deg,rgba(196,120,53,0.92),rgba(110,182,168,0.9))]"
                    :style="{ width: jobsBarWidth(tool) }"
                  />
                </div>
              </div>
            </td>
            <td class="px-3 py-4 align-top font-medium text-[var(--color-brand-ink-strong)]">
              {{ formatGb(tool.avg_memory_gb) }}
            </td>
            <td class="px-3 py-4 align-top font-medium text-[var(--color-brand-ink-strong)]">
              {{ formatGb(tool.max_memory_gb) }}
            </td>
            <td class="px-3 py-4 align-top font-medium text-[var(--color-brand-ink-strong)]">
              {{ formatGb(tool.median_memory_gb) }}
            </td>
            <td class="px-3 py-4 align-top">
              {{ formatRuntime(tool) }}
            </td>
            <td class="px-3 py-4 align-top">
              {{ formatCpu(tool.avg_cpu_cores) }}
            </td>
            <td class="px-3 py-4 align-top">
              <span class="ui-chip">{{ tool.jobs }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
