<!--
  Copyright (c) 2026 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { ChevronDownIcon, BarsArrowDownIcon, BarsArrowUpIcon } from '@heroicons/vue/20/solid'
import type { JobHistorySortCriterion, JobHistorySortOrder } from '@/composables/GatewayAPI'

const props = defineProps<{
  sort: JobHistorySortCriterion
  order: JobHistorySortOrder
}>()

const emit = defineEmits<{
  (e: 'update:sort', value: JobHistorySortCriterion): void
  (e: 'update:order', value: JobHistorySortOrder): void
}>()

const sortOptions: Array<{ name: string; type: JobHistorySortCriterion }> = [
  { name: 'Submit time', type: 'submit_time' },
  { name: '#ID', type: 'id' },
  { name: 'State', type: 'state' },
  { name: 'User', type: 'user' },
  { name: 'Priority', type: 'priority' },
  { name: 'Resources', type: 'resources' }
]

function sortSelected(newCriteria: JobHistorySortCriterion) {
  emit('update:sort', newCriteria)
}

function triggerSortOrder() {
  emit('update:order', props.order === 'asc' ? 'desc' : 'asc')
}
</script>
<template>
  <div class="inline-flex rounded-md shadow-sm">
    <button
      type="button"
      class="relative inline-flex items-center rounded-l-md bg-white px-2 py-1 text-sm font-semibold text-gray-600 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-10 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-700 hover:dark:bg-gray-700"
      @click="triggerSortOrder()"
    >
      <span class="sr-only">Order</span>
      <BarsArrowDownIcon v-if="order === 'asc'" class="size-4" />
      <BarsArrowUpIcon v-else class="size-4" />
    </button>
    <Menu as="div" class="relative -ml-px block">
      <MenuButton
        class="relative inline-flex items-center rounded-r-md bg-white px-2 py-2 text-sm text-gray-600 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-10 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-700 hover:dark:bg-gray-700"
      >
        Sort
        <ChevronDownIcon class="size-5" aria-hidden="true" />
      </MenuButton>
      <transition
        enter-active-class="transition ease-out duration-100"
        enter-from-class="transform opacity-0 scale-95"
        enter-to-class="transform opacity-100 scale-100"
        leave-active-class="transition ease-in duration-75"
        leave-from-class="transform opacity-100 scale-100"
        leave-to-class="transform opacity-0 scale-95"
      >
        <MenuItems
          class="absolute left-0 z-10 mt-2 -mr-1 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black/5 focus:outline-none dark:bg-gray-800"
        >
          <div class="py-1">
            <MenuItem v-for="option in sortOptions" :key="option.name" v-slot="{ active }">
              <a
                :class="[
                  option.type === sort
                    ? 'font-medium text-gray-900 dark:text-gray-100'
                    : 'text-gray-500 dark:text-gray-400',
                  active ? 'bg-gray-100 dark:bg-gray-700' : '',
                  'block px-4 py-2 text-sm'
                ]"
                @click="sortSelected(option.type)"
              >
                {{ option.name }}
              </a>
            </MenuItem>
          </div>
        </MenuItems>
      </transition>
    </Menu>
  </div>
</template>
