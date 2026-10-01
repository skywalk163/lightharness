# Day3 任务书（与 Day2 并行版）· LP-D-012 并发原语定靶与调度层迁移

> 起草：2026-10-02（Day2 由「小浣熊」在跑，本任务书为 Day3 并行开工而写）
> 隔离工位：**`G:/dswork/duan-light-merge/lightharness-day3`（分支 `day3-lp012`，基于 `1065a9b`）**
> 前置：Day2 正在 `light-merge-day2`（`day2-lp011`）改 `light-merge/antlrparser/**`

---

## 一、并行可行性结论：**可以并行，但有三条硬边界**

**文件占用对比（实测）**

| 路线 | 工位 | 占用文件 | 仓 |
|---|---|---|---|
| Day2（小浣熊，进行中） | `light-merge-day2` / `day2-lp011` | `antlrparser/LightLangParser.g4`、`indent_preprocessor.py`、`interpreter_core.py`、`light_ast.py`、`light_parser/*`（重新生成）、`light_visitor.py`、`visitor_stmt.py` | light-merge |
| **Day3（本任务书）** | `lightharness-day3` / `day3-lp012` | `src/任务拉取泵.light`、`src/代理循环.light`、`src/工具执行.light` | **lightharness** |

→ **文件级零重叠、且跨仓**，因此可以并行。

### 三条硬边界（违反即停）

1. **只能在 `lightharness-day3` worktree 里改，绝不碰 lightharness 主树。**
   原因：`同步0.82.py` 打的是**主树**（`lightharness` + `light-merge` 两个目录）。
   若 Day3 半成品落在 LH 主树，会被同步进 0.82，**污染 Day2 的门禁结果**（Day2 的红会是 Day3 造成的）。
2. **本轮不碰 `light-merge/src/` 与 `light-merge/antlrparser/`。**
   Day2 正在改 antlrparser；codegen 是全仓唯一瓶颈（一轮只让一条路动 `src/`）。
   探针若得出结论「需要新增并发语法」→ **按砍线条款冻结**，不自己动手改 codegen（见 §四）。
3. **0.82 权威门严格排队，绝不与 Day2 同时跑。**
   顺序：① Day2 合流到主树 → Day2 跑「Day2→Day3 快门」→ ② Day3 合流到主树 → Day3 跑门。
   **Day3 在拿到 team lead 的放行信号前不得调用 `082全量回归.py`。**

---

## 二、Day3 主线（按序）

### 第 0 步 · 探针定靶（首个 30 分钟，只跑不改）
已确证的事实（Day1 取证，不要重复求证）：
- `异步 段落` / `等待` / `异步睡眠` **已在 lightharness 生产代码中使用**
  （`src/中止.light:49`、`src/客户端.light:295`、`src/异步代理.light:42`、`src/mock大模型服务器.light:393`）
- codegen 已有 `AwaitExpr` / `RunAsyncStmt` / `ParallelBlockStmt` / `AsyncScope`
  与 `# ---- A2-3 异步并发原语 ----` 段（`light-merge/src/code_generator.py:354/362/364`，含 `并发等待` / `首个完成`）

**要回答的唯一问题**：缺的到底是哪一层？
- (a) 新语法不存在？→ 需要新增
- (b) 语法在、但**调度层没用**（仍是注入式推进器）？→ 只需迁移 ← **大概率是这个**
- (c) 原语名不对/不够？→ 补名

产物：写清「缺口层级 = (a)/(b)/(c)」及判据，写进报告。

### 第 1 步 · 三模块 A/B 迁移（`lightharness-day3`）
- `src/任务拉取泵.light`
- `src/代理循环.light`
- `src/工具执行.light`

A = 当前注入式推进器；B = 原生并发语义。**B 必须无回归**。

### 第 2 步 · lightharness 侧同步消化新并发语义，改调度层

---

## 三、验证（三元判据：failed 不增 / skipped 不增 / passed 不降）

本机（在 worktree 内跑，注意解释器）：
```bash
cd /g/dswork/duan-light-merge/lightharness-day3
PYTHONUTF8=1 LIGHT_MERGE=G:/dswork/duan-light-merge/light-merge \
PYTHONPATH=G:/dswork/duan-light-merge/light-merge/src \
CODEBUDDY_SAFE_DELETE_ENABLED=0 \
/c/Python314/python.exe -m pytest tests/test_回归.py tests/unit/ -q -o "addopts=" -n 4
```
基线：`1171 passed / 1 skipped`（Day1 实测，32:37）。

> ⚠️ **必须加 `CODEBUDDY_SAFE_DELETE_ENABLED=0`**：本环境每 turn 50 次删除护栏触发后，
> 每次 `os.remove()` 都抛 `SystemExit(1)`，会把会删临时文件的用例成片打成假红
> （Day1 实测 LH 20 条 + LM 20 条全假）。详见 `docs/国庆7天/README.md`。

0.82 权威门（**拿到放行信号后**）：
```bash
cd /g/dswork/duan-light-merge/lightharness
MSYS_NO_PATHCONV=1 python scripts/082全量回归.py sync --mode full
MSYS_NO_PATHCONV=1 python scripts/082全量回归.py test  --mode full --py /usr/local/bin/python3.12
MSYS_NO_PATHCONV=1 python scripts/082全量回归.py diff
```
拆三步跑（不要用 `all`，会在 sync 后被 safe-delete 护栏拦停 → 只同步不验收的假成功）。
稳定 full 基线：**8489 / passed 8352→8357 / failed 0 / skipped 126→121**（比对用稳定值，
不要把偶发 xpassed 的 8354 当基线）。

---

## 四、砍线（15:00 未达标即降级）

若三模块 B 方案仍不能无回归 → **冻结为「新原语可用、调度层不迁」**，
把迁移移出 7 天窗口，Day4 起按原计划推进，**不得让 Day3 吃掉 Day4**。

若探针结论是 (a)「需要新增语法」→ 同样冻结，**语法新增排到 Day2 收口之后**，
本轮只交「缺口层级 = (a)」的结论 + 最小复现，不自己改 `light-merge/src/`。

---

## 五、反跑判据

1. 破坏并发语句生成 → 三模块 A/B 测试立红
2. 破坏 `代理循环` 中排空 inbox 的逻辑 → `用例_inbox异步消费` 立红（沿用 R6 C 线既有判据）

---

## 六、交付与纪律

- 报告：`docs/国庆7天/Day3_并发原语.md`（三段式，含「探针结论：缺口层级」一段）
- **不要 commit / push / git add**，team lead 统一收口
- 不要 `git checkout --` 任何文件（要备份用 `cp`）
- 回报必须含：每条命令原文 + 退出码 + 三元数字；没跑就写「未跑」
- 临时文件用完自清；清理被 safe-delete 护栏拦下时，在回报里点名残留路径

---

## 七、给「小浣熊」（Day2）的约定 —— 需由用户转达

1. Day3 在 `lightharness-day3`，**不会碰 `light-merge/antlrparser/`**，也不会碰 LH 主树。
2. **你跑 0.82 门前，Day3 不会占用门**；Day3 等你跑完再排队。
3. ⚠️ **你自己的隐患**：`同步0.82.py` 打的是 **light-merge 主树**，而你的改动在
   `light-merge-day2` worktree → **不同步进去的话，你的门测不到你改的东西**（假绿）。
   跑门前必须先把 worktree 改动合到主树（或改用主树跑）。
4. Day2 收口若动了 `src/code_generator_unified.py`，请在回报里点名行号，Day3 需据此判断是否触及边界 2。
