const zhCN = {
  common: {
    locale: {
      en: 'English',
      zhCN: '简体中文',
      switcher: '语言'
    },
    buttons: {
      close: '关闭',
      cancel: '取消',
      apply: '应用',
      reset: '重置',
      goBack: '返回',
      signIn: '登录',
      signOut: '退出登录'
    },
    notifications: {
      info: '提示',
      error: '错误',
      close: '关闭'
    },
    pagination: {
      showing: '显示',
      to: '到',
      of: '共',
      perPage: '每页',
      previous: '上一页',
      next: '下一页',
      itemCount: '{count} 个{label}',
      itemCount_plural: '{count} 个{label}'
    },
    status: {
      loading: '加载中',
      working: '处理中...'
    },
    forms: {
      required: '必填',
      optional: '可选',
      selectOption: '请选择'
    }
  },
  shell: {
    mainMenu: {
      openSidebar: '打开侧边栏',
      closeSidebar: '关闭侧边栏',
      clusterOps: '集群运维',
      slurmMonitor: 'Slurm 监控',
      settings: '设置',
      dashboard: '概览',
      analysis: '分析',
      jobs: '作业',
      jobsHistory: '历史作业',
      resources: '资源',
      qos: 'QOS',
      reservations: '预留',
      accounts: '账户',
      ai: 'AI',
      admin: '管理'
    },
    userMenu: {
      myWorkspace: '我的工作区',
      accountPermissions: '账户权限'
    },
    settings: {
      title: '设置',
      subtitle: '全局偏好与服务状态',
      tabsTitle: '设置',
      tabsDescription: '个人偏好、会话诊断与账户可见性。',
      general: '常规',
      errors: '错误',
      account: '账户'
    }
  },
  login: {
    secureAccess: '安全访问',
    heroTitle: '进入 Slurm Web Plus 控制中心。',
    heroDescription: '统一集群运维、作业观测和基础设施导航，提供更清晰一致的控制台体验。',
    entryTitle: '入口',
    entryDescription: '一次登录，快速进入集群、作业与资源工作区。',
    focusTitle: '聚焦',
    focusDescription: '为运维清晰度优化的视觉层级。',
    brandTitle: '品牌',
    brandDescription: '与最新品牌标识系统一致的现代化外壳。',
    authentication: '身份验证',
    accessTitle: '访问 Slurm Web Plus',
    accessDescription: '登录后继续访问请求页面，或进入集群网关。',
    requestedPageNotice: '请登录以访问请求的页面。',
    usernameLabel: '登录名',
    usernamePlaceholder: '用户名',
    passwordLabel: '密码',
    passwordPlaceholder: '输入密码',
    authenticating: '验证中',
    usernameRequired: '用户名不能为空',
    passwordRequired: '密码不能为空'
  },
  publicPages: {
    anonymous: {
      kicker: '匿名访问',
      title: '正在准备公共会话访问。',
      description: '当关闭身份验证时，Slurm Web Plus 仍可通过轻量匿名会话将访问者引导到控制中心。',
      status: '状态',
      authBlocked: '已启用身份验证，匿名访问不可用。',
      authFailed: '匿名访问失败：{message}'
    },
    clusters: {
      signOut: '退出登录',
      kicker: '集群网关',
      title: '选择一个集群',
      description: '比较当前可见环境，查看可用性，并直接进入共享运维控制台。',
      statsTitle: '集群',
      statsDescription: '当前会话可见。',
      routingTitle: '路由',
      routingDescription: '按权限进入，并支持单集群自动跳转。',
      signalsTitle: '信号',
      signalsDescription: '进入前先查看状态、版本与运行时上下文。',
      entryKicker: '集群入口',
      entryDescription: '选择一个可用环境以打开控制界面。',
      clustersVisible: '可见集群',
      unableTitle: '无法加载集群列表',
      retry: '请尝试刷新…',
      loading: '正在加载集群…',
      emptyTitle: '集群列表为空'
    },
    forbidden: {
      kicker: '访问受限',
      title: '需要权限',
      description: '此页面受保护。请联系管理员申请所需权限。',
      deniedTitle: '当前页面无访问权限',
      missingPermission: '缺少所需权限：{permission}',
      genericDetail: '你当前的角色没有访问此页面的权限。',
      contactAdmin: '请联系管理员申请权限。',
      openDashboard: '打开概览',
      goToClusters: '前往集群列表'
    },
    notFound: {
      kicker: '路由缺失',
      title: '页面不存在',
      description: '请求的路由不可用或已迁移。请返回集群网关继续操作。',
      detail: '你访问的页面不存在或已被移动。',
      goToClusters: '前往集群列表'
    },
    signout: {
      bye: '再见！',
      done: '你已退出登录'
    }
  },
  alerts: {
    seeErrors: '查看错误',
    clusterNotFound: '未找到集群',
    applicationErrorsEmpty: '当前会话中没有记录到应用错误。'
  },
  settings: {
    general: {
      title: '常规设置',
      description: '配置应用的常规偏好。',
      localeLabel: '显示语言',
      localeDescription: '选择导航、表单、页面文案和前端通知所使用的语言。',
      showNodeNames: '在集群拓扑图中显示节点名称',
      showNodeNamesHint:
        '启用后，若空间足够，会在集群拓扑图中显示节点名称。名称会根据节点尺寸自适应缩放并自动定位。'
    },
    errors: {
      title: '错误',
      description: '当前会话中记录的应用错误。',
      columns: {
        timestamp: '时间',
        route: '路由',
        message: '消息'
      }
    }
  },
  actionDialog: {
    kicker: '集群操作',
    confirm: '确认执行{action}。',
    customTimeRange: '自定义时间范围',
    customTimeRangeDescription: '选择精确到分钟的开始和结束时间。',
    closeCustomTimeRange: '关闭自定义时间范围',
    startTime: '开始时间',
    endTime: '结束时间',
    invalidDateRange: '开始时间和结束时间都必须是有效日期时间。',
    invalidDateOrder: '开始时间必须早于结束时间。'
  },
  errors: {
    authentication: '认证错误：{message}',
    permission: '权限错误：{message}',
    server: '服务端错误：{message}',
    other: '其他错误：{message}'
  }
}

export default zhCN
