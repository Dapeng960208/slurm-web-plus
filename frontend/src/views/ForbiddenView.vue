<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { LockClosedIcon } from '@heroicons/vue/24/outline'
import BrandLogo from '@/components/BrandLogo.vue'

const route = useRoute()
const router = useRouter()

const cluster = computed(() => (typeof route.query.cluster === 'string' ? route.query.cluster : null))
const permission = computed(() =>
  typeof route.query.permission === 'string' ? route.query.permission : null
)

const detail = computed(() => {
  if (permission.value) {
    return `Missing required permission: ${permission.value}`
  }
  return 'Your current role does not grant access to this page.'
})

const homeTarget = computed(() => {
  if (cluster.value) {
    return { name: 'dashboard', params: { cluster: cluster.value } }
  }
  return { name: 'clusters' }
})

function goBack() {
  router.back()
}
</script>

<template>
  <main class="ui-public-shell">
    <section class="ui-public-grid">
      <aside class="ui-public-aside">
        <div class="space-y-6">
          <BrandLogo size="lg" />
          <div class="space-y-4">
            <p class="ui-page-kicker">Access Restricted</p>
            <h1 class="text-4xl font-bold text-white md:text-5xl">Permission required</h1>
            <p class="max-w-xl text-sm leading-7 text-white/72 md:text-base">
              This page is protected. Contact your administrator to request the required access.
            </p>
          </div>
        </div>
      </aside>

      <div class="ui-public-panel flex items-center justify-center px-5 py-6 sm:px-8">
        <div class="ui-forbidden-panel">
          <div class="ui-forbidden-icon">
            <LockClosedIcon class="h-8 w-8" aria-hidden="true" />
          </div>
          <div class="space-y-4 text-center">
            <h2 class="text-3xl font-bold text-[var(--color-brand-ink-strong)]">403</h2>
            <p class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
              当前页面无访问权限
            </p>
            <p class="text-sm leading-7 text-[var(--color-brand-muted)]">
              {{ detail }}
            </p>
            <p class="text-sm leading-7 text-[var(--color-brand-muted)]">
              请联系管理员申请权限。
            </p>
          </div>
          <div class="flex flex-wrap justify-center gap-3">
            <button type="button" class="ui-button-secondary" @click="goBack">Go back</button>
            <RouterLink :to="homeTarget" class="ui-button-primary">
              {{ cluster ? 'Open dashboard' : 'Go to clusters' }}
            </RouterLink>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
