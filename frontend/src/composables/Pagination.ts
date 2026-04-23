/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

export const DEFAULT_PAGE_SIZE = 25
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const
export type PageSizeOption = (typeof PAGE_SIZE_OPTIONS)[number]

export function parsePositivePage(value: unknown): number {
  if (typeof value !== 'string') return 1
  const parsed = parseInt(value, 10)
  return Number.isNaN(parsed) ? 1 : Math.max(parsed, 1)
}

export function parsePageSize(value: unknown): PageSizeOption {
  if (typeof value !== 'string') return DEFAULT_PAGE_SIZE
  const parsed = parseInt(value, 10)
  return PAGE_SIZE_OPTIONS.includes(parsed as PageSizeOption)
    ? (parsed as PageSizeOption)
    : DEFAULT_PAGE_SIZE
}

export function lastPage(total: number, pageSize: number): number {
  return Math.max(Math.ceil(total / pageSize), 1)
}

export function paginationRange(
  currentPage: number,
  totalPages: number
): { id: number; ellipsis: boolean }[] {
  const result: { id: number; ellipsis: boolean }[] = []
  let ellipsis = false

  for (let page = 1; page <= totalPages; page++) {
    if (page < 3 || page > totalPages - 2 || (page >= currentPage - 1 && page <= currentPage + 1)) {
      ellipsis = false
      result.push({ id: page, ellipsis: false })
    } else if (!ellipsis) {
      ellipsis = true
      result.push({ id: page, ellipsis: true })
    }
  }

  return result
}
