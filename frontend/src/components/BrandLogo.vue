<script setup lang="ts">
const logoUrl = new URL(
  `${(import.meta.env.BASE_URL ?? '/').replace(/\/?$/, '/')}logo/logo.png`,
  window.location.origin
).toString()

withDefaults(
  defineProps<{
    alt?: string
    size?: 'sm' | 'md' | 'lg'
    framed?: boolean
  }>(),
  {
    alt: 'Slurm-web',
    size: 'md',
    framed: true
  }
)
</script>

<template>
  <div
    :class="[
      framed ? 'brand-logo-frame' : '',
      size === 'sm' ? 'brand-logo-sm' : size === 'lg' ? 'brand-logo-lg' : 'brand-logo-md'
    ]"
  >
    <img :src="logoUrl" :alt="alt" class="brand-logo-image" />
  </div>
</template>
