#!/bin/bash
# 验证前端控制台日志是否正确添加

echo "=========================================="
echo "前端控制台日志验证脚本"
echo "=========================================="
echo ""

# 1. 检查源代码中是否包含日志
echo "1. 检查源代码中的日志..."
echo ""

echo "检查 GatewayAPI.ts:"
if grep -q "集群列表已加载" frontend/src/composables/GatewayAPI.ts; then
    echo "  ✅ 找到集群列表日志"
else
    echo "  ❌ 未找到集群列表日志"
fi

if grep -q "jobs_history 请求 URL" frontend/src/composables/GatewayAPI.ts; then
    echo "  ✅ 找到作业历史请求日志"
else
    echo "  ❌ 未找到作业历史请求日志"
fi

if grep -q "node_metrics 请求 URL" frontend/src/composables/GatewayAPI.ts; then
    echo "  ✅ 找到节点指标请求日志"
else
    echo "  ❌ 未找到节点指标请求日志"
fi

echo ""
echo "检查 JobsHistoryView.vue:"
if grep -q "作业历史页面已挂载" frontend/src/views/JobsHistoryView.vue; then
    echo "  ✅ 找到作业历史页面挂载日志"
else
    echo "  ❌ 未找到作业历史页面挂载日志"
fi

echo ""
echo "检查 NodeView.vue:"
if grep -q "节点详情页面已挂载" frontend/src/views/NodeView.vue; then
    echo "  ✅ 找到节点详情页面挂载日志"
else
    echo "  ❌ 未找到节点详情页面挂载日志"
fi

echo ""
echo "=========================================="
echo "2. 检查构建配置..."
echo ""

if grep -qi "drop.*console\|console.*drop" frontend/vite.config.ts; then
    echo "  ⚠️  警告: vite.config.ts 中可能配置了移除 console"
else
    echo "  ✅ vite.config.ts 未配置移除 console"
fi

echo ""
echo "=========================================="
echo "3. 构建状态检查..."
echo ""

if [ -d "frontend/dist" ]; then
    echo "  ✅ dist 目录存在"
    echo "  最后构建时间: $(stat -c %y frontend/dist 2>/dev/null || stat -f %Sm frontend/dist 2>/dev/null || echo '无法获取')"
    
    # 检查构建产物中是否包含日志（中文可能被编码）
    if ls frontend/dist/assets/*.js >/dev/null 2>&1; then
        echo ""
        echo "  检查构建产物中的日志代码..."
        if grep -r "GatewayAPI" frontend/dist/assets/*.js >/dev/null 2>&1; then
            echo "    ✅ 构建产物中包含 GatewayAPI 相关代码"
        else
            echo "    ⚠️  构建产物中未找到 GatewayAPI 字符串"
        fi
        
        if grep -r "JobsHistory" frontend/dist/assets/*.js >/dev/null 2>&1; then
            echo "    ✅ 构建产物中包含 JobsHistory 相关代码"
        else
            echo "    ⚠️  构建产物中未找到 JobsHistory 字符串"
        fi
    else
        echo "    ⚠️  未找到构建的 JS 文件"
    fi
else
    echo "  ❌ dist 目录不存在，需要运行 npm run build"
fi

echo ""
echo "=========================================="
echo "4. 部署建议"
echo "=========================================="
echo ""
echo "如果源代码检查通过但浏览器中没有日志，请执行："
echo ""
echo "  cd frontend"
echo "  npm run build"
echo "  cp -r dist/* /usr/share/slurm-web/html/  # 替换为实际路径"
echo ""
echo "然后在浏览器中："
echo "  1. 按 Ctrl+Shift+Delete 清除缓存"
echo "  2. 按 Ctrl+F5 强制刷新"
echo "  3. 打开 F12 开发者工具查看 Console"
echo ""
echo "或者使用开发模式直接测试："
echo "  cd frontend"
echo "  npm run dev"
echo "  访问 http://localhost:5173"
echo ""
