# 前端部署步骤

## 前端已在 Windows 本地构建完成

构建输出位置：`C:\Users\guojianpeng\Downloads\Slurm-web-main\Slurm-web-main\frontend\dist`

## 部署到 Linux 服务器

**重要：** 前端文件应部署到 `/usr/share/slurm-web/frontend/`（不是 html 目录）

### 方法 1：使用 SCP（推荐）

```bash
# 在 Windows PowerShell 中执行
scp -r C:\Users\guojianpeng\Downloads\Slurm-web-main\Slurm-web-main\frontend\dist\* root@your-server:/tmp/slurm-web-frontend/

# 然后在 Linux 服务器上执行
ssh root@your-server
cd /tmp/slurm-web-frontend
rm -rf /usr/share/slurm-web/frontend/*
cp -r * /usr/share/slurm-web/frontend/
systemctl restart slurm-web-gateway
```

### 方法 2：使用 WinSCP 或 FileZilla

1. 打开 WinSCP 或 FileZilla
2. 连接到你的 Linux 服务器
3. 删除服务器上 `/usr/share/slurm-web/frontend/` 目录下的旧文件
4. 将 `C:\Users\guojianpeng\Downloads\Slurm-web-main\Slurm-web-main\frontend\dist` 目录下的所有文件上传到服务器的 `/usr/share/slurm-web/frontend/`
5. 在服务器上执行：
   ```bash
   systemctl restart slurm-web-gateway
   ```

### 方法 3：在服务器上直接构建（推荐，如果服务器有 Node.js）

```bash
# 在服务器上执行
cd /path/to/Slurm-web-main
cd frontend
npm install
npm run build

# 部署
rm -rf /usr/share/slurm-web/frontend/*
cp -r dist/* /usr/share/slurm-web/frontend/
systemctl restart slurm-web-gateway
```

## 验证部署

1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 访问 `http://your-server:5012`
3. 检查以下内容：

### 如果配置了 persistence.enabled = true
- 左侧菜单应显示 "Jobs History" 项（时钟图标）
- 点击进入作业历史页面
- 可以筛选和查询历史作业

### 如果配置了 node_metrics.enabled = true
- 进入任意节点详情页
- 底部应显示 "Real-time Metrics" 面板
- 显示 CPU、内存、磁盘使用率

### 如果功能未启用
- 对应的菜单项不显示
- 直接访问 URL 会被重定向

## 故障排查

### 菜单没有更新
```bash
# 1. 确认文件已更新
ls -lh /usr/share/slurm-web/html/assets/index-*.js

# 2. 清除浏览器缓存
# Chrome: Ctrl+Shift+Delete → 选择"缓存的图片和文件"

# 3. 强制刷新页面
# Chrome: Ctrl+F5 或 Ctrl+Shift+R

# 4. 检查浏览器控制台是否有错误
# F12 → Console 标签
```

### 页面显示空白或报错
```bash
# 检查 gateway 日志
journalctl -u slurm-web-gateway -n 100

# 检查文件权限
ls -la /usr/share/slurm-web/html/

# 确保文件可读
chmod -R 644 /usr/share/slurm-web/html/*
chmod 755 /usr/share/slurm-web/html
```

## 构建文件清单

部署后 `/usr/share/slurm-web/frontend/` 应包含：

```
/usr/share/slurm-web/frontend/
├── index.html
├── assets/
│   ├── index-1kC13rNr.css
│   ├── index-D1_rxi9c.js
│   └── vendor-CiGd9Lby.js
├── logo/
│   ├── slurm-web_horizontal.png
│   ├── slurm-web_horizontal_dark.png
│   ├── slurm-web_logo.png
│   └── slurm-web_logo_dark.png
├── chart_placeholder.svg
├── config.json
└── favicon.ico
```

**注意：** Gateway 启动时会自动从 `/usr/share/slurm-web/frontend/` 复制文件到运行时目录（通常是 `/run/slurm-web-gateway/ui/`）

## 后续开发流程

每次修改前端代码后：

1. **在 Windows 本地构建：**
   ```powershell
   cd C:\Users\guojianpeng\Downloads\Slurm-web-main\Slurm-web-main\frontend
   npm run build
   ```

2. **上传到服务器：**
   ```powershell
   scp -r dist\* root@your-server:/usr/share/slurm-web/frontend/
   ```

3. **重启服务：**
   ```bash
   ssh root@your-server "systemctl restart slurm-web-gateway"
   ```

4. **清除浏览器缓存并刷新页面**
