# 第22轮 收口说明框架（路M 收口检查清单对照）

> 日期：2026-09-14 ｜ 模板状态：任务2/4/6部分已填实，任务1/3/5与全量CI部分待各责任路回填

---

## 一、6路交付物核对

| 任务 | 修改文件 | 反跑/验证脚本 | 交付报告 | 状态 |
|---|---|---|---|---|
| 1 | lexer.py _EMBED_MAX_MATCH_KEYWORDS 定义+引用块 | _antirun_r22_t1_嵌入关键字移除.py | _task1_R22_嵌入关键字冗余评估_交付报告.md | ✅ 已完成（结论：_EMBED_MAX_MATCH_KEYWORDS **保留**，非冗余，17文件依赖） |
| 2 | lexer.py IDENTIFIER_SAFE_* 定义（17→5/3条） | _sweep_r22_t2_identifier_safe.py + _antirun_r22_t2_identifier_safe精简.py | _task2_R22_IDENTIFIER_SAFE精简_交付报告.md | ✅ 本轮完成 |
| 3 | lexer.py _COMPOUND_SAFE_SINGLE_KEYWORDS 定义 | _sweep_r22_t3_compound_safe_single.py + 反跑 | _task3_R22_COMPOUND_SAFE_SINGLE精简_交付报告.md | ✅ 已完成（52→24条，见其交付报告；遗留单测契约回归见第四节第5条） |
| 4 | lexer.py _TRAILING_ALIAS_MERGE+COMMON_COMPOUND_WORDS 定义（10→1、216→184） | _sweep_r22_t4_trailing_alias.py + _sweep_r22_t4_ccw_guard.py + _antirun_r22_t4_trailing_alias+ccw精简.py | _task4_R22_TRAILING_ALIAS+CCW护栏精简_交付报告.md | ✅ 本轮完成 |
| 5 | （无源码修改） | _antirun_r22_t5_全量回归扫描.py | _task5_R22_全量回归扫描报告.md | ✅ 已完成（_task5_R22_全量回归扫描报告.md：token序列零变化） |
| 6 | docs三件 | — | _task6_R22_docs更新草案.md + _task6_R22_保护表通用化策略建议.md + 本框架 | ✅ 本轮完成 |

## 二、路M收口检查清单逐项状态

1. 6路交付物齐全 —— 部分（2/4/6✅，1/3/5待回填）
2. 任务1 _EMBED_MAX_MATCH_KEYWORDS 冗余验证 —— ✅ 完成：**保留（非冗余）**，等价置空法+770文件判据③，纯嵌入场景17文件依赖；纠正第21轮「L-084单点仍绿」窄点误判
3. 任务2 IDENTIFIER_SAFE_* 20条逐条验证 —— ✅ 完成：12条删除（语料级中立）、5条保留（4条语料护栏+`标准库`单测契约）、SUFFIX_ONLY 3条全保留
4. 任务3 _COMPOUND_SAFE_SINGLE 52条逐条验证 —— 待回填（注意：`当` 不在主集合，仅在派生集合 _P0A_COMPOUND_SAFE = 主集合|{'当'}，本轮已确认派生集合不受任务2/4影响）
5. 任务4 TAM 10条 + CCW TierB 32条重估 —— ✅ 完成：TAM 10→1（`己`护栏，test_L120.light依赖，L-120用例编译rc=0）；TierB 32条全部冗余删除
6. 任务5 全量回归扫描 —— 待回填（本轮已提供最终态全语料763文件token零变化的直接证据，任务5的精简前后对比可直接复用）
7. 任务6 docs三件回填 + 通用化策略建议 —— ✅ 完成（#134/#135已登记且#135已按任务1保留结论回填为已完成；R22-D1/D2已写入并回填；缺陷账L-084/092/137无需追加——任务1未移除该集合，不满足任务书追加前提）
8. 全量CI无例外全绿 —— ✅ **lightharness ci_test.py 全量通过（2026-09-14 17:14，pytest 477 passed + smoke 5/5，日志 _r22_ci_run.log）**，且在任务2/4最终态上复跑通过。注意：light-merge/tests 另有 19 failed（HEAD 既有9 + 任务3引入10），不属轮次门禁，已提示任务3路
9. 第19/20/21轮反跑全部ALL OK —— 待收口统一复跑（本轮改动不影响其判据：_EMBED未动、_COMPOUND_SAFE_SINGLE未动、预扫描未动）
10. light-merge / lightharness 分路提交 —— 待收口（本轮变更：light-merge/src/lexer.py 1个文件；lightharness 新增 _sweep/_antirun/_task 报告共 12 个文件）
11. 收口说明撰写 —— 以本框架为底稿，待 1/3/5 回填后成文
12. 收口提交 —— 待第10项完成后

