<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRuntimeStore } from '@/stores/runtime'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { AuthenticationError } from '@/composables/HTTPErrors'
import LoginServiceMessage from '@/components/login/LoginServiceMessage.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import BrandLogo from '@/components/BrandLogo.vue'

const gateway = useGatewayAPI()

const username: Ref<string | null> = ref(null)
const password: Ref<string | null> = ref(null)
const disableSubmission: Ref<boolean> = ref(false)
const highlightLogin: Ref<boolean> = ref(false)
const highlightPassword: Ref<boolean> = ref(false)
const shakeLoginButton: Ref<boolean> = ref(false)

const authStore = useAuthStore()
const runtimeStore = useRuntimeStore()

function reportAuthenticationError(message: string) {
  runtimeStore.reportError(`Authentication error: ${message}`)
  setTrueFor(shakeLoginButton, 300)
  disableSubmission.value = false
}

function setTrueFor(reference: Ref<boolean>, timeout: number) {
  reference.value = true
  setTimeout(() => {
    reference.value = false
  }, timeout)
}

async function submitLogin() {
  if (username.value == null || username.value == '') {
    reportAuthenticationError('Username is required')
    setTrueFor(highlightLogin, 2000)
    return
  }
  if (password.value == null || password.value == '') {
    reportAuthenticationError('Password is required')
    setTrueFor(highlightPassword, 2000)
    return
  }
  try {
    disableSubmission.value = true
    const response = await gateway.login({ user: username.value, password: password.value })
    authStore.login(response.token, username.value, response.fullname, response.groups)
  } catch (error) {
    if (error instanceof AuthenticationError) {
      reportAuthenticationError(error.message)
    } else if (error instanceof Error) {
      runtimeStore.reportError(`Other error: ${error.message}`)
    }
  }
}
</script>

<template>
  <main class="ui-public-shell">
    <section class="ui-public-grid">
      <aside class="ui-public-aside">
        <div class="space-y-6">
          <BrandLogo size="lg" />
          <div class="space-y-4">
            <p class="ui-page-kicker">Secure Access</p>
            <h1 class="text-4xl font-bold text-white md:text-5xl">
              Enter the Slurm-web control center.
            </h1>
            <p class="max-w-xl text-sm leading-7 text-white/72 md:text-base">
              Unified cluster operations, job observability and infrastructure navigation in a
              cleaner, brand-aligned experience.
            </p>
          </div>
        </div>
        <div class="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <div class="rounded-[22px] border border-white/10 bg-white/6 p-4">
            <p class="text-xs font-semibold tracking-[0.14em] text-white/50 uppercase">Entry</p>
            <p class="mt-2 text-sm text-white/80">
              Sign in once and jump into clusters, jobs and resources.
            </p>
          </div>
          <div class="rounded-[22px] border border-white/10 bg-white/6 p-4">
            <p class="text-xs font-semibold tracking-[0.14em] text-white/50 uppercase">Focus</p>
            <p class="mt-2 text-sm text-white/80">Visual hierarchy tuned for operational clarity.</p>
          </div>
          <div class="rounded-[22px] border border-white/10 bg-white/6 p-4">
            <p class="text-xs font-semibold tracking-[0.14em] text-white/50 uppercase">Brand</p>
            <p class="mt-2 text-sm text-white/80">
              A modern shell aligned with your updated logo system.
            </p>
          </div>
        </div>
      </aside>

      <div class="ui-public-panel flex items-center justify-center px-5 py-6 sm:px-8">
        <div class="w-full max-w-md space-y-6">
          <div class="space-y-3">
            <p class="ui-page-kicker">Authentication</p>
            <h2 class="text-3xl font-bold text-[var(--color-brand-ink-strong)]">Access Slurm-web</h2>
            <p class="text-sm leading-6 text-[var(--color-brand-muted)]">
              Sign in to continue to the requested page or open the cluster gateway.
            </p>
          </div>

          <InfoAlert v-if="authStore.returnUrl !== null">
            Please log in to access the requested page.
          </InfoAlert>

          <form class="space-y-5" action="#" @submit.prevent="submitLogin">
            <div>
              <label
                for="user"
                class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]"
              >
                Login
              </label>
              <input
                id="user"
                v-model="username"
                name="user"
                class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white/90 px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:bg-white focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                :class="{ 'bg-gray-50': !highlightLogin, 'bg-red-200': highlightLogin }"
                placeholder="Username"
              />
            </div>
            <div>
              <label
                for="password"
                class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]"
              >
                Password
              </label>
              <input
                id="password"
                v-model="password"
                type="password"
                name="password"
                class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white/90 px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:bg-white focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                :class="{ 'bg-gray-50': !highlightPassword, 'bg-red-200': highlightPassword }"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              :disabled="disableSubmission"
              class="ui-button-primary w-full justify-center py-4 text-base disabled:cursor-not-allowed disabled:opacity-50"
              :class="{ 'animate-horizontal-shake': shakeLoginButton }"
            >
              <template v-if="disableSubmission">
                <svg
                  class="mx-2 -ml-2 inline-block h-4 w-4 animate-spin text-[var(--color-brand-deep)]"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Authenticating
              </template>
              <template v-else>Sign in</template>
            </button>
          </form>

          <LoginServiceMessage />
        </div>
      </div>
    </section>
  </main>
</template>
