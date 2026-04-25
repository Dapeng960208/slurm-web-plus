# Cache 测试计划（Settings > Cache）

## 1. 测试范围

本次测试覆盖 `Cache` 页面前端渲染与 cache 相关后端接口回归，目标是验证：

- 页面不再出现右侧空白块
- 无数据场景有明确空态
- metrics 关闭场景有明确说明
- 现有 cache 后端能力未回归

## 2. 前置条件

- 前端依赖已安装
- Python 虚拟环境已可用
- 后端测试必须使用 `.venv\Scripts\python.exe`

## 3. 测试点

### 3.1 前端页面级

- `cache=true` 且 `metrics=true` 时：
  - 显示 cache statistics
  - 显示 cache metrics
  - 不显示 `Live cache metrics are unavailable`
- `cache=true` 且 `metrics=false` 时：
  - 显示 cache statistics
  - 不显示 cache metrics 组件
  - 显示 metrics disabled 提示
- 无 `cache-view` 权限时：
  - 显示无权限提示
  - 不显示 cache statistics
  - 不显示 cache metrics
- `cache=false` 时：
  - 显示 cache disabled 提示
  - 不显示 cache statistics
  - 不显示 cache metrics

### 3.2 前端组件级

- 统计表能够展示 hit/miss key 并集
- 总计行计算正确
- 加载态显示 `Loading statistics...`
- 错误态显示错误提示
- hit/miss 总量为 0 时显示“等待缓存活动”空态
- 有 `cache-reset` 权限时显示 reset 按钮
- 点击 reset 后调用 `cache_reset` 并刷新数据
- metrics 图表在无样本时显示空态说明，而不是空白图表区域

### 3.3 后端回归

- `GET /cache/stats` 正常返回 hit/miss 统计
- `POST /cache/reset` 正常执行 reset 并返回重置后的统计
- cache 服务关闭时，接口返回 501
- cache 核心服务单元测试保持通过

## 4. 回归点

- `SettingsCache` 视图渲染分支
- `SettingsCacheStatistics` 表格与 reset 行为
- `SettingsCacheMetrics` 图表空态
- `slurmweb.cache` 核心逻辑
- agent cache 相关视图接口

## 5. 执行命令

前端：

```powershell
cd frontend
npm.cmd run test:unit -- --run tests/views/settings/SettingsCache.spec.ts tests/components/settings/SettingsCacheStatistics.spec.ts tests/components/settings/SettingsCacheMetrics.spec.ts
```

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest slurmweb/tests/test_cache.py slurmweb/tests/views/test_agent.py -k cache
```

## 6. 风险

- Chart.js 在测试环境依赖 canvas mock，若测试环境依赖异常，可能影响图表相关断言
- 前端组件文案调整后，页面级测试需要同步维护
- 当前后端未新增字段，若未来扩展 cache 统计结构，需要同步补充前后端契约测试
