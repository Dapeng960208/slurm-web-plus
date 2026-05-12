const en = {
  analysis: {
    labels: {
      latencyMs: 'Latency (ms)',
      jobsSubmitted: 'Jobs Submitted',
      jobsStarted: 'Jobs Started',
      jobsCompleted: 'Jobs Completed',
      jobsCanceled: 'Jobs Canceled',
      scheduleCycleLast: 'Schedule Cycle Last',
      scheduleCycleMax: 'Schedule Cycle Max',
      scheduleCycleMean: 'Schedule Cycle Mean'
    },
    scoreSummary: {
      efficient: 'Resources are well used and queue pressure is currently contained.',
      recoverCapacity:
        'Cluster throughput is being reduced by unavailable capacity that should be recovered first.',
      fragmentation:
        'Idle capacity exists, but job shape and node packing are preventing fast starts.',
      backlog: 'Backlog is building faster than the scheduler can admit work.',
      steady: 'The cluster is operating steadily with limited queue friction.'
    },
    summary: {
      cpuOccupancy: {
        label: 'CPU occupancy',
        detail: '{busy} of {total} CPU(s) are currently busy.',
        unavailable: 'CPU occupancy is not available.'
      },
      queuePressure: {
        label: 'Queue pressure',
        low: 'Low',
        detail: '{pending} pending job(s) versus {running} active job(s).'
      },
      waitSample: {
        label: 'Queue wait',
        value: '{minutes} min',
        proxy: 'Proxy',
        detail: 'Median wait from {samples} recent completed jobs.',
        fallback:
          'Using live backlog as the queue delay proxy because history samples are unavailable.'
      },
      recovery: {
        label: 'Recovery potential',
        unavailable: 'Recovering unavailable capacity will immediately increase admission throughput.',
        available: 'Schedulable free CPU currently available for backfill and smaller jobs.'
      }
    },
    capacity: {
      cpu: {
        label: 'CPU busy',
        detail: '{busy}/{total} CPU(s) allocated or requested by active jobs.',
        unavailable: 'CPU totals are unavailable.'
      },
      memory: {
        label: 'Memory committed',
        detail: '{committed} committed out of {total}.',
        unavailable: 'Memory commitment is unavailable in current telemetry.'
      },
      gpu: {
        label: 'GPU busy',
        detail: '{running}/{total} GPU(s) are actively in use.',
        unavailable: 'No GPU capacity is declared for this cluster.'
      },
      nodes: {
        label: 'Schedulable nodes',
        detail: '{schedulable}/{total} node(s) are currently schedulable.',
        unavailable: 'Node inventory is unavailable.'
      }
    },
    recommendations: {
      recoverCapacity: {
        title: 'Recover unavailable nodes before planning expansion',
        summary: 'The fastest capacity gain comes from returning drained or down nodes to service.',
        evidence: '{nodes} node(s) and {cpu} CPU(s) are currently unavailable.'
      },
      fragmentation: {
        title: 'Mitigate CPU fragmentation for single-node jobs',
        summary:
          'Backfill smaller jobs, reduce oversized single-node requests or rebalance partitions to turn idle cores into admitted work.',
        evidence:
          '{count} pending job(s) can fit in cluster-wide free CPU but not on any single schedulable node.'
      },
      expandBusy: {
        title: 'Expand or rebalance the busiest capacity pool',
        summary:
          'Resource-bound jobs dominate the queue while active capacity is already heavily occupied.',
        evidence:
          '{share}% of pending jobs are blocked on resources at {cpu}% CPU occupancy.'
      },
      priority: {
        title: 'Review QOS and priority policy before adding hardware',
        summary: 'Queue delay appears to be policy-bound rather than purely capacity-bound.',
        evidence:
          '{share}% of pending jobs are blocked by priority while CPU occupancy is {cpu}%.'
      },
      gpu: {
        title: 'Protect GPU throughput with tighter GPU queue classes',
        summary: 'GPU demand is building while accelerator capacity is already hot.',
        evidence:
          '{gpu} GPU(s) are requested by pending jobs and active GPU occupancy is {occupancy}%.'
      },
      waitTime: {
        title: 'Reduce queue wait with shorter walltime classes and backfill',
        summary:
          'Observed wait samples show users are spending meaningful time in queue before admission.',
        evidence: 'Median sampled queue wait is {minutes} min across {samples} completed jobs.'
      },
      balance: {
        title: 'Keep admission balanced across job sizes',
        summary:
          'Track partition pressure and promote smaller backfill windows to keep the cluster full without starving large jobs.',
        evidence:
          '{pending} pending job(s), {running} active job(s) and {cpu} schedulable free CPU(s) are in play right now.'
      }
    },
    historyCards: {
      peakPending: {
        label: 'Peak pending',
        detail: 'Largest queued backlog in the selected telemetry range.'
      },
      averagePending: {
        label: 'Average pending',
        detail: 'Average queue depth across the selected range.'
      },
      peakRunning: {
        label: 'Peak running',
        detail: 'Maximum concurrently running jobs observed in range.'
      },
      busyCores: {
        label: 'Peak busy cores',
        detail: '{percent} average of declared CPU capacity',
        unavailable: 'CPU history unavailable'
      }
    }
  },
  common: {
    locale: {
      en: 'English',
      zhCN: 'Simplified Chinese',
      switcher: 'Language'
    },
    buttons: {
      close: 'Close',
      cancel: 'Cancel',
      apply: 'Apply',
      reset: 'Reset',
      goBack: 'Go back',
      signIn: 'Sign in',
      signOut: 'Sign out',
      create: 'Create',
      edit: 'Edit',
      delete: 'Delete',
      view: 'View',
      saveChanges: 'Save changes',
      open: 'Open',
      search: 'Search',
      retry: 'Retry',
      today: 'Today'
    },
    notifications: {
      info: 'Info',
      error: 'Error',
      close: 'Close'
    },
    pagination: {
      showing: 'Showing',
      to: 'to',
      of: 'of',
      perPage: 'Per page',
      previous: 'Previous',
      next: 'Next',
      itemCount: '{count} {label}',
      itemCount_plural: '{count} {label}s'
    },
    status: {
      loading: 'Loading',
      working: 'Working...',
      refreshing: 'Refreshing...',
      unavailable: 'Unavailable',
      noData: 'No data',
      noPermission: 'No permission',
      disabled: 'Disabled',
      healthy: 'Healthy',
      stable: 'Stable',
      nominal: 'Nominal',
      attention: 'Attention',
      highLoad: 'High load',
      highUsage: 'High usage'
    },
    forms: {
      required: 'Required',
      optional: 'Optional',
      selectOption: 'Select an option'
    },
    labels: {
      state: 'State',
      user: 'User',
      group: 'Group',
      account: 'Account',
      partition: 'Partition',
      qos: 'QOS',
      priority: 'Priority',
      reason: 'Reason',
      actions: 'Actions',
      resources: 'Resources',
      memory: 'Memory',
      cpu: 'CPU',
      gpu: 'GPU',
      nodes: 'Nodes',
      timeRange: 'Time Range',
      submitTime: 'Submit Time',
      duration: 'Duration',
      users: 'Users',
      accounts: 'Accounts',
      name: 'Name',
      description: 'Description',
      organization: 'Organization',
      title: 'Title',
      updated: 'Updated',
      code: 'Code',
      tool: 'Tool',
      interface: 'Interface',
      created: 'Created',
      summary: 'Summary',
      shortcuts: 'Shortcuts',
      fullName: 'Full name',
      username: 'Username',
      cluster: 'Cluster',
      flags: 'Flags',
      from: 'From',
      to: 'To'
    },
    metricRanges: {
      hour: 'Hour',
      day: 'Day',
      week: 'Week',
      custom: 'Custom',
      reset: 'Reset',
      oneDay: '1 day',
      threeDays: '3 days',
      sevenDays: '7 days',
      fifteenDays: '15 days',
      oneMonth: '1 month',
      lastHour: 'Last hour'
    },
    entities: {
      jobs: 'jobs',
      job: 'job',
      records: 'records',
      record: 'record',
      nodes: 'nodes',
      nodeGroups: 'node groups',
      accounts: 'accounts',
      rootAccounts: 'root accounts',
      userAssociations: 'user associations',
      reservations: 'reservations',
      qosPolicies: 'qos policies',
      users: 'users'
    }
  },
  shell: {
    mainMenu: {
      openSidebar: 'Open sidebar',
      closeSidebar: 'Close sidebar',
      clusterOps: 'Cluster Ops',
      slurmMonitor: 'Slurm Monitor',
      settings: 'Settings',
      dashboard: 'Dashboard',
      analysis: 'Analysis',
      jobs: 'Jobs',
      jobsHistory: 'Jobs History',
      resources: 'Resources',
      qos: 'QOS',
      reservations: 'Reservations',
      accounts: 'Accounts',
      ai: 'AI',
      admin: 'Admin'
    },
    userMenu: {
      myWorkspace: 'My workspace',
      accountPermissions: 'Account permissions'
    },
    settings: {
      title: 'Settings',
      subtitle: 'Global preferences and service state',
      tabsTitle: 'Settings',
      tabsDescription: 'Personal preferences, session diagnostics and account visibility.',
      general: 'General',
      errors: 'Errors',
      account: 'Account'
    }
  },
  login: {
    secureAccess: 'Secure Access',
    heroTitle: 'Enter the Slurm Web Plus control center.',
    heroDescription:
      'Unified cluster operations, job observability and infrastructure navigation in a cleaner, brand-aligned experience.',
    entryTitle: 'Entry',
    entryDescription: 'Sign in once and jump into clusters, jobs and resources.',
    focusTitle: 'Focus',
    focusDescription: 'Visual hierarchy tuned for operational clarity.',
    brandTitle: 'Brand',
    brandDescription: 'A modern shell aligned with your updated logo system.',
    authentication: 'Authentication',
    accessTitle: 'Access Slurm Web Plus',
    accessDescription: 'Sign in to continue to the requested page or open the cluster gateway.',
    requestedPageNotice: 'Please log in to access the requested page.',
    usernameLabel: 'Login',
    usernamePlaceholder: 'Username',
    passwordLabel: 'Password',
    passwordPlaceholder: 'Enter password',
    authenticating: 'Authenticating',
    usernameRequired: 'Username is required',
    passwordRequired: 'Password is required'
  },
  publicPages: {
    anonymous: {
      kicker: 'Anonymous Access',
      title: 'Preparing public session access.',
      description:
        'When authentication is disabled, Slurm Web Plus can still route visitors into the control center with a lightweight anonymous session.',
      status: 'Status',
      authBlocked: 'Anonymous access is blocked because authentication is enabled.',
      authFailed: 'Anonymous access failed: {message}'
    },
    clusters: {
      signOut: 'Sign out',
      kicker: 'Cluster Gateway',
      title: 'Select a cluster',
      description:
        'Compare visible environments, inspect availability and jump straight into the shared operations console.',
      statsTitle: 'Clusters',
      statsDescription: 'Visible to this session.',
      routingTitle: 'Routing',
      routingDescription: 'Permission-aware entry and single-cluster auto redirect.',
      signalsTitle: 'Signals',
      signalsDescription: 'Status, version and runtime context before you enter.',
      entryKicker: 'Cluster Entry',
      entryDescription: 'Pick an available environment to open the control surface.',
      clustersVisible: 'clusters visible',
      unableTitle: 'Unable to load cluster list',
      retry: 'Try to refresh…',
      loading: 'Loading clusters…',
      emptyTitle: 'Empty cluster list'
    },
    forbidden: {
      kicker: 'Access Restricted',
      title: 'Permission required',
      description:
        'This page is protected. Contact your administrator to request the required access.',
      deniedTitle: 'Current page access is restricted',
      missingPermission: 'Missing required permission: {permission}',
      genericDetail: 'Your current role does not grant access to this page.',
      contactAdmin: 'Please contact an administrator to request access.',
      openDashboard: 'Open dashboard',
      goToClusters: 'Go to clusters'
    },
    notFound: {
      kicker: 'Missing Route',
      title: 'Page not found',
      description:
        'The requested route is unavailable or has moved. Return to the cluster gateway to continue.',
      detail: 'The page you are looking for does not exist or has been moved.',
      goToClusters: 'Go to clusters'
    },
    signout: {
      bye: 'Bye!',
      done: 'You have been signed out'
    }
  },
  alerts: {
    seeErrors: 'See Errors',
    clusterNotFound: 'Cluster not found',
    applicationErrorsEmpty: 'No application errors have been recorded in this session.'
  },
  settings: {
    general: {
      title: 'General Settings',
      description: 'Configure general application preferences.',
      localeLabel: 'Display language',
      localeDescription:
        'Choose the language for navigation, forms, page copy and frontend notifications.',
      showNodeNames: 'Show node names on cluster diagram',
      showNodeNamesHint:
        'When enabled, node names are displayed on the cluster diagram, provided there is enough space. Names are shown with adaptive sizing and automatically positioned based on node dimensions.'
    },
    errors: {
      title: 'Errors',
      description: 'Application errors captured during the current session.',
      columns: {
        timestamp: 'Timestamp',
        route: 'Route',
        message: 'Message'
      }
    },
    account: {
      title: 'Account',
      description: 'Personal identity, group membership and cluster-level permissions.',
      username: 'Username',
      fullName: 'Full name',
      groups: 'Groups',
      clusterPermissions: 'Cluster Permissions',
      clusterDescription:
        'Policy, custom overrides and merged permissions resolved for this cluster.',
      actions: {
        openWorkspace: 'Open my workspace',
        openAnalysis: 'Open my analysis',
        viewHistoryJobs: 'View my history jobs'
      },
      permissionSources: {
        policy: {
          title: 'Policy',
          description: 'Base RBAC roles and actions from the active policy.'
        },
        custom: {
          title: 'Custom',
          description: 'Site-specific additions or overrides.'
        },
        merged: {
          title: 'Merged',
          description: 'Effective permissions exposed to the application.'
        }
      },
      sourceSummary: '{title} Roles & Actions',
      roles: 'Roles',
      actionsLabel: 'Actions',
      rules: 'Rules',
      emptyRoles: 'No roles declared.',
      emptyActions: 'No actions declared.',
      emptyRules: 'No route rules declared.'
    }
  },
  actionDialog: {
    kicker: 'Cluster Operation',
    confirm: 'Confirm {action}.',
    customTimeRange: 'Custom time range',
    customTimeRangeDescription: 'Select start and end time to the minute.',
    closeCustomTimeRange: 'Close custom time range',
    startTime: 'Start time',
    endTime: 'End time',
    invalidDateRange: 'Start and end time must both be valid datetimes.',
    invalidDateOrder: 'Start time must be earlier than end time.'
  },
  errors: {
    authentication: 'Authentication error: {message}',
    permission: 'Permission error: {message}',
    server: 'Server error: {message}',
    other: 'Other error: {message}'
  },
  components: {
    chartSkeleton: {
      loadingChart: 'Loading chart'
    },
    jobBack: {
      toNode: 'Back to node',
      toJobsHistory: 'Back to jobs history',
      toJobs: 'Back to jobs'
    },
    resourcesBack: {
      toResources: 'Back to resources'
    },
    settingsBack: {
      toDashboards: 'Back to dashboards'
    },
    admin: {
      title: 'Admin',
      description: 'Cluster-scoped administration, cache services and access controls.',
      ai: 'AI',
      cache: 'Cache',
      users: 'Users',
      accessControl: 'Access Control'
    },
    metricRangeSelector: {
      ariaLabel: 'Select time range'
    }
  },
  filters: {
    title: 'Filters',
    active: 'Filters active',
    add: 'Add filters',
    closeMenu: 'Close menu',
    remove: 'Remove filter for {group}:{value}',
    partitions: 'Partitions',
    states: {
      completed: 'Completed',
      failed: 'Failed',
      running: 'Running',
      pending: 'Pending'
    },
    history: {
      keyword: 'Keyword',
      keywordPlaceholder: 'Search workdir / command',
      userPlaceholder: 'Username',
      accountPlaceholder: 'Account name',
      partitionPlaceholder: 'Partition name',
      qosPlaceholder: 'QOS name',
      jobId: 'Job ID',
      timeRange: 'Time Range',
      apply: 'Apply Filters',
      active: 'Active filters',
      fromValue: 'from {value}',
      toValue: 'to {value}'
    }
  },
  sort: {
    label: 'Sort',
    order: 'Order'
  },
  tables: {
    jobs: {
      columns: {
        id: '#ID',
        state: 'State',
        userAccount: 'User (account)',
        resources: 'Resources',
        partition: 'Partition',
        qos: 'QOS',
        priority: 'Priority',
        reason: 'Reason',
        actions: 'Actions',
        submitTime: 'Submit Time'
      }
    },
    reservations: {
      columns: {
        name: 'Name',
        nodes: 'Nodes',
        duration: 'Duration',
        users: 'Users',
        accounts: 'Accounts',
        flags: 'Flags',
        actions: 'Actions'
      }
    },
    resources: {
      columns: {
        nodeName: 'Nodename',
        state: 'State',
        allocation: 'Allocation',
        cpu: 'CPU',
        memory: 'Memory',
        gpu: 'GPU',
        partitions: 'Partitions'
      }
    },
    qos: {
      columns: {
        name: 'Name',
        priority: 'Priority',
        jobs: 'Jobs',
        resources: 'Resources',
        time: 'Time',
        flags: 'Flags',
        actions: 'Actions'
      }
    },
    userAssociations: {
      columns: {
        user: 'User',
        account: 'Account',
        jobLimits: 'Job limits',
        resourceLimits: 'Resource limits',
        timeLimits: 'Time limits',
        qos: 'QOS',
        actions: 'Actions'
      }
    }
  },
  pages: {
    dashboard: {
      title: 'Dashboard',
      description:
        'Live cluster statistics, workload activity and metric trends in a unified control view.',
      openAnalysis: 'Open analysis',
      partitionAll: 'Entire cluster',
      stats: {
        nodes: 'Nodes',
        cores: 'Cores',
        totalMemory: 'Total Memory',
        allocatedMemory: 'Allocated Memory',
        availableMemory: 'Available Memory',
        clusterCapacity: 'Cluster capacity',
        requestedByJobs: 'Requested by jobs',
        totalMinusAllocated: 'Total minus allocated',
        runningJobs: 'Running Jobs',
        totalJobs: 'Total Jobs'
      },
      toolbar: {
        kicker: 'Live Controls',
        title: 'Realtime Metrics',
        description:
          'Filter dashboard stats by queue and adjust the live window from one aligned toolbar.',
        partitionQueue: 'Partition / Queue',
        selectMetricsRange: 'Select dashboard metrics range'
      },
      errors: {
        unableToRetrieve: 'Unable to retrieve statistics from cluster {cluster}'
      }
    },
    jobs: {
      title: 'Jobs',
      description:
        'Queue visibility, active states, account context and fast drill-down into job details.',
      metricLabel: 'job found',
      metricLabelPlural: 'jobs found',
      addFilters: 'Add filters',
      submitJob: 'Submit job',
      noJobs: 'No jobs found on cluster {cluster}',
      unableToRetrieve: 'Unable to retrieve jobs from cluster {cluster}',
      headingFilters: 'Filters',
      actions: {
        edit: 'Edit',
        cancel: 'Cancel',
        view: 'View'
      },
      dialogs: {
        submit: {
          title: 'Submit Job',
          description: 'Create a new Slurm job from the Jobs workspace.',
          submit: 'Submit job',
          fields: {
            name: 'Job name',
            script: 'Script',
            partition: 'Partition',
            account: 'Account',
            qos: 'QOS'
          }
        },
        edit: {
          title: 'Edit Job',
          description: 'Update job {jobId} on {cluster}.',
          submit: 'Save changes',
          fields: {
            partition: 'Partition',
            qos: 'QOS',
            priority: 'Priority',
            memoryPerCpuMb: 'Memory per CPU (MB)',
            memoryPerCpuHint: 'Optional',
            memoryPerCpuTooltip:
              'Submitted as Slurm REST memory_per_cpu.number when set.',
            timeLimit: 'Time limit',
            comment: 'Comment'
          },
          errors: {
            invalidMemoryPerCpu: 'Memory per CPU must be a positive integer in MB.'
          }
        },
        cancel: {
          title: 'Cancel Job',
          description: 'Cancel job {jobId}. This action is destructive.',
          submit: 'Cancel job',
          fields: {
            signal: 'Signal',
            reason: 'Reason'
          }
        }
      },
      notifications: {
        submitRequested: 'Job submission requested on {cluster}.',
        updateRequested: 'Job {jobId} update requested.',
        cancelRequested: 'Job {jobId} cancel requested.'
      }
    },
    jobsHistory: {
      title: 'Jobs History',
      description:
        'Historical job records with scheduler context, state transitions and searchable execution metadata.',
      metricLabel: 'record found',
      metricLabelPlural: 'records found',
      addFilters: 'Add filters',
      noRecords: 'No job history records found on cluster {cluster}',
      liveJob: 'Live job',
      history: 'History',
      headingFilters: 'Filters'
    },
    job: {
      kicker: 'Job Detail',
      title: 'Job {jobId}',
      description:
        'Execution state, request metadata and allocated resources for the selected job.',
      loadingTitle: 'Job {jobId}',
      summary: {
        user: 'User',
        account: 'Account',
        partition: 'Partition',
        nodes: 'Nodes',
        requested: 'Requested',
        requestedSubtle: '{count} GPU requested',
        requestedUnavailable: 'GPU request unavailable',
        allocated: 'Allocated',
        allocatedSubtle: '{count} GPU allocated',
        allocatedUnavailable: 'GPU allocation unavailable',
        exitCode: 'Exit Code',
        stateReason: 'State Reason'
      },
      fields: {
        user: 'User',
        group: 'Group',
        account: 'Account',
        wckeys: 'Wckeys',
        priority: 'Priority',
        nodes: 'Nodes',
        partition: 'Partition',
        qos: 'QOS',
        exitCode: 'Exit Code',
        name: 'Name',
        comments: 'Comments',
        submitLine: 'Submit line',
        script: 'Script',
        workingDirectory: 'Working directory',
        requested: 'Requested',
        allocated: 'Allocated'
      },
      panels: {
        executionTimelineTitle: 'Execution Timeline',
        executionTimelineDescription:
          'Submission, scheduling and runtime milestones for this job.',
        configurationTitle: 'Job Configuration',
        configurationDescription:
          'Core identity, command context and requested versus allocated resources.',
        detailedTitle: 'Detailed Resources & Commands',
        detailedDescription:
          'Longer fields stay expanded for readability and copy-friendly access.'
      },
      actions: {
        edit: 'Edit',
        cancel: 'Cancel'
      },
      errors: {
        unableToRetrieve: 'Unable to retrieve job {jobId} from cluster {cluster}'
      },
      dialogs: {
        edit: {
          title: 'Edit Job',
          description: 'Update job {jobId} on {cluster}.',
          submit: 'Save changes'
        },
        cancel: {
          title: 'Cancel Job',
          description: 'Cancel job {jobId}. This action is destructive.',
          submit: 'Cancel job'
        }
      },
      notifications: {
        updateRequested: 'Job {jobId} update requested.',
        cancelRequested: 'Job {jobId} cancel requested.'
      }
    },
    resources: {
      title: 'Nodes',
      description:
        'Current node state, allocation pressure and partition visibility across the cluster.',
      metricLabel: 'node found',
      metricLabelPlural: 'nodes found',
      actions: {
        showRackDiagram: 'Show Rack Diagram',
        hideRackDiagram: 'Hide Rack Diagram',
        toggleFoldedNodes: 'Toggle folded nodes {name}'
      },
      errors: {
        unableToRetrieve: 'Unable to retrieve nodes from cluster {cluster}'
      }
    },
    node: {
      kicker: 'Node Detail',
      title: 'Node {nodeName}',
      description:
        'Live allocation status, hardware profile and workload occupancy for the selected node.',
      overviewTitle: 'Node Overview',
      overviewDescription:
        'Scheduling status, hardware layout, assigned partitions and currently running jobs.',
      realtimeTitle: 'Realtime Metrics',
      realtimeDescription:
        'Prometheus-backed realtime and historical usage signals for this node.',
      usageHistoryTitle: 'Usage History',
      usageHistoryDescription: 'CPU, memory and disk usage trends across the selected interval.',
      stats: {
        cpuCapacity: 'CPU Capacity',
        cpuLayout: '{sockets} sockets x {cores} cores',
        memory: 'Memory',
        gpuSlots: 'GPU Slots',
        realtimeCpu: 'Realtime CPU',
        allocated: 'Allocated: {value}',
        metricsUnavailable: 'Metrics unavailable',
        updatedEvery15s: 'Updated every 15s',
        actualCpu: '{used} / {total} cores'
      },
      detail: {
        nodeStatus: 'Node status',
        allocationStatus: 'Allocation status',
        currentJobs: 'Current jobs',
        cpuLayout: 'CPU layout',
        threadsPerCore: 'Threads/core',
        architecture: 'Architecture',
        memory: 'Memory',
        gpu: 'GPU',
        partitions: 'Partitions',
        osKernel: 'OS Kernel',
        reboot: 'Reboot',
        lastBusy: 'Last busy',
        reasonLabel: 'reason: {reason}',
        unableToRetrieveJobs: 'Unable to retrieve jobs',
        loadingJobs: 'Loading jobs...'
      },
      metrics: {
        cpuUsage: 'CPU Usage',
        memoryUsage: 'Memory Usage',
        diskUsage: 'Disk Usage',
        disk: 'Disk',
        actual: 'Actual: {value}',
        noActualValue: 'Actual: N/A',
        na: 'N/A',
        loadingRealtime: 'Loading realtime metrics...',
        loadingHistory: 'Loading history...',
        noHistory: 'No metrics history is available for this range.',
        unableRealtime: 'Unable to retrieve realtime metrics for this node.',
        unableHistory: 'Unable to retrieve metrics history for this node.'
      },
      actions: {
        edit: 'Edit',
        delete: 'Delete',
        editTooltip: 'Edit the node state and set a scheduler-visible reason.',
        deleteTooltip: 'Delete this node definition from the cluster.'
      },
      toolbar: {
        selectRange: 'Select node metrics range'
      },
      errors: {
        unableToRetrieve: 'Unable to retrieve node {nodeName} from cluster {cluster}',
        deleteConfirmation: 'Type DELETE to confirm.'
      },
      dialogs: {
        edit: {
          title: 'Edit Node',
          description: 'Update node {nodeName} on {cluster}.',
          submit: 'Save changes',
          tooltip:
            'Apply the edited node state and optional reason to the selected cluster node.',
          fields: {
            state: 'State',
            statePlaceholder: 'Select node state',
            stateHint:
              'Current node state: {state}. Select the Slurm state action to apply to this node.',
            stateTooltip:
              'Use DRAIN to start draining a node. Slurm may later report the node as DRAINING or DRAINED depending on running jobs.',
            reason: 'Reason',
            reasonHint:
              'Optional audit note shown with the node state inside the cluster UI and scheduler output.',
            reasonTooltip:
              'Use this when draining or changing node behavior so operators understand why.'
          }
        },
        delete: {
          title: 'Delete Node',
          description: 'Delete node {nodeName}. This action is destructive.',
          submit: 'Delete node',
          tooltip: 'Permanently remove the node definition after confirmation.',
          fields: {
            confirmation: 'Type DELETE to confirm',
            confirmationHint: 'Enter DELETE exactly to unlock this destructive action.',
            confirmationTooltip: 'This safeguard prevents accidental node removal.'
          }
        }
      },
      notifications: {
        updateRequested: 'Node {nodeName} update requested.',
        deleteRequested: 'Node {nodeName} delete requested.'
      }
    },
    accounts: {
      title: 'Accounts',
      description:
        'Accounts defined on cluster, with hierarchy, delegated users and structure laid out in one tree.',
      metricLabel: 'account found',
      metricLabelPlural: 'accounts found',
      create: 'Create account',
      unableToRetrieve: 'Unable to retrieve accounts from cluster {cluster}',
      noAccounts: 'No account defined on cluster {cluster}',
      paginationLabel: 'root account',
      dialogs: {
        create: {
          title: 'Create Account',
          description: 'Add a new SlurmDB account from the account tree workspace.',
          submit: 'Create account',
          fields: {
            name: 'Account name',
            description: 'Description',
            organization: 'Organization',
            parentAccount: 'Parent account',
            qos: 'QOS (comma separated)'
          }
        }
      },
      notifications: {
        createRequested: 'Account {name} creation requested.'
      }
    },
    account: {
      kicker: 'Account Detail',
      description:
        'Hierarchy, inherited policy and per-user overrides for the selected Slurm account.',
      metricLabel: 'user association',
      metricLabelPlural: 'user associations',
      back: 'Back to accounts',
      overviewTitle: 'Account Overview',
      overviewDescription: 'Parent hierarchy, scoped QoS and inherited account-wide limits.',
      userAssociationsTitle: 'User Associations',
      userAssociationsDescription:
        'User associations attached to this account, with inherited values visually de-emphasized.',
      noAccount: 'Account {account} does not exist on this cluster.',
      noAssociations: 'Account {account} has no end-user associations.',
      noAssociationsYet: 'Account {account} has no end-user associations yet.',
      actions: {
        viewJobs: 'View jobs',
        addUser: 'Add user',
        edit: 'Edit',
        delete: 'Delete',
        editQos: 'Edit QOS'
      },
      stats: {
        parentChain: 'Parent Chain',
        directSubaccounts: 'Direct subaccounts',
        qosScope: 'QoS Scope',
        appliedAtAccountLevel: 'Applied at account level',
        jobLimits: 'Job Limits',
        configuredLimitEntries: 'Configured limit entries',
        timeLimits: 'Time Limits',
        walltimePolicies: 'Walltime policies'
      },
      detail: {
        parentAccounts: 'Parent accounts',
        subaccounts: 'Subaccounts',
        qos: 'QoS',
        jobLimits: 'Job limits',
        resourceLimits: 'Resource limits',
        timeLimits: 'Time limits'
      },
      limits: {
        running: 'Running',
        submitted: 'Submitted',
        runningPerUser: 'Running / user',
        submittedPerUser: 'Submitted / user',
        total: 'Total',
        perJob: 'Per job',
        perNode: 'Per node'
      },
      tables: {
        defaultQos: 'Default: {qos}'
      },
      errors: {
        unableToRetrieve: 'Unable to retrieve associations for cluster {cluster}'
      },
      dialogs: {
        edit: {
          title: 'Edit Account',
          description: 'Update account {account}.',
          submit: 'Save changes'
        },
        addUserAssociation: {
          title: 'Add User Association',
          description: 'Add a user to account {account}.',
          submit: 'Add user'
        },
        editUserQos: {
          title: 'Edit User QOS',
          description: 'Update QOS for {user} on {account}.',
          submit: 'Save changes'
        },
        delete: {
          title: 'Delete Account',
          description: 'Delete account {account}. This action is destructive.',
          submit: 'Delete account'
        },
        deleteAssociation: {
          title: 'Delete User Association',
          description: 'Remove {user} from account {account}. This action is destructive.',
          submit: 'Delete association'
        },
        fields: {
          description: 'Description',
          organization: 'Organization',
          parentAccount: 'Parent account',
          qosCsv: 'QOS (comma separated)',
          username: 'Username',
          assignedQosCsv: 'Assigned QOS (comma separated)',
          defaultQos: 'Default QOS'
        }
      },
      notifications: {
        updateRequested: 'Account {account} update requested.',
        addUserRequested: 'User {user} association requested for account {account}.',
        updateQosRequested: 'QOS update requested for {user} on {account}.',
        removeUserRequested: 'User {user} removal requested from {account}.',
        deleteRequested: 'Account {account} deletion requested.'
      }
    },
    analysis: {
      kicker: 'Capacity Analysis',
      title: 'Cluster Efficiency',
      metricLabel: 'operational score',
      actions: {
        liveDashboard: 'Live dashboard',
        inspectQueue: 'Inspect queue',
        openResources: 'Open resources'
      },
      loading: 'Building the cluster analysis workspace...',
      status: {
        prefix: 'Status:',
        updated: 'Updated {time}',
        refreshing: 'Refreshing',
        efficient: 'Efficient',
        stable: 'Stable',
        pressured: 'Pressured',
        constrained: 'Constrained',
        neutral: 'Neutral',
        warning: 'Warning',
        danger: 'Critical',
        success: 'Healthy',
        ready: 'Ready'
      },
      toolbar: {
        selectRange: 'Select cluster analysis range'
      },
      sections: {
        capacityTitle: 'Capacity Envelope',
        capacityDescription: 'Current utilization and schedulable headroom across the cluster.',
        blockersTitle: 'Queue Blockers',
        blockersDescription:
          'Why jobs are waiting, and whether the queue is blocked by capacity, policy or packing.',
        partitionTitle: 'Partition Hotspots',
        partitionDescription:
          'Partition-level pressure helps decide whether to expand hardware, rebalance jobs or adjust QOS.',
        historicalTitle: 'Historical Pressure',
        historicalDescription:
          'Fast historical snapshots show whether capacity pressure is steady, bursty or policy-driven.',
        actionsTitle: 'Recommended Actions',
        actionsDescription:
          'The list below is generated from live telemetry to help reduce queue time and increase job throughput.',
        healthTitle: 'Controller Health',
        healthDescription:
          'Lightweight controller status checks from the Slurm `ping` and `diag` endpoints.'
      },
      blockers: {
        noJobPermission: 'Job visibility is required to analyze queue blockers.',
        jobsUnavailable: 'Job queue data is currently unavailable.',
        none: 'No pending jobs are currently blocking the queue.',
        pendingJobs: '{count} pending job(s)',
        packingSignal: 'Packing signal',
        packingDetail:
          '{count} pending single-node job(s) appear blocked by fragmentation while {cpu} schedulable CPU(s) remain free.'
      },
      partition: {
        noPermission:
          'Both job and node visibility are required for partition pressure analysis.',
        none: 'No partition-level pressure is currently visible.',
        pendingActive: '{pending} pending, {running} active',
        cpuChip: 'CPU {running}/{total}',
        pendingCpu: 'Pending CPU: {value}',
        totalCpu: 'Total CPU: {value}',
        schedulableCpu: 'Schedulable CPU: {value}'
      },
      historical: {
        metricsDisabled:
          'Metrics collection is disabled for this cluster. Live analysis remains available.',
        metricsUnavailable: 'Historical metrics are temporarily unavailable.',
        latestTelemetry: 'Latest telemetry',
        latestTelemetryDetail: 'Jobs at the most recent metric sample in the selected range.',
        waitSamples: 'Wait samples',
        waitMedian: '{minutes} min median',
        waitP90: 'p90 {p90} min from {samples} recent completed jobs.',
        waitUnavailable: 'Job history samples are unavailable for this cluster or time range.',
        waitDisabled: 'Historical wait samples are not enabled on this cluster.'
      },
      health: {
        ping: 'Ping',
        diag: 'Diag',
        pingUnavailable: 'Ping data is currently unavailable for this cluster.',
        pingEmpty: 'No controller ping fields are available in the current response.',
        diagUnavailable: 'Diagnostic data is currently unavailable for this cluster.',
        diagEmpty: 'No diagnostic summary fields are available in the current response.',
        fallbackController: 'Controller'
      }
    },
    reservations: {
      title: 'Reservations',
      description:
        'Advanced reservations, affected nodes and account or user access windows.',
      metricLabel: 'reservations',
      create: 'Create reservation',
      unableToRetrieve: 'Unable to retrieve reservations from cluster {cluster}',
      noReservations: 'No reservation defined on cluster {cluster}',
      paginationLabel: 'reservation',
      nodeCount: '{count} nodes',
      actions: {
        edit: 'Edit',
        delete: 'Delete'
      },
      dialogs: {
        create: {
          title: 'Create Reservation',
          description: 'Create a new reservation on this cluster.',
          submit: 'Create reservation'
        },
        edit: {
          title: 'Edit Reservation',
          description: 'Update reservation {name}.',
          submit: 'Save changes'
        },
        delete: {
          title: 'Delete Reservation',
          description: 'Delete reservation {name}. This action is destructive.',
          submit: 'Delete reservation'
        },
        fields: {
          name: 'Reservation name',
          nodeList: 'Node list',
          partition: 'Partition',
          users: 'Users (comma separated)',
          accounts: 'Accounts (comma separated)'
        }
      },
      notifications: {
        createRequested: 'Reservation {name} creation requested.',
        updateRequested: 'Reservation {name} update requested.',
        deleteRequested: 'Reservation {name} deletion requested.'
      }
    },
    qos: {
      title: 'QOS',
      description:
        'Quality-of-service policies, resource ceilings and scheduling constraints defined on this cluster.',
      metricLabel: 'qos policies',
      create: 'Create QOS',
      unableToRetrieve: 'Unable to retrieve qos from cluster {cluster}',
      noQos: 'No qos defined on cluster {cluster}',
      paginationLabel: 'qos policy',
      actions: {
        edit: 'Edit',
        delete: 'Delete',
        viewJobs: 'View jobs'
      },
      limits: {
        global: 'Global',
        submitPerUser: 'Submit / User',
        submitPerAccount: 'Submit / Account',
        maxPerUser: 'Max / User',
        maxPerAccount: 'Max / Account',
        maxPerJob: 'Max / Job',
        maxPerNode: 'Max / Node'
      },
      dialogs: {
        create: {
          title: 'Create QOS',
          description: 'Add a new quality-of-service policy for this cluster.',
          submit: 'Create QOS'
        },
        edit: {
          title: 'Edit QOS',
          description: 'Update {name}.',
          submit: 'Save changes'
        },
        delete: {
          title: 'Delete QOS',
          description: 'Delete QOS {name}. This action is destructive.',
          submit: 'Delete QOS'
        },
        fields: {
          name: 'Name',
          description: 'Description',
          priority: 'Priority',
          maxSubmitJobsPerUser: 'MaxSubmitJobsPerUser',
          maxSubmitJobsPerUserHint:
            'Current submitted jobs per user, including running and pending jobs.',
          maxJobsPerUser: 'MaxJobsPerUser',
          maxJobsPerUserHint: 'Maximum concurrently running jobs per user.',
          maxWallDurationPerJob: 'MaxWallDurationPerJob',
          maxWallDurationPerJobHint: 'Single-job maximum runtime as days-hh:mm:ss.'
        },
        errors: {
          invalidPositiveInteger: 'QOS job limits must be positive integer values.',
          invalidWallDuration:
            'MaxWallDurationPerJob must use days-hh:mm:ss or hh:mm:ss.',
          invalidWallDurationRange:
            'MaxWallDurationPerJob must use valid hours, minutes and seconds.'
        }
      },
      notifications: {
        createRequested: 'QOS {name} creation requested.',
        updateRequested: 'QOS {name} update requested.',
        deleteRequested: 'QOS {name} deletion requested.'
      }
    },
    user: {
      kicker: 'User Workspace',
      selfDescription:
        'Personal identity, effective cluster permissions, account associations and user analytics in one workspace.',
      description:
        'Account associations, history shortcuts and analytics for the selected user.',
      metricLabel: 'account associated',
      metricLabelPlural: 'accounts associated',
      breadcrumb: {
        myWorkspace: 'My Workspace',
        userPrefix: 'User {user}'
      },
      backToDashboard: 'Back to dashboard',
      backToAccounts: 'Back to accounts',
      actions: {
        viewJobs: 'View jobs',
        viewHistoryJobs: 'View history jobs',
        accountPermissions: 'Account permissions',
        editUser: 'Edit user',
        deleteUser: 'Delete user'
      },
      selfStats: {
        username: 'Username',
        noFullName: 'No full name cached',
        cluster: 'Cluster',
        currentWorkspaceContext: 'Current workspace context',
        effectiveRoles: 'Effective Roles',
        mergedPolicyAndCustomRoles: 'Merged policy and custom roles',
        effectiveActions: 'Effective Actions',
        permissionsExposed: 'Permissions exposed to the frontend'
      },
      identity: {
        summaryKicker: 'Identity Summary',
        summaryTitle: 'My account and permissions',
        summaryDescription: 'Local account identity plus merged cluster-level permissions.',
        identity: 'Identity',
        mergedActions: 'Merged actions',
        mergedRules: 'Merged rules',
        username: 'Username:',
        fullName: 'Full name:',
        groups: 'Groups:',
        noActions: 'No actions declared.',
        noRules: 'No route rules declared.'
      },
      profile: {
        kicker: 'User Profile',
        title: 'Account associations and limits',
        description:
          'LDAP-linked account associations, quota boundaries and job history shortcuts for this user.',
        historyJobs: 'History Jobs',
        historyAccessGranted: 'History access granted',
        historyShortcut:
          'Jump directly into persisted jobs history filtered on this user.',
        accounts: 'Accounts',
        accountAssociationsFound:
          'Account association found for this user.',
        accountAssociationsFoundPlural:
          'Account associations found for this user.',
        noAssociations: 'User {user} has no associations on this cluster.',
        accountAssociationsTitle: 'Account Associations',
        accountAssociationsDescription:
          'Each row represents one account binding and the limits attached to it.'
      },
      analytics: {
        kicker: 'User Analysis',
        title: 'Submission and tool analytics',
        description:
          'Submission trends, dual-metric tool analysis and execution summaries for this user.',
        backToUser: 'Back to user detail',
        userDetail: 'User detail'
      },
      analyticsPanels: {
        disabled: 'User analytics is not enabled for this cluster.',
        unavailable:
          'User tool analysis is not available for this cluster. LDAP and association details remain available.',
        profile: {
          ldapAvailable: 'LDAP profile available',
          ldapUnavailable: 'LDAP profile unavailable'
        },
        window: {
          title: 'Analysis Window',
          description: 'One shared time window for activity, usage and completed tool analysis.',
          updated: 'Updated {value}',
          ariaLabel: 'Select user analytics time range'
        },
        cards: {
          submitted: {
            title: 'Submitted in Range',
            detail: 'Submission events captured in the selected window'
          },
          completed: {
            title: 'Completed in Range',
            detail: 'Completed jobs captured in the selected window'
          },
          activeTools: {
            title: 'Active Tools',
            detail: 'Top tool: {tool}'
          },
          avgRuntime: {
            title: 'Average Runtime',
            detail: 'Across completed jobs captured in the selected window'
          }
        },
        activity: {
          title: 'Submission Activity',
          description: 'Submission and completion trends in the selected time range.',
          unable: 'Unable to retrieve submission or completion history for this user.',
          loading: 'Loading activity history...',
          empty: 'No submission or completion history is available for this range.'
        },
        usage: {
          title: 'Usage Profile',
          description: 'Aggregate behaviour across completed jobs in the selected time range.',
          avgMemoryTitle: 'Average Memory',
          avgMemoryDetail: 'Per completed job across recorded tools in the selected window',
          maxMemoryTitle: 'Max Memory',
          maxMemoryDetail: 'Highest recorded completed-job memory across the selected window',
          medianMemoryTitle: 'Median Memory',
          medianMemoryDetail: 'Typical completed-job memory across recorded tools in the selected window',
          avgCpuTitle: 'Average CPU Cores',
          avgCpuDetail: "Core allocation requested by this user's tool runs in the selected window"
        },
        table: {
          title: 'Completed Job Tool Analysis',
          description:
            'Tool-level analysis for completed jobs in the selected time range, combining completed job volume with memory, CPU and runtime averages.',
          empty: 'No completed job tool activity has been recorded for this user yet.',
          workload: 'Workload',
          avgMemory: 'Avg Memory',
          maxMemory: 'Max Memory',
          medianMemory: 'Median Memory',
          avgRuntime: 'Avg Runtime',
          avgCpu: 'Avg CPU',
          jobsCount: '{count} job(s)'
        },
        chart: {
          submissions: 'Submissions',
          completions: 'Completions',
          jobsUnit: 'jobs'
        },
        units: {
          seconds: '{value} sec',
          minutes: '{value} min',
          hoursMinutes: '{hours}h {minutes}m',
          hoursOnly: '{hours}h',
          gb: '{value} GB',
          hours: '{value} h',
          cores: '{value} cores'
        }
      },
      emptyState: {
        title: 'Additional sections are unavailable',
        description:
          'This workspace can show account associations through `user/profile:view:*` and analytics through `user/analysis:view:*` on clusters where user metrics are enabled.'
      },
      limits: {
        runningPerUser: 'Running / user',
        submittedPerUser: 'Submitted / user',
        total: 'Total',
        perJob: 'Per job',
        perNode: 'Per node'
      },
      dialogs: {
        create: {
          title: 'Create User',
          description: 'Create SlurmDB user {user}.',
          submit: 'Create user'
        },
        edit: {
          title: 'Edit User',
          description: 'Update SlurmDB user {user}.',
          submit: 'Save changes'
        },
        delete: {
          title: 'Delete User',
          description: 'Delete SlurmDB user {user}. This action is destructive.',
          submit: 'Delete user'
        },
        fields: {
          description: 'Description',
          defaultAccount: 'Default account',
          defaultQos: 'Default QOS',
          assignedQosCsv: 'Assigned QOS (comma separated)',
          defaultWckey: 'Default WCKEY',
          adminLevel: 'Admin level'
        }
      },
      notifications: {
        updateRequested: 'User {user} update requested.',
        deleteRequested: 'User {user} deletion requested.'
      }
    },
    jobHistoryDetail: {
      kicker: 'Job History',
      title: 'Job {jobId}',
      description:
        'Recorded timeline, scheduler context and resource details captured for this finished job.',
      liveJob: 'Live job',
      recordedFieldsTitle: 'Recorded Fields',
      recordedFieldsDescription:
        'Scheduler metadata and accounting values archived for this historical record.',
      executionTimelineTitle: 'Execution Timeline',
      executionTimelineDescription:
        'Historical checkpoints captured across submission, scheduling and completion.',
      detailedTitle: 'Detailed Resources & Commands',
      detailedDescription:
        'Longer fields stay expanded for readability and copy-friendly access.',
      timeline: {
        submitted: 'Submitted',
        eligible: 'Eligible',
        scheduling: 'Scheduling',
        running: 'Running',
        completed: 'Completed',
        terminated: 'Terminated'
      },
      summary: {
        jobId: 'Job ID',
        user: 'User',
        account: 'Account',
        partition: 'Partition',
        nodes: 'Nodes',
        maxMemory: 'Max Memory',
        avgCpuCores: 'Avg CPU Cores',
        avgCpuCoresSubtle: 'Average concurrent cores used',
        exitCode: 'Exit Code'
      },
      fields: {
        jobId: 'Job ID',
        name: 'Name',
        stateReason: 'State Reason',
        user: 'User',
        group: 'Group',
        account: 'Account',
        partition: 'Partition',
        qos: 'QOS',
        priority: 'Priority',
        nodes: 'Nodes',
        resources: 'Resources',
        requested: 'Requested',
        allocated: 'Allocated',
        tresPerJob: 'TRES/Job',
        tresPerNode: 'TRES/Node',
        gres: 'GRES',
        maxMemory: 'Max Memory',
        avgCpuCores: 'Average CPU Cores Used',
        timeLimit: 'Time Limit',
        exitCode: 'Exit Code',
        workdir: 'Working Directory',
        command: 'Command'
      },
      helps: {
        avgCpuCoresTitle: 'Average CPU Cores Used',
        avgCpuCoresBody:
          'Estimated average concurrent CPU cores used while the job ran. Calculated as sum(step.time.total) / job_elapsed_seconds from the included job steps.'
      },
      resourcesLabel: {
        nodes: '{count} node',
        nodesPlural: '{count} nodes',
        cpus: '{count} CPU',
        cpusPlural: '{count} CPUs'
      },
      duration: {
        minutes: '{minutes}m',
        hoursMinutes: '{hours}h {minutes}m'
      },
      errors: {
        unableToRetrieve: 'Unable to retrieve job history record {id}: {error}'
      }
    }
  }
}

export default en
