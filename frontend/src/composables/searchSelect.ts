/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { useGatewayAPI } from '@/composables/GatewayAPI'

export interface SearchSelectOption {
  value: string
  label: string
  description?: string
}

export interface SearchSelectSource {
  search(query: string): Promise<SearchSelectOption[]>
}

export function createUserSearchSource(cluster: string): SearchSelectSource {
  const gateway = useGatewayAPI()
  return {
    async search(query: string) {
      const response = await gateway.access_users(cluster, {
        username: query || undefined,
        page: 1,
        page_size: 20
      })

      return response.items.map((user) => ({
        value: user.username,
        label: user.username,
        description: user.fullname || user.username
      }))
    }
  }
}

export function createStaticSearchSource(
  load: () => Promise<SearchSelectOption[]>
): SearchSelectSource {
  let cached: SearchSelectOption[] | null = null
  let inflight: Promise<SearchSelectOption[]> | null = null

  async function ensureOptions(): Promise<SearchSelectOption[]> {
    if (cached) return cached
    if (!inflight) {
      inflight = load().then((items) => {
        cached = items
        inflight = null
        return items
      })
    }
    return inflight
  }

  return {
    async search(query: string) {
      const options = await ensureOptions()
      const keyword = query.trim().toLowerCase()
      if (!keyword) return options
      return options.filter((option) => {
        const description = option.description?.toLowerCase() ?? ''
        return option.label.toLowerCase().includes(keyword) || description.includes(keyword)
      })
    }
  }
}
