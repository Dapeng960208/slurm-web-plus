<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import RemoteSearchSelect from '@/components/forms/RemoteSearchSelect.vue'
import { createStaticSearchSource, createUserSearchSource } from '@/composables/searchSelect'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { useI18n } from 'vue-i18n'
import type { JobHistoryFilters } from '@/composables/GatewayAPI'
import {
  Dialog,
  DialogPanel,
  Disclosure,
  DisclosureButton,
  DisclosurePanel,
  TransitionChild,
  TransitionRoot
} from '@headlessui/vue'
import {
  ChevronDownIcon,
  BoltIcon,
  RectangleGroupIcon,
  MagnifyingGlassIcon,
  UserIcon,
  UsersIcon,
  SwatchIcon,
  HashtagIcon,
  CalendarIcon
} from '@heroicons/vue/20/solid'
import { XMarkIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{
  open: boolean
  filters: JobHistoryFilters
  total: number
  cluster: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'search'): void
  (e: 'update:filters', filters: JobHistoryFilters): void
}>()
const { t } = useI18n()
const gateway = useGatewayAPI()
const userSearchSource = createUserSearchSource(props.cluster)
const partitionSearchSource = createStaticSearchSource(async () =>
  (await gateway.partitions(props.cluster)).map((partition) => ({
    value: partition.name,
    label: partition.name
  }))
)
const qosSearchSource = createStaticSearchSource(async () =>
  (await gateway.qos(props.cluster)).map((qos) => ({
    value: qos.name,
    label: qos.name,
    description: qos.description || qos.name
  }))
)

const state_options = [
  'RUNNING',
  'PENDING',
  'COMPLETED',
  'FAILED',
  'CANCELLED',
  'TIMEOUT',
  'NODE_FAIL',
  'OUT_OF_MEMORY'
]

function updateFilters(patch: Partial<JobHistoryFilters>) {
  emit('update:filters', {
    ...props.filters,
    ...patch
  })
}

function updateTextFilter(key: keyof JobHistoryFilters, event: Event) {
  const target = event.target as HTMLInputElement
  updateFilters({ [key]: target.value } as Partial<JobHistoryFilters>)
}

function updateNumericFilter(key: keyof JobHistoryFilters, event: Event) {
  const target = event.target as HTMLInputElement
  const raw = target.value.trim()
  updateFilters({
    [key]: raw ? Number(raw) : undefined
  } as Partial<JobHistoryFilters>)
}

function toggleState(state: string) {
  updateFilters({
    state: props.filters.state === state ? '' : state
  })
}
</script>

