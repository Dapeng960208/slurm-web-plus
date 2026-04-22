<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { CheckCircleIcon, XCircleIcon } from '@heroicons/vue/24/outline'
import { XMarkIcon } from '@heroicons/vue/20/solid'
import { useRuntimeStore } from '@/stores/runtime'
import type { Notification } from '@/stores/runtime'

const runtimeStore = useRuntimeStore()

const { notification } = defineProps<{ notification: Notification }>()
</script>

<template>
  <div
    class="pointer-events-auto w-full overflow-hidden rounded-[24px] border border-white/70 bg-[rgba(255,255,255,0.92)] shadow-[var(--shadow-panel)] backdrop-blur-xl"
  >
    <div class="flex items-start p-4">
      <div class="shrink-0 rounded-full p-2" :class="notification.type == 'INFO' ? 'bg-[rgba(123,191,31,0.12)]' : 'bg-[rgba(216,75,80,0.12)]'">
        <CheckCircleIcon
          v-if="notification.type == 'INFO'"
          class="h-6 w-6 text-[var(--color-brand-success)]"
          aria-hidden="true"
        />
        <XCircleIcon
          v-else-if="notification.type == 'ERROR'"
          class="h-6 w-6 text-[var(--color-brand-danger)]"
          aria-hidden="true"
        />
      </div>
      <div class="ml-3 w-0 flex-1 pt-0.5">
        <p class="text-sm font-semibold tracking-[0.14em] text-[var(--color-brand-muted)] uppercase">
          {{ notification.type }}
        </p>
        <p class="mt-1 text-sm leading-6 text-[var(--color-brand-ink)]">{{ notification.message }}</p>
      </div>
      <div class="ml-4 flex shrink-0">
        <button
          type="button"
          @click="runtimeStore.removeNotification(notification)"
          class="inline-flex rounded-full bg-[rgba(239,244,246,0.88)] p-2 text-[var(--color-brand-muted)] transition hover:bg-white hover:text-[var(--color-brand-ink-strong)] focus:outline-hidden"
        >
          <span class="sr-only">Close</span>
          <XMarkIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </div>
  </div>
</template>
