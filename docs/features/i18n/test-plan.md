# 前端国际化测试计划

## 1. 测试目标

验证前端中英文切换在共享入口、核心业务页面、持久化、通知和常用设置路径中能够稳定工作，不影响既有路由和主要交互。

## 2. 核心场景

- locale store
  - 切换到 `zh-CN` 后写入 `localStorage['locale']`
  - 切换到 `en` 后写入 `localStorage['locale']`
  - 切换时同步更新 `document.documentElement.lang`

- 登录页
  - 默认英文下显示英文登录文案
  - 切换到中文后，标题、字段标签和按钮同步切换
  - 登录失败时前端生成的认证错误仍可显示

- 主导航与用户菜单
  - 主导航默认英文可见
  - 切换到中文后，导航标签同步变更
  - 用户菜单中可切换语言

- 核心业务页面
  - `Dashboard`、`Cluster Analysis`、`Jobs`、`Jobs History`、`Job`
  - `Resources`、`Node`、`Accounts`、`Account`、`User`、`User Analysis`
- `QOS`、`Reservations`
  - 每页至少验证页头标题/说明、1 组工具栏或筛选文案、1 组内容区文案或空态可随语言切换
- `AI`、`Admin > AI`、`Admin > AI Conversation Detail`
- `Admin > Cache`
- `Admin > Users`
- `Admin > Access Control`
  - 至少验证页头、主要按钮/筛选、表头或空态、前端生成提示在两种语言下同步变化

- Settings
  - `SettingsTabs` 在中英文下显示正确标签
  - `Settings > General` 显示语言偏好项
  - `Settings > General` 中节点名称开关文案可随语言切换
  - `Settings > Errors` 的标题和表头走翻译资源

- 公共组件
  - 通知面板中的 `INFO` / `ERROR` 类型标签可切换
  - 分页组件中的汇总文案、每页标签和按钮辅助文案可切换
  - 公共对话框、字段标签和前端错误消息走翻译资源
  - 时间范围选择器、图表图例、摘要卡、副标题和空态在两种语言下同步变化

## 3. 执行命令

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run`
- `npm --prefix frontend run build`

本轮补齐 AI/Admin 页面主体后，已额外执行：

- `cd frontend && npx vitest run tests/views/AssistantView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAIConversationDetail.spec.ts tests/views/settings/SettingsCache.spec.ts tests/views/settings/SettingsLdapCache.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/components/settings/SettingsCacheStatistics.spec.ts tests/components/settings/SettingsCacheMetrics.spec.ts`

## 4. 当前边界

- 本轮“全站”范围限定为所有前端静态文案和前端自行生成的展示文案。
- 后端直接返回的消息不纳入本轮双语验证范围。
