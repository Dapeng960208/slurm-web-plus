<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue'
import {
  CalendarIcon,
  ChartBarSquareIcon,
  ChatBubbleLeftRightIcon,
  ShieldCheckIcon,
  Cog6ToothIcon,
  HomeIcon,
  PlayCircleIcon,
  CpuChipIcon,
  SwatchIcon,
  XMarkIcon,
  UserGroupIcon,
  ClockIcon
} from '@heroicons/vue/24/outline'
import { TagIcon } from '@heroicons/vue/16/solid'

import { hasClusterAIAssistant } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import BrandLogo from '@/components/BrandLogo.vue'

const { entry, clusterContext } = defineProps<{
  entry: string
  clusterContext?: string
}>()

const sidebarOpen = defineModel<boolean>()

const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()
const ADMIN_RESOURCES = [
  'admin/system',
  'admin/ai',
  'admin/access-control',
  'admin/cache',
  'admin/ldap-cache'
] as const
const navigation: Array<{
  name: string
  route: string
  icon: object
  resource: string
  operation: 'view' | 'edit' | 'delete'
  feature?: string
}> = [
  {
    name: 'Dashboard',
    route: 'dashboard',
    icon: HomeIcon,
    resource: 'dashboard',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'Analysis',
    route: 'analysis',
    icon: ChartBarSquareIcon,
    resource: 'analysis',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'Admin',
    route: 'admin-system',
    icon: ShieldCheckIcon,
    resource: 'admin/system',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'AI',
    route: 'ai',
    icon: ChatBubbleLeftRightIcon,
    resource: 'ai',
    operation: 'view',
    feature: 'ai'
  },
  {
    name: 'Jobs',
    route: 'jobs',
    icon: PlayCircleIcon,
    resource: 'jobs',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'Jobs History',
    route: 'jobs-history',
    icon: ClockIcon,
    resource: 'jobs-history',
    operation: 'view',
    feature: 'job_history'
  },
  {
    name: 'Resources',
    route: 'resources',
    icon: CpuChipIcon,
    resource: 'resources',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'QOS',
    route: 'qos',
    icon: SwatchIcon,
    resource: 'qos',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'Reservations',
    route: 'reservations',
    icon: CalendarIcon,
    resource: 'reservations',
    operation: 'view',
    feature: undefined
  },
  {
    name: 'Accounts',
    route: 'accounts',
    icon: UserGroupIcon,
    resource: 'accounts',
    operation: 'view',
    feature: undefined
  }
]

function isFeatureEnabled(feature: string | undefined): boolean {
  if (!feature) return true
  const cluster = navigationCluster.value
  if (!cluster) return false
  if (feature === 'ai') {
    return hasClusterAIAssistant(cluster)
  }
  if (feature === 'job_history') {
    return cluster.capabilities?.job_history === true || cluster.persistence === true
  }
  return !!(cluster as unknown as Record<string, unknown>)[feature]
}

function hasNavigationPermission(resource?: string, operation: 'view' | 'edit' | 'delete' = 'view'): boolean {
  if (!resource) return true
  const cluster = navigationCluster.value
  if (cluster) {
    if (resource === 'jobs' && operation === 'view') {
      return runtimeStore.hasRoutePermissionAnyScope(cluster.name, resource, operation)
    }
    if (resource === 'admin/system' && operation === 'view') {
      return (
        runtimeStore.hasRoutePermission(cluster.name, 'admin/*', 'view') ||
        ADMIN_RESOURCES.some((adminResource) =>
          runtimeStore.hasRoutePermission(cluster.name, adminResource, 'view')
        )
      )
    }
    return runtimeStore.hasRoutePermission(cluster.name, resource, operation)
  }
  return false
}

const navigationCluster = computed(() => {
  if (clusterContext) {
    return runtimeStore.getCluster(clusterContext)
  }
  return runtimeStore.currentCluster
})

function navigationTarget(route: string): RouteLocationRaw {
  const cluster = navigationCluster.value
  return cluster ? { name: route, params: { cluster: cluster.name } } : { name: route }
}
</script>

