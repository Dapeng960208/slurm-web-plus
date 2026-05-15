<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, onUnmounted, useTemplateRef, watch } from 'vue'
import { Chart } from 'chart.js/auto'
import type { Point } from 'chart.js'
import 'chartjs-adapter-luxon'
import { useI18n } from 'vue-i18n'
import type { UserMetricsHistory } from '@/composables/GatewayAPI'

const { history } = defineProps<{
  history: UserMetricsHistory | null
}>()

const { t, locale } = useI18n()
const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
let chart: Chart<'line'> | null = null
const submissionsLabel = computed(() => t('pages.user.analyticsPanels.chart.submissions'))
const completionsLabel = computed(() => t('pages.user.analyticsPanels.chart.completions'))
const runningLabel = computed(() => t('pages.user.analyticsPanels.chart.running'))
const pendingLabel = computed(() => t('pages.user.analyticsPanels.chart.pending'))
const failedLabel = computed(() => t('pages.user.analyticsPanels.chart.failed'))
const cancelledLabel = computed(() => t('pages.user.analyticsPanels.chart.cancelled'))
const jobsUnit = computed(() => t('pages.user.analyticsPanels.chart.jobsUnit'))

function toPoints(series: Array<[number, number]>): Point[] {
  return series.map(([x, y]) => ({ x, y }))
}

function updateChart() {
  if (!chart) return
  if (!history) {
    chart.data.datasets = []
    chart.update('none')
    return
  }

  chart.data.datasets = [
    {
      label: submissionsLabel.value,
      data: toPoints(history.submissions),
      borderColor: '#50697f',
      backgroundColor: 'rgba(80, 105, 127, 0.14)',
      borderWidth: 2.4,
      pointRadius: 0,
      tension: 0.28,
      fill: true
    },
    {
      label: completionsLabel.value,
      data: toPoints(history.completions ?? []),
      borderColor: '#ef9b28',
      backgroundColor: 'rgba(239, 155, 40, 0.1)',
      borderWidth: 2.2,
      pointRadius: 0,
      tension: 0.24,
      fill: false
    },
    {
      label: runningLabel.value,
      data: toPoints(history.running_jobs ?? []),
      borderColor: '#7bbf1f',
      backgroundColor: 'rgba(123, 191, 31, 0.08)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.22,
      fill: false
    },
    {
      label: pendingLabel.value,
      data: toPoints(history.pending_jobs ?? []),
      borderColor: '#d4a03f',
      backgroundColor: 'rgba(212, 160, 63, 0.08)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.22,
      fill: false
    },
    {
      label: failedLabel.value,
      data: toPoints(history.failed_jobs ?? []),
      borderColor: '#d84b50',
      backgroundColor: 'rgba(216, 75, 80, 0.08)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.22,
      fill: false
    },
    {
      label: cancelledLabel.value,
      data: toPoints(history.cancelled_jobs ?? []),
      borderColor: '#8a6fb5',
      backgroundColor: 'rgba(138, 111, 181, 0.08)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.22,
      fill: false
    }
  ]
  chart.update('none')
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
            label: (context) =>
              `${context.dataset.label}: ${context.parsed.y.toFixed(0)} ${jobsUnit.value}`
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

watch(locale, () => updateChart())

onUnmounted(() => {
  chart?.destroy()
})
</script>

<template>
  <div class="ui-chart-shell h-[16rem]">
    <canvas ref="chartCanvas" class="h-full w-full" />
  </div>
</template>
