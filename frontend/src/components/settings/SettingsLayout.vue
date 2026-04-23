<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import LeaveSettingsButton from '@/components/settings/LeaveSettingsButton.vue'
import MainMenu from '@/components/MainMenu.vue'
import { Bars3Icon, ArrowRightOnRectangleIcon, ServerStackIcon } from '@heroicons/vue/24/outline'

const sidebarOpen = ref(false)
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()
const authStore = useAuthStore()

const navigationCluster = computed(() => {
  if (runtimeStore.currentCluster) return runtimeStore.currentCluster
  const routeCluster = runtimeStore.beforeSettingsRoute?.params?.cluster
  if (typeof routeCluster === 'string') {
    const cluster = runtimeStore.getCluster(routeCluster)
    if (cluster) return cluster
  }
  return runtimeStore.getAllowedClusters()[0]
})
</script>
<template>
  <MainMenu entry="settings" v-model="sidebarOpen" :cluster-context="navigationCluster?.name" />
  <div class="ui-shell lg:pl-80">
    <div
      class="sticky top-0 z-40 mx-3 mt-3 flex h-18 shrink-0 items-center gap-x-4 rounded-[28px] border border-white/60 bg-[rgba(255,255,255,0.8)] px-4 shadow-[var(--shadow-soft)] backdrop-blur-xl sm:gap-x-6 lg:mx-4 lg:px-5"
    >
      <button
        type="button"
        class="-m-2.5 rounded-full p-2.5 text-[var(--color-brand-ink)] transition hover:bg-[rgba(182,232,44,0.14)] lg:hidden"
        @click="sidebarOpen = true"
      >
        <span class="sr-only">Open sidebar</span>
        <Bars3Icon class="h-6 w-6" aria-hidden="true" />
      </button>

      <div class="h-6 w-px bg-[rgba(80,105,127,0.16)] lg:hidden" aria-hidden="true" />

      <div class="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <div class="relative flex flex-1 items-center gap-3 overflow-hidden">
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold text-[var(--color-brand-ink-strong)]">
              Settings
            </div>
            <div class="truncate text-xs text-[var(--color-brand-muted)]">
              Global preferences and service state
            </div>
          </div>
        </div>
        <div class="flex items-center gap-x-4 lg:gap-x-6">
          <RouterLink :to="{ name: 'clusters' }" custom v-slot="{ navigate }">
            <button
              v-if="runtimeStore.getAllowedClusters().length > 1"
              @click="navigate"
              role="link"
              class="rounded-full p-2.5 text-[var(--color-brand-muted)] transition hover:bg-[rgba(182,232,44,0.14)] hover:text-[var(--color-brand-ink-strong)] lg:-m-2.5"
            >
              <ServerStackIcon class="h-6 w-6" />
            </button>
          </RouterLink>

          <div
            class="hidden lg:block lg:h-6 lg:w-px lg:bg-[rgba(80,105,127,0.16)]"
            aria-hidden="true"
          />

          <span v-if="runtimeConfiguration.authentication" class="hidden lg:flex lg:items-center">
            <span
              class="m-2 rounded-full bg-[rgba(239,244,246,0.92)] px-3 py-1.5 text-sm leading-6 font-semibold text-[var(--color-brand-ink-strong)]"
              aria-hidden="true"
            >
              {{ authStore.fullname }}
            </span>
          </span>

          <RouterLink
            v-if="runtimeConfiguration.authentication"
            :to="{ name: 'signout' }"
            custom
            v-slot="{ navigate }"
          >
            <button
              @click="navigate"
              role="link"
              class="rounded-full p-2.5 text-[var(--color-brand-muted)] transition hover:bg-[rgba(182,232,44,0.14)] hover:text-[var(--color-brand-ink-strong)] lg:-m-2.5"
            >
              <ArrowRightOnRectangleIcon class="h-6 w-6" />
            </button>
          </RouterLink>
        </div>
      </div>
    </div>

    <main class="px-2 py-3 sm:px-3 lg:px-4 lg:py-4 xl:px-5 2xl:px-6">
      <div
        class="rounded-[36px] border border-white/60 bg-[rgba(255,255,255,0.5)] px-3 py-2.5 shadow-[var(--shadow-soft)] backdrop-blur-sm sm:px-5 sm:py-3 lg:px-6 lg:py-4 xl:px-6 xl:py-4 2xl:px-7"
      >
        <div class="ui-page ui-page-readable">
          <LeaveSettingsButton />
          <RouterView />
        </div>
      </div>
    </main>
  </div>
</template>
