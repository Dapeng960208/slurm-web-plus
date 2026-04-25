<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useRoute } from 'vue-router'
import type { RouteRecordName } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { Popover, PopoverButton, PopoverPanel } from '@headlessui/vue'
import { ChevronDownIcon } from '@heroicons/vue/20/solid'
import { ServerIcon } from '@heroicons/vue/24/outline'

const { cluster } = defineProps<{ cluster: string }>()

const route = useRoute()
const runtimeStore = useRuntimeStore()
</script>

<template>
  <template v-if="runtimeStore.getAllowedClusters().length > 1">
    <Popover class="relative">
      <PopoverButton
        class="ui-frost inline-flex items-center gap-x-2 rounded-full px-3.5 py-2.5 text-sm font-semibold text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] focus:outline-hidden"
      >
        <ChevronDownIcon class="h-5 w-5" aria-hidden="true" />
        <span>{{ cluster }}</span>
      </PopoverButton>

      <transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 translate-y-1"
      >
        <PopoverPanel
          v-slot="{ close }"
          class="absolute left-0 z-10 mt-5 flex w-screen max-w-max px-0"
        >
          <div
            class="w-screen max-w-md flex-auto overflow-hidden rounded-[28px] border border-white/70 bg-[rgba(255,255,255,0.94)] text-sm leading-6 shadow-[var(--shadow-panel)]"
          >
            <div class="p-4">
              <div
                v-for="cluster in runtimeStore.getAllowedClusters()"
                :key="cluster.name"
                class="group relative flex gap-x-6 rounded-[20px] p-4 transition hover:bg-[rgba(182,232,44,0.12)]"
              >
                <div
                  v-if="(cluster.permissions.actions?.length ?? 0) > 0 || (cluster.permissions.rules?.length ?? 0) > 0"
                  class="mt-1 flex items-center justify-evenly gap-x-1.5"
                >
                  <div
                    :class="[
                      cluster.error ? 'bg-[rgba(239,155,40,0.18)]' : 'bg-[rgba(123,191,31,0.16)]',
                      'flex-none rounded-full p-1.5'
                    ]"
                  >
                    <div
                      :class="[
                        cluster.error ? 'bg-[var(--color-brand-warning)]' : 'bg-[var(--color-brand-success)]',
                        'h-1.5 w-1.5 rounded-full'
                      ]"
                    />
                  </div>
                </div>

                <RouterLink
                  :to="{
                    name: route.name as RouteRecordName,
                    params: { cluster: cluster.name },
                    query: route.query
                  }"
                  class="flex grow font-semibold text-[var(--color-brand-ink-strong)]"
                  @click="close()"
                >
                  {{ cluster.name }}
                  <span class="absolute inset-0" />
                </RouterLink>

                <span
                  v-if="cluster.stats"
                  class="mt-1 flex w-30 text-xs leading-5 text-[var(--color-brand-muted)]"
                >
                  <ServerIcon class="mx-1 h-5" />
                  {{ cluster.stats.resources.nodes }} node{{
                    cluster.stats.resources.nodes > 1 ? 's' : ''
                  }}
                </span>
              </div>
            </div>
          </div>
        </PopoverPanel>
      </transition>
    </Popover>
  </template>
  <span
    v-else
    class="inline-flex items-center gap-x-1 rounded-sm p-3 leading-6 font-bold text-gray-700"
  >
    {{ cluster }}
  </span>
</template>
