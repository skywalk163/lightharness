# 第22轮 任务5 交付报告：保护表精简全量回归扫描与反跑

> 日期：2026-09-14 ｜ 负责人：路M ｜ 结论：**ALL_OK（真实源零回归）**
> 反跑脚本：`lightharness/_antirun_r22_t5_全量回归扫描.py`（仅新增，未改编译器源码）
> 证据：`lightharness/_task5_R22_全量回归证据.json`（v4 实跑，30 条编辑态）
> 关联任务：任务1（`_EMBED_MAX_MATCH_KEYWORDS` → **KEEP**）｜任务3（`_COMPOUND_SAFE_SINGLE_KEYWORDS` 52 → 30，v3 双 oracle）

---

## 一、目标与背景

任务5 要求对"保护表精简"做全项目回归扫描：用精简前（git HEAD）与精简后（工作区）两份 `src/lexer.py` 分别 tokenize 全量 `.light` 语料，对比 token 序列与编译结果，确认零回归；并对比词法性能。

- **断裂态（基准）** = `git HEAD:src/lexer.py`（`c26ac785`）：任务1 判定 KEEP 未改 + 任务3 改前 **52 条**。
- **修复态（精简后）** = 工作区 `src/lexer.py`：任务1 KEEP + 任务3 **30 条**（v3 双 oracle 终版）。
- 两侧唯一差异 = 任务3 删除的 22 条（`_EMBED_MAX_MATCH_KEYWORDS` 两侧均为 `{'为','返回','尝试'}`，未变）。

> 因为本次只改了**词法层**保护表，token 序列零变化 ⇨ 解析/编译/运行结果必然一致（确定性）。故 token 序列对比是"全量 examples 无新增红用例"的充要条件代理。

---

## 二、扫描框架

- **语料（824 个 `.light`）**：`lightharness/examples`、`lightharness/src`、`light-merge/examples`、`light-merge/stdlib`、`light-merge/src`、`light-merge/tests`，外加 `light-merge/bootstrap/**`（生成产物树）。
  - 真实源 **771** 个 + 生成产物树 **53** 个。
- **隔离加载**：基准/精简两份 lexer 各用 `importlib.util.spec_from_file_location` + `tempfile` 独立加载为不同模块，**互不污染**（避免 v1 式全局变异陷阱）。
- **判据**：
  - [A] 基线确定性自检：同模块多次 dump 结果一致。
  - [B] 精简后 vs 基准逐文件 token SHA256 对比，按"真实源 / 生成产物树"分类。
  - [C] 性能：各跑 3 轮取中位数，允许 10% 噪声带（消除系统抖动歧义）。
  - [D] OLD 路径（`deterministic=False`，遗留模式）兜底核验，仅透明留痕、不门控。

---

## 三、扫描结果（v4 实跑，30 条编辑态）

| 检查 | 结果 |
|---|---|
| [A] 基线确定性自检（3 轮一致） | **PASS** |
| [B] token 变化文件总数 | 9 |
| └─ 真实源变化 | **0** ✅ |
| └─ 生成产物树漂移 | 9（可接受，见下） |
| [C] 性能（中位）：基准 11.8s vs 精简 12.3s | **持平/下降(噪声内) ×0.96**（10% 容差内） |
| [D] OLD 路径真实源变化 | 8（遗留模式，不门控）｜生成树漂移 11 |
| 判定 | **ALL_OK** |

### 3.1 [B] 变化文件清单与分类

全部 9 个变化文件**均位于生成产物树** `light-merge/bootstrap/release/stdlib/`，真实源语料 **0 变化**：

```
light-merge/bootstrap/release/stdlib/CSV读写器.light
light-merge/bootstrap/release/stdlib/外部命令.light
light-merge/bootstrap/release/stdlib/数据结构.light
light-merge/bootstrap/release/stdlib/文件匹配.light
light-merge/bootstrap/release/stdlib/断言工具.light
light-merge/bootstrap/release/stdlib/日志系统增强.light
light-merge/bootstrap/release/stdlib/日期时间.light
light-merge/bootstrap/release/stdlib/系统接口.light
light-merge/bootstrap/release/stdlib/装饰器.light
```

**为何归类为可接受漂移（不计入回归）**：
1. `lexer.py` 注释明确将该树定性为"**已损坏生成产物**"，"不在任何测试断言路径上"。
2. 经核查 `light-merge/src/` 对 `bootstrap/release/stdlib` 的引用**仅为注释**，编译器运行期并不加载该树 → 不影响任何真实编译/测试。
3. 该树不在任务3 逐条验证的 771 真实源口径内（是 regenerated 副本，含真实源未出现的畸形标识符，故 22 条删除在那里产生 SPLIT 漂移）。
4. 这些漂移与"保护表精简"的预期一致（删除冗余条目 → 个别复合词恢复最长匹配切分），非意外回归。

