<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { AuthenticationError } from '@/composables/HTTPErrors'
import BrandLogo from '@/components/BrandLogo.vue'

const msg: Ref<string> = ref('')

const gateway = useGatewayAPI()
const authStore = useAuthStore()
const runtimeStore = useRuntimeStore()
const runtimeConfiguration = useRuntimeConfiguration()

function reportAuthenticationError(message: string) {
  runtimeStore.reportError(`Authentication error: ${message}`)
  msg.value = `Anonymous access failed: ${message}`
}

onMounted(async () => {
  if (runtimeConfiguration.authentication) {
    msg.value = 'Anonymous access is blocked because authentication is enabled.'
  } else {
    try {
      const response = await gateway.anonymousLogin()
      authStore.anonymousLogin(response.token)
    } catch (error) {
      if (error instanceof AuthenticationError) {
        reportAuthenticationError(error.message)
      } else if (error instanceof Error) {
        runtimeStore.reportError(`Other error: ${error.message}`)
      }
    }
  }
})
</script>

<template>
  <main class="ui-public-shell">
    <section class="ui-public-grid">
      <aside class="ui-public-aside">
        <div class="space-y-6">
          <BrandLogo size="lg" />
          <div class="space-y-4">
            <p class="ui-page-kicker">Anonymous Access</p>
            <h1 class="text-4xl font-bold text-white md:text-5xl">Preparing public session access.</h1>
            <p class="max-w-xl text-sm leading-7 text-white/72 md:text-base">
              When authentication is disabled, Slurm-web can still route visitors into the control
              center with a lightweight anonymous session.
            </p>
          </div>
        </div>
      </aside>
      <div class="ui-public-panel flex items-center justify-center px-5 py-6 sm:px-8">
        <div class="max-w-lg space-y-4 text-center">
          <BrandLogo size="sm" />
          <p class="ui-page-kicker mx-auto w-fit">Status</p>
          <p class="text-2xl font-bold text-[var(--color-brand-ink-strong)]">{{ msg }}</p>
        </div>
      </div>
    </section>
  </main>
</template>
