/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

type RgbColor = {
  red: number
  green: number
  blue: number
}

export const QUEUE_WAIT_BASELINE_SECONDS = 60
export const QUEUE_WAIT_WARNING_SECONDS = 300
export const QUEUE_WAIT_DANGER_SECONDS = 900

const baseColor: RgbColor = {
  red: 182,
  green: 232,
  blue: 44
}

const warningColor: RgbColor = {
  red: 239,
  green: 155,
  blue: 40
}

const dangerColor: RgbColor = {
  red: 216,
  green: 75,
  blue: 80
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function interpolateColor(start: RgbColor, end: RgbColor, ratio: number): RgbColor {
  return {
    red: Math.round(start.red + (end.red - start.red) * ratio),
    green: Math.round(start.green + (end.green - start.green) * ratio),
    blue: Math.round(start.blue + (end.blue - start.blue) * ratio)
  }
}

function toRgba(color: RgbColor, alpha: number): string {
  return `rgba(${color.red}, ${color.green}, ${color.blue}, ${clamp(alpha, 0, 1)})`
}

function resolveColor(seconds: number): RgbColor {
  if (seconds <= QUEUE_WAIT_BASELINE_SECONDS) return baseColor

  if (seconds <= QUEUE_WAIT_WARNING_SECONDS) {
    const ratio =
      (seconds - QUEUE_WAIT_BASELINE_SECONDS) /
      (QUEUE_WAIT_WARNING_SECONDS - QUEUE_WAIT_BASELINE_SECONDS)
    return interpolateColor(baseColor, warningColor, ratio)
  }

  if (seconds <= QUEUE_WAIT_DANGER_SECONDS) {
    const ratio =
      (seconds - QUEUE_WAIT_WARNING_SECONDS) /
      (QUEUE_WAIT_DANGER_SECONDS - QUEUE_WAIT_WARNING_SECONDS)
    return interpolateColor(warningColor, dangerColor, ratio)
  }

  return dangerColor
}

export function queueWaitColorForSeconds(seconds: number, alpha = 1): string {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(seconds, 0) : 0
  return toRgba(resolveColor(safeSeconds), alpha)
}

export function queueWaitGradientStop(seconds: number, maxSeconds: number): number {
  const safeMaxSeconds = Math.max(maxSeconds, QUEUE_WAIT_DANGER_SECONDS)
  return clamp(seconds / safeMaxSeconds, 0, 1)
}
