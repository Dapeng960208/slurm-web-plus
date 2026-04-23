<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  lastPage,
  paginationRange,
  type PageSizeOption
} from '@/composables/Pagination'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/20/solid'

const props = withDefaults(
  defineProps<{
    page: number
    pageSize: number
    total: number
    itemLabel: string
  }>(),
  {
    pageSize: DEFAULT_PAGE_SIZE
  }
)

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [pageSize: PageSizeOption]
}>()

const totalPages = computed(() => lastPage(props.total, props.pageSize))
const firstItem = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const lastItem = computed(() => Math.min(props.page * props.pageSize, props.total))
const pages = computed(() => paginationRange(props.page, totalPages.value))

function changePage(page: number) {
  if (page < 1 || page > totalPages.value || page === props.page) return
  emit('update:page', page)
}

function changePageSize(event: Event) {
  const value = parseInt((event.target as HTMLSelectElement).value, 10) as PageSizeOption
  if (!PAGE_SIZE_OPTIONS.includes(value)) return
  emit('update:pageSize', value)
}
</script>

<template>
  <div
    class="flex flex-col gap-3 border-t border-[rgba(80,105,127,0.08)] px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:px-5"
  >
    <p class="text-sm text-[var(--color-brand-muted)]">
      Showing
      <span class="font-medium">{{ firstItem }}</span>
      to
      <span class="font-medium">{{ lastItem }}</span>
      of
      <span class="font-medium">{{ total }}</span>
      {{ itemLabel }}{{ total === 1 ? '' : 's' }}
    </p>

    <div class="flex flex-wrap items-center gap-3">
      <label class="flex items-center gap-2 text-sm text-[var(--color-brand-muted)]">
        <span>Per page</span>
        <select
          :value="pageSize"
          class="rounded-full border-[rgba(80,105,127,0.16)] bg-white py-1.5 pr-8 pl-3 text-sm font-semibold text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] focus:border-[rgba(182,232,44,0.65)] focus:ring-[rgba(182,232,44,0.18)]"
          @change="changePageSize"
        >
          <option v-for="option in PAGE_SIZE_OPTIONS" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
      </label>

      <nav
        v-if="totalPages > 1"
        class="isolate inline-flex -space-x-px rounded-full shadow-[var(--shadow-soft)]"
        aria-label="Pagination"
      >
        <button
          type="button"
          :class="[
            page === 1
              ? 'cursor-default bg-gray-100 text-gray-100'
              : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
            'relative inline-flex items-center rounded-l-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
          ]"
          @click="changePage(page - 1)"
        >
          <span class="sr-only">Previous</span>
          <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
        </button>

        <template v-for="pageItem in pages" :key="pageItem.id">
          <button
            v-if="pageItem.ellipsis"
            type="button"
            class="relative z-10 inline-flex items-center bg-white px-3 py-2 text-xs font-semibold text-[var(--color-brand-muted)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset"
          >
            ...
          </button>
          <button
            v-else
            type="button"
            :class="[
              pageItem.id === page
                ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                : 'bg-white text-[var(--color-brand-ink-strong)] ring-1 ring-[rgba(80,105,127,0.16)] ring-inset hover:bg-[rgba(182,232,44,0.12)]',
              'relative z-10 inline-flex items-center px-3 py-2 text-sm font-semibold focus:z-20'
            ]"
            @click="changePage(pageItem.id)"
          >
            {{ pageItem.id }}
          </button>
        </template>

        <button
          type="button"
          :class="[
            page === totalPages
              ? 'cursor-default bg-gray-100 text-gray-100'
              : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
            'relative inline-flex items-center rounded-r-full px-3 py-2 ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-20 focus:outline-offset-0'
          ]"
          @click="changePage(page + 1)"
        >
          <span class="sr-only">Next</span>
          <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </nav>
    </div>
  </div>
</template>
