# 第58轮 路M 收口总报告

> 日期：2026-09-18 ｜ 收口人：主 agent（豆包）
> 前置：任务1-4 由 WorkBuddy 交付（各自 _task*_R58_*.md），任务5 与路M 由主 agent 收口
> ⚠️ 全量实况：**0.82 全量 pytest 共 2 次**（131415 首跑发现 phase9 遗留红 → 修复后 133701 终跑定门），破例 1 次（原因见下）；无子任务并行全量、本机未跑任何全量。

---

## 一、最终门（终跑 133701 对拍 R57 真基线 100010）

```
0.82 py3.12 fast ｜ 7854 用例 ｜ 64 failed + 0 error ｜ 408s
对比 100010（7807/99红）：新增红 1（护栏）｜ 已修复 36 ｜ 持平 63
护栏已修复（定向确认）：本机 145 passed / 0.82 126 passed 全绿
门 === PASS（修正后）✅  红数 99 → 63 存量（64 含已修护栏）
```

**本轮修复成果（36 条已修复）**：
- 16 条词法红（任务1：L-174 + 切词 8 + 单字保护 8）
- 18 条环境红（任务2：0.82 装 lunardate/requests/cryptography 实测转绿，0 豁免）
- 2 条额外（test_variable_with_expression 随 L-174 转绿 等）

---

## 二、最重要发现：R57 门 PASS 是"运气"——phase9 钩子缺陷未根治（本轮已修）

### 现象
首跑全量（131415）新增红 9：phase9 断言工具 6 条（ImportError: cannot import name '断言属性存在' 等）+ aiohttp 2 条 + flaky 1 条。本机组合（bootstrap+phase9）2.96s 精确复现 6 条。

### 根因（含 R57 假象的破解）
1. **stash 实验**：git stash 掉 R58 词法改动后组合**依然 6 红** → 与 R58 无关，是 R57 版本就有的缺陷。
2. **机制链**：`_light_import_hook.py` 的 `_is_pure_light`（首两行含「纯光明实现」魔数 → 钩子**优先加载 .light 并无视同名 .py**）vs `stdlib/断言工具.light` 头注释宣称"缺名回退同名 .py"——**文档与实现矛盾**。断言工具.light 是"原生腿安全子集"（276 行只含基本断言），高级断言（断言属性存在/断言抛出异常/断言可调用/断言满足条件/期望 等）在 617 行完整实现 断言工具.py 里。钩子装载时 .light 优先 → 高级断言 ImportError。
3. **R57 为什么绿**：phase9 所在 worker 是否装钩子随机——100010 全量恰好未触发（.py 路径）→ 门 PASS 有运气成分；R56 各轮红绿抖动同源。**R57 的 L-175 只修了"类基类 NameError"层，没修"钩子 vs .py 优先"层**。

### 修复（最小，1 个文件）
`stdlib/断言工具.light` 首行**去掉「纯光明实现」魔数**（并遵守护栏 test_pure_light_hook：文件内不再出现该魔数字样）→ `_is_pure_light=False` → 钩子放行 CPython 原生机制 → 同名 .py（完整实现）优先 → phase9 全绿。
- 取舍：断言工具.light 的"自举演示"（钩子编译验证）放弃——它明确是"原生腿安全子集"且头注释自己声明回退 .py，去魔数兑现文档承诺。
- 登记：**L-176（R58 已修）**：纯光明魔数与"缺名回退 .py"自相矛盾致 phase9 高级断言在钩子环境 ImportError。

### 验证
| 项 | 结果 |
|---|---|
| 本机组合（bootstrap+phase9+护栏） | ✅ 145 passed / 0 failed（修复前 6 failed） |
| 0.82 定向（护栏+phase9） | ✅ 126 passed / 0 failed |
| 终跑全量 133701 | ✅ phase9 6 条消失、aiohttp 2 条消失、护栏 1 条修复后定向确认 |

---

## 三、其余新增红处置

| 红 | 处置 | 结果 |
|---|---|---|
| aiohttp 2 条（test_http_client.py::test_async_client*） | 0.82 装 aiohttp 3.14.3（FreeBSD 源码编译）——test_http_client 文件级 importorskip("requests")，装 requests 后不再 skip、暴露缺 aiohttp（任务书风险③预告场景） | ✅ 定向 49 passed |
| flaky 1 条（test_重派与心跳_杀节点后重派且无静默丢条） | 0.82 单条重跑 10 次 | ✅ 10/10 绿 → 确认为全量高负载下偶发抖动（R57 轮询修复有效，非确定性失败），登记已知 flaky |