<template>
  <TransitionRoot as="template" :show="props.open">
    <Dialog as="div" class="relative z-40" @close="emit('close')">
      <TransitionChild
        as="template"
        enter="ease-in-out duration-500"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in-out duration-500"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-gray-400/50 transition-opacity dark:bg-gray-900/60" />
      </TransitionChild>

      <div class="fixed inset-0 z-40 flex">
        <TransitionChild
          as="template"
          enter="transition ease-in-out duration-300 transform"
          enter-from="translate-x-full"
          enter-to="translate-x-0"
          leave="transition ease-in-out duration-300 transform"
          leave-from="translate-x-0"
          leave-to="translate-x-full"
        >
          <DialogPanel
            class="relative ml-auto flex h-full w-full max-w-xs flex-col overflow-y-auto bg-white py-4 pb-12 shadow-xl dark:bg-gray-700"
          >
            <div class="flex items-center justify-between px-4">
              <h2 class="text-lg font-medium text-gray-900 dark:text-gray-100">
                {{ t('filters.title') }}
                <span
                  class="text-slurmweb dark:text-slurmweb-light dark:bg-slurmweb-verydark ml-3 hidden rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium md:inline-block"
                  >{{ props.total }}</span
                >
              </h2>
              <button
                type="button"
                class="-mr-2 flex h-10 w-10 items-center justify-center rounded-md p-2 text-gray-400"
                @click="emit('close')"
              >
                <span class="sr-only">{{ t('filters.closeMenu') }}</span>
                <XMarkIcon class="h-6 w-6" aria-hidden="true" />
              </button>
            </div>

            <form class="mt-4" @submit.prevent="() => { emit('search'); emit('close') }">
              <!-- Keyword -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <MagnifyingGlassIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-slate-600 p-2 text-white dark:bg-slate-500"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('filters.history.keyword') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    :value="props.filters.keyword"
                    :placeholder="t('filters.history.keywordPlaceholder')"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-slurmweb dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                    @input="updateTextFilter('keyword', $event)"
                  />
                </DisclosurePanel>
              </Disclosure>

              <!-- State -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <BoltIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-gray-600 p-2 text-white dark:bg-gray-500"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('common.labels.state') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-6">
                  <div class="space-y-3">
                    <div
                      v-for="s in state_options"
                      :key="s"
                      class="flex items-center"
                    >
                      <input
                        :id="`hist-state-${s}`"
                        type="checkbox"
                        :value="s"
                        :checked="props.filters.state === s"
                        class="text-slurmweb focus:ring-slurmweb h-4 w-4 rounded-sm border-gray-300"
                        @change="toggleState(s)"
                      />
                      <label
                        :for="`hist-state-${s}`"
                        class="ml-3 text-sm text-gray-500 dark:text-gray-300"
                        >{{ s }}</label
                      >
                    </div>
                  </div>
                </DisclosurePanel>
              </Disclosure>

              <!-- User -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <UserIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-emerald-500 p-2 text-white"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('common.labels.user') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <RemoteSearchSelect
                    :model-value="props.filters.user ?? ''"
                    :source="userSearchSource"
                    :min-query-length="1"
                    :placeholder="t('filters.history.userPlaceholder')"
                    @update:model-value="updateFilters({ user: $event as string })"
                  />
                </DisclosurePanel>
              </Disclosure>

              <!-- Account -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <UsersIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-yellow-500 p-2 text-white"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('common.labels.account') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    :value="props.filters.account"
                    :placeholder="t('filters.history.accountPlaceholder')"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
                    @input="updateTextFilter('account', $event)"
                  />
                </DisclosurePanel>
              </Disclosure>

              <!-- Partition -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <RectangleGroupIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-amber-700 p-2 text-white"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('common.labels.partition') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <RemoteSearchSelect
                    :model-value="props.filters.partition ?? ''"
                    :source="partitionSearchSource"
                    :placeholder="t('filters.history.partitionPlaceholder')"
                    @update:model-value="updateFilters({ partition: $event as string })"
                  />
                </DisclosurePanel>
              </Disclosure>

              <!-- QOS -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <SwatchIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-purple-500 p-2 text-white"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('common.labels.qos') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <RemoteSearchSelect
                    :model-value="props.filters.qos ?? ''"
                    :source="qosSearchSource"
                    :placeholder="t('filters.history.qosPlaceholder')"
                    @update:model-value="updateFilters({ qos: $event as string })"
                  />
                </DisclosurePanel>
              </Disclosure>

              <!-- Job ID -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <HashtagIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-sky-500 p-2 text-white"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('filters.history.jobId') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    :value="props.filters.job_id ?? ''"
                    type="number"
                    min="1"
                    :placeholder="t('filters.history.jobId')"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
                    @input="updateNumericFilter('job_id', $event)"
                  />
                </DisclosurePanel>
              </Disclosure>

              <!-- Time range -->
              <Disclosure
                as="div"
                class="border-t border-gray-200 px-4 py-6 dark:border-gray-600"
                v-slot="{ open: dOpen }"
              >
                <h3 class="-mx-2 -my-3 flow-root">
                  <DisclosureButton
                    class="flex w-full items-center justify-between px-2 py-3 text-sm text-gray-400"
                  >
                    <span class="flex">
                      <CalendarIcon
                        class="-mt-1 mr-2 -ml-1 h-8 w-8 rounded-full bg-rose-500 p-2 text-white"
                      />
                      <span class="font-medium text-gray-900 dark:text-gray-100">{{ t('filters.history.timeRange') }}</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4 space-y-3">
                  <div>
                    <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">{{ t('common.labels.from') }}</label>
                    <input
                      :value="props.filters.start"
                      type="datetime-local"
                      step="1"
                      class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
                      @input="updateTextFilter('start', $event)"
                    />
                  </div>
                  <div>
                    <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">{{ t('common.labels.to') }}</label>
                    <input
                      :value="props.filters.end"
                      type="datetime-local"
                      step="1"
                      class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
                      @input="updateTextFilter('end', $event)"
                    />
                  </div>
                </DisclosurePanel>
              </Disclosure>

              <!-- Apply button -->
              <div class="border-t border-gray-200 dark:border-gray-600 px-4 pt-6">
                <button
                  type="submit"
                  class="w-full bg-slurmweb dark:bg-slurmweb-verydark hover:bg-slurmweb-darker focus-visible:outline-slurmweb rounded-md px-3 py-2 text-sm font-semibold text-white shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2"
                >
                  {{ t('filters.history.apply') }}
                </button>
              </div>
            </form>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
