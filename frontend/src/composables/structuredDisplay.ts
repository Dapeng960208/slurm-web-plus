/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

export interface SummaryField {
  key: string
  label: string
  value: string
}

export interface SummaryCard {
  title: string
  badge?: string
  fields: SummaryField[]
}

type UnknownRecord = Record<string, unknown>

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isPrimitiveValue(value: unknown): value is string | number | boolean {
  return ['string', 'number', 'boolean'].includes(typeof value)
}

function toTitleCase(key: string): string {
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function formatStructuredValue(value: unknown): string {
  if (value == null) return '--'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '--'
  if (typeof value === 'string') return value.trim() || '--'
  if (Array.isArray(value) && value.every((item) => isPrimitiveValue(item))) {
    return value.length > 0 ? value.map((item) => formatStructuredValue(item)).join(', ') : '--'
  }
  return '--'
}

export function extractSummaryFields(
  payload: unknown,
  options: {
    preferredOrder?: string[]
    labelMap?: Record<string, string>
    omitKeys?: string[]
  } = {}
): SummaryField[] {
  if (!isRecord(payload)) return []

  const preferredOrder = options.preferredOrder ?? []
  const labelMap = options.labelMap ?? {}
  const omitKeys = new Set(options.omitKeys ?? [])
  const keys = Object.keys(payload).filter((key) => !omitKeys.has(key))
  keys.sort((left, right) => {
    const leftIndex = preferredOrder.indexOf(left)
    const rightIndex = preferredOrder.indexOf(right)
    if (leftIndex === -1 && rightIndex === -1) return left.localeCompare(right)
    if (leftIndex === -1) return 1
    if (rightIndex === -1) return -1
    return leftIndex - rightIndex
  })

  return keys
    .map((key) => {
      const value = payload[key]
      if (
        !isPrimitiveValue(value) &&
        !(Array.isArray(value) && value.every((item) => isPrimitiveValue(item)))
      ) {
        return null
      }
      return {
        key,
        label: labelMap[key] ?? toTitleCase(key),
        value: formatStructuredValue(value)
      }
    })
    .filter((field): field is SummaryField => field !== null)
}

function pickArray(payload: unknown, keys: string[]): UnknownRecord[] {
  if (Array.isArray(payload)) {
    return payload.filter((item): item is UnknownRecord => isRecord(item))
  }
  if (!isRecord(payload)) return []
  for (const key of keys) {
    const value = payload[key]
    if (Array.isArray(value)) {
      return value.filter((item): item is UnknownRecord => isRecord(item))
    }
  }
  return []
}

export function extractSummaryCards(
  payload: unknown,
  options: {
    listKeys?: string[]
    titleKeys?: string[]
    badgeKeys?: string[]
    preferredOrder?: string[]
    labelMap?: Record<string, string>
    fallbackTitle?: string
  } = {}
): SummaryCard[] {
  const records = pickArray(payload, options.listKeys ?? [])
  const titleKeys = options.titleKeys ?? []
  const badgeKeys = options.badgeKeys ?? []
  const fallbackTitle = options.fallbackTitle ?? 'Item'

  return records.map((record, index) => {
    const title =
      titleKeys
        .map((key) => record[key])
        .find((value) => typeof value === 'string' && value.trim().length > 0) ??
      `${fallbackTitle} ${index + 1}`

    const badgeValue = badgeKeys
      .map((key) => record[key])
      .find((value) => isPrimitiveValue(value) && String(value).trim().length > 0)

    return {
      title: String(title),
      badge: badgeValue != null ? String(badgeValue) : undefined,
      fields: extractSummaryFields(record, {
        preferredOrder: options.preferredOrder,
        labelMap: options.labelMap,
        omitKeys: [...titleKeys, ...badgeKeys]
      })
    }
  })
}
