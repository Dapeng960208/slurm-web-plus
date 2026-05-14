<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useI18n } from 'vue-i18n'

const runtimeStore = useRuntimeStore()
const { t } = useI18n()

const query = ref('')

const manualUsername = computed(() => query.value.trim())
const canAddManualUsername = computed(() => {
  const username = manualUsername.value
  if (!username) return false
  return !runtimeStore.jobs.filters.users.some(
    (user) => user.toLocaleLowerCase() === username.toLocaleLowerCase()
  )
})

function addManualUsername() {
  if (!canAddManualUsername.value) return
  runtimeStore.jobs.filters.users.push(manualUsername.value)
  query.value = ''
}

function updateQuery(event: Event) {
  query.value = (event.target as HTMLInputElement).value
}

function queryPlaceholder() {
  if (runtimeStore.jobs.filters.users.length == 0) {
    return t('filters.users.usernamePlaceholder')
  } else {
    return runtimeStore.jobs.filters.users.join(', ')
  }
}
</script>

<template>
  <div class="relative mt-2">
    <div class="flex gap-2">
      <div class="relative min-w-0 flex-1">
        <input
          class="ui-combobox-input"
          :value="query"
          type="text"
          autocomplete="off"
          :placeholder="queryPlaceholder()"
          @input="updateQuery"
          @keydown.enter.prevent="addManualUsername"
        />
      </div>
      <button
        type="button"
        class="ui-button-primary shrink-0"
        :disabled="!canAddManualUsername"
        @click="addManualUsername"
      >
        {{ t('filters.users.addUsername') }}
      </button>
    </div>
  </div>
</template>
