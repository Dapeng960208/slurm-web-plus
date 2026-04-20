#!/bin/bash
# 诊断脚本 - 检查 Slurm-web 新功能状态

echo "=========================================="
echo "Slurm-web 功能诊断"
echo "=========================================="
echo ""

# 1. 检查配置文件
echo "1. 检查配置文件"
echo "----------------------------------------"
if [ -f /etc/slurm-web/agent.ini ]; then
    echo "✓ agent.ini 存在"
    
    if grep -q "\[persistence\]" /etc/slurm-web/agent.ini; then
        echo "✓ 找到 [persistence] 配置段"
        grep -A 5 "\[persistence\]" /etc/slurm-web/agent.ini | grep "enabled"
    else
        echo "✗ 未找到 [persistence] 配置段"
    fi
    
    if grep -q "\[node_metrics\]" /etc/slurm-web/agent.ini; then
        echo "✓ 找到 [node_metrics] 配置段"
        grep -A 5 "\[node_metrics\]" /etc/slurm-web/agent.ini | grep "enabled"
    else
        echo "✗ 未找到 [node_metrics] 配置段"
    fi
else
    echo "✗ agent.ini 不存在"
fi
echo ""

# 2. 检查服务状态
echo "2. 检查服务状态"
echo "----------------------------------------"
systemctl is-active slurm-web-agent >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ slurm-web-agent 正在运行"
else
    echo "✗ slurm-web-agent 未运行"
fi

systemctl is-active slurm-web-gateway >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ slurm-web-gateway 正在运行"
else
    echo "✗ slurm-web-gateway 未运行"
fi
echo ""

# 3. 测试 API
echo "3. 测试 API 端点"
echo "----------------------------------------"

# 获取 token（匿名模式）
echo "尝试获取 token..."
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:5012/anonymous 2>/dev/null)
if [ $? -eq 0 ]; then
    TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
    if [ -n "$TOKEN" ]; then
        echo "✓ 成功获取 token"
        
        # 测试 /clusters API
        echo ""
        echo "测试 /clusters API..."
        CLUSTERS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5012/clusters 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "✓ /clusters API 响应成功"
            echo ""
            echo "集群信息："
            echo "$CLUSTERS_RESPONSE" | python3 -m json.tool 2>/dev/null | grep -E "(name|persistence|node_metrics)" | head -10
        else
            echo "✗ /clusters API 请求失败"
        fi
    else
        echo "✗ 无法从响应中提取 token"
    fi
else
    echo "✗ 无法获取 token（可能启用了 LDAP 认证）"
    echo "   如果启用了认证，请手动测试："
    echo "   TOKEN=\$(curl -s -X POST http://localhost:5012/login -H 'Content-Type: application/json' -d '{\"user\":\"your_user\",\"password\":\"your_password\"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"token\"])')"
    echo "   curl -H \"Authorization: Bearer \$TOKEN\" http://localhost:5012/clusters | python3 -m json.tool"
fi
echo ""

# 4. 检查前端文件
echo "4. 检查前端文件"
echo "----------------------------------------"
if [ -d /usr/share/slurm-web/frontend ]; then
    echo "✓ 前端源目录存在 (/usr/share/slurm-web/frontend)"
    
    # 检查关键文件
    if [ -f /usr/share/slurm-web/frontend/index.html ]; then
        echo "✓ index.html 存在"
    else
        echo "✗ index.html 不存在"
    fi
    
    # 检查 assets 目录
    if [ -d /usr/share/slurm-web/frontend/assets ]; then
        echo "✓ assets 目录存在"
        JS_FILES=$(ls /usr/share/slurm-web/frontend/assets/*.js 2>/dev/null | wc -l)
        echo "  - 找到 $JS_FILES 个 JS 文件"
        
        # 检查最新的 JS 文件修改时间
        LATEST_JS=$(ls -lt /usr/share/slurm-web/frontend/assets/*.js 2>/dev/null | head -1)
        if [ -n "$LATEST_JS" ]; then
            echo "  - 最新 JS 文件："
            echo "    $LATEST_JS"
        fi
    else
        echo "✗ assets 目录不存在"
    fi
else
    echo "✗ 前端源目录不存在 (/usr/share/slurm-web/frontend)"
fi

echo ""
echo "检查运行时目录："
if [ -d /run/slurm-web-gateway/ui ]; then
    echo "✓ 运行时 UI 目录存在 (/run/slurm-web-gateway/ui)"
    ls -lh /run/slurm-web-gateway/ui/ | head -10
else
    echo "✗ 运行时 UI 目录不存在（gateway 可能未运行）"
fi
echo ""

# 5. 检查数据库（如果 persistence 启用）
echo "5. 检查数据库"
echo "----------------------------------------"
sudo -u postgres psql -d slurmweb -c "SELECT COUNT(*) as total_snapshots FROM job_snapshots;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ 数据库连接成功"
else
    echo "✗ 数据库连接失败或表不存在"
    echo "  如果启用了 persistence，请运行："
    echo "  alembic upgrade head"
fi
echo ""

# 6. 检查日志中的错误
echo "6. 检查最近的错误日志"
echo "----------------------------------------"
echo "Agent 错误："
journalctl -u slurm-web-agent --since "5 minutes ago" | grep -i error | tail -5
echo ""
echo "Gateway 错误："
journalctl -u slurm-web-gateway --since "5 minutes ago" | grep -i error | tail -5
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="
echo ""
echo "下一步操作建议："
echo "1. 如果前端文件不是最新的，请部署新构建的文件"
echo "2. 如果配置未启用，请编辑 /etc/slurm-web/agent.ini"
echo "3. 修改配置后重启服务：systemctl restart slurm-web-agent slurm-web-gateway"
echo "4. 清除浏览器缓存并刷新页面"
