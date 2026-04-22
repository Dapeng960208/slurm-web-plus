<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import BrandLogo from '@/components/BrandLogo.vue'
</script>

<template>
  <main class="ui-public-shell">
    <section class="ui-public-grid">
      <aside class="ui-public-aside">
        <div class="space-y-6">
          <BrandLogo size="lg" />
          <div class="space-y-4">
            <p class="ui-page-kicker">Missing Route</p>
            <h1 class="text-4xl font-bold text-white md:text-5xl">Page not found</h1>
            <p class="max-w-xl text-sm leading-7 text-white/72 md:text-base">
              The requested route is unavailable or has moved. Return to the cluster gateway to
              continue.
            </p>
          </div>
        </div>
      </aside>
      <div class="ui-public-panel flex items-center justify-center px-5 py-6 sm:px-8">
        <div class="mx-auto max-w-md text-center">
          <div class="mb-8">
            <h2 class="text-[7rem] font-bold leading-none text-[var(--color-brand-muted)]" aria-label="404">404</h2>
          </div>
          <div class="mb-8">
            <p class="text-sm leading-7 text-[var(--color-brand-muted)]">
              The page you are looking for does not exist or has been moved.
            </p>
          </div>
          <div>
            <RouterLink :to="{ name: 'clusters' }" class="ui-button-primary">
              Go to clusters
            </RouterLink>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
