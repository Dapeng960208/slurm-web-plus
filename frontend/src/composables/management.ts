/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

export function parseCsvList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

export function stringifyList(values: string[] | string | null | undefined): string {
  if (!values) return ''
  if (typeof values === 'string') return values
  return values.join(', ')
}
