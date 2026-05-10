# 待确认问题

本文件只记录当前仓库无法仅靠静态代码审查确认、且不适合猜测的事项。

## 1. 部署层命名兼容范围

- 当前代码已经把对外发布名切到 `slurm-web-plus`，但 systemd unit、默认目录路径和部分兼容脚本仍保留旧 `slurm-web` 前缀。
- 仅从仓库代码无法确认正式发布是否要求同时迁移：
  - service 名
  - `/etc` 配置目录
  - `/var/lib` 数据目录
  - 旧 CLI / 旧路径兼容策略

## 2. Linux 发布环境的完整回归基线

- 当前本地定向测试已覆盖本轮修复点。
- 但仓库无法单靠静态审查确认最终发布环境是否仍包含：
  - `python-ldap`
  - `racksdb`
  - 真实 SlurmDB 写权限
  - 与生产一致的 system package 路径

## 3. `admin/ldap-cache:edit:*` 的真实业务语义

- 权限目录和前端页面中已经为 `admin/ldap-cache:edit:*` 预留能力。
- 仅从当前实现无法确认后续是否会补真实写接口，还是继续只保留只读/刷新类操作。

## 4. 旧 `actions[]` 的最终退场计划

- 当前前后端都还保留兼容层，用于旧角色数据、旧测试夹具和少量 fallback。
- 仅从本轮代码无法确认项目是否准备在后续某个版本彻底移除：
  - `permissions.actions`
  - `roles.actions`
  - 前端 `hasPermission()` / `hasClusterPermission()` fallback
