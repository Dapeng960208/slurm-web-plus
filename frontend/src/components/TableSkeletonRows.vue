<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    columns: number
    rows?: number
    firstCellClass?: string
    cellClass?: string
  }>(),
  {
    rows: 5,
    firstCellClass: '',
    cellClass: ''
  }
)
</script>

<template>
  <tbody class="divide-y divide-gray-200 text-sm text-gray-500 dark:divide-gray-700 dark:text-gray-300">
    <tr v-for="row in props.rows" :key="row" class="animate-pulse" data-testid="table-skeleton-row">
      <td
        v-for="column in props.columns"
        :key="`${row}-${column}`"
        :class="[
          column === 1 ? props.firstCellClass : props.cellClass,
          'px-3 py-4 whitespace-nowrap'
        ]"
      >
        <div
          :class="[
            column === 1 ? 'w-16' : column === props.columns ? 'ml-auto w-8' : 'w-full',
            'h-4 rounded-full bg-[rgba(80,105,127,0.12)]'
          ]"
        />
      </td>
    </tr>
  </tbody>
</template>
