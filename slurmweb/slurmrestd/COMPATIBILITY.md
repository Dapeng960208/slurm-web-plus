# Slurm REST API Compatibility / Slurm REST API 兼容性

## Overview / 概览

This directory contains the runtime compatibility layer that lets the current
Slurm-web 6.x branch work with older `slurmrestd` API versions while keeping the
same external agent, gateway, and frontend contract.

本目录包含运行时兼容层，用于让当前 Slurm-web 6.x 分支在更老版本的
`slurmrestd` API 上继续工作，同时保持 agent、gateway 和 frontend 的对外契约不变。

The original 6.x implementation was designed around Slurm REST API `0.0.41+`.
The current compatibility chain extends support to `0.0.40` and `0.0.39`.

6.x 原始实现以 Slurm REST API `0.0.41+` 为基线。当前兼容链向前扩展到了
`0.0.40` 和 `0.0.39`。

`slurmweb4.2/` is used only as a local behavior reference for `0.0.40`. Schema
evolution and compatibility rules are derived from the official Slurm OpenAPI
release notes and REST API documentation.

`slurmweb4.2/` 仅作为 `0.0.40` 的本地行为参考。schema 演进和兼容规则以官方
Slurm OpenAPI release notes 与 REST API 文档为准。

References / 参考资料:

- `https://slurm.schedmd.com/openapi_release_notes.html`
- `https://slurm.schedmd.com/rest_clients.html`

## Supported Matrix / 支持矩阵

By default, version discovery tries the following API versions in descending
order:

默认情况下，版本发现按以下顺序从高到低尝试 API 版本：

- `0.0.44`
- `0.0.43`
- `0.0.42`
- `0.0.41`
- `0.0.40`
- `0.0.39`

Responses from older versions are normalized through this forward adaptation
chain:

老版本响应通过以下前向适配链归一化：

- `0.39 -> 0.40 -> 0.41 -> 0.42 -> 0.43 -> 0.44`

The compatibility goal is narrow and explicit: all currently used agent-side
data interfaces must keep returning the shape expected by the current 6.x code.

兼容目标是明确且收敛的：当前 agent 侧实际使用的数据接口，都必须继续返回
当前 6.x 代码所期望的结构。

## Version Discovery / 版本发现

`Slurmrestd.discover()` now supports both old and new ping metadata layouts.

`Slurmrestd.discover()` 现在同时兼容旧版和新版 ping 元数据结构。

For `0.40+`, discovery reads version information from `result["meta"]["slurm"]`.

对于 `0.40+`，发现逻辑从 `result["meta"]["slurm"]` 读取版本信息。

For `0.39`, discovery also accepts `result["meta"]["Slurm"]`.

对于 `0.39`，发现逻辑也接受 `result["meta"]["Slurm"]`。

Some `0.39` ping responses do not expose a cluster name. In that case, the
runtime uses `cluster_name_hint`, which is passed from `settings.service.cluster`
by the agent and `connect-check`. If no hint is available, discovery falls back
to `"unknown"` and still succeeds.

部分 `0.39` 的 ping 响应不包含 cluster 名称。此时运行时会使用
`cluster_name_hint`，该参数由 agent 和 `connect-check` 从
`settings.service.cluster` 传入。如果没有提供 hint，则回退为 `"unknown"`，
但不会阻止版本发现成功。

## Adapter Responsibilities / 适配器职责

`AdapterV0_0_39` is responsible for converting `0.0.39` payloads into the
`0.0.40` shape.

`AdapterV0_0_39` 负责把 `0.0.39` 响应转换为 `0.0.40` 形状。

`AdapterV0_0_40` is responsible for converting `0.0.40` payloads into the
`0.0.41` shape.

`AdapterV0_0_40` 负责把 `0.0.40` 响应转换为 `0.0.41` 形状。

Existing adapters continue to bridge later versions:

现有适配器继续负责后续版本桥接：

- `AdapterV0_0_41`: `0.0.41 -> 0.0.42`
- `AdapterV0_0_42`: `0.0.42 -> 0.0.43`
- `AdapterV0_0_43`: `0.0.43 -> 0.0.44`

The adaptation chain is built dynamically from the discovered source version to
the highest configured target version.

