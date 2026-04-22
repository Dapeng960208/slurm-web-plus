<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number
  }>(),
  {
    rows: 8
  }
)
</script>

<template>
  <div class="ui-detail-list animate-pulse" data-testid="detail-skeleton-list">
    <dl>
      <div
        v-for="row in rows"
        :key="row"
        class="px-4 py-3 sm:grid sm:grid-cols-3 sm:gap-5 sm:px-0"
      >
        <dt class="h-4 w-24 rounded-full bg-[rgba(80,105,127,0.12)]" />
        <dd class="mt-3 sm:col-span-2 sm:mt-0">
          <div class="h-4 w-full rounded-full bg-[rgba(80,105,127,0.12)]" />
        </dd>
      </div>
    </dl>
  </div>
</template>
