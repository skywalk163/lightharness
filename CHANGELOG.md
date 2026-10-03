# 更新日志

本项目的所有值得记录的变更都写在这里。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号以轮次发布 tag 为准（如 `r95-dev`）。

## [未发布]

> **R110 收口（2026-10-03，维持 `v0.4.0-rc2`）**：A/C/D 文档交付、B 核实 0 移植、E Windows 本机双全量 0 新增红。零可执行代码改动 → 不 bump 版本号、不新建 tag。lightharness 三远端已推；light-merge 无 R110 改动未推。

### 新增

- 对齐 deepseek-harness 上游 `dsh-v0.2.0-rc.2`（`639ed01539`）相对 rc.1 的增量（**187 commits / 1022 真增量文件 / +33253 / -6141**，三点基准 `rc.1...rc.2`，merge-base `4878cdabd8`）。
- B 路经核实为 **0 移植**（lightharness 无对应纯逻辑层承载 A 清单 §4 的 4 组候选：schedule framing / user-questions 状态机 / tool-ask-user timed / shell 提示词文案）；`对标清单.json` 末位仍 #313，无 R110 新增。

### 修复

- 宿主面增量 15 条 append 进 `docs/宿主面登记清单.md` §7（44→59）：Windows ACL 修复链 / web-desktop UI / whale perf / Cordis inspect / desktop installer / llm pi-ai 升级 / CI 等。
- fork FreeBSD 脚本对账：上游 rc.2 无 freebsd/ 目录，fork 侧 `e5b5ccbfcb..8bf6c9250f` 零改动 → 零同步（`R110_D路_FreeBSD脚本对账.md`）。

### 验证

- LH 本机 Windows 全量 **2074 用例 / 0 failed / 0 new_red**（`reports/R110_lh_windows_latest.json`）。
- LM 本机 Windows 全量 **8489 用例 / 0 new_red**（1 为已知 flaky `test_进程类` 单跑复绿；R55 时代 5 红全清）。
- 锚点修正：分发书 `e5b5ccbfcb..rc.2` 两点口径有误（`e5b5ccbfcb` 是 fork 合流提交，会冒 freebsd 假删除）；真基准三点 `rc.1...rc.2`（merge-base `4878cdabd8`）。
- 遗留：0.86 Linux / 0.82 FreeBSD 基线 JSON 未生成（B=0 代码改动 ⇒ 逻辑上无 R110 新红风险，待补）。

---

## [r95-dev] — 2026-09-25

R95 收口：**根因战场闭环**（LH `61e004a`，分支 `release/r95`，tag `r95-dev`）。

### 新增

- 发布分支 `release/r95` 与 tag `r95-dev`。
- Job Object 与创建时间闸门：为进程树治理提供可复用的根治判据。

### 修复

- 进程树根因类问题闭环：从"现象修补"推进到"根因可验证"，同类问题不再反复复发。

### 验证

- Job Object 闸门 + 创建时间闸门双证据链，为进程树的根治结论提供端到端验证。
- 远端 FreeBSD 门禁机三平台回归通过。

---

## [r94-dev] — 2026-09-25

R94 收口：**开发冻结收口**（LH `eae81f1`，分支 `release/r94`，tag `r94-dev`）。

### 新增

- 发布分支 `release/r94` 与 tag `r94-dev`，把本轮开发面冻结在一个可回溯的提交上。

### 修复

- 本轮开发面冻结，此后不再接受散乱改动，变更一律走新的发布分支。

### 验证

- 冻结面对应的回归门禁通过，作为 R95 根因战场的基线。

---

## [r87] — 2026-09-23

R87 收口：**上游 0.1.7 纯逻辑面移植**（HEAD `7cc0fa8`）。

### 新增

- 对齐 deepseek-harness 上游 0.1.7 的纯逻辑增量，完成对应区域的移植与落位。
- 移植过程产生的语言侧需求登记进 `docs/功能对标/语言缺陷账.md`。

### 修复

- 移植暴露的 flaky 用例完成根治处置（见 `_taskE_R87_flaky根治报告.md`）。
- 门禁补位：修正 light-merge 侧与本仓之间的回归门缺口（见 `_taskD_R87_LM门禁补位报告.md`）。

### 验证

- 三平台 LH 全量回归：**1400 用例 0 失败**。
- 环境固化项入档（见 `_taskF_R87_环境固化报告.md`），确保不同机器跑出同一结果。
