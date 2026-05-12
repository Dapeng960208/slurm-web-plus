# 前端国际化需求说明

## 1. 背景与目标

为 Slurm Web Plus 前端增加中英文切换能力，覆盖全站前端静态文案与前端自身生成的展示文案，降低中英文用户混用时的理解成本。

本轮目标是：

- 在前端统一接入国际化框架
- 首次进入按浏览器语言自动选择中文或英文
- 用户切换后持久化语言偏好
- 登录前和登录后都提供语言切换入口
- 覆盖业务页面标题、按钮、筛选、表格头、图表标签、空态、弹窗、通知和前端状态提示

## 2. 功能范围

本轮覆盖：

- 登录页
- 集群入口等公共未登录页面
- 主导航、用户菜单、Settings 导航
- Settings General / Errors
- 公共弹窗、分页、通知、错误提示
- 前端生成的认证错误、权限错误、服务端错误和普通提示
- Dashboard、Cluster Analysis、Jobs、Jobs History、Job
- Resources、Node、Accounts、Account、User、User Analysis
- QOS、Reservations、相关公共筛选器、时间范围控件和业务分析面板

本轮不覆盖：

- 后端直接返回的错误消息内容翻译
- 集群名、用户名、QOS、分区名等业务实体值翻译
- 后端接口协议、路由参数和运行时配置字段调整

## 3. 启用条件

- 前端默认启用国际化，不需要额外 feature gate。
- 支持的语言固定为：
  - `zh-CN`
  - `en`

## 4. 默认策略与持久化

- 首次进入时：
  - 若 `localStorage['locale']` 已存在且合法，则优先使用该值
  - 否则当 `navigator.language` 以 `zh` 开头时使用 `zh-CN`
  - 其他情况使用 `en`
- 用户主动切换后：
  - 立即更新当前页面语言
  - 写入 `localStorage['locale']`
  - 同步更新 `document.documentElement.lang`

## 5. 页面与入口

- 登录页右上区域提供语言切换控件
- 登录后通过右上 `UserMenu` 提供语言切换控件
- `Settings > General` 提供语言偏好入口，作为第二落点

## 6. 依赖与实现约束

- 前端使用 `vue-i18n`，不使用自建字符串映射器
- 翻译资源集中维护在 `frontend/src/locales/`
- 新增前端可见文案时，必须通过翻译 key 引用，不再新增英文硬编码
- 公共组件优先接收翻译 key，以减少业务页重复包裹 `t()`

## 7. 降级行为与边界

- 缺失翻译 key 时回退到英文
- 不因语言切换刷新页面、不重置路由、不清空当前前端状态
- 后端直接返回的原始错误消息保持原样显示
- 集群名、用户名、QOS 名、分区名、节点名等实体值保持原样显示
- 后端原始业务字段值不做翻译；只有前端主动构造的映射 label 才进入 i18n

## 8. 相关验证入口

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run`
- `npm --prefix frontend run build`
