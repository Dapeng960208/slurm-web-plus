<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import {
  ChevronDownIcon,
  ArrowRightOnRectangleIcon,
  IdentificationIcon,
  ShieldCheckIcon,
  UserCircleIcon
} from '@heroicons/vue/20/solid'
import { useAuthStore } from '@/stores/auth'

const { cluster } = defineProps<{
  cluster?: string
}>()

const authStore = useAuthStore()

const workspaceTarget = computed(() => {
  if (!cluster) return null
  return { name: 'my-profile', params: { cluster } }
})
</script>

<template>
  <Menu as="div" class="relative">
    <MenuButton class="ui-user-menu-button">
      <span class="ui-user-menu-avatar">
        <UserCircleIcon class="h-5 w-5" aria-hidden="true" />
      </span>
      <span class="hidden min-w-0 lg:block">
        <span class="block truncate text-sm font-semibold text-[var(--color-brand-ink-strong)]">
          {{ authStore.fullname || authStore.username }}
        </span>
        <span class="block truncate text-xs text-[var(--color-brand-muted)]">
          {{ authStore.username }}
        </span>
      </span>
      <ChevronDownIcon class="h-4 w-4 text-[var(--color-brand-muted)]" aria-hidden="true" />
    </MenuButton>

    <transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <MenuItems class="ui-user-menu-panel">
        <div class="ui-user-menu-header">
          <div class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
            {{ authStore.fullname || authStore.username }}
          </div>
          <div class="text-xs text-[var(--color-brand-muted)]">
            {{ authStore.username }}
          </div>
        </div>

        <div class="ui-user-menu-list">
          <MenuItem v-if="workspaceTarget" v-slot="{ active }">
            <RouterLink
              :to="workspaceTarget"
              :class="['ui-user-menu-item', active ? 'ui-user-menu-item-active' : '']"
            >
              <IdentificationIcon class="h-5 w-5" aria-hidden="true" />
              My workspace
            </RouterLink>
          </MenuItem>

          <MenuItem v-slot="{ active }">
            <RouterLink
              :to="{ name: 'settings-account' }"
              :class="['ui-user-menu-item', active ? 'ui-user-menu-item-active' : '']"
            >
              <ShieldCheckIcon class="h-5 w-5" aria-hidden="true" />
              Account permissions
            </RouterLink>
          </MenuItem>

          <MenuItem v-slot="{ active }">
            <RouterLink
              :to="{ name: 'signout' }"
              :class="['ui-user-menu-item', active ? 'ui-user-menu-item-active' : '']"
            >
              <ArrowRightOnRectangleIcon class="h-5 w-5" aria-hidden="true" />
              Sign out
            </RouterLink>
          </MenuItem>
        </div>
      </MenuItems>
    </transition>
  </Menu>
</template>
