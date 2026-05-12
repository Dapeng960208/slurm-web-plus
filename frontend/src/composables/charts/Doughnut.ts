/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT

*/
import { onMounted, useTemplateRef } from 'vue'
import { Chart } from 'chart.js/auto'
import type { ChartOptions } from 'chart.js'

export default function useDoughnutChart(
  canvasRef: string,
  labels: { name: string; color: string }[],
  data: number[]
) {
  const chartCanvas = useTemplateRef<HTMLCanvasElement>(canvasRef)
  let currentLabels = labels

  let chart: Chart | null = null
  const genericOptions: ChartOptions = {
    responsive: true,

    plugins: {
      legend: {
        position: 'top'
      }
    }
  }

  let borderColor = '#ffffff'
  /* Detect dark mode to set darker grid and axis colors */
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    borderColor = '#333333'
  }

  function updateData(data: number[]) {
    if (!chart) return
    chart.data.labels = currentLabels.map((label) => label.name)
    chart.data.datasets = [
      {
        data: data,
        backgroundColor: currentLabels.map((label) => label.color),
        borderColor: borderColor,
        rotation: 180
      }
    ]
    chart.update()
  }

  function setLabels(newLabels: { name: string; color: string }[]) {
    currentLabels = newLabels
    if (!chart) return
    chart.data.labels = currentLabels.map((label) => label.name)
    if (chart.data.datasets[0]) {
      chart.data.datasets[0].backgroundColor = currentLabels.map((label) => label.color)
    }
    chart.update()
  }

  onMounted(() => {
    if (chartCanvas.value) {
      chart = new Chart(chartCanvas.value, {
        type: 'doughnut',
        data: {
          labels: currentLabels.map((label) => label.name),
          datasets: []
        },
        options: genericOptions
      })
      updateData(data)
    }
  })

  return { updateData, setLabels }
}
