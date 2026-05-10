<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import BrandLogo from '@/components/BrandLogo.vue'

const { t } = useI18n()
</script>

<template>
  <main class="ui-public-shell">
    <section class="ui-public-grid">
      <aside class="ui-public-aside">
        <div class="space-y-6">
          <BrandLogo size="lg" />
          <div class="space-y-4">
            <p class="ui-page-kicker">{{ t('publicPages.notFound.kicker') }}</p>
            <h1 class="text-4xl font-bold text-white md:text-5xl">
              {{ t('publicPages.notFound.title') }}
            </h1>
            <p class="max-w-xl text-sm leading-7 text-white/72 md:text-base">
              {{ t('publicPages.notFound.description') }}
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
              {{ t('publicPages.notFound.detail') }}
            </p>
          </div>
          <div>
            <RouterLink :to="{ name: 'clusters' }" class="ui-button-primary">
              {{ t('publicPages.notFound.goToClusters') }}
            </RouterLink>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
