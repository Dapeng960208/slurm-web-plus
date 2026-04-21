<!--
  Copyright (c) 2023-2024 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
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
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'search'): void
}>()

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
                Filters
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
                <span class="sr-only">Close menu</span>
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">Keyword</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    v-model="props.filters.keyword"
                    placeholder="Search workdir / command"
                    class="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-slurmweb dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">State</span>
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
                        @change="props.filters.state = (props.filters.state === s ? '' : s)"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">User</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    v-model="props.filters.user"
                    placeholder="Username"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">Account</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    v-model="props.filters.account"
                    placeholder="Account name"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">Partition</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    v-model="props.filters.partition"
                    placeholder="Partition name"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">QOS</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    v-model="props.filters.qos"
                    placeholder="QOS name"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">Job ID</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4">
                  <input
                    v-model.number="props.filters.job_id"
                    type="number"
                    min="1"
                    placeholder="Job ID"
                    class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
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
                      <span class="font-medium text-gray-900 dark:text-gray-100">Time Range</span>
                    </span>
                    <ChevronDownIcon
                      :class="[dOpen ? '-rotate-180' : 'rotate-0', 'h-5 w-5 transform']"
                      aria-hidden="true"
                    />
                  </DisclosureButton>
                </h3>
                <DisclosurePanel class="pt-4 space-y-3">
                  <div>
                    <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">From</label>
                    <input
                      v-model="props.filters.start"
                      type="datetime-local"
                      step="1"
                      class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
                    />
                  </div>
                  <div>
                    <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">To</label>
                    <input
                      v-model="props.filters.end"
                      type="datetime-local"
                      step="1"
                      class="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-slurmweb"
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
                  Apply Filters
                </button>
              </div>
            </form>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
