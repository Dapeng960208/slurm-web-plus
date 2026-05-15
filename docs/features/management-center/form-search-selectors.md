# 管理表单共享搜索选择器说明

## 1. 目标

统一收口前端管理与筛选表单中 `用户名`、`节点名`、`QOS`、`分区` 四类输入，避免继续混用文本输入框和各页面自定义选择器。

## 2. 当前实现范围

本轮仅覆盖以下字段：

- `用户名`
- `节点名`
- `QOS`
- `分区`

已接入位置包括：

- `JobsView` / `JobView` 的 `partition`、`qos`
- `AccountView` 的 `user`、`qos`、`default_qos`
- `AccountsView` 的 `qos`
- `UserView` 的 `default_qos`、`qos`
- `ReservationsView` 的 `node_list`、`allowed_partitions`、`qos`
- `JobsHistoryFiltersPanel` 的 `user`、`partition`、`qos`
- `UserFilterSelector`

## 3. 数据来源

### 3.1 用户名

- 走现有 `GET /agents/:cluster/access/users`
- 使用 `username` query 做分页和关键字过滤
- 前端当前固定取第一页，默认 `page_size=20`

### 3.2 QOS / 分区 / 节点

- `QOS`：`GET /agents/:cluster/qos`
- `分区`：`GET /agents/:cluster/partitions`
- `节点`：`GET /agents/:cluster/nodes`

说明：

- 这三类当前没有新增后端搜索接口
- “远程搜索”在本轮中的实际含义是“选项从远端加载，再在前端下拉中筛选”

## 4. 提交格式

- 单选字段继续提交单个字符串
- 多选字段在前端表单层序列化为 CSV string
- 业务页面继续复用现有 `parseCsvList` / `parseOptionalCsvList`
- `Reservations.node_list` 多选后提交为逗号分隔的节点名字符串

## 5. 边界与行为变化

- `Reservations.node_list` 已从自由文本输入收紧为“当前集群节点多选”
- 不再支持在该字段直接输入 nodeset 表达式
- 本轮不扩展到 `account / groups / accounts` 等其它未指定字段
- 本轮不新增后端 `qos / partition / node` 模糊搜索接口
