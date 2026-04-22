<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import NodeMainState from '@/components/resources/NodeMainState.vue'
import NodeAllocationState from '@/components/resources/NodeAllocationState.vue'

const badges = [
  { status: ['DOWN'], desc: 'Node down' },
  { status: ['IDLE'], desc: 'Node idle' },
  { status: ['ALLOCATED'], desc: 'Node allocated' },
  { status: ['MIXED'], desc: 'Node mixed' },
  { status: ['ERROR'], desc: 'Node error' },
  { status: ['FUTURE'], desc: 'Node future' },
  { status: ['MIXED', 'FAIL'], desc: 'Node failing' },
  { status: ['IDLE', 'FAIL'], desc: 'Node failed' },
  { status: ['ALLOCATED', 'DRAIN'], desc: 'Node allocated draining' },
  { status: ['MIXED', 'DRAIN'], desc: 'Node mixed draining' },
  { status: ['IDLE', 'DRAIN'], desc: 'Node drained' },
  { status: ['DOWN', 'NOT_RESPONDING'], desc: 'Node down, not responding' },
  { status: ['IDLE', 'RESERVED'], desc: 'Node idle reserved' },
  { status: ['IDLE', 'UNDRAIN'], desc: 'Node idle undrained' },
  { status: ['FUTURE', 'CLOUD'], desc: 'Node future cloud' },
  { status: ['ALLOCATED', 'COMPLETING'], desc: 'Node allocated completing' },
  { status: ['IDLE', 'POWERED_DOWN'], desc: 'Node idle automatically powered on' },
  { status: ['IDLE', 'POWERING_UP'], desc: 'Node idle automatically powering up' },
  { status: ['IDLE', 'MAINTENANCE'], desc: 'Node idle in maintenance' },
  { status: ['MIXED', 'REBOOT_REQUESTED'], desc: 'Node mixed with reboot requested' },
  { status: ['IDLE', 'POWERING_DOWN'], desc: 'Node idle powering down' },
  { status: ['FUTURE', 'DYNAMIC_FUTURE'], desc: 'Future node dynamic' },
  { status: ['IDLE', 'REBOOT_ISSUED'], desc: 'Node idle with reboot issued' },
  { status: ['IDLE', 'PLANNED'], desc: 'Node idle with planned job' },
  { status: ['DOWN', 'INVALID_REG'], desc: 'Node down with invalid registration' },
  { status: ['IDLE', 'POWER_DOWN'], desc: 'Node idle manually powered down' },
  { status: ['IDLE', 'POWER_UP'], desc: 'Node idle manually powered up' },
  { status: ['MIXED', 'DRAIN', 'POWER_DRAIN'], desc: 'Node mixed manually powered down ASAP' },
  { status: ['FUTURE', 'DYNAMIC_NORM'], desc: 'Future node dynamic norm' }
]
</script>

<template>
  <div class="ui-page mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
    <PageHeader
      kicker="Visual Test"
      title="Node Status Badges"
      description="Reference surface for verifying updated node state and allocation badge styling."
      :metric-value="badges.length"
      metric-label="states"
    />

    <div class="ui-table-shell overflow-x-auto">
      <div class="inline-block min-w-full align-middle">
        <table class="ui-table min-w-full">
          <thead>
            <tr>
              <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Badge</th>
              <th scope="col" class="px-3 py-3.5 text-left">Allocation</th>
              <th scope="col" class="px-3 py-3.5 text-left">Status</th>
              <th scope="col" class="px-3 py-3.5 text-left">Description</th>
            </tr>
          </thead>
          <tbody class="text-sm text-[var(--color-brand-muted)]">
            <tr v-for="badge in badges" :key="badge.desc">
              <td class="py-4 pr-3 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                <NodeMainState :status="badge.status" />
              </td>
              <td class="px-3 py-4 whitespace-nowrap">
                <NodeAllocationState :status="badge.status" />
              </td>
              <td class="px-3 py-4 text-xs whitespace-nowrap">{{ badge.status.join(', ') }}</td>
              <td class="px-3 py-4 whitespace-nowrap">{{ badge.desc }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
