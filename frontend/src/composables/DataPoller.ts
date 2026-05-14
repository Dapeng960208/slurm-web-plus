/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { ref, onUnmounted, onMounted } from 'vue'
import type { Ref } from 'vue'
import { i18n } from '@/plugins/i18n'
import {
  AuthenticationError,
  PermissionError,
  CanceledRequestError
} from '@/composables/HTTPErrors'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import type { GatewayAnyClusterApiKey } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import { useErrorsHandler } from '@/composables/ErrorsHandler'

export type ClusterDataPollerQuery = Record<string, string | number | boolean | null | undefined>
export type ClusterDataPollerParam = string | number | ClusterDataPollerQuery

export interface ClusterDataPoller<ResponseType> {
  data: Ref<ResponseType | undefined>
  unable: Ref<boolean>
  loaded: Ref<boolean>
  initialLoading: Ref<boolean>
  refreshing: Ref<boolean>
  refresh: () => Promise<void>
  setCluster: (newCluster: string) => void
  setCallback: (newCallback: GatewayAnyClusterApiKey) => void
  setParam: (newOtherParam: ClusterDataPollerParam | undefined) => void
}

export function useClusterDataPoller<Type>(
  cluster: string,
  initialCallback: GatewayAnyClusterApiKey,
  timeout: number,
  initialOtherParam?: ClusterDataPollerParam
): ClusterDataPoller<Type> {
  let callback = initialCallback
  let otherParam = initialOtherParam
  const data: Ref<Type | undefined> = ref()
  const unable: Ref<boolean> = ref(false)
  const loaded: Ref<boolean> = ref(false)
  const initialLoading: Ref<boolean> = ref(true)
  const refreshing: Ref<boolean> = ref(false)
  let _stop: boolean = false
  let _polling: boolean = false
  const gateway = useGatewayAPI()
  const runtime = useRuntimeStore()
  const { reportAuthenticationError, reportPermissionError } = useErrorsHandler()
  let _timeout: number = -1

  function serializeParam(param: ClusterDataPollerParam | undefined): string {
    return JSON.stringify(param ?? null)
  }

  function reportOtherError(error: Error) {
    runtime.reportError(i18n.global.t('errors.server', { message: error.message }))
    unable.value = true
  }

  async function poll() {
    if (_polling) return
    _polling = true
    initialLoading.value = !loaded.value
    refreshing.value = loaded.value
    try {
      unable.value = false
      if (otherParam !== undefined) {
        const method = gateway[callback] as (
          cluster: string,
          param: ClusterDataPollerParam
        ) => Promise<Type>
        data.value = await method(cluster, otherParam)
      } else {
        const method = gateway[callback] as (cluster: string) => Promise<Type>
        data.value = await method(cluster)
      }

      loaded.value = true
    } catch (error) {
      if (error instanceof AuthenticationError) {
        reportAuthenticationError(error)
      } else if (error instanceof PermissionError) {
        reportPermissionError(error)
        stop()
        unable.value = true
      } else if (!(error instanceof CanceledRequestError) && error instanceof Error) {
        /* Ignore canceled requests errors */
        reportOtherError(error)
      }
    } finally {
      initialLoading.value = false
      refreshing.value = false
      _polling = false
    }
  }

  async function start() {
    console.log(`Start polling ${callback} on cluster ${cluster}`)
    clearTimeout(_timeout)
    if (typeof document !== 'undefined' && document.hidden) {
      _stop = true
      return
    }
    _stop = false
    await poll()
    if (!_stop) {
      _timeout = window.setTimeout(start, timeout)
    }
  }

  function stop() {
    console.log(`Stop polling ${callback} for cluster ${cluster}`)
    _stop = true
    clearTimeout(_timeout)
    gateway.abort()
  }

  function setCluster(newCluster: string) {
    stop()
    cluster = newCluster
    data.value = undefined
    unable.value = false
    loaded.value = false
    initialLoading.value = true
    refreshing.value = false
    start()
  }

  function setCallback(newCallback: GatewayAnyClusterApiKey) {
    stop()
    callback = newCallback
    data.value = undefined
    unable.value = false
    loaded.value = false
    initialLoading.value = true
    refreshing.value = false
    start()
  }

  function setParam(newOtherParam: ClusterDataPollerParam | undefined) {
    if (serializeParam(otherParam) === serializeParam(newOtherParam)) return
    stop()
    otherParam = newOtherParam
    data.value = undefined
    unable.value = false
    loaded.value = false
    initialLoading.value = true
    refreshing.value = false
    start()
  }

  async function refresh() {
    clearTimeout(_timeout)
    _stop = false
    await poll()
    if (!_stop && (typeof document === 'undefined' || !document.hidden)) {
      _timeout = window.setTimeout(start, timeout)
    }
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      stop()
    } else {
      start()
    }
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    start()
  })
  onUnmounted(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    stop()
  })

  return {
    data,
    unable,
    loaded,
    initialLoading,
    refreshing,
    refresh,
    setCluster,
    setCallback,
    setParam
  }
}
