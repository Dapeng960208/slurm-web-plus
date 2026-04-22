/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

export function formatGigabytes(value: number): string {
  return `${Math.round(value * 100) / 100}GB`
}
