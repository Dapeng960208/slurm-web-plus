<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'

const authStore = useAuthStore()
const runtimeStore = useRuntimeStore()
const router = useRouter()
const runtimeConfiguration = useRuntimeConfiguration()
const { t } = useI18n()

onMounted(() => {
  authStore.logout()
  runtimeStore.reportInfo(t('publicPages.signout.done'))

  if (runtimeConfiguration.authentication) {
    router.push({ name: 'login' })
  } else {
    router.push({ name: 'anonymous' })
  }
})
</script>

<template>
  <main>{{ t('publicPages.signout.bye') }}</main>
</template>
