<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import type { UserToolActivityRecord } from '@/composables/GatewayAPI'
import { getMBHumanUnit } from '@/composables/GatewayAPI'

const { tools } = defineProps<{
  tools: UserToolActivityRecord[]
}>()

function formatDuration(seconds: number | null): string {
  if (seconds == null || Number.isNaN(seconds)) return 'N/A'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

const maxMemory = computed(() =>
  Math.max(...tools.map((tool) => tool.avg_max_memory_mb ?? 0), 0)
)

const maxJobs = computed(() => Math.max(...tools.map((tool) => tool.jobs), 0))

function memoryWidth(tool: UserToolActivityRecord): string {
  if (!maxMemory.value) return '0%'
  return `${((tool.avg_max_memory_mb ?? 0) / maxMemory.value) * 100}%`
}

function jobsWidth(tool: UserToolActivityRecord): string {
  if (!maxJobs.value) return '0%'
  return `${(tool.jobs / maxJobs.value) * 100}%`
}
</script>

<template>
  <div class="ui-tool-chart">
    <article
      v-for="tool in tools"
      :key="tool.tool"
      class="ui-tool-chart-row"
      :data-testid="`tool-chart-${tool.tool}`"
    >
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div class="font-semibold text-[var(--color-brand-ink-strong)]">
            {{ tool.tool }}
          </div>
          <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
            {{ tool.jobs }} completed job(s)
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <span class="ui-chip">
            {{ tool.avg_max_memory_mb != null ? getMBHumanUnit(tool.avg_max_memory_mb) : 'N/A' }}
          </span>
          <span class="ui-chip">{{ tool.jobs }} jobs</span>
        </div>
      </div>

      <div class="mt-4 grid gap-4 xl:grid-cols-2">
        <div>
          <div class="mb-2 flex items-center justify-between gap-3">
            <span class="ui-stat-label">Average Max Memory</span>
            <span class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
              {{ tool.avg_max_memory_mb != null ? getMBHumanUnit(tool.avg_max_memory_mb) : 'N/A' }}
            </span>
          </div>
          <div class="ui-tool-chart-track">
            <div
              class="ui-tool-chart-fill ui-tool-chart-fill-memory"
              :style="{ width: memoryWidth(tool) }"
            />
          </div>
        </div>

        <div>
          <div class="mb-2 flex items-center justify-between gap-3">
            <span class="ui-stat-label">Completed Jobs</span>
            <span class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
              {{ tool.jobs }}
            </span>
          </div>
          <div class="ui-tool-chart-track">
            <div
              class="ui-tool-chart-fill ui-tool-chart-fill-jobs"
              :style="{ width: jobsWidth(tool) }"
            />
          </div>
        </div>
      </div>

      <div class="mt-4 grid gap-2 text-sm text-[var(--color-brand-muted)] sm:grid-cols-3">
        <div>
          CPU:
          {{ tool.avg_cpu_cores != null ? `${tool.avg_cpu_cores.toFixed(1)} cores` : 'N/A' }}
        </div>
        <div>Runtime: {{ formatDuration(tool.avg_runtime_seconds) }}</div>
        <div>
          Peak reference:
          {{ maxMemory > 0 ? getMBHumanUnit(maxMemory) : 'N/A' }}
        </div>
      </div>
    </article>
  </div>
</template>
