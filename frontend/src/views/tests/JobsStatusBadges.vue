<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'

const badges = [
  { status: ['PENDING'], desc: 'Queued waiting for initiation' },
  { status: ['RUNNING'], desc: 'Allocated resources and executing' },
  { status: ['SUSPENDED'], desc: 'Allocated resources, execution suspended' },
  { status: ['COMPLETED'], desc: 'Completed execution successfully' },
  { status: ['CANCELLED'], desc: 'Cancelled by user' },
  { status: ['FAILED'], desc: 'Completed execution unsuccessfully' },
  { status: ['TIMEOUT'], desc: 'Terminated on reaching time limit' },
  { status: ['NODE_FAIL'], desc: 'Terminated on node failure' },
  { status: ['PREEMPTED'], desc: 'Terminated due to preemption' },
  { status: ['BOOT_FAIL'], desc: 'Terminated due to node boot failure' },
  { status: ['DEADLINE'], desc: 'Terminated on deadline' },
  { status: ['OUT_OF_MEMORY'], desc: 'Experienced out of memory error' },
  { status: ['FAILED', 'LAUNCH_FAILED'], desc: 'Job launch failed' },
  { status: ['PENDING', 'REQUEUED', 'RECONFIG_FAIL'], desc: 'Node configuration failed and the job was requeued' },
  { status: ['PENDING', 'POWER_UP_NODE'], desc: 'Allocated powered down nodes, waiting for reboot' },
  { status: ['RUNNING', 'COMPLETING'], desc: 'Waiting for epilog completion' },
  { status: ['COMPLETED', 'STAGE_OUT'], desc: 'Staging out data from burst buffer' },
  { status: ['PENDING', 'CONFIGURING'], desc: 'Allocated nodes are booting' },
  { status: ['RUNNING', 'RESIZING'], desc: 'Job size is about to change' },
  { status: ['PENDING', 'REQUEUED'], desc: 'Job was requeued in completing state' },
  { status: ['PENDING', 'REQUEUE_FED'], desc: 'Job is being requeued by federation' },
  { status: ['PENDING', 'REQUEUE_HOLD'], desc: 'Job is requeued in hold' },
  { status: ['PENDING', 'RESV_DEL_HOLD'], desc: 'Job is being held' },
  { status: ['FAILED', 'SPECIAL_EXIT'], desc: 'Exit state requires requeue hold' },
  { status: ['RUNNING', 'STOPPED'], desc: 'Job is stopped while still holding resources' },
  { status: ['FAILED', 'REVOKED'], desc: 'Sibling job revoked' },
  { status: ['TIMEOUT', 'SIGNALING'], desc: 'Outgoing signal is pending' }
]
</script>

<template>
  <div class="ui-page mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
    <PageHeader
      kicker="Visual Test"
      title="Job Status Badges"
      description="Reference surface for verifying updated job state badge styling."
      :metric-value="badges.length"
      metric-label="states"
    />

    <div class="ui-table-shell overflow-x-auto">
      <div class="inline-block min-w-full align-middle">
        <table class="ui-table min-w-full">
          <thead>
            <tr>
              <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Badge</th>
              <th scope="col" class="px-3 py-3.5 text-left">Status</th>
              <th scope="col" class="px-3 py-3.5 text-left">Description</th>
            </tr>
          </thead>
          <tbody class="text-sm text-[var(--color-brand-muted)]">
            <tr v-for="badge in badges" :key="badge.desc">
              <td class="py-4 pr-3 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                <JobStatusBadge :status="badge.status" />
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
