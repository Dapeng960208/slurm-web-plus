# 前端控制台日志排查指南

## 问题：浏览器控制台没有任何打印信息

### 可能原因及解决方案

#### 1. 前端代码未重新构建和部署

**症状**：修改了源代码，但浏览器中运行的还是旧版本

**解决方案**：
```bash
# 进入前端目录
cd frontend

# 重新安装依赖（如果是首次构建）
npm install

# 构建生产版本
npm run build

# 查找前端部署路径（示例：从 gateway.ini 中定位 ui.path）
# 注意：实际配置路径以你的环境为准
# FRONTEND_PATH=$(grep -r "ui" /etc/slurm-web/gateway.ini | grep path | awk -F'=' '{print $2}' | tr -d ' ')
# echo "前端路径: $FRONTEND_PATH"

# 备份旧版本
cp -r $FRONTEND_PATH ${FRONTEND_PATH}.bak.$(date +%Y%m%d_%H%M%S)

# 部署新版本
cp -r dist/* $FRONTEND_PATH/

# 清除浏览器缓存
# 在浏览器中按 Ctrl+Shift+Delete，清除缓存
# 或者强制刷新：Ctrl+F5 (Windows) / Cmd+Shift+R (Mac)
```

#### 2. 浏览器控制台过滤设置问题

**症状**：日志被过滤器隐藏了

**解决方案**：
1. 打开浏览器开发者工具（F12）
2. 切换到 Console 标签
3. 检查过滤器设置：
   - 确保 "All levels" 或至少 "Info" 级别已启用
   - 清空搜索框中的过滤文本
   - 确保没有勾选 "Hide network messages"

#### 3. 生产环境 console.log 被移除

**症状**：构建工具在生产模式下移除了 console.log

**检查方法**：
```bash
# 检查 vite.config.ts 中是否配置了移除 console
cat frontend/vite.config.ts | grep -i "console"

# 检查构建后的文件中是否包含日志代码
grep -r "GatewayAPI.*集群列表" frontend/dist/assets/*.js
```

**临时解决方案**：使用开发模式运行
```bash
cd frontend
npm run dev
# 然后访问 http://localhost:5173
```

#### 4. 页面未正确加载 Vue 组件

**症状**：页面显示空白或组件未挂载

**检查方法**：
1. 打开浏览器控制台
2. 查看是否有 JavaScript 错误（红色错误信息）
3. 检查 Network 标签，确认所有资源都成功加载（状态码 200）

**解决方案**：
- 如果有 404 错误，检查前端文件是否完整部署
- 如果有 CORS 错误，检查 gateway 配置
- 如果有 JavaScript 语法错误，可能是构建不完整

#### 5. 路由未正确配置

**症状**：访问作业历史或节点详情页面时，组件未加载

**检查方法**：
```bash
# 确认路由配置中包含新页面
cat frontend/src/router/index.ts | grep -A 5 "jobs-history"
cat frontend/src/router/index.ts | grep -A 5 "node.*metrics"
```

**解决方案**：
- 确保 `frontend/src/router/index.ts` 中有 `jobs-history` 路由
- 确保 `frontend/src/components/MainMenu.vue` 中有菜单项

#### 6. 快速验证方法

在浏览器控制台直接输入以下代码测试：

```javascript
// 测试 1: 检查 Vue 是否正常运行
console.log('Test: Vue app loaded')

// 测试 2: 手动触发一个日志
console.log('[Manual Test] 手动测试日志')

// 测试 3: 检查是否能访问 window 对象
console.log('Window location:', window.location.href)
```

如果上述测试都能正常显示，说明控制台本身没问题，问题在于：
- 前端代码未更新
- 组件未被加载/挂载

---

## 调试步骤（按顺序执行）

### 步骤 1：确认前端已重新构建
```bash
cd frontend
npm run build
ls -lh dist/  # 检查构建时间
```

### 步骤 2：确认前端已部署
```bash
# 查找部署路径
FRONTEND_PATH=/usr/share/slurm-web/html  # 根据实际情况修改

# 检查文件时间戳
ls -lh $FRONTEND_PATH/index.html
ls -lh $FRONTEND_PATH/assets/*.js | head -5

# 部署新版本
cp -r frontend/dist/* $FRONTEND_PATH/
```

### 步骤 3：清除浏览器缓存
- Chrome/Edge: Ctrl+Shift+Delete → 清除缓存
- 或者使用隐私/无痕模式访问

### 步骤 4：强制刷新页面
- Windows: Ctrl+F5
- Mac: Cmd+Shift+R
- 或者：右键点击刷新按钮 → "清空缓存并硬性重新加载"

### 步骤 5：检查控制台
1. 打开 F12 开发者工具
2. 切换到 Console 标签
3. 刷新页面
4. 查找 `[GatewayAPI]` 开头的日志

### 步骤 6：如果还是没有日志

**使用开发模式直接测试**：
```bash
cd frontend
npm run dev
```
然后访问 `http://localhost:5173`，这样可以直接看到源代码的日志输出。

---

## 验证日志是否存在于源代码中

```bash
# 检查源代码中是否包含日志
grep -n "GatewayAPI.*集群列表" frontend/src/composables/GatewayAPI.ts
grep -n "JobsHistory.*作业历史页面" frontend/src/views/JobsHistoryView.vue
grep -n "NodeView.*节点详情页面" frontend/src/views/NodeView.vue

# 如果上述命令有输出，说明源代码中有日志
# 如果没有输出，说明文件未正确修改
```

---

## 最终确认清单

- [ ] 源代码文件已修改（通过 grep 验证）
- [ ] 前端已重新构建（`npm run build`）
- [ ] 构建产物已部署到服务器
- [ ] 浏览器缓存已清除
- [ ] 页面已强制刷新
- [ ] 控制台过滤器设置正确
- [ ] 没有 JavaScript 错误

如果以上都确认无误，但仍然没有日志，请提供：
1. 浏览器控制台的截图（包括 Console 和 Network 标签）
2. `frontend/dist/` 目录的文件列表和时间戳
3. 部署路径下的文件列表和时间戳
