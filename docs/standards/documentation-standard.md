# 内部文档编写规范（必须遵守）

本规范用于约束后续开发者和 AI 在仓库中如何新增、更新和追踪**内部维护型**文档。

本规范不重构也不替代 Antora/手册体系（`docs/modules/`、`docs/man/`、`docs/antora.yml`、`docs/update-materials`）。

## 1. 基本原则

### 1.1 代码事实优先

- 文档必须基于当前仓库代码、配置、接口和页面行为。
- 不允许把“计划中的设计”写成“已实现功能”。
- 对于未完成内容，必须显式标记为“待实现”“待验证”或“仅设计”。

### 1.2 变更必须同步文档

以下改动必须同步更新 `docs/`：

- 功能行为变化
- 路由变化
- API 变化
- 配置项变化
- 权限模型变化
- 数据库结构变化（包含 Alembic revision）
- 部署步骤变化
- 测试/验证入口变化

### 1.3 统一中文（内容）+ 统一英文（文件名）

- 内部维护型 Markdown 文档内容统一使用简体中文。
- 文件名与目录名统一使用英文 `kebab-case`，禁止中文文件名。
- 配置名、接口名、权限名、表名、字段名使用原始英文并加反引号。

命名与目录规则见：[`docs/standards/document-naming-convention.md`](./document-naming-convention.md)。

## 2. 稳定文档入口与目录职责

内部维护型文档目录结构固定为：

```text
docs/
  README.md
  overview/
  guides/
  features/
  standards/
  tracking/
```

约束：

- `docs/README.md` 是唯一索引入口；后续不要在 `docs/` 根目录散写新专题文件。
- `docs/overview/` 只放项目级稳定说明（项目概览、架构、最新增强等）。
- `docs/guides/` 只放交付/运维/迁移/排障/验收类指南。
- `docs/features/<feature>/` 放单功能专题文档（需求、测试计划、验证、后端说明等）。
- `docs/standards/` 放规范（文档规范、命名规范等）。
- `docs/tracking/` 只承接开发过程对接、同步状态、遗留项；不能把过程只留在聊天或提交信息里。

## 2.4 开发错误复盘（强制）

开发过程中遇到可复现错误时，必须做复盘并写入错误库，避免同一个错误被反复踩到：

- 错误库入口：`docs/tracking/error-log.md`
- 标准：`docs/standards/development-error-summary.md`

## 2.5 AI Git 工作流（强制）

AI 在开发与提交时必须遵循 Git 工作流约束，尤其是：

- 所有提交信息必须符合 `type(scope): subject`
- 每次提交前必须先检查工作区 `git status --porcelain`
- 对工作区未提交改动，必须先与开发者确认是否提交
- 网络不可用导致无法 push 时，也必须完成本地 commit，并在 `docs/tracking/` 留下可追溯记录

标准见：`docs/standards/ai-development-standard.md`。

## 3. 每类文档应包含的最小结构

### 3.1 功能专题文档

至少包含：

1. 背景/目标
2. 功能范围
3. 启用条件
4. 配置项
5. 页面或接口
6. 权限要求
7. 数据模型或依赖
8. 降级行为/边界
9. 相关测试或验证入口

### 3.2 运维/交付指南

至少包含：

1. 适用范围
2. 前置条件
3. 执行顺序
4. 命令示例
5. 验证步骤
6. 回滚方案与边界

### 3.3 跟踪文档

至少包含：

1. 当前主题/目标
2. 已完成项
3. 进行中项
4. 风险与阻塞
5. 需要同步的正式文档
6. 验证状态

## 4. 编写风格规则（必须写清的边界）

- 标题直接说明内容，不写空泛标题。
- 有能力门控（capability/feature gate）的功能，必须写清楚开启条件与降级行为。
- 有权限限制的页面与接口，必须写清楚所需 action（例如 `view-ai`、`view-history-jobs`）。
- 有多数据源时，必须明确“实时数据”和“历史数据”分别来自哪里，链路是否不同。

## 5. 更新顺序建议

每次功能改动至少检查一次文档更新需求，不能默认跳过。建议顺序：

1. `docs/tracking/current-release.md`（或新建专题跟踪）
2. 对应 `docs/features/<feature>/` 文档
3. `docs/overview/architecture-overview.md` / `docs/overview/project-overview.md`
4. `docs/README.md`

## 6. 完成前检查

提交前至少自查：

- 文档中的路由、接口、权限名是否与代码一致
- 配置项是否真实存在
- 功能是否真的已经落地（不要把未实现写成已完成）
- 是否写清了启用条件与不可用时的行为
- 是否更新了 `docs/tracking/`

配套清单见：[`docs/tracking/templates/doc-update-checklist.md`](../tracking/templates/doc-update-checklist.md)。