---

## 四、验收清单（全过）

- [x] 16 条词法红转绿（L-174 设甲为三 + 切词 + 单字保护并集 _P0A_SINGLE_CHAR_PROTECTED）；互举反跑 677 零新增；token A/B 38084 文件仅 1 文件变化
- [x] 18 条环境红实测转绿（0 豁免 0 悬置）；aiohttp 环境补全（2 条）
- [x] 35 条（代码生成 21 + 类/成员 14）+ 30 条（其余）归因完成（结构化 JSON/CSV）
- [x] **phase9 钩子缺陷修复（L-176）**——R57 遗留根治，本机+0.82 定向全绿
- [x] 对标清单 #197 追加+定稿（无损往返自证）、MEMORY 更新、探针移档
- [x] 全程 0.82 全量 2 次（破例 1 次：首跑暴露 R57 遗留 → 修复 → 终跑定门），无并行，本机零全量
- [x] 门 PASS（修正后）：新增红 0（133701 的 1 条护栏已定向修复确认）
- [x] 提交完成（不 push，范围见下）

---

## 五、提交清单（两仓分开，显式列文件）

**light-merge**：
- `src/lexer.py`（L-174 + 切词 + 单字保护并集 + R30 收窄 + 数字前缀，任务1）
- `stdlib/断言工具.light`（L-176 魔数修复）
- `tests/test_lexer.py`、`tests/unit/test_break_continue_aliases.py`、`test_interface_aliases.py`、`test_l0_char_alias_async_yi.py`、`test_l0_char_alias_const_chang.py`、`test_l0_char_aliases_paradigm_ac.py`、`test_lexer_compound_safe_alignment.py`、`test_match_elif_import_aliases.py`、`test_modifier_await_aliases.py`（任务1 测试迁移/钉现状更新）

**lightharness**：
- `docs/功能对标/对标清单.json`（#197）
- `_task1/2/3/4/5_R58_*.md` + `_taskM_R58_收口总报告.md` + `_task3/4_R58_*归因明细.json/csv`
- `docs/历史存档/R58探针/`（移档）
- `reports/082_lightmerge基线_2026-09-18-131415.json`、`-133701.json`（latest）、`082_diff_*131431.json`、`-133838.json`、配套 xml
- `scripts/082全量回归.py`、`scripts/同步0.82.py`（R56 时代改进未提交，本次一并纳入——mtime 排序/--py 透传）

**不提交（保持原状）**：`examples/harness/评测报告.md`（R56 阶段工作树改动，任务1 已还原）、light-merge 历史未跟踪探针（_ssh_*/_r24_*/_taskR11B_test_*/_tmp_* 等）、`.blocking_backup/`、`.bugfix/`、`docs/dataset_*`、`tools/convert_to_deepseek_r1_format.py` 等。

---

## 六、遗留与建议（R59 行动清单，源自任务3/4 归因）

| 优先级 | 行动 | 条数 | 说明 |
|---|---|---|---|
| P0 | codegen 粘连 `己X` 读取位不展开（两后端 _resolve_* 加类属性白名单分支） | 14 | 一条修复可全清（任务3） |
| P0 | 测试期望更新：L-096 _light_attr_get/_set helper 形态 | 21 | 改断言或升行为断言（任务3） |
| P1 | 网络请求 stdlib 修 property/签名/import | 5 | test_stdlib_phase3.py（任务4） |
| P1 | 内置清单再生成脚本 | 3 | 低垂果实（任务4） |
| P1 | 文档门：清理 L1 文档 ROT/噪声块 | 2 | 任务4 |
| P2 | 异步修饰符编译期报错 | 5 | 报错信息质量（任务4） |
| P2 | 其余语义债 9 条 + 旧式语法 2 条 | 11 | 任务4 清单 |
| P3 | test_为搭配函数调用 `'=='` 预置误伤 | 1 | 收窄断言面（任务3） |
| 观察 | test_period_in_class_body 产物 `def get(self, self)` 静默错编形状 | — | 任务3 附带观察，建议立工作项 |

**全量纪律备忘**：R57 门 PASS 的"运气"教训——**钩子/装载顺序类缺陷定向全绿也会漏**；本轮 phase9 红绿抖动的真相（魔数 vs .py 优先）已记录，R59 起 phase9 不再有随机性。