适配链会根据实际发现到的源版本，动态构建到当前最高目标版本的完整链路。

## Field Normalization / 字段归一化

Only fields that are consumed by the current repository are normalized here.
Schema differences that are not used by the agent, persistence layer, or
frontend are intentionally ignored.

这里只归一化当前仓库实际消费的字段。对于 agent、持久化层或 frontend
没有使用到的 schema 差异，当前实现会有意忽略。

### `0.39 -> 0.40` for `slurm jobs/job` / `0.39 -> 0.40` 的 `slurm jobs/job`

- `job_state: string -> string[]`
- Legacy integer timestamps are wrapped into optional-number objects for:
  `submit_time`, `start_time`, `end_time`, `accrue_time`, `eligible_time`,
  `last_sched_evaluation`, `preempt_time`, `preemptable_time`, `pre_sus_time`,
  `resize_time`, `suspend_time`, and `deadline`
- `exit_code` and `derived_exit_code` are normalized to the verbose structure:
  `status: string[]`, `return_code: {set, infinite, number}`,
  `signal.id: {set, infinite, number}`

- `job_state: string -> string[]`
- 旧版整型时间字段会包装为 optional-number 对象，覆盖：
  `submit_time`、`start_time`、`end_time`、`accrue_time`、`eligible_time`、
  `last_sched_evaluation`、`preempt_time`、`preemptable_time`、`pre_sus_time`、
  `resize_time`、`suspend_time` 和 `deadline`
- `exit_code` 与 `derived_exit_code` 会归一化为 verbose 结构：
  `status: string[]`、`return_code: {set, infinite, number}`、
  `signal.id: {set, infinite, number}`

### `0.39 -> 0.40` for `slurm nodes/node` / `0.39 -> 0.40` 的 `slurm nodes/node`

- `boot_time`, `last_busy`, `slurmd_start_time`, and `reason_changed_at` are
  wrapped from legacy integers into optional-number objects
- `cpu_load` intentionally remains unchanged because the current code does not
  consume it

- `boot_time`、`last_busy`、`slurmd_start_time` 和 `reason_changed_at`
  从旧整型包装为 optional-number 对象
- `cpu_load` 刻意保持原状，因为当前代码不消费该字段

### `0.39 -> 0.40` for `slurm reservations` / `0.39 -> 0.40` 的 `slurm reservations`

- `start_time` and `end_time` are wrapped into optional-number objects

- `start_time` 与 `end_time` 会包装为 optional-number 对象

### `0.39 -> 0.40` for `slurmdb jobs/job` / `0.39 -> 0.40` 的 `slurmdb jobs/job`

- Top-level `exit_code` and `derived_exit_code` use the same verbose
  normalization as `slurm jobs`
- `steps[].state: string -> string[]`
- `steps[].exit_code` is normalized to the same verbose structure
- `steps[].step.id` is normalized from
  `{job_id, step_id, step_het_component}` to the string form `"{job_id}.{step_id}"`
- Top-level `stdin`, `stdout`, `stderr`, and expanded fields are not added here;
  they are added by the next adapter step

- 顶层 `exit_code` 与 `derived_exit_code` 使用与 `slurm jobs` 相同的 verbose
  归一化规则
- `steps[].state: string -> string[]`
- `steps[].exit_code` 会归一化为相同的 verbose 结构
- `steps[].step.id` 会从
  `{job_id, step_id, step_het_component}` 归一化为字符串 `"{job_id}.{step_id}"`
- 顶层 `stdin`、`stdout`、`stderr` 及 expanded 字段不会在这一跳补齐，而是留给下一跳处理

### `0.39 -> 0.40` for `slurmdb associations` / `0.39 -> 0.40` 的 `slurmdb associations`

- `id` is synthesized as an object:
  `{"account", "cluster", "partition", "user", "id"}`
- `cluster` uses `cluster_name_hint` when available, otherwise `"unknown"`

- `id` 会补为对象结构：
  `{"account", "cluster", "partition", "user", "id"}`
- 其中 `cluster` 优先使用 `cluster_name_hint`，否则回退为 `"unknown"`

### `0.40 -> 0.41` for `slurmdb jobs/job` / `0.40 -> 0.41` 的 `slurmdb jobs/job`

