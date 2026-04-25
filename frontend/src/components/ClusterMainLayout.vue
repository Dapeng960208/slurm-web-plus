<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { onMounted, ref } from 'vue'
import type { Ref } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { Bars3Icon, ServerStackIcon } from '@heroicons/vue/24/outline'
import { ChevronRightIcon } from '@heroicons/vue/20/solid'
import MainMenu from '@/components/MainMenu.vue'
import ClustersPopOver from '@/components/ClustersPopOver.vue'
import UserMenu from '@/components/UserMenu.vue'

type BreadcrumbPart = {
  title: string
  routeName?: string
}

const { menuEntry, cluster, breadcrumb } = defineProps<{
  menuEntry: string
  cluster: string
  breadcrumb: BreadcrumbPart[]
}>()

const clusterNotFound: Ref<boolean> = ref(false)
const sidebarOpen = ref(false)
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()

onMounted(() => {
  if (!runtimeStore.checkClusterAvailable(cluster)) {
    clusterNotFound.value = true
  }
})
</script>

<template>
  <MainMenu :entry="menuEntry" v-model="sidebarOpen" />
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

      <!-- Separator -->
      <div class="h-6 w-px bg-[rgba(80,105,127,0.16)] lg:hidden" aria-hidden="true" />

      <div class="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <div class="relative mt-1 flex flex-1 items-center gap-2 overflow-hidden">
          <ClustersPopOver :cluster="cluster" />
          <span
            v-for="breadcrumbPart in breadcrumb"
            :key="breadcrumbPart.title"
            class="flex min-w-0 items-center"
          >
            <ChevronRightIcon
              class="h-5 w-8 shrink-0 text-[var(--color-brand-muted)]/70"
              aria-hidden="true"
            />
            <router-link
              v-if="breadcrumbPart.routeName"
              :to="{ name: breadcrumbPart.routeName, params: { cluster } }"
              class="truncate text-sm font-medium text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
              >{{ breadcrumbPart.title }}</router-link
            >
            <span
              v-else
              class="truncate text-sm font-semibold text-[var(--color-brand-ink-strong)]"
              >{{ breadcrumbPart.title }}</span
            >
          </span>
        </div>
        <div class="flex items-center gap-x-4 lg:gap-x-6">
          <!-- Selects clusters button-->
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

          <!-- Separator -->
          <div
            class="hidden lg:block lg:h-6 lg:w-px lg:bg-[rgba(80,105,127,0.16)]"
            aria-hidden="true"
          />

          <UserMenu v-if="runtimeConfiguration.authentication" :cluster="cluster" />
        </div>
      </div>
    </div>

    <main class="px-2 py-3 sm:px-3 lg:px-4 lg:py-4 xl:px-5 2xl:px-6">
      <div
        class="rounded-[36px] border border-white/60 bg-[rgba(255,255,255,0.5)] px-3 py-2.5 shadow-[var(--shadow-soft)] backdrop-blur-sm sm:px-5 sm:py-3 lg:px-6 lg:py-4 xl:px-6 xl:py-4 2xl:px-7"
      >
        <div v-if="clusterNotFound">Cluster not found</div>
        <div v-else class="home ui-page ui-page-wide">
          <slot></slot>
        </div>
      </div>
    </main>
  </div>
</template>
