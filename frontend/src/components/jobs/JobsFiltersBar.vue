<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import type { FunctionalComponent } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import type { JobsViewFilters } from '@/stores/runtime/jobs'
import {
  FunnelIcon,
  BoltIcon,
  RectangleGroupIcon,
  UserIcon,
  UsersIcon,
  SwatchIcon
} from '@heroicons/vue/20/solid'

const runtimeStore = useRuntimeStore()

const activeFiltersGroups: Array<{
  group: string
  list: keyof JobsViewFilters
  icon: FunctionalComponent
  removeCallback: (this: typeof runtimeStore.jobs, filter: string) => void
  colors: { badge: string; button: string }
}> = [
  {
    group: 'state',
    list: 'states',
    icon: BoltIcon,
    removeCallback: runtimeStore.jobs.removeStateFilter,
    colors: {
      badge: 'border-[rgba(80,105,127,0.16)] bg-[rgba(80,105,127,0.92)]',
      button: 'text-white/70 hover:bg-white/14 hover:text-white'
    }
  },
  {
    group: 'user',
    list: 'users',
    icon: UserIcon,
    removeCallback: runtimeStore.jobs.removeUserFilter,
    colors: {
      badge: 'border-[rgba(123,191,31,0.18)] bg-[rgba(123,191,31,0.94)]',
      button: 'text-white/70 hover:bg-white/14 hover:text-white'
    }
  },
  {
    group: 'account',
    list: 'accounts',
    icon: UsersIcon,
    removeCallback: runtimeStore.jobs.removeAccountFilter,
    colors: {
      badge: 'border-[rgba(239,155,40,0.18)] bg-[rgba(239,155,40,0.92)]',
      button: 'text-white/70 hover:bg-white/14 hover:text-white'
    }
  },
  {
    group: 'qos',
    list: 'qos',
    icon: SwatchIcon,
    removeCallback: runtimeStore.jobs.removeQosFilter,
    colors: {
      badge: 'border-[rgba(80,105,127,0.16)] bg-[linear-gradient(135deg,rgba(80,105,127,0.96),rgba(108,122,128,0.96))]',
      button: 'text-white/70 hover:bg-white/14 hover:text-white'
    }
  },
  {
    group: 'partition',
    list: 'partitions',
    icon: RectangleGroupIcon,
    removeCallback: runtimeStore.jobs.removePartitionFilter,
    colors: {
      badge: 'border-[rgba(32,42,53,0.18)] bg-[rgba(32,42,53,0.94)]',
      button: 'text-white/70 hover:bg-white/14 hover:text-white'
    }
  }
]
</script>

<template>
  <!-- Active filters -->
  <div
    v-show="!runtimeStore.jobs.emptyFilters()"
    class="ui-panel-soft rounded-[24px] px-4 py-4 sm:px-6"
  >
    <div class="mx-auto sm:flex sm:items-center">
      <h3 class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
        <FunnelIcon class="mr-1 h-4 w-4" />
        <span class="sr-only">Filters active</span>
      </h3>

      <div
        aria-hidden="true"
        class="hidden h-5 w-px bg-[rgba(80,105,127,0.16)] sm:ml-4 sm:block"
      />

      <div class="mt-2 sm:mt-0 sm:ml-4">
        <div class="-m-1 flex flex-wrap items-center">
          <template v-for="activeFilterGroup in activeFiltersGroups" :key="activeFilterGroup.group">
            <span
              v-for="activeFilter in runtimeStore.jobs.filters[activeFilterGroup.list]"
              :key="activeFilter"
              :class="[
                activeFilterGroup.colors.badge,
                'm-1 inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-medium text-white shadow-[var(--shadow-soft)]'
              ]"
            >
              <component :is="activeFilterGroup.icon" class="mr-1 h-4 w-4"></component>
              <span>{{ activeFilter }}</span>
              <button
                type="button"
                :class="[
                  activeFilterGroup.colors.button,
                  'ml-1 inline-flex h-4 w-4 shrink-0 rounded-full p-1'
                ]"
                @click="activeFilterGroup.removeCallback.call(runtimeStore.jobs, activeFilter)"
              >
                <span class="sr-only"
                  >Remove filter for {{ activeFilterGroup.group }}:{{ activeFilter }}</span
                >
                <svg class="h-2 w-2" stroke="currentColor" fill="none" viewBox="0 0 8 8">
                  <path stroke-linecap="round" stroke-width="1.5" d="M1 1l6 6m0-6L1 7" />
                </svg>
              </button>
            </span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