## 三、本轮（任务2/4/6）核心数字

- 删除保护表条目：12（任务2）+ 41（任务4）= **53条**（16:31 文件覆盖事故后已在任务3当前态上重新应用并复验）
- 剩余规模：IDENTIFIER_SAFE 5条、SUFFIX_ONLY 3条、TAM 1条、CCW 184条
- 全语料（764个.light）token序列变化：**0文件**
- 单测契约护栏：`标准库`（tests/unit/test_lexer.py::test_identifier_safe_module_print_merged_inside_word）
- L-120 关联：test_L120.light 编译 rc=0，`己` 词尾并入护栏保留

## 四、收口时注意事项

1. **#135 与 L-084/092/137 回填**：✅ 已完成——#135 已按任务1「保留」结论回填为已完成；行为差异清单 R22-D2 已回填并订正R21-D2；缺陷账L-084/092/137按任务书前提（仅移除才追加）无需改动。
2. **R21-D3 订正已写入**：收口说明引用保护表数字时以本轮为准（CCW=184，非216/32）。
3. **提交拆分**：light-merge 一笔（lexer.py 保护表精简）；lightharness 一笔（脚本+报告+docs）。
4. **语言缺陷账.md 含 NUL 字节**：编辑须用字节级操作，避免文本模式全量重写。
5. **【跨任务发现，任务3区域】**：任务3并发落地（_COMPOUND_SAFE_SINGLE_KEYWORDS 精简）后，light-merge/tests 词法5文件出现新增失败（HEAD 基线 9 failed 噪音 → 当前 19 failed），失败样本均为任务3删除条目的单测契约：`减法(a,b)`、`去除空格`、`首字母大写`、`首项`、`月末`、`周末`、`余额`、`是可打印`（tests/test_lexer.py / tests/unit/test_lexer.py）等。**归属判定（2026-09-14 内存回滚实验）**：将本轮任务2/4的删除在内存中回滚后仍为 19 failed——即 19 个失败全部来自任务3区域删除，任务2/4 的 53 条删除零新增失败。教训与任务2的 `标准库` 相同：**语料级中立 ≠ 无单测契约，删除前必须双验证（全语料 token 对比 + tests/unit/test_lexer*.py 全集）**。请任务3路核对其验证脚本是否遗漏单测判据，恢复被单测契约依赖的条目（或随精简同步修订契约用例并在交付报告中明示）。
6. **【文件覆盖事故，已恢复】**：2026-09-14 16:31 lexer.py 被并发重写，本轮任务2/4 的编辑曾被整体覆盖回退（仅任务3变更保留）。已在任务3当前态（CSS 52→24）之上重新应用任务2/4 全部编辑，并完成复验：①全语料 764 文件 token 序列零变化（叠加任务3态）；②_antirun_r22_t2 / _t4 反跑 ALL OK；③light-merge 词法5测试文件 19 failed 与任务3-only 态完全一致（零新增）。**收口前请各路确认编辑均已落盘再跑统一门禁；lexer.py 为多任务共享文件，建议后续轮次以 git 提交粒度协调。**
