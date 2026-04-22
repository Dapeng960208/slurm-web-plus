<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number
  }>(),
  {
    rows: 4
  }
)
</script>

<template>
  <div class="ui-panel ui-section animate-pulse" data-testid="panel-skeleton">
    <div class="mb-5">
      <div class="h-5 w-40 rounded-full bg-[rgba(80,105,127,0.12)]" />
      <div class="mt-3 h-4 w-full rounded-full bg-[rgba(80,105,127,0.12)]" />
    </div>
    <div class="space-y-4">
      <div
        v-for="row in rows"
        :key="row"
        class="h-4 rounded-full bg-[rgba(80,105,127,0.12)]"
      />
    </div>
  </div>
</template>
