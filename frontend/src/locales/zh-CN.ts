const zhCN = {
  analysis: {
    labels: {
      latencyMs: '延迟（毫秒）',
      jobsSubmitted: '提交作业数',
      jobsStarted: '启动作业数',
      jobsCompleted: '完成作业数',
      jobsCanceled: '取消作业数',
      scheduleCycleLast: '最近一次调度周期',
      scheduleCycleMax: '最大调度周期',
      scheduleCycleMean: '平均调度周期'
    },
    scoreSummary: {
      efficient: '资源利用良好，当前队列压力处于可控范围内。',
      recoverCapacity: '不可用容量正在降低集群吞吐，应优先恢复这些容量。',
      fragmentation: '集群中仍有空闲容量，但作业形态和节点装箱方式阻碍了快速启动。',
      backlog: '队列积压增长速度已经快于调度器接纳作业的速度。',
      steady: '集群整体运行平稳，队列摩擦较小。'
    },
    summary: {
      cpuOccupancy: {
        label: 'CPU 占用率',
        detail: '当前有 {busy} / {total} 个 CPU 正在忙碌。',
        unavailable: 'CPU 占用率当前不可用。'
      },
      queuePressure: {
        label: '队列压力',
        low: '低',
        detail: '{pending} 个待处理作业，对比 {running} 个活跃作业。'
      },
      waitSample: {
        label: '排队等待',
        value: '{seconds} 秒',
        proxy: '代理值',
        detail: '基于最近 {samples} 个已完成作业的中位等待时间。',
        fallback: '由于缺少最近已完成作业，当前使用实时积压作为排队延迟代理值。'
      },
      recovery: {
        label: '恢复潜力',
        unavailable: '恢复不可用容量将立即提高作业接纳吞吐。',
        available: '当前仍有可调度空闲 CPU 可用于回填和较小作业。'
      }
    },
    capacity: {
      cpu: {
        label: 'CPU 忙碌度',
        detail: '活跃作业已分配或请求 {busy}/{total} 个 CPU。',
        unavailable: 'CPU 总量当前不可用。'
      },
      memory: {
        label: '内存承诺量',
        detail: '已承诺 {committed}，总量 {total}。',
        unavailable: '当前遥测中没有可用的内存承诺量。'
      },
      gpu: {
        label: 'GPU 忙碌度',
        detail: '当前有 {running}/{total} 个 GPU 正在使用中。',
        unavailable: '该集群未声明 GPU 容量。'
      },
      nodes: {
        label: '可调度节点',
        detail: '当前有 {schedulable}/{total} 个节点可调度。',
        unavailable: '节点清单当前不可用。'
      }
    },
    recommendations: {
      recoverCapacity: {
        title: '优先恢复不可用节点，再评估是否扩容',
        summary: '最快的容量增益来自将 drained 或 down 的节点恢复到服务中。',
        evidence: '当前有 {nodes} 个节点和 {cpu} 个 CPU 不可用。'
      },
      fragmentation: {
        title: '缓解单节点作业的 CPU 碎片化',
        summary: '可通过回填小作业、减少过大单节点请求或重平衡分区，将空闲核心转化为可接纳作业。',
        evidence: '有 {count} 个待处理作业在全局空闲 CPU 足够时，仍无法落到任何单个可调度节点上。'
      },
      expandBusy: {
        title: '扩容或重平衡最繁忙的容量池',
        summary: '队列中以资源受限作业为主，而活跃容量已经处于较高占用。',
        evidence: '{share}% 的待处理作业因资源受限而阻塞，CPU 占用率为 {cpu}%。'
      },
      priority: {
        title: '在加硬件前先复查 QOS 与优先级策略',
        summary: '当前排队延迟更像是策略约束，而不完全是容量不足。',
        evidence: '{share}% 的待处理作业因优先级阻塞，而 CPU 占用率为 {cpu}%。'
      },
      gpu: {
        title: '用更严格的 GPU 队列类别保护 GPU 吞吐',
        summary: 'GPU 需求正在累积，而加速器容量已经偏热。',
        evidence: '待处理作业共请求 {gpu} 个 GPU，当前 GPU 占用率为 {occupancy}%。'
      },
      waitTime: {
        title: '通过更短时限类别和回填降低排队时间',
        summary: '已完成作业的等待历史表明，用户在被接纳前已经经历了较明显的排队。',
        evidence: '中位排队时间为 {seconds} 秒，统计覆盖 {samples} 个已完成作业。'
      },
      balance: {
        title: '在不同作业规模之间保持接纳平衡',
        summary: '持续跟踪分区压力，并释放更小的回填窗口，让集群保持满载同时不饿死大作业。',
        evidence: '当前有 {pending} 个待处理作业、{running} 个活跃作业，以及 {cpu} 个可调度空闲 CPU 参与调度。'
      }
    },
    historyCards: {
      peakPending: {
        label: '待处理峰值',
        detail: '所选遥测时间范围内最大的排队积压。'
      },
      averagePending: {
        label: '平均待处理',
        detail: '所选时间范围内的平均队列深度。'
      },
      peakRunning: {
        label: '运行峰值',
        detail: '该时间范围内观测到的最大并发运行作业数。'
      },
      busyCores: {
        label: '繁忙核心峰值',
        detail: '约为声明 CPU 容量平均值的 {percent}',
        unavailable: 'CPU 历史数据不可用'
      }
    }
  },
  common: {
    navigation: {
      back: '返回',
      openPartition: '打开分区 {partition}'
    },
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
      refresh: '刷新',
      clear: '清空',
      goBack: '返回',
      signIn: '登录',
      signOut: '退出登录',
      create: '创建',
      edit: '编辑',
      delete: '删除',
      view: '查看',
      saveChanges: '保存更改',
      open: '打开',
      search: '搜索',
      retry: '重试',
      previous: '上一页',
      next: '下一页',
      send: '发送',
      enable: '启用',
      disable: '禁用',
      today: '今天'
    },
    notifications: {
      info: '提示',
      error: '错误',
      close: '关闭'
    },
    pagination: {
      showing: '显示',
      to: '至',
      of: '共',
      perPage: '每页',
      previous: '上一页',
      next: '下一页',
      itemCount: '{count} 个{label}',
      itemCount_plural: '{count} 个{label}'
    },
    status: {
      loading: '加载中',
      working: '处理中...',
      refreshing: '刷新中...',
      unavailable: '不可用',
      noData: '无数据',
      noPermission: '无权限',
      disabled: '已禁用',
      healthy: '健康',
      stable: '稳定',
      nominal: '正常',
      attention: '注意',
      highLoad: '高负载',
      highUsage: '高使用率'
    },
    forms: {
      required: '必填',
      optional: '可选',
      selectOption: '请选择'
    },
    labels: {
      state: '状态',
      user: '用户',
      group: '组',
      account: '账户',
      partition: '分区',
      qos: 'QOS',
      priority: '优先级',
      reason: '原因',
      actions: '操作',
      resources: '资源',
      memory: '内存',
      cpu: 'CPU',
      gpu: 'GPU',
      nodes: '节点',
      timeRange: '时间范围',
      submitTime: '提交时间',
      duration: '持续时间',
      users: '用户',
      accounts: '账户',
      partitions: '分区',
      name: '名称',
      description: '说明',
      organization: '组织',
      title: '标题',
      updated: '更新时间',
      code: '代码',
      tool: '工具',
      interface: '接口',
      created: '创建时间',
      summary: '摘要',
      shortcuts: '快捷入口',
      fullName: '姓名',
      username: '用户名',
      cluster: '集群',
      flags: '标记',
      from: '从',
      to: '到'
    },
    metricRanges: {
      hour: '小时',
      day: '天',
      week: '周',
      custom: '自定义',
      reset: '重置',
      oneDay: '1 天',
      threeDays: '3 天',
      sevenDays: '7 天',
      fifteenDays: '15 天',
      oneMonth: '1 个月',
      lastHour: '最近一小时'
    },
    entities: {
      jobs: '作业',
      job: '作业',
      records: '记录',
      record: '记录',
      nodes: '节点',
      nodeGroups: '节点组',
      accounts: '账户',
      rootAccounts: '根账户',
      userAssociations: '用户关联',
      reservations: '预留',
      qosPolicies: 'QOS 策略',
      users: '用户'
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
    heroDescription:
      '统一集群运维、作业观测与基础设施导航，提供更清晰一致的控制台体验。',
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
      description:
        '当关闭身份验证时，Slurm Web Plus 仍可通过轻量匿名会话将访问者引导到控制中心。',
      status: '状态',
      authBlocked: '已启用身份验证，匿名访问不可用。',
      authFailed: '匿名访问失败：{message}'
    },
    clusters: {
      signOut: '退出登录',
      kicker: '集群网关',
      title: '选择一个集群',
      description:
        '比较当前可见环境、查看可用性，并直接进入共享运维控制台。',
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
      deniedTitle: '当前页面访问受限',
      missingPermission: '缺少所需权限：{permission}',
      genericDetail: '你当前的角色没有访问此页面的权限。',
      contactAdmin: '请联系管理员申请访问权限。',
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
    },
    account: {
      title: '账户',
      description: '查看个人身份、所属组以及集群级权限。',
      username: '用户名',
      fullName: '姓名',
      groups: '组',
      clusterPermissions: '集群权限',
      clusterDescription: '查看此集群解析后的策略、自定义覆盖和合并权限。',
      actions: {
        openWorkspace: '打开我的工作区',
        openAnalysis: '打开我的分析页',
        viewHistoryJobs: '查看我的历史作业'
      },
      permissionSources: {
        policy: {
          title: '策略',
          description: '来自当前活动策略的基础 RBAC 角色与动作。'
        },
        custom: {
          title: '自定义',
          description: '站点级补充项或覆盖项。'
        },
        merged: {
          title: '合并结果',
          description: '最终暴露给应用的有效权限。'
        }
      },
      sourceSummary: '{title} 角色与动作',
      roles: '角色',
      actionsLabel: '动作',
      rules: '规则',
      emptyRoles: '未声明角色。',
      emptyActions: '未声明动作。',
      emptyRules: '未声明路由规则。'
    },
    ai: {
      title: 'AI',
      description: '在同一工作区中管理集群 AI 模型、连通性校验以及管理员侧对话审计。',
      actions: {
        goToChat: '前往对话',
        newModel: '新建模型',
        edit: '编辑',
        testConnection: '测试连接',
        testing: '测试中...',
        setDefault: '设为默认',
        delete: '删除',
        deleting: '删除中...',
        keep: '保留',
        replace: '替换',
        clear: '清除',
        createModel: '创建模型'
      },
      alerts: {
        noClusterContext: '当前没有可用于 AI 设置的集群上下文。',
        unavailable: '当前集群未启用 AI 能力。',
        noPermission: '当前用户无权查看此集群的 AI 设置。',
        readOnly: '当前用户可以查看 AI 设置，但无权在此集群上修改。'
      },
      configs: {
        title: '模型配置',
        description: '每一行定义一个集群模型目标，包含提供方路由、密钥状态和校验状态。',
        loading: '正在加载模型配置...',
        empty: '此集群暂时还没有模型配置。',
        columns: {
          displayName: '显示名称',
          provider: '提供方',
          model: '模型',
          state: '状态',
          default: '默认',
          secret: '密钥',
          validated: '已校验',
          actions: '操作'
        },
        state: {
          enabled: '已启用',
          disabled: '已禁用',
          default: '默认',
          configured: '已配置',
          notConfigured: '未配置'
        },
        actionTitles: {
          create: '创建一个新的集群级 AI 模型配置。',
          edit: '打开编辑器，更新提供方设置、路由、提示词和密钥。',
          test: '使用当前模型配置执行一次在线连通性检查。',
          setDefault: '将此模型设为新 AI 对话的默认目标。',
          toggle: '启用或禁用此模型，而不删除已保存配置。',
          delete: '删除此模型配置及其已保存密钥。'
        }
      },
      audit: {
        title: '对话审计',
        description: '以表格方式查看集群级 AI 对话记录，并可打开详情页查看完整消息与工具历史。',
        filters: {
          username: '用户名',
          usernamePlaceholder: '按用户名筛选',
          title: '标题',
          titlePlaceholder: '按对话标题筛选'
        },
        loading: '正在加载对话审计...',
        empty: '此集群暂无 AI 对话记录。',
        noMatch: '当前筛选条件下没有匹配的 AI 对话记录。',
        state: {
          deleted: '已删除',
          active: '活动中'
        },
        openDetail: '打开详情',
        columns: {
          title: '标题',
          user: '用户',
          state: '状态',
          updated: '更新时间',
          details: '详情'
        }
      },
      modal: {
        kicker: '模型编辑器',
        createTitle: '创建模型配置',
        editTitle: '编辑模型配置',
        description: '提供方密钥保存在数据库中，只会以脱敏摘要的形式返回到 UI。'
      },
      fields: {
        configName: '配置名称',
        displayName: '显示名称',
        provider: '提供方',
        model: '模型',
        baseUrl: '基础 URL',
        sortOrder: '排序权重',
        deployment: '部署名',
        apiVersion: 'API 版本',
        requestTimeout: '请求超时',
        temperature: '温度',
        systemPrompt: '系统提示词',
        extraOptions: '扩展选项',
        apiKey: 'API Key',
        enabled: '启用',
        isDefault: '设为默认'
      },
      hints: {
        configName: '用于标识该已保存模型条目的稳定标识符。',
        configNameTooltip: '用于集群配置列表和审计记录内部识别。',
        displayName: '终端用户选择模型时看到的友好名称。',
        displayNameTooltip: '可以比提供方模型标识更易读。',
        provider: '选择接收聊天请求的上游 AI 服务。',
        providerTooltip: '提供方决定下面需要填写哪些连接参数。',
        model: '提供方侧的模型标识、部署名或运行时标签。',
        modelTooltip: '例如：gpt-4.1、claude-3-7-sonnet、qwen-max、llama3.1。',
        baseUrl: '当提供方通过自定义端点提供服务时，可选覆盖默认地址。',
        baseUrlTooltip: '留空则使用该提供方的默认 API 基础地址。',
        sortOrder: '用于控制模型在 UI 中顺序的可选数值权重。',
        sortOrderTooltip: '值越小越靠前；留空时回退为 0。',
        deployment: 'Azure OpenAI 用于将请求路由到目标模型的部署名称。',
        deploymentTooltip: 'Azure 请求时使用部署标识，而不是原始模型名。',
        apiVersion: '附加到请求中的 Azure API 版本，用于兼容性控制。',
        apiVersionTooltip: '请与部署启用的 Azure OpenAI API 版本保持一致。',
        requestTimeout: '聊天或校验请求在被中止前的可选超时时间（秒）。',
        requestTimeoutTooltip: '适用于较慢的提供方或本地私有网关。',
        temperature: '可选采样控制项，用于调整生成的随机性与确定性。',
        temperatureTooltip: '留空则由提供方或服务端默认值决定。',
        secretDescription: '对当前模型保留、替换或清除已保存的密钥。',
        replaceSecretTitle: '用新的 API key 替换当前已存储密钥。',
        clearSecretTitle: '移除当前已存储密钥。未重新设置前后续请求会失败。',
        apiKey: '安全存储的凭证，只会以脱敏形式回显到 UI。',
        apiKeyTooltip: '对使用 bearer secret 认证的提供方是必填项。',
        systemPrompt: '可选的指令前缀，会附加到该模型的每次新对话。',
        systemPromptTooltip: '可用于约束语气、范围、安全策略或集群专属上下文。',
        extraOptions: '用于填写提供方专有请求字段的可选 JSON 对象，适用于表单中没有单独控件的情况。',
        extraOptionsTooltip: '例如 max_tokens、top_p、reasoning 选项或自定义 header。'
      },
      secret: {
        title: '密钥'
      },
      placeholders: {
        apiKey: '请输入 API 密钥',
        extraOptions: '{ }'
      },
      submitTitles: {
        create: '为该集群创建新的模型配置。',
        edit: '将编辑后的模型配置保存到集群。'
      },
      feedback: {
        created: '模型配置已创建。',
        updated: '模型配置已更新。',
        enabled: '{name} 已启用。',
        disabled: '{name} 已禁用。',
        defaultSet: '{name} 已设为默认模型。',
        validated: '连接校验成功：{sample}',
        deleted: '{name} 已删除。'
      },
      errors: {
        requestTimeoutInteger: 'request_timeout 必须是整数',
        integerField: '{field} 必须是整数',
        temperatureNumeric: 'temperature 必须是数字',
        extraOptionsObject: 'extra_options 必须是 JSON 对象',
        apiKeyRequired: '创建非 Ollama 模型时必须提供 api_key',
        apiKeyReplaceRequired: '替换当前密钥前，请先输入新的 api_key'
      }
    },
    aiDetail: {
      title: 'AI 对话详情',
      description: '查看单条审计对话的完整消息历史和工具执行记录。',
      actions: {
        backToAudit: '返回审计列表'
      },
      alerts: {
        noClusterContext: '当前管理路由没有可用的集群上下文。',
        unavailable: '当前集群未启用 AI 能力。',
        noPermission: '当前用户无权查看此集群的 AI 审计数据。',
        invalidConversationId: '对话 ID 无效。',
        detailUnavailable: '对话详情不可用。'
      },
      loading: '正在加载对话详情...',
      summary: {
        title: '标题',
        user: '用户',
        updated: '更新时间',
        state: '状态',
        deleted: '已删除',
        active: '活动中'
      },
      messages: {
        title: '消息',
        description: '完整对话内容按时间顺序展示，不再和主审计表相互竞争视觉焦点。'
      },
      toolCalls: {
        title: '工具调用',
        description: '工具执行记录与消息分离，方便运维人员快速定位失败和时延，而无需通读整段对话。',
        empty: '该对话没有记录任何工具调用。',
        columns: {
          tool: '工具',
          interface: '接口',
          status: '状态',
          code: '代码',
          duration: '耗时',
          created: '创建时间',
          summary: '摘要'
        },
        durationMs: '{value} 毫秒'
      }
    },
    cache: {
      title: '缓存服务',
      description: '查看每个集群的缓存可用性、命中率和实时指标。',
      clusterKicker: '集群缓存',
      clusterTitle: '集群 {cluster}',
      alerts: {
        noPermission: '无权查看该集群的缓存信息。',
        disabled: '该集群未启用缓存。'
      },
      metricsUnavailable: {
        kicker: '指标不可用',
        title: '实时缓存指标不可用',
        description: '该集群提供了缓存统计，但没有启用指标采集，因此当前无法展示实时缓存时间线。'
      },
      statistics: {
        title: '缓存统计',
        description: '按 key 分组统计命中与未命中比例，并展示整个集群缓存的总命中率。',
        error: '无法获取缓存统计。',
        loading: '正在加载统计...',
        reset: '重置统计',
        columns: {
          name: '名称',
          hit: '命中',
          miss: '未命中',
          total: '总计',
          hitRate: '命中率'
        },
        total: '总计',
        overviewKicker: '缓存概览',
        overviewTitle: '流量快照',
        overviewDescription: '快速查看当前缓存活动窗口下的总请求量和命中质量。',
        overviewEmptyDescription: '当前尚未记录到任何缓存请求，因此图表会在有流量之前保持隐藏。',
        cards: {
          hitRate: '命中率',
          requests: '请求数',
          keyGroups: 'Key 分组'
        },
        waitingTitle: '等待缓存活动',
        waitingDescription: '当集群记录到命中或未命中后，这里会展示分布图表。',
        chart: {
          hit: '命中',
          miss: '未命中'
        }
      },
      metrics: {
        title: '缓存指标',
        description: '查看缓存操作中的实时命中与未命中活动。',
        error: '无法获取缓存指标。',
        emptyTitle: '当前时间范围内没有实时缓存指标样本',
        emptyDescription: '请切换时间范围，或等待缓存流量产生新的命中与未命中数据点。'
      }
    },
    ldapUsers: {
      alerts: {
        authDisabled: 'LDAP 认证已禁用，因此无法查看缓存目录用户。',
        noClusterDatabase: '当前没有启用数据库支持的集群可用于查看缓存目录用户。',
        noPermission: '无权查看该集群的缓存目录用户。',
        databaseDisabled: '该集群未启用数据库支持。',
        empty: '该集群未找到任何缓存用户。'
      },
      search: {
        label: '按用户名搜索',
        placeholder: '搜索用户名...'
      },
      loading: '正在加载缓存用户...',
      resultsCount: '找到 {count} 个用户',
      resultsCountPlural: '找到 {count} 个用户',
      columns: {
        username: '用户名',
        fullName: '姓名',
        shortcuts: '快捷入口'
      },
      actions: {
        viewUser: '查看用户',
        openAnalysis: '打开分析',
        viewHistoryJobs: '查看历史作业'
      }
    },
    accessControl: {
      title: '访问控制',
      description: '管理当前集群基于数据库的自定义角色、路由权限规则和用户角色绑定。',
      activeCluster: '当前集群',
      resourcesCount: '{count} 个资源',
      alerts: {
        noClusterContext: '当前没有可用于访问控制管理的集群上下文。',
        unavailable: '当前集群未启用访问控制。',
        noPermission: '无权查看该集群的访问控制数据。',
        readOnly: '你可以查看该集群角色，但编辑需要 `{permission}` 权限。'
      },
      roles: {
        kicker: '自定义角色',
        title: '角色定义',
        description: '通过 `resource:operation:scope` 规则精确控制路由权限。为兼容旧动作会自动推导 legacy actions。',
        loading: '正在加载访问控制数据...',
        empty: '当前还没有自定义角色。首次启用数据库后会自动初始化种子角色。',
        noDescription: '未提供说明。',
        permissions: '权限',
        compatibilityActions: '兼容动作',
        noLegacyActions: '没有推导出 legacy action。',
        createKicker: '创建角色',
        editKicker: '编辑角色',
        createTitle: '权限矩阵',
        editTitle: '正在编辑 {name}',
        clear: '清除',
        roleName: '角色名称',
        roleNamePlaceholder: 'ops-viewer',
        roleDescription: '说明',
        roleDescriptionPlaceholder: '对集群路由提供只读访问。',
        resourceMatrix: '资源矩阵',
        resourceMatrixDescription: '可授予精确规则、`settings/*` 这类通配资源，或 `*:*:*` 形式的全局管理权限。',
        selectedCount: '已选择 {count} 项',
        ownerAware: '仅本人',
        clusterWide: '全局',
        ruleLabel: '{operation} / {scope}',
        selectedRules: '已选择规则',
        noRulesSelected: '尚未选择任何规则。',
        derivedActions: '推导出的 legacy actions',
        noDerivedActions: '没有推导出兼容动作。',
        createSubmit: '创建角色',
        saveSubmit: '保存角色',
        reset: '重置',
        errors: {
          roleNameRequired: '角色名称不能为空。',
          permissionRequired: '请至少选择一条权限规则。'
        }
      },
      users: {
        kicker: '用户分配',
        title: '用户角色绑定',
        description: '将缓存用户绑定到自定义角色。策略角色保持只读，来源于当前生效的 RBAC 文件。',
        searchPlaceholder: '搜索用户名...',
        loading: '正在加载用户...',
        empty: '当前搜索条件下没有匹配的缓存用户。',
        noFullNameCached: '没有缓存姓名。',
        roleCount: '{count} 个自定义角色',
        roleCountPlural: '{count} 个自定义角色',
        page: '第 {page} 页 / 共 {total} 页',
        assignmentKicker: '分配详情',
        assignmentEmptyTitle: '选择一个用户',
        assignmentTitle: '{user}',
        assignmentDescription: '为该缓存用户附加自定义角色。最终生效的路由权限是策略规则与自定义规则的并集。',
        loadingAssignment: '正在加载用户分配...',
        selectUserNotice: '请选择一个用户以查看并修改角色绑定。',
        policyRoles: '策略角色',
        customRoles: '自定义角色',
        mergedActions: '合并动作',
        none: '无',
        assignedRoles: '已分配的自定义角色',
        createRoleFirst: '请先创建至少一个角色，再为用户分配。',
        noDescription: '未提供说明。',
        saveAssignments: '保存分配',
        resetSelection: '重置选择'
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
  },
  components: {
    chartSkeleton: {
      loadingChart: '图表加载中'
    },
    jobBack: {
      toNode: '返回节点',
      toJobsHistory: '返回历史作业',
      toJobs: '返回作业'
    },
    resourcesBack: {
      toResources: '返回资源'
    },
    settingsBack: {
      toDashboards: '返回概览'
    },
    admin: {
      title: '管理',
      description: '面向集群范围的管理、缓存服务与访问控制。',
      ai: 'AI',
      cache: '缓存',
      users: '用户',
      accessControl: '访问控制'
    },
    metricRangeSelector: {
      ariaLabel: '选择时间范围'
    }
  },
  filters: {
    title: '筛选',
    active: '筛选已启用',
    add: '添加筛选',
    closeMenu: '关闭菜单',
    remove: '移除筛选 {group}:{value}',
    partitions: '分区',
    users: {
      usernamePlaceholder: '输入用户名...',
      addUsername: '添加用户名'
    },
    states: {
      completed: '已完成',
      failed: '失败',
      running: '运行中',
      pending: '排队中'
    },
    history: {
      keyword: '关键词',
      keywordPlaceholder: '搜索工作目录 / 命令',
      userPlaceholder: '用户名',
      accountPlaceholder: '账户名',
      partitionPlaceholder: '分区名',
      qosPlaceholder: 'QOS 名称',
      jobId: '作业 ID',
      timeRange: '时间范围',
      apply: '应用筛选',
      active: '已启用筛选',
      fromValue: '从 {value}',
      toValue: '到 {value}'
    }
  },
  sort: {
    label: '排序',
    order: '顺序'
  },
  tables: {
    jobs: {
      columns: {
        id: '#ID',
        state: '状态',
        userAccount: '用户（账户）',
        resources: '资源',
        partition: '分区',
        qos: 'QOS',
        priority: '优先级',
        reason: '原因',
        actions: '操作',
        submitTime: '提交时间'
      }
    },
    reservations: {
      columns: {
        name: '名称',
        nodes: '节点',
        duration: '持续时间',
        users: '用户',
        accounts: '账户',
        flags: '标记',
        actions: '操作'
      }
    },
    resources: {
      columns: {
        nodeName: '节点名',
        state: '状态',
        allocation: '分配',
        cpu: 'CPU',
        memory: '内存',
        gpu: 'GPU',
        partitions: '分区'
      }
    },
    qos: {
      columns: {
        name: '名称',
        priority: '优先级',
        jobs: '作业',
        resources: '资源',
        time: '时间',
        flags: '标记',
        actions: '操作'
      }
    },
    userAssociations: {
      columns: {
        user: '用户',
        account: '账户',
        jobLimits: '作业限制',
        resourceLimits: '资源限制',
        timeLimits: '时间限制',
        qos: 'QOS',
        actions: '操作'
      }
    }
  },
  pages: {
    dashboard: {
      title: '概览',
      description: '在统一控制视图中查看集群实时统计、工作负载活动与指标趋势。',
      openAnalysis: '打开分析',
      partitionAll: '整个集群',
      stats: {
        nodes: '节点',
        cores: '核心',
        totalMemory: '总内存',
        allocatedMemory: '已分配内存',
        availableMemory: '可用内存',
        clusterCapacity: '集群容量',
        requestedByJobs: '作业请求量',
        totalMinusAllocated: '总量减已分配',
        runningJobs: '运行中作业',
        totalJobs: '总作业数'
      },
      toolbar: {
        kicker: '实时控制',
        title: '实时指标',
        description: '在同一工具栏中按队列筛选概览统计，并调整实时观察窗口。',
        partitionQueue: '分区 / 队列',
        selectMetricsRange: '选择概览指标时间范围'
      },
      errors: {
        unableToRetrieve: '无法从集群 {cluster} 获取统计信息'
      }
    },
    jobs: {
      title: '作业',
      description: '查看队列、活动状态、账户上下文，并快速钻取到作业详情。',
      metricLabel: '个作业',
      metricLabelPlural: '个作业',
      addFilters: '添加筛选',
      submitJob: '提交作业',
      noJobs: '集群 {cluster} 上没有作业',
      unableToRetrieve: '无法从集群 {cluster} 获取作业',
      headingFilters: '筛选',
      actions: {
        edit: '编辑',
        cancel: '取消',
        view: '查看'
      },
      dialogs: {
        submit: {
          title: '提交作业',
          description: '从作业工作区创建新的 Slurm 作业。',
          submit: '提交作业',
          fields: {
            name: '作业名称',
            script: '脚本',
            partition: '分区',
            account: '账户',
            qos: 'QOS'
          }
        },
        edit: {
          title: '编辑作业',
          description: '更新 {cluster} 上的作业 {jobId}。',
          submit: '保存更改',
          fields: {
            partition: '分区',
            qos: 'QOS',
            priority: '优先级',
            memoryPerCpuMb: '每 CPU 内存（MB）',
            memoryPerCpuHint: '可选',
            memoryPerCpuTooltip: '设置后将作为 Slurm REST 的 memory_per_cpu.number 提交。',
            timeLimit: '时间限制',
            comment: '备注'
          },
          errors: {
            invalidMemoryPerCpu: '每 CPU 内存必须是正整数（MB）。'
          }
        },
        cancel: {
          title: '取消作业',
          description: '取消作业 {jobId}。此操作具有破坏性。',
          submit: '取消作业',
          fields: {
            signal: '信号',
            reason: '原因'
          }
        }
      },
      notifications: {
        submitRequested: '已请求在 {cluster} 上提交作业。',
        updateRequested: '已请求更新作业 {jobId}。',
        cancelRequested: '已请求取消作业 {jobId}。'
      }
    },
    jobsHistory: {
      title: '历史作业',
      description: '查看带有调度上下文、状态变化和可搜索执行元数据的历史作业记录。',
      metricLabel: '条记录',
      metricLabelPlural: '条记录',
      addFilters: '添加筛选',
      noRecords: '集群 {cluster} 上没有历史作业记录',
      liveJob: '实时作业',
      history: '历史详情',
      headingFilters: '筛选'
    },
    job: {
      kicker: '作业详情',
      title: '作业 {jobId}',
      description: '查看所选作业的执行状态、请求元数据和已分配资源。',
      loadingTitle: '作业 {jobId}',
      summary: {
        user: '用户',
        account: '账户',
        partition: '分区',
        nodes: '节点',
        requested: '请求资源',
        requestedSubtle: '请求了 {count} 个 GPU',
        requestedUnavailable: 'GPU 请求不可用',
        allocated: '已分配资源',
        allocatedSubtle: '已分配 {count} 个 GPU',
        allocatedUnavailable: 'GPU 分配不可用',
        exitCode: '退出码',
        stateReason: '状态原因'
      },
      fields: {
        user: '用户',
        group: '组',
        account: '账户',
        wckeys: 'Wckeys',
        priority: '优先级',
        nodes: '节点',
        partition: '分区',
        qos: 'QOS',
        exitCode: '退出码',
        name: '名称',
        comments: '备注',
        submitLine: '提交命令',
        script: '脚本',
        workingDirectory: '工作目录',
        requested: '请求资源',
        allocated: '已分配资源'
      },
      panels: {
        executionTimelineTitle: '执行时间线',
        executionTimelineDescription: '查看该作业的提交、调度和运行阶段里程碑。',
        configurationTitle: '作业配置',
        configurationDescription: '核心身份、命令上下文以及请求与已分配资源。',
        detailedTitle: '详细资源与命令',
        detailedDescription: '较长字段保持展开，便于阅读和复制。'
      },
      actions: {
        edit: '编辑',
        cancel: '取消'
      },
      errors: {
        unableToRetrieve: '无法从集群 {cluster} 获取作业 {jobId}'
      },
      dialogs: {
        edit: {
          title: '编辑作业',
          description: '更新 {cluster} 上的作业 {jobId}。',
          submit: '保存更改'
        },
        cancel: {
          title: '取消作业',
          description: '取消作业 {jobId}。此操作具有破坏性。',
          submit: '取消作业'
        }
      },
      notifications: {
        updateRequested: '已请求更新作业 {jobId}。',
        cancelRequested: '已请求取消作业 {jobId}。'
      }
    },
    resources: {
      title: '节点',
      description: '查看整个集群中的节点当前状态、分配压力和分区可见性。',
      metricLabel: '个节点',
      metricLabelPlural: '个节点',
      rack: '机架',
      actions: {
        showRackDiagram: '显示机架图',
        hideRackDiagram: '隐藏机架图',
        toggleFoldedNodes: '切换折叠节点 {name}'
      },
      errors: {
        unableToRetrieve: '无法从集群 {cluster} 获取节点'
      }
    },
    partition: {
      description: '查看所选分区的拓扑、节点覆盖范围和核心容量。',
      detailTitle: '分区详情',
      detailDescription: '查看该分区的节点集合定义以及当前工作区可见的容量情况。',
      metrics: {
        kicker: '实时指标',
        title: '分区实时曲线',
        description: '复用 dashboard 曲线，按分区 {partition} 查看资源和作业走势。',
        selectRange: '选择分区指标时间范围'
      },
      nodeSets: '节点集合',
      nodeSetsDescription: '节点集合表达式用于说明该分区由哪些主机提供容量。',
      nodeSetsEmpty: '该分区当前没有可展示的节点集合表达式。',
      notFound: '当前集群中不存在分区 {partition}。',
      summary: {
        nodes: '节点数',
        allocatedNodes: '已分配节点',
        idleNodes: '空闲节点',
        totalCpu: '总 CPU',
        allocatedCpu: '已分配 CPU',
        totalMemory: '总内存',
        gpu: 'GPU'
      }
    },
    node: {
      kicker: '节点详情',
      title: '节点 {nodeName}',
      description: '查看所选节点的实时分配状态、硬件配置和工作负载占用情况。',
      overviewTitle: '节点概览',
      overviewDescription: '调度状态、硬件布局、所属分区以及当前运行作业。',
      realtimeTitle: '实时指标',
      realtimeDescription: '该节点由 Prometheus 支持的实时与历史使用情况指标。',
      usageHistoryTitle: '使用历史',
      usageHistoryDescription: '所选时间范围内的 CPU、内存和磁盘使用趋势。',
      stats: {
        cpuCapacity: 'CPU 容量',
        cpuLayout: '{sockets} 个插槽 x {cores} 个核心',
        memory: '内存',
        gpuSlots: 'GPU 插槽',
        realtimeCpu: '实时 CPU',
        allocated: '已分配：{value}',
        metricsUnavailable: '指标不可用',
        updatedEvery15s: '每 15 秒更新一次',
        actualCpu: '{used} / {total} 核'
      },
      detail: {
        nodeStatus: '节点状态',
        allocationStatus: '分配状态',
        currentJobs: '当前作业',
        cpuLayout: 'CPU 布局',
        threadsPerCore: '每核线程数',
        architecture: '架构',
        memory: '内存',
        gpu: 'GPU',
        partitions: '分区',
        osKernel: '操作系统内核',
        reboot: '重启时间',
        lastBusy: '最近繁忙时间',
        reasonLabel: '原因：{reason}',
        unableToRetrieveJobs: '无法获取作业',
        loadingJobs: '正在加载作业...'
      },
      metrics: {
        cpuUsage: 'CPU 使用率',
        memoryUsage: '内存使用率',
        diskUsage: '磁盘使用率',
        disk: '磁盘',
        actual: '实际值：{value}',
        noActualValue: '实际值：N/A',
        na: 'N/A',
        loadingRealtime: '正在加载实时指标...',
        loadingHistory: '正在加载历史数据...',
        noHistory: '此时间范围没有可用的指标历史。',
        unableRealtime: '无法获取该节点的实时指标。',
        unableHistory: '无法获取该节点的历史指标。'
      },
      actions: {
        edit: '编辑',
        delete: '删除',
        editTooltip: '编辑节点状态并设置调度器可见原因。',
        deleteTooltip: '从集群中删除该节点定义。'
      },
      toolbar: {
        selectRange: '选择节点指标时间范围'
      },
      errors: {
        unableToRetrieve: '无法从集群 {cluster} 获取节点 {nodeName}',
        deleteConfirmation: '请输入 DELETE 以确认。'
      },
      dialogs: {
        edit: {
          title: '编辑节点',
          description: '更新 {cluster} 上的节点 {nodeName}。',
          submit: '保存更改',
          tooltip: '将编辑后的节点状态和可选原因应用到所选集群节点。',
          fields: {
            state: '状态',
            statePlaceholder: '选择节点状态',
            stateHint: '当前节点状态：{state}。请选择要应用到该节点的 Slurm 状态动作。',
            stateTooltip:
              '使用 DRAIN 开始排空节点。根据运行中的作业情况，Slurm 后续可能将其显示为 DRAINING 或 DRAINED。',
            reason: '原因',
            reasonHint: '可选审计说明，会随节点状态显示在集群界面和调度器输出中。',
            reasonTooltip: '当排空或改变节点行为时使用，便于运维人员理解原因。'
          }
        },
        delete: {
          title: '删除节点',
          description: '删除节点 {nodeName}。此操作具有破坏性。',
          submit: '删除节点',
          tooltip: '确认后永久移除该节点定义。',
          fields: {
            confirmation: '输入 DELETE 以确认',
            confirmationHint: '准确输入 DELETE 才能解锁此破坏性操作。',
            confirmationTooltip: '该保护措施可防止误删节点。'
          }
        }
      },
      notifications: {
        updateRequested: '已请求更新节点 {nodeName}。',
        deleteRequested: '已请求删除节点 {nodeName}。'
      }
    },
    accounts: {
      title: '账户',
      description: '以树形结构展示集群中的账户、层级关系、委派用户和组织结构。',
      metricLabel: '个账户',
      metricLabelPlural: '个账户',
      create: '创建账户',
      unableToRetrieve: '无法从集群 {cluster} 获取账户',
      noAccounts: '集群 {cluster} 上没有定义账户',
      paginationLabel: '根账户',
      dialogs: {
        create: {
          title: '创建账户',
          description: '在账户树工作区中新增 SlurmDB 账户。',
          submit: '创建账户',
          fields: {
            name: '账户名称',
            description: '说明',
            organization: '组织',
            parentAccount: '父账户',
            qos: 'QOS（逗号分隔）'
          }
        }
      },
      notifications: {
        createRequested: '已请求创建账户 {name}。'
      }
    },
    account: {
      kicker: '账户详情',
      description: '查看所选 Slurm 账户的层级、继承策略和按用户覆盖配置。',
      metricLabel: '个用户关联',
      metricLabelPlural: '个用户关联',
      back: '返回账户',
      overviewTitle: '账户概览',
      overviewDescription: '父级层级、QoS 范围以及账户级继承限制。',
      userAssociationsTitle: '用户关联',
      userAssociationsDescription: '挂载到此账户的用户关联，继承值会以弱化方式展示。',
      noAccount: '账户 {account} 在此集群中不存在。',
      noAssociations: '账户 {account} 没有终端用户关联。',
      noAssociationsYet: '账户 {account} 还没有终端用户关联。',
      actions: {
        viewJobs: '查看作业',
        addUser: '添加用户',
        edit: '编辑',
        delete: '删除',
        editQos: '编辑 QOS'
      },
      stats: {
        parentChain: '父链',
        directSubaccounts: '直接子账户',
        qosScope: 'QoS 范围',
        appliedAtAccountLevel: '应用于账户级别',
        jobLimits: '作业限制',
        configuredLimitEntries: '已配置限制项',
        timeLimits: '时间限制',
        walltimePolicies: '运行时策略'
      },
      detail: {
        parentAccounts: '父账户',
        subaccounts: '子账户',
        qos: 'QoS',
        jobLimits: '作业限制',
        resourceLimits: '资源限制',
        timeLimits: '时间限制'
      },
      limits: {
        running: '运行中',
        submitted: '已提交',
        runningPerUser: '每用户运行中',
        submittedPerUser: '每用户已提交',
        total: '总量',
        perJob: '每作业',
        perNode: '每节点'
      },
      tables: {
        defaultQos: '默认：{qos}'
      },
      errors: {
        unableToRetrieve: '无法获取集群 {cluster} 的关联信息'
      },
      dialogs: {
        edit: {
          title: '编辑账户',
          description: '更新账户 {account}。',
          submit: '保存更改'
        },
        addUserAssociation: {
          title: '添加用户关联',
          description: '将用户添加到账户 {account}。',
          submit: '添加用户'
        },
        editUserQos: {
          title: '编辑用户 QOS',
          description: '更新 {account} 上用户 {user} 的 QOS。',
          submit: '保存更改'
        },
        delete: {
          title: '删除账户',
          description: '删除账户 {account}。此操作具有破坏性。',
          submit: '删除账户'
        },
        deleteAssociation: {
          title: '删除用户关联',
          description: '将用户 {user} 从账户 {account} 中移除。此操作具有破坏性。',
          submit: '删除关联'
        },
        fields: {
          description: '说明',
          organization: '组织',
          parentAccount: '父账户',
          qosCsv: 'QOS（逗号分隔）',
          username: '用户名',
          assignedQosCsv: '分配的 QOS（逗号分隔）',
          defaultQos: '默认 QOS'
        }
      },
      notifications: {
        updateRequested: '已请求更新账户 {account}。',
        addUserRequested: '已请求为账户 {account} 添加用户关联 {user}。',
        updateQosRequested: '已请求更新 {account} 上用户 {user} 的 QOS。',
        removeUserRequested: '已请求从 {account} 中移除用户 {user}。',
        deleteRequested: '已请求删除账户 {account}。'
      }
    },
    analysis: {
      kicker: '容量分析',
      title: '集群效率',
      metricLabel: '运维评分',
      actions: {
        liveDashboard: '实时概览',
        inspectQueue: '查看队列',
        openResources: '打开资源页'
      },
      loading: '正在构建集群分析工作区...',
      status: {
        prefix: '状态：',
        updated: '更新时间 {time}',
        refreshing: '刷新中',
        efficient: '高效',
        stable: '稳定',
        pressured: '有压力',
        constrained: '受限',
        neutral: '中性',
        warning: '警告',
        danger: '严重',
        success: '健康',
        ready: '就绪'
      },
      toolbar: {
        selectRange: '选择集群分析时间范围'
      },
      sections: {
        capacityTitle: '容量边界',
        capacityDescription: '查看整个集群当前利用率以及可调度冗余空间。',
        blockersTitle: '队列阻塞因素',
        blockersDescription: '查看作业为何等待，以及队列是被容量、策略还是装箱方式阻塞。',
        partitionTitle: '分区热点',
        partitionDescription: '分区级压力有助于判断是扩容、重平衡作业还是调整 QOS。',
        historicalTitle: '历史压力',
        historicalDescription: '快速历史快照可帮助判断容量压力是持续、突发还是策略驱动。',
        nodeHotspotsTitle: '节点热点',
        nodeHotspotsDescription: '展示所选分析时间窗内 CPU 或内存持续超过 80% 的节点。',
        actionsTitle: '建议动作',
        actionsDescription: '下面的建议基于实时遥测生成，用于降低排队时间并提升作业吞吐。',
        healthTitle: '控制器健康',
        healthDescription: '来自 Slurm `ping` 和 `diag` 端点的轻量控制器状态检查。'
      },
      blockers: {
        noJobPermission: '分析队列阻塞需要作业可见权限。',
        jobsUnavailable: '当前无法获取作业队列数据。',
        none: '当前没有待处理作业在阻塞队列。',
        pendingJobs: '{count} 个待处理作业',
        packingSignal: '装箱信号',
        packingDetail:
          '{count} 个待处理单节点作业似乎受碎片化影响而被阻塞，同时仍有 {cpu} 个可调度 CPU 空闲。'
      },
      partition: {
        noPermission: '分析分区压力同时需要作业和节点可见权限。',
        none: '当前未观察到分区级压力。',
        pendingActive: '{pending} 个待处理，{running} 个活跃',
        cpuChip: 'CPU {running}/{total}',
        pendingCpu: '待处理 CPU：{value}',
        totalCpu: '总 CPU：{value}',
        schedulableCpu: '可调度 CPU：{value}'
      },
      historical: {
        metricsDisabled: '该集群未启用指标采集，但仍可使用实时分析。',
        metricsUnavailable: '历史指标暂时不可用。',
        avgQueueWait: '平均排队时间',
        avgQueueWaitDetail: '按提交时间到启动时间的平均等待时长分组展示，数值单位为秒。',
        aggregationLabel: '聚合粒度',
        aggregationAria: '排队时间聚合粒度 {value}',
        aggregationOptions: {
          minute: '分钟',
          hour: '小时',
          day: '天'
        },
        secondsUnit: '秒',
        latestTelemetry: '最新遥测',
        latestTelemetryDetail: '所选时间范围内最近一次指标采样的作业情况。',
        waitSamples: '已完成作业',
        waitMedian: '中位等待 {seconds} 秒',
        waitP90: 'p90 为 {p90} 秒，基于最近 {samples} 个已完成作业。',
        waitUnavailable: '该集群或时间范围内的已完成作业历史不可用。',
        waitDisabled: '该集群未启用已完成作业历史。'
      },
      health: {
        ping: 'Ping',
        diag: 'Diag',
        pingUnavailable: '当前无法获取该集群的 Ping 数据。',
        pingEmpty: '当前响应中没有可用的控制器 Ping 字段。',
        diagUnavailable: '当前无法获取该集群的诊断数据。',
        diagEmpty: '当前响应中没有可用的诊断摘要字段。',
        fallbackController: '控制器'
      },
      nodeHotspots: {
        empty: '当前时间窗内没有节点 CPU 或内存热点事件超过 80% 阈值。',
        summary: '节点 {node}',
        detail: '{time} {metric} 利用率达到 {usage}。',
        duration: '{seconds} 秒'
      }
    },
    reservations: {
      title: '预留',
      description: '查看高级预留、受影响节点以及账户或用户访问窗口。',
      metricLabel: '个预留',
      create: '创建预留',
      unableToRetrieve: '无法从集群 {cluster} 获取预留',
      noReservations: '集群 {cluster} 上没有定义预留',
      paginationLabel: '预留',
      nodeCount: '{count} 个节点',
      actions: {
        edit: '编辑',
        delete: '删除'
      },
      dialogs: {
        create: {
          title: '创建预留',
          description: '在此集群上创建新的预留。',
          submit: '创建预留'
        },
        edit: {
          title: '编辑预留',
          description: '更新预留 {name}。',
          submit: '保存更改'
        },
        delete: {
          title: '删除预留',
          description: '删除预留 {name}。此操作具有破坏性。',
          submit: '删除预留'
        },
        fields: {
          name: '预留名称',
          nodeList: '节点列表',
          partition: '分区',
          users: '用户（逗号分隔）',
          accounts: '账户（逗号分隔）'
        }
      },
      notifications: {
        createRequested: '已请求创建预留 {name}。',
        updateRequested: '已请求更新预留 {name}。',
        deleteRequested: '已请求删除预留 {name}。'
      }
    },
    qos: {
      title: 'QOS',
      description: '查看此集群上定义的服务质量策略、资源上限和调度约束。',
      metricLabel: '个 QOS 策略',
      create: '创建 QOS',
      unableToRetrieve: '无法从集群 {cluster} 获取 QOS',
      noQos: '集群 {cluster} 上没有定义 QOS',
      paginationLabel: 'QOS 策略',
      actions: {
        edit: '编辑',
        delete: '删除',
        viewJobs: '查看作业'
      },
      limits: {
        global: '全局',
        submitPerUser: '每用户提交',
        submitPerAccount: '每账户提交',
        maxPerUser: '每用户最大值',
        maxPerAccount: '每账户最大值',
        maxPerJob: '每作业最大值',
        maxPerNode: '每节点最大值'
      },
      dialogs: {
        create: {
          title: '创建 QOS',
          description: '为此集群新增服务质量策略。',
          submit: '创建 QOS'
        },
        edit: {
          title: '编辑 QOS',
          description: '更新 {name}。',
          submit: '保存更改'
        },
        delete: {
          title: '删除 QOS',
          description: '删除 QOS {name}。此操作具有破坏性。',
          submit: '删除 QOS'
        },
        fields: {
          name: '名称',
          description: '说明',
          priority: '优先级',
          maxSubmitJobsPerUser: 'MaxSubmitJobsPerUser',
          maxSubmitJobsPerUserHint: '每用户当前已提交作业数，包括运行中和排队中的作业。',
          maxJobsPerUser: 'MaxJobsPerUser',
          maxJobsPerUserHint: '每用户同时运行作业的最大数量。',
          maxWallDurationPerJob: 'MaxWallDurationPerJob',
          maxWallDurationPerJobHint: '单作业最大运行时间，格式为 days-hh:mm:ss。'
        },
        errors: {
          invalidPositiveInteger: 'QOS 作业限制必须为非负整数。',
          invalidWallDuration: 'MaxWallDurationPerJob 必须使用 days-hh:mm:ss 或 hh:mm:ss 格式。',
          invalidWallDurationRange: 'MaxWallDurationPerJob 必须使用有效的小时、分钟和秒。'
        }
      },
      notifications: {
        createRequested: '已请求创建 QOS {name}。',
        updateRequested: '已请求更新 QOS {name}。',
        deleteRequested: '已请求删除 QOS {name}。'
      }
    },
    user: {
      kicker: '用户工作区',
      selfDescription: '在一个工作区中查看个人身份、集群有效权限、账户关联和用户分析。',
      description: '查看所选用户的账户关联、历史快捷入口和分析信息。',
      metricLabel: '个关联账户',
      metricLabelPlural: '个关联账户',
      breadcrumb: {
        myWorkspace: '我的工作区',
        userPrefix: '用户 {user}'
      },
      backToDashboard: '返回概览',
      backToAccounts: '返回账户',
      actions: {
        viewJobs: '查看作业',
        viewHistoryJobs: '查看历史作业',
        accountPermissions: '账户权限',
        editUser: '编辑用户',
        deleteUser: '删除用户'
      },
      selfStats: {
        username: '用户名',
        noFullName: '未缓存姓名',
        cluster: '集群',
        currentWorkspaceContext: '当前工作区上下文',
        effectiveRoles: '有效角色',
        mergedPolicyAndCustomRoles: '合并后的策略与自定义角色',
        effectiveActions: '有效动作',
        permissionsExposed: '前端可见权限'
      },
      identity: {
        summaryKicker: '身份摘要',
        summaryTitle: '我的账户与权限',
        summaryDescription: '本地账户身份与合并后的集群级权限。',
        identity: '身份',
        mergedActions: '合并动作',
        mergedRules: '合并规则',
        username: '用户名：',
        fullName: '姓名：',
        groups: '组：',
        noActions: '未声明动作。',
        noRules: '未声明路由规则。'
      },
      profile: {
        kicker: '用户资料',
        title: '账户关联与限制',
        description: '查看此用户的 LDAP 关联账户、配额边界和历史作业快捷入口。',
        historyJobs: '历史作业',
        historyAccessGranted: '已授予历史访问',
        historyShortcut: '可直接跳转到按此用户过滤的持久化历史作业列表。',
        accounts: '账户',
        accountAssociationsFound: '为该用户找到 1 个账户关联。',
        accountAssociationsFoundPlural: '为该用户找到 {count} 个账户关联。',
        noAssociations: '用户 {user} 在此集群上没有任何关联。',
        accountAssociationsTitle: '账户关联',
        accountAssociationsDescription: '每一行代表一个账户绑定以及附带的限制。'
      },
      analytics: {
        kicker: '用户分析',
        title: '提交与工具分析',
        description: '查看该用户的提交趋势、双指标工具分析和执行摘要。',
        backToUser: '返回用户详情',
        userDetail: '用户详情'
      },
      analyticsPanels: {
        disabled: '此集群未启用用户分析。',
        unavailable: '该集群暂不提供用户工具分析。LDAP 与账户关联详情仍可查看。',
        profile: {
          ldapAvailable: 'LDAP 资料可用',
          ldapUnavailable: 'LDAP 资料不可用'
        },
        window: {
          title: '分析窗口',
          description: '活动、使用情况和已完成工具分析共用同一个时间窗口。',
          updated: '更新时间 {value}',
          ariaLabel: '选择用户分析时间范围'
        },
        cards: {
          submitted: {
            title: '范围内已提交',
            detail: '所选时间窗口内捕获到的提交事件'
          },
          completed: {
            title: '范围内已完成',
            detail: '所选时间窗口内捕获到的完成作业'
          },
          activeTools: {
            title: '活跃工具数',
            detail: '最繁忙工具：{tool}'
          },
          avgRuntime: {
            title: '平均运行时长',
            detail: '基于所选时间窗口内捕获的已完成作业'
          },
          running: {
            title: '运行中作业',
            detail: '所选时间窗口内观察到的运行中或收尾作业'
          },
          pending: {
            title: '排队中作业',
            detail: '所选时间窗口内观察到的待调度作业'
          },
          failed: {
            title: '失败作业',
            detail: '所选时间窗口内观察到的失败或超时作业'
          },
          cancelled: {
            title: '取消作业',
            detail: '所选时间窗口内观察到的取消或抢占作业'
          }
        },
        activity: {
          title: '提交活动',
          description: '查看所选时间范围内的提交与完成趋势。',
          unable: '无法获取该用户的提交或完成历史。',
          loading: '正在加载活动历史...',
          empty: '该时间范围内没有可用的提交或完成历史。'
        },
        usage: {
          title: '使用画像',
          description: '查看所选时间范围内已完成作业的聚合行为。',
          avgMemoryTitle: '平均内存',
          avgMemoryDetail: '所选窗口内记录工具的每个已完成作业平均内存',
          maxMemoryTitle: '最大内存',
          maxMemoryDetail: '所选窗口内记录到的已完成作业峰值内存',
          medianMemoryTitle: '中位内存',
          medianMemoryDetail: '所选窗口内记录工具的典型已完成作业内存',
          avgCpuTitle: '平均 CPU 核数',
          avgCpuDetail: '该用户工具运行在所选窗口内请求的核心分配情况'
        },
        table: {
          title: '已完成作业工具分析',
          description: '按工具维度分析所选时间范围内的已完成作业，结合内存、CPU 和运行时均值查看作业量。',
          empty: '该用户尚未记录到任何已完成作业的工具活动。',
          workload: '工作负载',
          avgMemory: '平均内存',
          maxMemory: '最大内存',
          medianMemory: '中位内存',
          avgRuntime: '平均运行时长',
          avgCpu: '平均 CPU',
          jobsCount: '{count} 个作业'
        },
        chart: {
          submissions: '提交数',
          completions: '完成数',
          running: '运行中',
          pending: '排队中',
          failed: '失败',
          cancelled: '取消',
          jobsUnit: '个作业'
        },
        units: {
          seconds: '{value} 秒',
          minutes: '{value} 分钟',
          hoursMinutes: '{hours} 小时 {minutes} 分钟',
          hoursOnly: '{hours} 小时',
          gb: '{value} GB',
          hours: '{value} 小时',
          cores: '{value} 核'
        }
      },
      emptyState: {
        title: '附加区域不可用',
        description:
          '此工作区可通过 `user/profile:view:*` 展示账户关联，并在集群启用用户指标时通过 `user/analysis:view:*` 展示分析。'
      },
      limits: {
        runningPerUser: '每用户运行中',
        submittedPerUser: '每用户已提交',
        total: '总量',
        perJob: '每作业',
        perNode: '每节点'
      },
      dialogs: {
        create: {
          title: '创建用户',
          description: '创建 SlurmDB 用户 {user}。',
          submit: '创建用户'
        },
        edit: {
          title: '编辑用户',
          description: '更新 SlurmDB 用户 {user}。',
          submit: '保存更改'
        },
        delete: {
          title: '删除用户',
          description: '删除 SlurmDB 用户 {user}。此操作具有破坏性。',
          submit: '删除用户'
        },
        fields: {
          description: '说明',
          defaultAccount: '默认账户',
          defaultQos: '默认 QOS',
          assignedQosCsv: '分配的 QOS（逗号分隔）',
          defaultWckey: '默认 WCKEY',
          adminLevel: '管理级别'
        }
      },
      notifications: {
        updateRequested: '已请求更新用户 {user}。',
        deleteRequested: '已请求删除用户 {user}。'
      }
    },
    assistant: {
      kicker: '集群副驾',
      title: 'AI',
      description: '使用集群助手进行多轮对话，并查看实时工具调用轨迹。',
      actions: {
        manageModels: '管理模型',
        newChat: '新建对话',
        reusePrompt: '复用问题'
      },
      alerts: {
        unavailable: '该集群未开放 AI 能力。',
        noPermission: '当前用户无权使用 AI 工作区。',
        noEnabledModel: '该集群当前没有已启用模型。请先在 管理 > AI 中创建模型。'
      },
      history: {
        kicker: '历史',
        title: '对话',
        loading: '正在加载对话...',
        empty: '发送一个问题即可创建第一条对话。',
        deleteTitle: '删除对话',
        updated: '更新时间 {time}'
      },
      workspace: {
        kicker: '工作区',
        newConversation: '新的集群对话',
        cluster: '集群 {cluster}',
        loading: '正在加载 AI 工作区...'
      },
      ready: {
        kicker: '就绪',
        title: '询问此集群中的作业、节点、分区或指标',
        description: '例如作业状态分析、空闲节点排序、集群资源摘要等主题。'
      },
      prompts: {
        summarizeCluster: '总结集群',
        bestNodeNow: '当前最佳节点',
        analyzeJob: '分析作业 12345',
        summarizeClusterPrompt: '总结当前集群负载和队列压力。',
        bestNodeNowPrompt: '现在剩余资源最多的是哪个节点？',
        analyzeJobPrompt: '解释作业 12345 当前状态及可能原因。'
      },
      messages: {
        copied: '已复制',
        copyMessage: '复制消息',
        generating: '正在生成回复...',
        user: '用户',
        assistant: '助手'
      },
      composer: {
        placeholder: '可以询问作业、节点资源、分区或其他只读型集群问题。',
        estimatedTokens: '预计 tokens {current} / {limit}',
        tokenExceededHint: '当前预计 token 数已超过限制。请缩短问题，或开启新对话。'
      },
      toolTrace: {
        kicker: '工具调用',
        title: '执行轨迹',
        empty: '当前运行的工具事件会显示在这里。',
        viewDetails: '查看详情',
        hideDetails: '隐藏详情',
        tool: '工具：{value}',
        interface: '接口：{value}',
        status: '状态：{value}',
        duration: '耗时：{value}',
        pending: '处理中',
        http: 'HTTP {code}',
        running: '运行中'
      },
      retry: {
        kicker: '重试',
        title: '上一次问题',
        empty: '尚未发送任何问题。'
      },
      time: {
        justNow: '刚刚'
      },
      errors: {
        tokenExceeded: '预计 token 用量已超过当前限制（{current}/{limit}）。请缩短问题或开始新对话。',
        noEnabledModel: '该集群当前没有可用的已启用模型。'
      }
    },
    jobHistoryDetail: {
      kicker: '作业历史',
      title: '作业 {jobId}',
      description: '查看该已完成作业记录的时间线、调度上下文和资源详情。',
      liveJob: '实时作业',
      recordedFieldsTitle: '已记录字段',
      recordedFieldsDescription: '该历史记录归档的调度元数据与计费字段。',
      executionTimelineTitle: '执行时间线',
      executionTimelineDescription: '查看提交、调度到完成各阶段的历史检查点。',
      detailedTitle: '详细资源与命令',
      detailedDescription: '较长字段保持展开，便于阅读和复制。',
      timeline: {
        submitted: '已提交',
        eligible: '可调度',
        scheduling: '调度中',
        running: '运行中',
        completed: '已完成',
        terminated: '已结束'
      },
      summary: {
        jobId: '作业 ID',
        user: '用户',
        account: '账户',
        partition: '分区',
        nodes: '节点',
        maxMemory: '最大内存',
        avgCpuCores: '平均 CPU 核数',
        avgCpuCoresSubtle: '平均并发使用核数',
        exitCode: '退出码'
      },
      fields: {
        jobId: '作业 ID',
        name: '名称',
        stateReason: '状态原因',
        user: '用户',
        group: '组',
        account: '账户',
        partition: '分区',
        qos: 'QOS',
        priority: '优先级',
        nodes: '节点',
        resources: '资源',
        requested: '请求资源',
        allocated: '已分配资源',
        tresPerJob: '每作业 TRES',
        tresPerNode: '每节点 TRES',
        gres: 'GRES',
        maxMemory: '最大内存',
        avgCpuCores: '平均 CPU 核使用数',
        timeLimit: '时间限制',
        exitCode: '退出码',
        workdir: '工作目录',
        command: '命令'
      },
      helps: {
        avgCpuCoresTitle: '平均 CPU 核使用数',
        avgCpuCoresBody:
          '估算作业运行期间平均并发使用的 CPU 核数。根据已包含步骤的 sum(step.time.total) / job_elapsed_seconds 计算。'
      },
      resourcesLabel: {
        nodes: '{count} 个节点',
        nodesPlural: '{count} 个节点',
        cpus: '{count} 个 CPU',
        cpusPlural: '{count} 个 CPU'
      },
      duration: {
        minutes: '{minutes} 分钟',
        hoursMinutes: '{hours} 小时 {minutes} 分钟'
      },
      errors: {
        unableToRetrieve: '无法获取历史作业记录 {id}：{error}'
      }
    }
  }
}

export default zhCN
