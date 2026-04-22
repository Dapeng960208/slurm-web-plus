<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

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
  <div class="inline-flex rounded-full shadow-[var(--shadow-soft)]">
    <button
      type="button"
      class="relative inline-flex items-center rounded-l-full bg-white px-3 py-2 text-sm font-semibold text-[var(--color-brand-muted)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset hover:bg-[rgba(182,232,44,0.12)]"
      @click="triggerSortOrder()"
    >
      <span class="sr-only">Order</span>
      <BarsArrowDownIcon v-if="order === 'asc'" class="size-4" />
      <BarsArrowUpIcon v-else class="size-4" />
    </button>
    <Menu as="div" class="relative -ml-px block">
      <MenuButton
        class="relative inline-flex items-center rounded-r-full bg-white px-4 py-2 text-sm font-semibold text-[var(--color-brand-ink-strong)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset hover:bg-[rgba(182,232,44,0.12)]"
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
          class="absolute left-0 z-10 mt-2 w-56 origin-top-right rounded-[22px] border border-white/80 bg-white/95 p-2 shadow-[var(--shadow-panel)] backdrop-blur-lg focus:outline-none"
        >
          <MenuItem v-for="option in sortOptions" :key="option.name" v-slot="{ active }">
            <button
              type="button"
              :class="[
                option.type === sort
                  ? 'bg-[rgba(182,232,44,0.14)] text-[var(--color-brand-ink-strong)]'
                  : 'text-[var(--color-brand-muted)]',
                active ? 'bg-[rgba(239,244,246,0.9)]' : '',
                'block w-full rounded-[16px] px-4 py-2 text-left text-sm font-medium'
              ]"
              @click="sortSelected(option.type)"
            >
              {{ option.name }}
            </button>
          </MenuItem>
        </MenuItems>
      </transition>
    </Menu>
  </div>
</template>
