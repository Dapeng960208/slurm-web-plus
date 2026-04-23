<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onMounted, onUnmounted, useTemplateRef, watch } from 'vue'
import { Chart } from 'chart.js/auto'
import type { Point } from 'chart.js'
import 'chartjs-adapter-luxon'
import type { NodeMetricsHistory } from '@/composables/GatewayAPI'

const { history } = defineProps<{
  history: NodeMetricsHistory | null
}>()

const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
let chart: Chart<'line'> | null = null

function toPoints(series: Array<[number, number]>): Point[] {
  return series.map(([x, y]) => ({ x, y }))
}

function updateChart() {
  if (!chart) return
  if (!history) {
    chart.data.datasets = []
    chart.update()
    return
  }

  chart.data.datasets = [
    {
      label: 'CPU',
      data: toPoints(history.cpu_usage),
      borderColor: 'rgb(80, 105, 127)',
      backgroundColor: 'rgba(80, 105, 127, 0.12)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.32
    },
    {
      label: 'Memory',
      data: toPoints(history.memory_usage),
      borderColor: 'rgb(110, 141, 43)',
      backgroundColor: 'rgba(110, 141, 43, 0.12)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.32
    },
    {
      label: 'Disk',
      data: toPoints(history.disk_usage),
      borderColor: 'rgb(239, 155, 40)',
      backgroundColor: 'rgba(239, 155, 40, 0.12)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.32
    }
  ]
  chart.update()
}

onMounted(() => {
  if (!chartCanvas.value) return
  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: { datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            boxHeight: 12
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        x: {
          type: 'time',
          time: {
            tooltipFormat: 'yyyy-LL-dd HH:mm'
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: 100,
          ticks: {
            callback: (value) => `${value}%`
          }
        }
      }
    }
  })
  updateChart()
})

watch(
  () => history,
  () => updateChart(),
  { deep: true }
)

onUnmounted(() => {
  chart?.destroy()
})
</script>

<template>
  <div class="ui-chart-shell h-[14rem]">
    <canvas ref="chartCanvas" class="h-full w-full" />
  </div>
</template>
