<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import type { JobHistoryFilters } from '@/composables/GatewayAPI'
import {
  FunnelIcon,
  BoltIcon,
  RectangleGroupIcon,
  MagnifyingGlassIcon,
  UserIcon,
  UsersIcon,
  SwatchIcon,
  HashtagIcon,
  CalendarIcon
} from '@heroicons/vue/20/solid'

const props = defineProps<{ filters: JobHistoryFilters }>()
const emit = defineEmits<{
  (e: 'search'): void
  (e: 'update:filters', filters: JobHistoryFilters): void
}>()

function removeFilter(key: keyof JobHistoryFilters) {
  const nextFilters: JobHistoryFilters = {
    ...props.filters
  }
  if (key === 'job_id') {
    nextFilters.job_id = undefined
  } else {
    ;(nextFilters as Record<string, unknown>)[key] = ''
  }
  emit('update:filters', nextFilters)
  emit('search')
}

interface ActiveFilter {
  key: keyof JobHistoryFilters
  label: string
  icon: unknown
}

function activeFilters(): ActiveFilter[] {
  const result: ActiveFilter[] = []
  if (props.filters.keyword) result.push({ key: 'keyword', label: props.filters.keyword, icon: MagnifyingGlassIcon })
  if (props.filters.state) result.push({ key: 'state', label: props.filters.state, icon: BoltIcon })
  if (props.filters.user) result.push({ key: 'user', label: props.filters.user, icon: UserIcon })
  if (props.filters.account) result.push({ key: 'account', label: props.filters.account, icon: UsersIcon })
  if (props.filters.partition) result.push({ key: 'partition', label: props.filters.partition, icon: RectangleGroupIcon })
  if (props.filters.qos) result.push({ key: 'qos', label: props.filters.qos, icon: SwatchIcon })
  if (props.filters.job_id) result.push({ key: 'job_id', label: String(props.filters.job_id), icon: HashtagIcon })
  if (props.filters.start) result.push({ key: 'start', label: `from ${props.filters.start}`, icon: CalendarIcon })
  if (props.filters.end) result.push({ key: 'end', label: `to ${props.filters.end}`, icon: CalendarIcon })
  return result
}
</script>

<template>
  <div v-show="activeFilters().length > 0" class="ui-panel-soft rounded-[24px] px-4 py-4 sm:px-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div class="flex items-center gap-2 text-sm font-semibold text-[var(--color-brand-ink-strong)]">
        <FunnelIcon class="h-4 w-4" />
        Active filters
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span
          v-for="filter in activeFilters()"
          :key="filter.key"
          class="inline-flex items-center gap-2 rounded-full border border-[rgba(182,232,44,0.34)] bg-[rgba(182,232,44,0.13)] px-3 py-1.5 text-xs font-medium text-[var(--color-brand-blue)]"
        >
          <component :is="filter.icon" class="h-4 w-4" />
          <span>{{ filter.label }}</span>
          <button
            type="button"
            class="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/80 text-[var(--color-brand-muted)] transition hover:bg-white hover:text-[var(--color-brand-ink-strong)]"
            @click="removeFilter(filter.key)"
          >
            <span class="sr-only">Remove filter {{ filter.key }}</span>
            <svg class="h-2.5 w-2.5" stroke="currentColor" fill="none" viewBox="0 0 8 8">
              <path stroke-linecap="round" stroke-width="1.5" d="M1 1l6 6m0-6L1 7" />
            </svg>
          </button>
        </span>
      </div>
    </div>
  </div>
</template>
