# PowerShell 部署脚本
# 用法: .\deploy-frontend.ps1 <服务器IP或主机名>
# 例如: .\deploy-frontend.ps1 192.168.1.100

param(
    [Parameter(Mandatory=$true)]
    [string]$Server
)

$LocalDistPath = "C:\Users\guojianpeng\Downloads\Slurm-web-main\Slurm-web-main\frontend\dist"
$RemoteTempPath = "/tmp/slurm-web-frontend-deploy"
$RemoteFinalPath = "/usr/share/slurm-web/frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Slurm-web 前端部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查本地构建文件是否存在
if (-not (Test-Path $LocalDistPath)) {
    Write-Host "错误: 构建文件不存在: $LocalDistPath" -ForegroundColor Red
    Write-Host "请先运行: cd frontend; npm run build" -ForegroundColor Yellow
    exit 1
}

Write-Host "1. 上传文件到服务器..." -ForegroundColor Green
Write-Host "   源: $LocalDistPath" -ForegroundColor Gray
Write-Host "   目标: ${Server}:${RemoteTempPath}" -ForegroundColor Gray

# 使用 SCP 上传文件
scp -r "$LocalDistPath\*" "root@${Server}:${RemoteTempPath}/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 文件上传失败" -ForegroundColor Red
    exit 1
}

Write-Host "   ✓ 文件上传成功" -ForegroundColor Green
Write-Host ""

Write-Host "2. 在服务器上部署文件..." -ForegroundColor Green

# 在服务器上执行部署命令
$DeployCommands = @"
echo '清理旧文件...'
rm -rf ${RemoteFinalPath}/*
echo '复制新文件...'
cp -r ${RemoteTempPath}/* ${RemoteFinalPath}/
echo '设置文件权限...'
chmod -R 644 ${RemoteFinalPath}/*
chmod 755 ${RemoteFinalPath}
find ${RemoteFinalPath} -type d -exec chmod 755 {} \;
echo '清理临时文件...'
rm -rf ${RemoteTempPath}
echo '重启 gateway 服务...'
systemctl restart slurm-web-gateway
echo '检查服务状态...'
systemctl is-active slurm-web-gateway
"@

ssh "root@${Server}" $DeployCommands

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 服务器部署失败" -ForegroundColor Red
    exit 1
}

Write-Host "   ✓ 部署完成" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "部署成功！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作：" -ForegroundColor Yellow
Write-Host "1. 清除浏览器缓存 (Ctrl+Shift+Delete)" -ForegroundColor White
Write-Host "2. 强制刷新页面 (Ctrl+F5)" -ForegroundColor White
Write-Host "3. 检查新功能是否显示" -ForegroundColor White
Write-Host ""
Write-Host "如果还有问题，在服务器上运行诊断脚本：" -ForegroundColor Yellow
Write-Host "   bash diagnose.sh" -ForegroundColor White
