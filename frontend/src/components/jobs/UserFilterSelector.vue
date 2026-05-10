<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import { useGatewayDataGetter } from '@/composables/DataGetter'
import type { UserDescription } from '@/composables/GatewayAPI'
import { ChevronUpDownIcon, CheckIcon } from '@heroicons/vue/20/solid'

import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions
} from '@headlessui/vue'

const runtimeStore = useRuntimeStore()

const query = ref('')

const filteredUsers = computed(() => {
  if (!data.value) {
    return []
  }
  return query.value === ''
    ? data.value
    : data.value.filter((user) => {
        return (
          user.fullname.toLowerCase().includes(query.value.toLowerCase()) ||
          user.login.toLowerCase().includes(query.value.toLowerCase())
        )
      })
})

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
    return 'Search user…'
  } else {
    return runtimeStore.jobs.filters.users.join(', ')
  }
}

const { data } = useGatewayDataGetter<UserDescription[]>('users')
</script>

<template>
  <div class="relative mt-2">
    <Combobox as="div" v-model="runtimeStore.jobs.filters.users" multiple>
      <div class="flex gap-2">
        <div class="relative min-w-0 flex-1">
          <ComboboxInput
            class="ui-combobox-input"
            :value="query"
            @input="updateQuery"
            :placeholder="queryPlaceholder()"
          />
          <ComboboxButton
            class="absolute inset-y-0 right-0 flex items-center rounded-r-md px-2 focus:outline-hidden"
          >
            <ChevronUpDownIcon class="h-5 w-5 text-gray-400" aria-hidden="true" />
          </ComboboxButton>
        </div>
        <button
          type="button"
          class="ui-button-primary shrink-0"
          :disabled="!canAddManualUsername"
          @click="addManualUsername"
        >
          Add username
        </button>
      </div>

      <ComboboxOptions
        v-if="filteredUsers.length > 0"
        class="ui-combobox-menu absolute z-10 mt-1 max-h-60 w-full text-base focus:outline-none sm:text-sm"
      >
        <ComboboxOption
          v-for="user in filteredUsers"
          :key="user.login"
          :value="user.login"
          as="template"
          v-slot="{ active, selected }"
        >
          <li
            :class="[
              'ui-combobox-option',
              active && 'ui-combobox-option-active'
            ]"
          >
            <div class="flex">
              <span :class="['truncate', selected && 'font-semibold']">
                {{ user.fullname }}
              </span>
              <span
                :class="[
                  'ml-2 truncate',
                  active ? 'text-[rgba(32,42,53,0.72)]' : 'text-[var(--color-brand-muted)]'
                ]"
              >
                {{ user.login }}
              </span>
            </div>

            <span
              v-if="selected"
              :class="[
                'absolute inset-y-0 right-0 flex items-center pr-4',
                active ? 'text-[var(--color-brand-deep)]' : 'text-[var(--color-brand-blue)]'
              ]"
            >
              <CheckIcon class="h-5 w-5" aria-hidden="true" />
            </span>
          </li>
        </ComboboxOption>
      </ComboboxOptions>
    </Combobox>
  </div>
</template>
