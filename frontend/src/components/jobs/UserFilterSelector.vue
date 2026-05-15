<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { useI18n } from 'vue-i18n'
import RemoteSearchSelect from '@/components/forms/RemoteSearchSelect.vue'
import { createUserSearchSource } from '@/composables/searchSelect'

const runtimeStore = useRuntimeStore()
const { t } = useI18n()
const route = useRoute()
const cluster = route.params.cluster as string
const userSearchSource = createUserSearchSource(cluster)
</script>

<template>
  <div class="relative mt-2">
    <RemoteSearchSelect
      v-model="runtimeStore.jobs.filters.users"
      multiple
      :source="userSearchSource"
      :min-query-length="1"
      :placeholder="t('filters.users.usernamePlaceholder')"
    />
  </div>
</template>