<template>
  <TransitionRoot as="template" :show="sidebarOpen">
    <Dialog as="div" class="relative z-50 lg:hidden" @close="sidebarOpen = false">
      <TransitionChild
        as="template"
        enter="transition-opacity ease-linear duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="transition-opacity ease-linear duration-300"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-[rgba(32,42,53,0.7)] backdrop-blur-sm" />
      </TransitionChild>

      <div class="fixed inset-0 flex">
        <TransitionChild
          as="template"
          enter="transition ease-in-out duration-300 transform"
          enter-from="-translate-x-full"
          enter-to="translate-x-0"
          leave="transition ease-in-out duration-300 transform"
          leave-from="translate-x-0"
          leave-to="-translate-x-full"
        >
          <DialogPanel class="relative mr-16 flex w-full max-w-sm flex-1">
            <TransitionChild
              as="template"
              enter="ease-in-out duration-300"
              enter-from="opacity-0"
              enter-to="opacity-100"
              leave="ease-in-out duration-300"
              leave-from="opacity-100"
              leave-to="opacity-0"
            >
              <div class="absolute top-0 left-full flex w-16 justify-center pt-5">
                <button type="button" class="-m-2.5 p-2.5" @click="sidebarOpen = false">
                  <span class="sr-only">Close sidebar</span>
                  <XMarkIcon class="h-6 w-6 text-white" aria-hidden="true" />
                </button>
              </div>
            </TransitionChild>

            <!-- Sidebar component -->
            <div
              class="flex grow flex-col gap-y-6 overflow-y-auto rounded-r-[32px] border-r border-white/10 bg-[linear-gradient(180deg,rgba(32,42,53,0.98),rgba(56,59,64,0.94))] px-6 pb-6 text-white shadow-[var(--shadow-panel)]"
            >
              <div class="flex shrink-0 items-center justify-center pt-7">
                <BrandLogo size="sm" :framed="false" />
              </div>
              <div
                class="mx-2 flex items-center justify-between rounded-full border border-white/10 bg-white/6 px-3 py-2 text-xs text-white/70"
              >
                <span class="font-semibold tracking-[0.18em] uppercase">Cluster Ops</span>
                <TagIcon class="inline size-3" aria-hidden="true" />
                <!-- {{ runtimeConfiguration.version }} -->
              </div>
              <nav class="flex flex-1 flex-col">
                <ul role="list" class="flex flex-1 flex-col gap-y-7">
                  <li>
                    <ul role="list" class="space-y-1.5">
                      <li v-for="item in navigation" :key="item.name">
                        <RouterLink
                          v-if="
                            hasNavigationPermission(item.resource, item.operation) &&
                            isFeatureEnabled(item.feature)
                          "
                          :to="navigationTarget(item.route)"
                          :class="[
                            item.route == entry
                              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                              : 'text-white/70 hover:bg-white/8 hover:text-white',
                            'group flex items-center gap-x-3 rounded-[18px] px-3.5 py-3 text-sm leading-6 font-semibold transition'
                          ]"
                          @click="sidebarOpen = false"
                        >
                          <component
                            :is="item.icon"
                            :class="[
                              item.route == entry
                                ? 'text-[var(--color-brand-deep)]'
                                : 'text-white/60 group-hover:text-white',
                              'h-6 w-6 shrink-0'
                            ]"
                            aria-hidden="true"
                          />
                          {{ item.name }}
                        </RouterLink>
                      </li>
                    </ul>
                  </li>
                  <li class="mt-auto">
                    <RouterLink
                      :to="{ name: 'settings' }"
                      class="group flex items-center gap-x-3 rounded-[18px] border border-white/10 bg-white/6 px-3.5 py-3 text-sm leading-6 font-semibold text-white/80 transition hover:bg-white/12 hover:text-white"
                    >
                      <Cog6ToothIcon
                        class="h-6 w-6 shrink-0 text-white/60 group-hover:text-white"
                        aria-hidden="true"
                      />
                      Settings
                    </RouterLink>
                  </li>
                </ul>
              </nav>
            </div>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>

  <!-- Static sidebar for desktop -->
  <div class="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-80 lg:flex-col lg:p-4">
    <div
      class="flex grow flex-col gap-y-6 overflow-y-auto rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(32,42,53,0.98),rgba(56,59,64,0.95))] px-6 pb-6 text-white shadow-[var(--shadow-panel)]"
    >
      <div class="flex shrink-0 items-center justify-center pt-7">
        <BrandLogo size="sm" :framed="false" />
      </div>
      <div
        class="flex items-center justify-between rounded-full border border-white/10 bg-white/6 px-3 py-2 text-xs text-white/70"
      >
        <span class="font-semibold tracking-[0.18em] uppercase">Slurm Monitor</span>
        <span
          ><TagIcon class="mr-1 inline size-3" aria-hidden="true" />
          {{ runtimeConfiguration.version }}</span
        >
      </div>
      <nav class="flex flex-1 flex-col">
        <ul role="list" class="flex flex-1 flex-col gap-y-7">
          <li>
            <ul role="list" class="space-y-1.5">
              <li v-for="item in navigation" :key="item.name">
                <RouterLink
                  v-if="hasNavigationPermission(item.resource, item.operation) && isFeatureEnabled(item.feature)"
                  :to="navigationTarget(item.route)"
                  :class="[
                    item.route == entry
                      ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
                      : 'text-white/70 hover:bg-white/8 hover:text-white',
                    'group flex items-center gap-x-3 rounded-[18px] px-3.5 py-3 text-sm leading-6 font-semibold transition'
                  ]"
                >
                  <component
                    :is="item.icon"
                    :class="[
                      item.route == entry
                        ? 'text-[var(--color-brand-deep)]'
                        : 'text-white/60 group-hover:text-white',
                      'h-6 w-6 shrink-0 transition'
                    ]"
                    aria-hidden="true"
                  />
                  {{ item.name }}
                </RouterLink>
              </li>
            </ul>
          </li>
          <li class="mt-auto">
            <RouterLink
              :to="{ name: 'settings' }"
              class="group flex items-center gap-x-3 rounded-[18px] border border-white/10 bg-white/6 px-3.5 py-3 text-sm leading-6 font-semibold text-white/80 transition hover:bg-white/12 hover:text-white"
            >
              <Cog6ToothIcon
                class="h-6 w-6 shrink-0 text-white/60 group-hover:text-white"
                aria-hidden="true"
              />
              Settings
            </RouterLink>
          </li>
        </ul>
      </nav>
    </div>
  </div>
</template>