- Backfill top-level `stdin`, `stdout`, `stderr`,
  `stdin_expanded`, `stdout_expanded`, and `stderr_expanded` with empty strings
- Backfill `time.planned` with an unset optional-number object

- 回填顶层 `stdin`、`stdout`、`stderr`、
  `stdin_expanded`、`stdout_expanded` 和 `stderr_expanded` 为空字符串
- 回填 `time.planned` 为 unset optional-number 对象

### `0.40 -> 0.41` for `slurmdb associations` / `0.40 -> 0.41` 的 `slurmdb associations`

- Flatten `id` from the object form to the integer value `id.id`
- Missing `id` falls back to `0`

- 将 `id` 从对象结构压平成整数 `id.id`
- 若 `id` 缺失，则回填 `0`

## Internal Interface Changes / 内部接口变化

The following runtime constructors now accept an optional
`cluster_name_hint: str | None = None` parameter:

以下运行时构造器现在支持可选参数
`cluster_name_hint: str | None = None`：

- `Slurmrestd`
- `SlurmrestdAdapter`
- `SlurmrestdFiltered`
- `SlurmrestdFilteredCached`

This is an internal compatibility parameter. It is not exposed through the
public HTTP API.

这是内部兼容参数，不会通过对外 HTTP API 暴露。

The agent and `slurm-web-connect-check` pass `settings.service.cluster` into
this parameter so old `0.39` ping responses can still be mapped to a meaningful
cluster name.

agent 与 `slurm-web-connect-check` 会把 `settings.service.cluster` 传入该参数，
从而让旧版 `0.39` ping 响应在缺失 cluster 时仍能映射到有意义的集群名称。

## Test Coverage / 测试覆盖

Compatibility is verified by focused unit tests instead of large per-version
asset snapshots.

兼容性通过聚焦的单元测试验证，而不是维护大体量的按版本静态资产快照。

Covered areas include:

当前覆盖范围包括：

- `discover()` behavior for `0.40` and `0.39`
- `meta.slurm` and `meta.Slurm` handling
- cluster fallback through `cluster_name_hint`
- adapter normalization for `jobs`, `nodes`, `reservations`, `slurmdb jobs`,
  and `associations`
- end-to-end shape checks after the full adapter chain
- `jobs_store` extraction against adapted `0.39` and `0.40` inputs
- app and configuration tests for agent and connect-check integration

- `discover()` 对 `0.40` 和 `0.39` 的行为
- `meta.slurm` 与 `meta.Slurm` 的兼容处理
- 通过 `cluster_name_hint` 的 cluster 回退
- `jobs`、`nodes`、`reservations`、`slurmdb jobs` 与 `associations`
  的适配归一化
- 完整适配链后的端到端结构校验
- `jobs_store` 对适配后 `0.39` 与 `0.40` 输入的提取验证
- agent 与 connect-check 集成的应用和配置测试

The main targeted test commands are:

主要目标测试命令如下：

- `pytest slurmweb/tests/slurmrestd/test_slurmrestd_discover.py`
- `pytest slurmweb/tests/slurmrestd/test_slurmrestd_adapter.py`
- `pytest slurmweb/tests/apps/test_jobs_store.py`
- `pytest slurmweb/tests/apps/test_connect.py slurmweb/tests/apps/test_agent.py`

## Constraints and Non-goals / 约束与非目标

This compatibility layer does not change the public API exposed by the current
agent.

这套兼容层不会改变当前 agent 暴露的公共 API。

The gateway, frontend, cache behavior, persistence contracts, and metrics code
continue to consume the normalized latest-version shape.

gateway、frontend、缓存行为、持久化契约以及 metrics 代码，仍然统一消费归一化后的最新版本结构。

`slurmweb4.2/` remains a local reference tree only and must not be committed to
the repository.

`slurmweb4.2/` 继续仅作为本地参考目录，不能提交到仓库中。

This implementation intentionally does not attempt to reproduce every OpenAPI
schema difference between Slurm releases. It only adapts fields that are
required by the current Slurm-web codebase.

当前实现不会试图覆盖 Slurm 各版本 OpenAPI 的全部 schema 差异，只适配当前
Slurm-web 代码库所必需的字段。
