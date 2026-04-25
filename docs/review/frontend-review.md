# 前端代码审查报告

## 1. 审查范围

本次前端审查覆盖：

- `frontend/src/**`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/README.md`

重点关注：

- 对外品牌名是否已切换到 `slurm-web-plus`
- 明显的 UI 文案、标题、资源命名不一致
- 发布前会影响构建或验收的低风险问题

## 2. 已直接修复的问题

### 2.1 前端入口标题仍显示旧产品名

- 文件：`frontend/index.html`
- 问题：浏览器标签页标题仍为 `Slurm-web`。
- 修复：统一改为 `Slurm Web Plus`。

### 2.2 登录页、匿名访问页和品牌组件仍混用旧名称

- 文件：
  - `frontend/src/views/LoginView.vue`
  - `frontend/src/views/AnonymousView.vue`
  - `frontend/src/components/BrandLogo.vue`
- 问题：用户在登录和匿名入口仍会看到旧品牌文案或旧 `alt` 文本。
- 修复：统一改为 `Slurm Web Plus`。

### 2.3 前端运行日志仍输出旧网关品牌名

- 文件：`frontend/src/composables/RESTAPI.ts`
- 问题：控制台日志继续打印 `Slurm-web gateway API ...`，不利于发布后排障一致性。
- 修复：改为 `Slurm Web Plus gateway API ...`。

### 2.4 前端锁文件根包名与 `package.json` 不一致

- 文件：`frontend/package-lock.json`
- 问题：锁文件根包仍是 `slurm-web-frontend`，与 `package.json` 的 `slurm-web-plus-frontend` 不一致。
- 修复：同步锁文件根包名，避免发布物元数据割裂。

### 2.5 前端开发说明仍使用旧 URL 前缀示例

- 文件：`frontend/README.md`
- 问题：`VITE_BASE_PATH` 示例仍为 `/slurm-web/`。
- 修复：示例更新为 `/slurm-web-plus/`。

## 3. 当前结论

- 本次快速审查未发现前端运行时阻塞级功能 bug。
- 已修复的问题主要集中在发布品牌一致性和构建元数据一致性。
- 现有前端设计 token 中的 `slurmweb` 类名和 CSS 变量当前更接近内部实现名，不属于必须立即替换的用户可见品牌问题。

## 4. 风险点

### 4.1 网关实际公开路径仍需和部署层一起确认

- 当前文档与前端示例已开始使用 `/slurm-web-plus/` 作为发布路径示例。
- 但运行时真正生效的公开路径仍取决于网关配置、反向代理和构建产物中的 base path 替换逻辑。
- 如果部署层仍保留旧前缀，前端不能单方面宣称“线上路径已切换完成”。

### 4.2 前端还有少量内部实现常量保留旧前缀

- 例如 `__SLURMWEB_BASE__`、样式 token `slurmweb` 等。
- 这些当前不直接暴露给终端用户，不建议为了表面统一在发布前做大范围替换。
- 若后续决定彻底改名，应先确认哪些是公共契约，哪些只是内部实现常量。

## 5. 待确认项

- 生产环境公开路径是否最终切换到 `/slurm-web-plus/`
- 文档站和仓库外链何时从旧 `/slurm-web/` slug 切换
- 是否需要把前端内部 token/占位符也一并改名，还是继续作为兼容实现细节保留

## 6. 验证记录

已执行：

- `npm --prefix frontend run type-check`
- `npx vitest run tests/components/BrandLogo.spec.ts`
- `npx vitest run tests/views/LoginView.spec.ts tests/components/BrandLogo.spec.ts`
- `npx vitest run tests/composables/GatewayAPI.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`

结果：

- 类型检查通过
- `BrandLogo` 相关测试通过
- `LoginView` 相关测试通过
- `GatewayAPI` 与 `UserToolAnalysisChart` 相关测试通过

## 7. 本次涉及文件

- `frontend/index.html`
- `frontend/README.md`
- `frontend/package-lock.json`
- `frontend/src/components/BrandLogo.vue`
- `frontend/src/composables/RESTAPI.ts`
- `frontend/src/views/LoginView.vue`
- `frontend/src/views/AnonymousView.vue`
- `docs/review/frontend-review.md`
