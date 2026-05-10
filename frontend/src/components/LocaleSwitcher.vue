<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'
import type { SupportedLocale } from '@/i18n/locale'

const { compact = false } = defineProps<{
  compact?: boolean
}>()

const { t } = useI18n()
const localeStore = useLocaleStore()

const options = computed<Array<{ value: SupportedLocale; label: string }>>(() => [
  { value: 'zh-CN', label: t('common.locale.zhCN') },
  { value: 'en', label: t('common.locale.en') }
])

function updateLocale(event: Event) {
  localeStore.setLocale((event.target as HTMLSelectElement).value as SupportedLocale)
}
</script>

<template>
  <label
    class="flex items-center gap-2 text-sm text-[var(--color-brand-muted)]"
    :class="compact ? 'justify-between' : ''"
  >
    <span class="font-medium text-[var(--color-brand-ink-strong)]">
      {{ t('common.locale.switcher') }}
    </span>
    <select
      :value="localeStore.locale"
      class="rounded-full border-[rgba(80,105,127,0.16)] bg-white px-3 py-2 text-sm font-semibold text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] focus:border-[rgba(182,232,44,0.65)] focus:ring-[rgba(182,232,44,0.18)]"
      @change="updateLocale"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
  </label>
</template>
