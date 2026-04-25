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
import { formatPercentValue } from '@/composables/percentages'

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
      borderColor: '#50697f',
      backgroundColor: 'rgba(80, 105, 127, 0.12)',
      borderWidth: 2.4,
      pointRadius: 0,
      tension: 0.32
    },
    {
      label: 'Memory',
      data: toPoints(history.memory_usage),
      borderColor: '#7bbf1f',
      backgroundColor: 'rgba(123, 191, 31, 0.14)',
      borderWidth: 2.4,
      pointRadius: 0,
      tension: 0.32
    },
    {
      label: 'Disk',
      data: toPoints(history.disk_usage),
      borderColor: '#d84b50',
      backgroundColor: 'rgba(216, 75, 80, 0.12)',
      borderWidth: 2.4,
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
            color: '#383b40',
            boxWidth: 12,
            boxHeight: 12,
            padding: 18,
            usePointStyle: true,
            pointStyle: 'line'
          }
        },
        tooltip: {
          backgroundColor: 'rgba(32, 42, 53, 0.94)',
          titleColor: '#eef3f4',
          bodyColor: '#eef3f4',
          borderColor: 'rgba(182, 232, 44, 0.28)',
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            label: (context) => `${context.dataset.label}: ${formatPercentValue(context.parsed.y, 2)}%`
          }
        }
      },
      scales: {
        x: {
          type: 'time',
          grid: {
            color: 'rgba(80, 105, 127, 0.08)'
          },
          ticks: {
            color: '#6c7a80',
            maxRotation: 0
          },
          time: {
            tooltipFormat: 'yyyy-LL-dd HH:mm'
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: 100,
          grid: {
            color: 'rgba(80, 105, 127, 0.1)'
          },
          ticks: {
            color: '#6c7a80',
            callback: (value) => `${formatPercentValue(Number(value), 0)}%`
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
