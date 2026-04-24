<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onMounted, onUnmounted, useTemplateRef, watch } from 'vue'
import { Chart } from 'chart.js/auto'
import type { TooltipItem } from 'chart.js'
import type { UserToolActivityRecord } from '@/composables/GatewayAPI'

const { tools } = defineProps<{
  tools: UserToolActivityRecord[]
}>()

const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
let chart: Chart<'bar'> | null = null

function formatDuration(seconds: number | null): string {
  if (seconds == null || Number.isNaN(seconds)) return 'N/A'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function updateChart() {
  if (!chart) return

  chart.data.labels = tools.map((tool) => tool.tool)
  chart.data.datasets = [
    {
      label: 'Jobs',
      data: tools.map((tool) => tool.jobs),
      backgroundColor: 'rgba(80, 105, 127, 0.82)',
      borderRadius: 10,
      borderSkipped: false,
      maxBarThickness: 18
    }
  ]
  chart.update()
}

onMounted(() => {
  if (!chartCanvas.value) return
  chart = new Chart(chartCanvas.value, {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(32, 42, 53, 0.94)',
          titleColor: '#eef3f4',
          bodyColor: '#eef3f4',
          borderColor: 'rgba(182, 232, 44, 0.28)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (context: TooltipItem<'bar'>) => {
              const tool = tools[context.dataIndex]
              return `${tool.jobs} jobs`
            },
            afterBody: (items: TooltipItem<'bar'>[]) => {
              const tool = tools[items[0].dataIndex]
              return [
                `Avg memory: ${
                  tool.avg_max_memory_mb != null
                    ? `${Math.round(tool.avg_max_memory_mb)} MB`
                    : 'N/A'
                }`,
                `Avg CPU: ${
                  tool.avg_cpu_cores != null ? `${tool.avg_cpu_cores.toFixed(1)} cores` : 'N/A'
                }`,
                `Avg runtime: ${formatDuration(tool.avg_runtime_seconds)}`
              ]
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: {
            color: 'rgba(80, 105, 127, 0.08)'
          },
          ticks: {
            color: '#6c7a80',
            precision: 0
          }
        },
        y: {
          grid: {
            display: false
          },
          ticks: {
            color: '#383b40'
          }
        }
      }
    }
  })
  updateChart()
})

watch(
  () => tools,
  () => updateChart(),
  { deep: true }
)

onUnmounted(() => {
  chart?.destroy()
})
</script>

<template>
  <div class="ui-chart-shell h-[18rem]">
    <canvas ref="chartCanvas" class="h-full w-full" />
  </div>
</template>
