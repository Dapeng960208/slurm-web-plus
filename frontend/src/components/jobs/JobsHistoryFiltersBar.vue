<!--
  Copyright (c) 2023-2024 Rackslab

  This file is part of Slurm-web.

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
const emit = defineEmits<{ (e: 'search'): void }>()

function removeFilter(key: keyof JobHistoryFilters) {
  if (key === 'job_id') {
    props.filters.job_id = undefined
  } else {
    ;(props.filters as Record<string, unknown>)[key] = ''
  }
  emit('search')
}

interface ActiveFilter {
  key: keyof JobHistoryFilters
  label: string
  value: string
  icon: unknown
  colors: { badge: string; button: string }
}

function activeFilters(): ActiveFilter[] {
  const result: ActiveFilter[] = []
  if (props.filters.keyword)
    result.push({
      key: 'keyword',
      label: props.filters.keyword,
      value: props.filters.keyword,
      icon: MagnifyingGlassIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-slate-600 dark:bg-slate-500',
        button: 'text-slate-600 hover:bg-slate-600 hover:text-slate-700'
      }
    })
  if (props.filters.state)
    result.push({
      key: 'state',
      label: props.filters.state,
      value: props.filters.state,
      icon: BoltIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-gray-600 dark:bg-gray-500',
        button: 'text-gray-400 hover:bg-gray-700 hover:text-gray-500'
      }
    })
  if (props.filters.user)
    result.push({
      key: 'user',
      label: props.filters.user,
      value: props.filters.user,
      icon: UserIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-emerald-500',
        button: 'text-emerald-600 hover:bg-emerald-600 hover:text-emerald-700'
      }
    })
  if (props.filters.account)
    result.push({
      key: 'account',
      label: props.filters.account,
      value: props.filters.account,
      icon: UsersIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-yellow-500',
        button: 'text-yellow-600 hover:bg-yellow-600 hover:text-yellow-700'
      }
    })
  if (props.filters.partition)
    result.push({
      key: 'partition',
      label: props.filters.partition,
      value: props.filters.partition,
      icon: RectangleGroupIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-amber-700',
        button: 'text-amber-800 hover:bg-amber-800 hover:text-amber-900'
      }
    })
  if (props.filters.qos)
    result.push({
      key: 'qos',
      label: props.filters.qos,
      value: props.filters.qos,
      icon: SwatchIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-purple-500',
        button: 'text-purple-600 hover:bg-purple-600 hover:text-purple-700'
      }
    })
  if (props.filters.job_id)
    result.push({
      key: 'job_id',
      label: String(props.filters.job_id),
      value: String(props.filters.job_id),
      icon: HashtagIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-sky-500',
        button: 'text-sky-600 hover:bg-sky-600 hover:text-sky-700'
      }
    })
  if (props.filters.start)
    result.push({
      key: 'start',
      label: `from ${props.filters.start}`,
      value: props.filters.start,
      icon: CalendarIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-rose-500',
        button: 'text-rose-600 hover:bg-rose-600 hover:text-rose-700'
      }
    })
  if (props.filters.end)
    result.push({
      key: 'end',
      label: `to ${props.filters.end}`,
      value: props.filters.end,
      icon: CalendarIcon,
      colors: {
        badge: 'border-gray-200 dark:border-gray-400 bg-rose-500',
        button: 'text-rose-600 hover:bg-rose-600 hover:text-rose-700'
      }
    })
  return result
}
</script>

<template>
  <div v-show="activeFilters().length > 0" class="bg-gray-100 dark:bg-gray-800">
    <div class="mx-auto px-4 py-3 sm:flex sm:items-center sm:px-6 lg:px-8">
      <h3 class="text-sm font-medium text-gray-500">
        <FunnelIcon class="mr-1 h-4 w-4" />
        <span class="sr-only">Filters active</span>
      </h3>
      <div aria-hidden="true" class="hidden h-5 w-px bg-gray-300 sm:ml-4 sm:block" />
      <div class="mt-2 sm:mt-0 sm:ml-4">
        <div class="-m-1 flex flex-wrap items-center">
          <span
            v-for="f in activeFilters()"
            :key="f.key"
            :class="[
              f.colors.badge,
              'm-1 inline-flex items-center rounded-full border py-1.5 pr-2 pl-3 text-xs font-medium text-white'
            ]"
          >
            <component :is="f.icon" class="mr-1 h-4 w-4" />
            <span>{{ f.label }}</span>
            <button
              type="button"
              :class="[f.colors.button, 'ml-1 inline-flex h-4 w-4 shrink-0 rounded-full p-1']"
              @click="removeFilter(f.key)"
            >
              <span class="sr-only">Remove filter {{ f.key }}</span>
              <svg class="h-2 w-2" stroke="currentColor" fill="none" viewBox="0 0 8 8">
                <path stroke-linecap="round" stroke-width="1.5" d="M1 1l6 6m0-6L1 7" />
              </svg>
            </button>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
