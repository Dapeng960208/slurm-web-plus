<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, onUnmounted, useTemplateRef, watch } from 'vue'
import { Chart } from 'chart.js/auto'
import type { ChartDataset, Point } from 'chart.js'
import 'chartjs-adapter-luxon'
import { useI18n } from 'vue-i18n'
import type { MetricValue } from '@/composables/GatewayAPI'
import {
  QUEUE_WAIT_BASELINE_SECONDS,
  QUEUE_WAIT_DANGER_SECONDS,
  QUEUE_WAIT_WARNING_SECONDS,
  queueWaitColorForSeconds,
  queueWaitGradientStop
} from '@/composables/queueWaitColors'
import type { QueueWaitAggregation } from '@/composables/queueWaitHistory'

const { series, aggregation } = defineProps<{
  series: MetricValue[]
  aggregation: QueueWaitAggregation
}>()

const { t, locale } = useI18n()
const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
const label = computed(() => t('pages.analysis.historical.avgQueueWait'))
const secondsUnit = computed(() => t('pages.analysis.historical.secondsUnit'))
let chart: Chart<'line'> | null = null

function toPoints(values: MetricValue[]): Point[] {
  return values.map(([x, y]) => ({ x, y }))
}

function formatSeconds(value: number): string {
  return String(Math.round(value))
}

function resolveContextValue(context: { parsed?: { y?: number }; raw?: unknown }): number {
  if (typeof context.parsed?.y === 'number') return context.parsed.y
  if (Array.isArray(context.raw) && typeof context.raw[1] === 'number') return context.raw[1]
  if (
    context.raw &&
    typeof context.raw === 'object' &&
    'y' in context.raw &&
    typeof (context.raw as { y?: unknown }).y === 'number'
  ) {
    return (context.raw as { y: number }).y
  }
  return 0
}

function createAreaGradient(chart: Chart<'line'>): CanvasGradient | string {
  const { chartArea, ctx, scales } = chart
  if (!chartArea) return queueWaitColorForSeconds(QUEUE_WAIT_BASELINE_SECONDS, 0.18)

  const maxSeconds = Math.max(
    QUEUE_WAIT_DANGER_SECONDS,
    Number(scales?.y?.max) || 0,
    ...series.map(([, value]) => value)
  )
  const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top)

  gradient.addColorStop(0, queueWaitColorForSeconds(QUEUE_WAIT_BASELINE_SECONDS, 0.12))
  gradient.addColorStop(
    queueWaitGradientStop(QUEUE_WAIT_BASELINE_SECONDS, maxSeconds),
    queueWaitColorForSeconds(QUEUE_WAIT_BASELINE_SECONDS, 0.16)
  )
  gradient.addColorStop(
    queueWaitGradientStop(QUEUE_WAIT_WARNING_SECONDS, maxSeconds),
    queueWaitColorForSeconds(QUEUE_WAIT_WARNING_SECONDS, 0.2)
  )
  gradient.addColorStop(
    queueWaitGradientStop(QUEUE_WAIT_DANGER_SECONDS, maxSeconds),
    queueWaitColorForSeconds(QUEUE_WAIT_DANGER_SECONDS, 0.24)
  )
  gradient.addColorStop(1, queueWaitColorForSeconds(QUEUE_WAIT_DANGER_SECONDS, 0.28))

  return gradient
}

function updateChart() {
  if (!chart) return
  const pointRadius = series.length === 1 ? 4 : 0
  const dataset: ChartDataset<'line', Point[]> = {
    label: label.value,
    data: toPoints(series),
    borderColor: queueWaitColorForSeconds(QUEUE_WAIT_BASELINE_SECONDS),
    backgroundColor: () => createAreaGradient(chart!),
    borderWidth: 2.8,
    pointRadius,
    pointHoverRadius: pointRadius === 0 ? 4 : 6,
    pointBackgroundColor: (context) =>
      queueWaitColorForSeconds(resolveContextValue(context as { parsed?: { y?: number }; raw?: unknown })),
    pointBorderColor: '#f8fbf5',
    pointBorderWidth: 2,
    tension: 0.26,
    fill: true,
    segment: {
      borderColor: (context) => {
        const start = context.p0.parsed.y
        const end = context.p1.parsed.y
        return queueWaitColorForSeconds((start + end) / 2)
      }
    }
  }

  chart.data.datasets = [
    dataset
  ]
  const xScale = chart.options.scales?.x
  if (xScale && 'time' in xScale) {
    xScale.time = {
      ...xScale.time,
      tooltipFormat: aggregation === 'day' ? 'yyyy-LL-dd' : 'yyyy-LL-dd HH:mm'
    }
  }
  const yScale = chart.options.scales?.y
  if (yScale && 'title' in yScale) {
    yScale.title = {
      ...yScale.title,
      display: true,
      text: secondsUnit.value,
      color: '#6c7a80'
    }
  }
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
            label: (context) =>
              `${context.dataset.label}: ${formatSeconds(context.parsed.y)} ${secondsUnit.value}`
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
            tooltipFormat: aggregation === 'day' ? 'yyyy-LL-dd' : 'yyyy-LL-dd HH:mm'
          }
        },
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(80, 105, 127, 0.1)'
          },
          ticks: {
            color: '#6c7a80',
            callback: (value) => `${formatSeconds(Number(value))}`
          },
          title: {
            display: true,
            text: secondsUnit.value,
            color: '#6c7a80'
          }
        }
      }
    }
  })
  updateChart()
})

watch(
  () => [series, aggregation],
  () => updateChart(),
  { deep: true }
)

watch(locale, () => updateChart())

onUnmounted(() => {
  chart?.destroy()
})
</script>

<template>
  <div class="ui-chart-shell h-[15rem]">
    <canvas ref="chartCanvas" class="h-full w-full" />
  </div>
</template>
