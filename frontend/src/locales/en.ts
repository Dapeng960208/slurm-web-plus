const en = {
  common: {
    locale: {
      en: 'English',
      zhCN: '简体中文',
      switcher: 'Language'
    },
    buttons: {
      close: 'Close',
      cancel: 'Cancel',
      apply: 'Apply',
      reset: 'Reset',
      goBack: 'Go back',
      signIn: 'Sign in',
      signOut: 'Sign out'
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
      working: 'Working...'
    },
    forms: {
      required: 'Required',
      optional: 'Optional',
      selectOption: 'Select an option'
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
  }
}

export default en
