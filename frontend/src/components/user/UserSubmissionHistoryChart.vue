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
import type { UserMetricsHistory } from '@/composables/GatewayAPI'

const { history } = defineProps<{
  history: UserMetricsHistory | null
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
      label: 'Submissions',
      data: toPoints(history.submissions),
      borderColor: '#50697f',
      backgroundColor: 'rgba(80, 105, 127, 0.14)',
      borderWidth: 2.4,
      pointRadius: 0,
      tension: 0.28,
      fill: true
    },
    {
      label: 'Completions',
      data: toPoints(history.completions ?? []),
      borderColor: '#ef9b28',
      backgroundColor: 'rgba(239, 155, 40, 0.1)',
      borderWidth: 2.2,
      pointRadius: 0,
      tension: 0.24,
      fill: false
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
          display: true,
          labels: {
            color: '#6c7a80',
            usePointStyle: true,
            boxWidth: 8
          }
        },
        tooltip: {
          backgroundColor: 'rgba(32, 42, 53, 0.94)',
          titleColor: '#eef3f4',
          bodyColor: '#eef3f4',
          borderColor: 'rgba(182, 232, 44, 0.28)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(0)} jobs`
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
          grid: {
            color: 'rgba(80, 105, 127, 0.1)'
          },
          ticks: {
            color: '#6c7a80',
            precision: 0,
            callback: (value) => `${value}`
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
  <div class="ui-chart-shell h-[16rem]">
    <canvas ref="chartCanvas" class="h-full w-full" />
  </div>
</template>
