# 第22轮 任务2 交付报告：IDENTIFIER_SAFE_KEYWORDS + IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS 逐条精简

> 日期：2026-09-14 ｜ 任务书：复刻_第22轮_任务prompt分发_保护表深度精简轮.md ｜ 状态：已完成
> 修改文件：light-merge/src/lexer.py（IDENTIFIER_SAFE_KEYWORDS 定义 + IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS 定义，仅增删条目与注释，未改引用代码）

---

## 一、精简结论

| 表 | 精简前 | 删除 | 精简后 | 幅度 |
|---|---|---|---|---|
| IDENTIFIER_SAFE_KEYWORDS | 17 条 | 12 条 | 5 条 | 70.6% |
| IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS | 3 条 | 0 条 | 3 条 | 0% |
| 合计（任务书口径 20 条） | 20 条 | 12 条 | 8 条（去重口径） | 60% |

满足任务书验证标准「至少删除 30% 的冗余条目」。

### 删除的 12 条冗余条目（主表）

`包含`、`匹配`、`回调`、`外部`、`排序`、`接口`、`枚举`、`结构体`、`联合体`、`段落`、`返回`、`配`

每条均通过判据③隔离中立验证：临时移除该条目后，全语料 763 个 .light 文件 token 序列**逐文件零变化**（含字符过滤加速：不含条目字符的文件不可能受影响，跳过 tokenize）。零变化说明该条目的保护场景已被第21轮任务2「非语句起始位置上下文敏感最大匹配」覆盖。

### 保留的 5 条真护栏（附依赖证据）

| 条目 | 依赖证据（移除后 token 变化的文件 / 契约） |
|---|---|
| 函数 | light-merge/examples/F阶段_标准库增强/F3_光明侧三个增强模块示例.light |
| 输出 | light-merge/tests/test_hashfs.light、lightharness/src/代理.light |
| 模块 | light-merge/examples/L2_wenyan/主程序.light |
| 打印 | light-merge/examples/L2_wenyan/主程序.light、学生模块.light、light-merge/tests/test_iface.light |
| 标准库 | 单测契约：tests/unit/test_lexer.py::test_identifier_safe_module_print_merged_inside_word 断言 `我的标准库` 合并为标识符 |

`标准库` 特殊说明：语料级隔离中立（763 文件零变化），但单测以合成串 `我的标准库` 断言词中合并行为契约，删除后该用例立红（SUBFAILED(src='我的标准库')），故保留。这是本轮确立的补充判据：**语料中立 + 单测契约双过才可删**。

SUFFIX_ONLY 3 条（模块/标准库/打印）全部保留：与主表同条目同步保留（子集约束）；词首仍作关键字的 scan_pos>0 门行为不变。

## 二、逐条验证结果表

完整机读证据：lightharness/_sweep_r22_t2_results.json；可复跑脚本：lightharness/_sweep_r22_t2_identifier_safe.py（输出 _r22_t2_sweep_out.txt）。

| 条目 | 主表移除后语料变化 | 判定 | 依赖文件 |
|---|---|---|---|
| 函数 | 1 文件 | 护栏 | F3_光明侧三个增强模块示例.light |
| 输出 | 2 文件 | 护栏 | test_hashfs.light、代理.light |
| 模块 | 1 文件 | 护栏 | L2_wenyan/主程序.light |
| 打印 | 3 文件（双删变体同） | 护栏 | L2_wenyan/主程序、学生模块、test_iface.light |
| 标准库 | 0 文件 | 护栏（单测契约） | tests/unit/test_lexer.py |
| 段落 | 0 文件 | 冗余，删除 | — |
| 返回 | 0 文件 | 冗余，删除（与任务书预判一致：已被上下文敏感切词覆盖） | — |
| 包含/匹配/回调/外部/排序/接口/枚举/结构体/联合体/配 | 均 0 文件 | 冗余，删除 | — |

任务书「特殊关注」复核：
- `函数`：确为真护栏（任务书预判正确）。
- `段落`：语料级冗余——所有"XX段落"场景已被预扫描+上下文敏感切词覆盖，与预判不同，以判据③为准。
- `返回`：冗余，任务书预判正确。
- `打印`：SUFFIX_ONLY 设计合理（词首是 print 语句），护栏保留。
- `模块`/`标准库`：`模块` 护栏；`标准库` 单测契约护栏。

## 三、验证与回归

1. **逐条隔离中立验证**：12 条删除条目补回后全语料 token 零变化（反跑 B 判据）。
2. **精简后全语料对比**：最终态（12 条删除 + 任务4的 9+32 条删除）与基线全语料 763 文件 token 序列零变化。
3. **单测**：词法相关 5 个测试文件（tests/test_lexer.py、tests/unit/test_lexer*.py×3、test_lexer_perf.py）与 HEAD 基线完全一致（9 failed / 58 passed / 140 subtests——9 个失败为 HEAD 既有噪音，与本次无关，HEAD 实测同样 9 failed）；本次编辑曾引入的 `标准库` 单测失败已通过保留该条目消除。
4. **全量 CI**：light-merge pytest 全量 + lightharness smoke（476 用例）见本轮收口记录；第22轮任务5全量回归扫描覆盖。
5. **反跑**：lightharness/_antirun_r22_t2_identifier_safe精简.py —— A 基线自检 / B 删除中立 / C 护栏正向控制 / D 单测契约，ALL OK（输出 _r22_t2_antirun_out.txt）；脚本在 finally 中恢复模块属性，不落盘修改。

## 四、通用约束遵守情况

- 文件互斥：仅改 lexer.py 行 43-79 保护表定义区（任务2互斥区域），未触碰引用代码。
- 只删不增：未新增任何条目。
- 逐条验证：12 条删除均逐条验证，未批量删除。
- 保留护栏证据：5 条保留条目全部记录依赖。