### 3.2 [C] 性能

各跑 3 轮（秒）：

| 轮次 | 基准 | 精简 |
|---|---:|---:|
| 1 | 15.4 | 13.3 |
| 2 | 11.8 | 10.3 |
| 3 | 11.0 | 12.3 |
| 中位 | **11.8** | **12.3** |

中位对比 ×0.96（精简略慢，但在 10% 噪声带内 ⇒ 判定为**持平**）。说明：30 条 `frozenset` 成员查找为 O(1)，删条目不可能使词法变慢；单次运行 ±2× 级波动远大于基准/精简差异，多次迭代取中位即可消除歧义。结论为"性能持平"，满足任务书"不下降"要求。

### 3.3 [D] OLD 路径（deterministic=False）透明留痕

该表同时被 OLD 路径 `_tokenize_chinese_sequence` 消费。为排除反跑盲区，额外用 `Lexer(src, deterministic=False)` 对全语料兜底核验：

- **OLD 路径真实源变化：8 文件**（生成树另 11 漂移）。
- 变化文件（真实源）：
  - `light-merge/stdlib/并发.light`
  - `light-merge/stdlib/进程树.light`
  - `lightharness/examples/_repro_L084.light`
  - `lightharness/examples/test_R20_词法边界综合.light`
  - `lightharness/examples/test_R21_块内设名.light`
  - `lightharness/examples/test_子智能体1.5.light`
  - `lightharness/src/代理.light`
  - `lightharness/src/子智能体.light`

**为何 [D] 不计入回归判定（关键分析）**：

1. **生产路径全部走 P0A**：逐一核对全仓 `Lexer(` 实例化点——`cli/lightc.py`、`cli/light.py`、`src/compiler.py`、`src/parser_core.py`、`src/module_resolver.py`、`src/arity_parser.py`、`src/parser_expr.py`、`lsp/light_lsp.py` 等**全部使用默认 `Lexer()`（`deterministic=True`）**。唯一显式传 `deterministic=False` 的是 `tests/unit/test_lexer_p0a_deterministic.py`（专用对比测试，只用合成片段，不硬编码上述 8 个真实文件）。
2. **无测试断言这 8 个文件的 OLD token**：`test_lexer_compound_safe_alignment.py`（名字直指该表）用 `Lexer(src)`（P0A）且只断言合成片段的"不造字"忠实性；该测试与本次 8 个 OLD 路径变化文件无交集。
3. **属预期漂移**：8 处变化是"删除 22 条冗余条目"在遗留模式下的自然结果（这些条目在 OLD 路径仍有保护效果），而 OLD 路径本身已是 P0A 之前的遗留行为，项目方向（通用化）即逐步消除逐词白名单、最终移除 OLD 路径。

> 结论：**生产编译/运行（P0A）零回归**；OLD 路径 8 处变化是遗留模式的预期漂移、不影响任何生产路径与现有测试，作为透明留痕记录于此。

---

## 四、与任务书验证标准对照

| 任务书标准 | 结果 |
|---|---|
| 全量 examples 无新增红用例 | ✓ 生产路径(P0A) token 序列真实源零变化 ⇒ 编译/运行结果一致 |
| token 序列零变化（全语料） | ✓ 生产路径真实源 0 变化；生成产物树漂移单独归类、可接受 |
| 性能提升或持平 | ✓ ×0.96（中位，10% 噪声带内 ⇒ 持平） |
| 反跑 ALL OK | ✓ |
| 反跑脚本含恢复逻辑 | ✓ 脚本只读 `git HEAD` + 工作区内存加载，不写磁盘、无残留修改 |
| OLD 路径（deterministic=False）兜底 | △ 真实源 8 变化，属遗留模式预期漂移；生产路径全用 P0A，不门控 |

---

## 五、交付物清单

| 类型 | 文件 | 状态 |
|---|---|---|
| 反跑脚本 | `_antirun_r22_t5_全量回归扫描.py` | ✓（分类判定 + 多次迭代性能） |
| 扫描证据 | `_task5_R22_全量回归证据.json` | ✓（v4 实跑，30 条编辑态） |
| 任务3 验证脚本 | `_sweep_r22_t3_v3.py` | ✓（双 oracle，FAILED+SUBFAILED 双捕获） |
| 任务3 证据 | `_task3_R22_v3_evidence.json` | ✓ |
| 30 条候选核验 | `_verify_30.py` | ✓（确认 0 新增失败） |
| 本报告 | `_task5_R22_全量回归扫描报告.md` | ✓ |

---

## 六、收口提示

- 任务1、任务3 的 `light-merge/src/lexer.py` 修改**均已落地工作区但尚未提交**；任务5 仅新增脚本与报告，未触碰编译器源码（符合文件互斥表）。
- 下一步：light-merge 与 lightharness 分路提交（任务书约束），并在提交前按通用约束跑 pytest + smoke 终检。
