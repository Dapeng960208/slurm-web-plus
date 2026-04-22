<script setup lang="ts">
withDefaults(
  defineProps<{
    cards?: number
  }>(),
  {
    cards: 4
  }
)
</script>

<template>
  <div class="ui-stat-grid" data-testid="stat-card-skeleton">
    <div
      v-for="card in cards"
      :key="card"
      class="ui-stat-card animate-pulse"
    >
      <div class="h-3 w-20 rounded-full bg-[rgba(80,105,127,0.12)]" />
      <div class="mt-4 h-8 w-24 rounded-full bg-[rgba(80,105,127,0.12)]" />
      <div class="mt-3 h-3 w-28 rounded-full bg-[rgba(80,105,127,0.12)]" />
    </div>
  </div>
</template>
