# 任务4 交付报告 —— 全量反跑 + 回归验证 + 导入路径检查（第 37 轮）

> 轮次：第 37 轮 ｜ 任务：4（P1）｜ 日期：2026-09-16
> 执行基线：任务1（代理循环统一·方案B 重命名）+ 任务2（agent-default-model 复刻）合并后的工作区
> 工具：`_antirun_r37_final.py`（新增，三节：snapshot/compare ＋ tests ＋ imports）
> 工作区 git 说明：执行时 `git rev-parse` 返回 not a git repository（用户手工管理 git，铁律 5），改动范围改用文件系统证据 + tokenize 确定性论证。

## 一、§A 全量反跑（tokenize，`_antirun_r37_final.py snapshot`）

| 指标 | 结果 |
|----|----|
| 语料文件数 | 870（lightharness + light-merge 全部 .light，R36 时 863） |
| 解析错误文件 | 2 —— 与 R30 起登记的既有红完全一致（`light-merge/bootstrap/release/stdlib/集合.light`、`light-merge/examples/_test_nested_closure.light`） |
| 新增解析错误 | **0** ✅ |
| 自愈 | 0 |
| 快照 | sha256 逐文件（deterministic=True，过滤 EOF/NEWLINE）已生成并留档 |

**零回归论证**：本轮代码改动 = 任务2 新增 `src/代理默认模型.light` + `examples/test_R37_代理默认模型.light`（2 个纯新增文件）；任务1 改动 = `stdlib/代理循环.light→代理运行时.light` 重命名 + 4 个 stdlib 文件纯注释路径更新（任务1 报告 §五 已用 `_r37_task5_perf.py` 证明逐文件 token 流与 HEAD 一致）。lexer 本轮零改动 → 既有文件 token 序列由确定性保证不变，快照实测无新增 ERR 与自愈。

## 二、§B 回归验证（`_antirun_r37_final.py tests`，345 文件全量）

**全量扫描：345 个 `examples/test_*.light`，rc=0 共 342，rc≠0 共 3 —— 逐一取证后有效回归为 0。**

| 红文件 | 红因取证 | 判定 |
|----|----|----|
| `test_L101.light` | 「回调」是保留关键字，解析期报错 | **EXPECT_RED 门禁内钉子**：`tests/test_回归.py` 登记「L-101 回调是保留关键字，误用作变量名应 rc!=0」——应红而红，非回归 |
| `test_L143.light` | 「作用域」是保留关键字，解析期报错 | **EXPECT_RED 门禁内钉子**（同上，L-143） |
| `test_会话存储.light` | 「初始会话列表为空 实际=4 期望=0」 | **运行残留状态污染**：测试自建根 `_e2_会话存储_tmp` 有上次中断残留（该测试清理段自述"尽力而为，失败不阻断验收"）。清除残留后复跑 **rc=0** ✅ |

重点用例（任务书 4.2）：`test_代理循环`、`test_R34_集成测试`、`test_R37_集成测试`、`test_代理`、`test_代理团队`、`test_R37_代理默认模型`（14 组全绿）——全部 rc=0。

 pytest 交叉证据（引用任务1 报告 §五）：`pytest tests/test_回归.py -q` → **382 passed / 0 failed**（R36 为 381，本轮 +1 为 R37 集成测试），与本扫描结论一致。

## 三、§C 导入路径检查（`_antirun_r37_final.py imports`，全语料 870 文件）

**1) `从 代理循环 导入` = 6 处，全部解析正确：**
- lightharness 侧 3 处（`test_代理循环.light:4`、`test_R34_集成测试.light:4`、`test_R37_集成测试.light:15`）→ 唯一解析到 `src/代理循环.light`（新版状态机；所引符号 `建循环/轮次待启` 等仅存在于 src 版），三测试 rc=0 实证。
- light-merge 侧 3 处（`examples/harness/{M2_流式对话,主程序,评测驱动}.light`）→ 解析到 **light-merge/stdlib/代理循环.light**（语言本体仓库自带同名文件 41643 字节，与原 lightharness stdlib 旧版同源）。light-merge 是上游语言仓库，不在本轮统一范围；**该同名文件是语言仓库现状，不是 lightharness 侧遗漏**。

**2) `从 代理运行时 导入` = 1 处**（`test_R37_集成测试.light:14`）→ 解析到 `stdlib/代理运行时.light`（重命名后），rc=0 实证。任务1 报告 §四 登记的 9 处 comment 路径引用已全部更新。

**3) `从 代理默认模型 导入` = 0 处实际导入**；`test_R37_集成测试.light:85` 为注释中的待补说明（任务3 交付时代理默认模型未就位，集成测试测试5 SKIP）。**移交**：该 SKIP 项的补做条件现已具备（任务2 已交付且 `test_R37_代理默认模型.light` 14 组全绿），归任务3/路M 收口补做，本任务不越权修改任务3 文件。

**4) 模块搜索路径（任务书风险 4 的实测核对）**：`lightharness/运行.py` 实际顺序为 **SRC > ROOT > STDLIB**（`for p in [STDLIB, ROOT, SRC, ...]: sys.path.insert(0, p)` 的反向叠加；`.light` 导入钩子 `install([SRC, STDLIB, ROOT])` 同序）。任务书背景「stdlib 优先于 src」与实测相反——与任务1 报告 §1.2 的独立证伪结论一致。任务1 重命名后 lightharness 内不再存在同名模块，该优先级问题已无实际影响面。

## 四、遗留登记（非本任务范围）

1. `light-merge/stdlib/代理循环.light`：语言仓库同名旧版，是否同步重命名属上游仓库决策，建议路M 在 docs（#158）中注明边界。
2. `test_R37_集成测试.light` 测试5 SKIP 待补做（条件已具备）。
3. `test_会话存储.light` 的"初始为空"假设依赖清理成功，残留即红——建议后续给测试改为随机子目录根（一次性的健壮性改进，本轮不改既有测试文件）。

## 五、交付物
- `lightharness/_antirun_r37_final.py`（反跑脚本：snapshot/compare/tests/imports 四模式）
- 本报告 `_task4_R37_全量反跑+回归验证+导入路径检查.md`
- 全量反跑证据：870 文件快照、无新增 ERR；回归证据：345 文件 342 绿 + 3 红逐一取证（2 钉子 + 1 污染已复跑转绿）；导入路径证据：§三 全表
