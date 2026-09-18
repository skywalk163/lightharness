# R57 任务4 —— 101 条存量红分类画像（纯只读）

> 日期：2026-09-18 ｜ 数据源：`reports/082_lightmerge基线_2026-09-18-072454.json` + `reports/_082_lm_results_2026-09-18-072453.xml`（同一次跑，id 归一后 100 红逐条一致）
>
> 铁律遵守：未跑任何 pytest、未连 0.82，仅解析 R56 已有产物。

## 一、口径核对：100 vs 101

| 轮次文件 | 收集数 | 红数 | 说明 |
|---|---|---|---|
| 002428 | 7806 | 117 |  |
| 005728 | 7806 | 116 |  |
| 010728 | 7806 | 116 |  |
| 070457 | 8109 | 150 | 收集总数 8109（含 e2e 等约 303 例），口径与其他轮不可比 |
| 071350 | 7806 | 117 |  |
| 072453 | 7806 | 100 | **真基线**（与 072454 JSON 同源） |

**结论**：

1. 真基线红数 = **100**（91 failure + 9 error）。
2. R56 所称「101 条存量红」口径还原：`071350` 轮 117 红 − 16 条 `tests/test_stdlib_phase9.py`（R54 引入的 `错误` 未定义红）= **101**，即基线 100 + `tests/test_cross_platform.py::test_stdlib_modules_importable` 1 条。两者不矛盾；本画像以真基线 100 条为准，另把 17 条「基线外稳定红」单列（见 §五）。

## 二、分类总览（12 类，合计 100）

| # | 类别 | 条数 | 建议动作 |
|---|---|---|---|
| 1 | 语义债-代码生成断言 | 21 | 语义轮 |
| 2 | 环境红-缺依赖 | 18 | 环境红 |
| 3 | 语义债-类/成员访问 | 14 | 语义轮 |
| 4 | 语义债-其他 | 12 | 逐条归因 |
| 5 | 词法层-切词行为 | 8 | 词法轮 |
| 6 | 词法层-单字保护/安全表 | 8 | 需归因 |
| 7 | 解析层-语法错误 | 7 | 疑与 G5（赋值无空格）同源 |
| 8 | 语义债-异步修饰符 | 5 | 语义轮 |
| 9 | 语义债-内置清单同步 | 3 | 低垂果实 |
| 10 | 文档门债 | 2 | 文档轮 |
| 11 | 性能断言-墙钟 | 1 | 本轮 R57 任务2 处置（阈值放宽/相对度量，留痕） |
| 12 | examples 聚合门 | 1 | R57 任务1 落地后复查（聚合 9 例 example 异常，含 4 例词法红，可能部分转绿） |

## 三、文件分布

红数 ≥2 的 16 个文件共 82 条；另有 18 个单红文件（合计 34 个文件）。

| 文件 | 红数 | 主类别 |
|---|---|---|
| tests/test_context_manager.py | 11 | 语义债-代码生成断言×7、语义债-类/成员访问×4 |
| tests/unit/test_v35_chained_call.py | 9 | 语义债-代码生成断言×9 |
| tests/test_datetime.py | 8 | 环境红-缺依赖×8 |
| tests/test_frontend_blockers_run.py | 8 | 语义债-异步修饰符×5、语义债-类/成员访问×3 |
| tests/test_lightpub_bridge.py | 6 | 环境红-缺依赖×6 |
| tests/test_parser.py | 6 | 解析层-语法错误×5、语义债-其他×1 |
| tests/test_stdlib_phase3.py | 5 | 语义债-其他×5 |
| tests/integration/test_class_system.py | 5 | 语义债-类/成员访问×5 |
| tests/unit/test_v34_syntax_sugar.py | 4 | 语义债-代码生成断言×4 |
| tests/_test_null_safety.py | 4 | 解析层-语法错误×2、语义债-其他×2 |
| tests/unit/test_lexer.py | 3 | 词法层-切词行为×3 |
| tests/unit/test_native_leg_capability.py | 3 | 语义债-内置清单同步×3 |
| tests/unit/test_lexer_p0a_deterministic.py | 3 | 词法层-切词行为×3 |
| tests/test_async_io_light.py | 3 | 环境红-缺依赖×3 |
| tests/unit/test_doc_examples_gate.py | 2 | 文档门债×2 |
| tests/unit/test_lexer_perf.py | 2 | 词法层-切词行为×1、性能断言-墙钟×1 |

## 四、18 条缺依赖环境红清单（不计入缺陷）

| # | 用例 | 缺失依赖 | 报错特征 |
|---|---|---|---|
| 1 | tests/test_datetime.py::test_公历转农历 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 2 | tests/test_datetime.py::test_农历转公历 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 3 | tests/test_datetime.py::test_日期时间转农历 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 4 | tests/test_datetime.py::test_日期转农历 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 5 | tests/test_datetime.py::test_春节日期 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 6 | tests/test_datetime.py::test_中秋日期 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 7 | tests/test_datetime.py::test_端午日期 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 8 | tests/test_datetime.py::test_中国节假日 | lunardate | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 9 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_HTTP提交 | requests | failed on setup with "ModuleNotFoundError: No module named ' |
| 10 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_HTTP获取 | requests | failed on setup with "ModuleNotFoundError: No module named ' |
| 11 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_URL编码解码 | requests | failed on setup with "ModuleNotFoundError: No module named ' |
| 12 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_导入 | requests | failed on setup with "ModuleNotFoundError: No module named ' |
| 13 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_拼接URL | requests | failed on setup with "ModuleNotFoundError: No module named ' |
| 14 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_获取JSON | requests | failed on setup with "ModuleNotFoundError: No module named ' |
| 15 | tests/test_tls_light.py::test_缺cryptography必须响亮降级 | cryptography | Failed: 本机缺 cryptography（No module named 'cryptography'）：TLS |
| 16 | tests/test_async_io_light.py::TestTLS异步读腿::test_tls异步读体拿到完整体且不占用事件循环 | cryptography | failed on setup with "ModuleNotFoundError: No module named ' |
| 17 | tests/test_async_io_light.py::TestTLS异步读腿::test_两路TLS串行与并发的关系 | cryptography | failed on setup with "ModuleNotFoundError: No module named ' |
| 18 | tests/test_async_io_light.py::TestTLS异步读腿::test_tls异步腿的读超时抛读取错误 | cryptography | failed on setup with "ModuleNotFoundError: No module named ' |

> 分布：cryptography 4（test_async_io_light 3 + test_tls_light 1）、requests 6（test_lightpub_bridge）、lunardate 8（test_datetime）。合计 18，与任务书预期一致。

## 五、稳定性画像（6 份 0.82 junitxml 交叉比对）

1. 基线 100 条中 **99 条 6/6 轮稳定红**（真存量）；1 条抖动 = `test_lexer_performance_10000_lines`（墙钟阈值并行敏感，R57 任务2 处置对象）。
2. **基线外稳定红 17 条（5/5 其他轮全红、唯独基线全绿 → 反常）**：
   - 16 条 `tests/test_stdlib_phase9.py`（`NameError: name '错误' is not defined`，R54 引入，G2，R57 任务1b 修复对象）；
   - 1 条 `tests/test_cross_platform.py::test_stdlib_modules_importable`（待归因，疑依赖生成时序/并行顺序）。
3. 真抖动：`test_重派与心跳_杀节点后重派且无静默丢条`（1/5 轮红，G3，任务2 处置）；e2e 33 例集中自 `070457` 轮——该轮收集总数 8109 与其他 7806 不同，属**口径差异**而非抖动。
4. ⚠️ **对路M 收口的预警**：真基线那次 phase9 16 条 + cross_platform 1 条全绿与其他 5 轮矛盾，真基线**低估存量**。任务1b 修复后这 16 条应稳定转绿；但 **cross_platform 1 条在收口全量中大概率回来**，若按「新增红 = 本轮失败 − 基线失败」的硬判据会被误判为新增红 → 建议路M 预先将其登记为已知不稳定红（附本画像为证）。

## 六、任务1 修复后预计转绿估算（口径：估算 + 条件）

| 用例 | 预计 | 条件/口径 |
|---|---|---|
| test_lexer_correctness_smoke | 1 | `甲为三` 由任务1a 顺带修；否则保持红并登记（任务书明示不承诺） |
| tests/test_lexer.py::test_basic_keywords（R36 钉现状） | 0~1 | 期望 设甲为三 整体成词，与 smoke 方向需对表，可能需改钉 |
| test_all_examples_output（聚合门） | 0~1 | 聚合 9 例 example 异常，4 例词法红修复后取决于其余 5 例 |
| tests/test_parser.py 5 条（期望'为'或'等于'，但得到「。」） | 0~5 | 疑与 G5（赋值无空格）同源，需归因；任务书禁止为修它扩大改动面 |
| 16 条 phase9（`错误` 未定义，基线外） | 16 | 任务1b 直接目标；注意其不在基线 100 内（见 §五） |

**要点**：4 例 example 红（R22/R26/R27）**不在基线 100 条内**——examples 不被 pytest 收集、不进全量门，这正是 G7 / 任务3 要补的覆盖缺口。

## 七、明细交付

- `reports/_task4_R57_存量红明细_072454.json`（baseline_reds 100 条全字段 + outside_baseline_reds 51 条基线外红含出现轮次）
- `reports/_task4_R57_存量红明细_072454.csv`（同口径 CSV，UTF-8-SIG 便于 Excel）

## 八、逐条明细（基线 100 条，按类别）

### 语义债-代码生成断言（21 条）

建议动作：语义轮：codegen 字符串断言族（点号/句号、成员赋值形态）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_v35_chained_call.py::TestDotPeriodSplit::test_dot_member_access | assert 'p.x' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a / b\… |
| 2 | tests/unit/test_v35_chained_call.py::TestDotPeriodSplit::test_mixed_period_and_dot | assert 'p.x' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a / b\… |
| 3 | tests/unit/test_v35_chained_call.py::TestDotPeriodSplit::test_no_period_no_dot_ambiguity | assert 'p.x = 3' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a … |
| 4 | tests/unit/test_v35_chained_call.py::TestDotPeriodSplit::test_period_in_class_body | assert 'self.x' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a /… |
| 5 | tests/unit/test_v35_chained_call.py::TestDotPeriodSplit::test_dot_access_after_new_keyword | assert 'a.x' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a / b\… |
| 6 | tests/test_context_manager.py::TestL2OOPCodegen::test_自_param_and_body_both_self | assert 'self.姓名 = 姓名' in '# 由光明编译器生成\n# 源文件: 光明代码\n\nfrom abc import ABC, abstractmethod\n… |
| 7 | tests/test_context_manager.py::TestAwaitMemberAccess::test_await_chained_member | assert 'await 甲.乙.丙()' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    ret… |
| 8 | tests/test_context_manager.py::TestJueyiE遍历为连接词::test_为搭配函数调用 | AssertionError: assert '==' not in '# 由光明编译器生成\...    print(i)'      '==' is contained her… |
| 9 | tests/test_async_class_method.py::TestAsyncClassMethod::test_03_async_method读写己属性 | AssertionError: assert ('self.值 = (self.值 + 1)' in '# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_… |
| 10 | tests/test_context_manager.py::TestJueyiOOP成员赋值目标::test_自之属性赋值 | assert 'self.姓名 = 姓名' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    retu… |
| 11 | tests/test_context_manager.py::TestJueyiOOP成员赋值目标::test_自之属性带索引赋值 | assert 'self.成绩[科目] = 分数' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    … |
| 12 | tests/test_context_manager.py::TestJueyiOOP成员赋值目标::test_普通标识符之成员赋值 | assert 'obj.字段 = 1' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return… |
| 13 | tests/test_context_manager.py::TestJueyiOOP成员赋值目标::test_点号成员赋值未被破坏 | assert 'obj.字段 = 1' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return… |
| 14 | tests/unit/test_v34_syntax_sugar.py::TestAttributeAssignment::test_self_attr_eq | assert 'self.x = 1' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return… |
| 15 | tests/unit/test_v34_syntax_sugar.py::TestAttributeAssignment::test_self_attr_等于 | assert ('self.x == 1' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    retu… |
| 16 | tests/unit/test_v34_syntax_sugar.py::TestAttributeAssignment::test_obj_attr_eq | assert 'p.x = 10' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a… |
| 17 | tests/unit/test_v34_syntax_sugar.py::TestAttributeAssignment::test_dot_access_still_works | assert 'p.x' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a / b\… |
| 18 | tests/unit/test_v35_chained_call.py::TestChainedAttributeAssignment::test_two_level_attr_assign | assert ('b.a.x = 42' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    retur… |
| 19 | tests/unit/test_v35_chained_call.py::TestChainedAttributeAssignment::test_self_chain_assign | assert ('self.inner.val' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    r… |
| 20 | tests/unit/test_v35_chained_call.py::TestChainedAttributeAssignment::test_three_level_attr_assign | assert ('a.b.c.val = 99' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    r… |
| 21 | tests/unit/test_v35_chained_call.py::TestChainedAttributeAssignment::test_attr_assign_with_expr | assert 'a.x = ' in "# 由光明编译器生成\n# 源文件: 光明代码\n\ndef _light_trunc_div(a, b):\n    return a /… |


### 环境红-缺依赖（18 条）

建议动作：环境红：永久豁免（0.82 不装第三方库为既定口径）；若环境决策改变（装 cryptography/lunardate/requests）可整类解锁

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/test_datetime.py::test_公历转农历 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 2 | tests/test_datetime.py::test_农历转公历 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 3 | tests/test_datetime.py::test_日期时间转农历 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 4 | tests/test_datetime.py::test_日期转农历 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 5 | tests/test_datetime.py::test_春节日期 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 6 | tests/test_datetime.py::test_中秋日期 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 7 | tests/test_datetime.py::test_端午日期 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 8 | tests/test_datetime.py::test_中国节假日 | RuntimeError: 农历转换需要 lunardate 库，请执行: pip install lunardate |
| 9 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_HTTP提交 | failed on setup with "ModuleNotFoundError: No module named 'requests'" |
| 10 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_HTTP获取 | failed on setup with "ModuleNotFoundError: No module named 'requests'" |
| 11 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_URL编码解码 | failed on setup with "ModuleNotFoundError: No module named 'requests'" |
| 12 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_导入 | failed on setup with "ModuleNotFoundError: No module named 'requests'" |
| 13 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_拼接URL | failed on setup with "ModuleNotFoundError: No module named 'requests'" |
| 14 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_获取JSON | failed on setup with "ModuleNotFoundError: No module named 'requests'" |
| 15 | tests/test_tls_light.py::test_缺cryptography必须响亮降级 | Failed: 本机缺 cryptography（No module named 'cryptography'）：TLS 测试无法生成自签证书，本文件的 TLS 覆盖为零。 修法二… |
| 16 | tests/test_async_io_light.py::TestTLS异步读腿::test_tls异步读体拿到完整体且不占用事件循环 | failed on setup with "ModuleNotFoundError: No module named 'cryptography'" |
| 17 | tests/test_async_io_light.py::TestTLS异步读腿::test_两路TLS串行与并发的关系 | failed on setup with "ModuleNotFoundError: No module named 'cryptography'" |
| 18 | tests/test_async_io_light.py::TestTLS异步读腿::test_tls异步腿的读超时抛读取错误 | failed on setup with "ModuleNotFoundError: No module named 'cryptography'" |


### 语义债-类/成员访问（14 条）

建议动作：语义轮：`己X` 未定义族归因（类/成员访问链路）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/test_frontend_blockers_run.py::test_a24_泛型类真跑 | AssertionError: [run] 退出码 1:   [运行错误] name '己项' is not defined       assert 1 == 0 |
| 2 | tests/test_frontend_blockers_run.py::test_a24_多参数泛型类 | AssertionError: [run] 退出码 1:   [运行错误] name '己左' is not defined       assert 1 == 0 |
| 3 | tests/test_context_manager.py::TestL0SingleCharClassKeywords::test_继承链可用 | NameError: name '己名称' is not defined |
| 4 | tests/test_context_manager.py::TestChaoSuper::test_chao_dot_plain_method | NameError: name '己名称' is not defined |
| 5 | tests/test_context_manager.py::TestChaoSuper::test_chao_zhi_form | NameError: name '己名称' is not defined |
| 6 | tests/test_context_manager.py::TestChaoSuper::test_chao_de_form | NameError: name '己名称' is not defined |
| 7 | tests/test_frontend_blockers_run.py::test_a25_两个嵌套类且外层成员不被吞 | AssertionError: [run] 退出码 1:   [运行错误] name '己号' is not defined       assert 1 == 0 |
| 8 | tests/test_level6_types.py::TestTypeScenarioClass::test_class_instantiation | NameError: name '己当前' is not defined |
| 9 | tests/test_edge_cases.py::TestEdgeCasesClasses::test_class_with_multiple_methods | RuntimeError: 执行错误: name '己初始值' is not defined 生成的Python代码: # 由光明编译器生成 # 源文件: 光明代码  def _l… |
| 10 | tests/integration/test_class_system.py::TestClassInheritance::test_constructor_with_inheritance | NameError: name '己名字' is not defined |
| 11 | tests/integration/test_class_system.py::TestClassBasic::test_class_with_attributes | NameError: name '己姓名' is not defined |
| 12 | tests/integration/test_class_system.py::TestMethodOverride::test_method_override | NameError: name '己半径' is not defined |
| 13 | tests/integration/test_class_system.py::TestClassAdvanced::test_self_method_call | NameError: name '己值' is not defined |
| 14 | tests/integration/test_class_system.py::TestMultipleClasses::test_multiple_classes_in_one_file | NameError: name '己品牌' is not defined |


### 语义债-其他（12 条）

建议动作：逐条归因：stdlib_phase3 网络运行时行为、URL 编码、null_safety 断言、R13B/R13C 对拍等

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_地板搬迁_列表_S2.py::test_十个段落全部导出且两版都可调用 | AssertionError: assert ['冻结', '列', '..., '列表弹出', ...] == ['列', '列表创建',..., '列表排序', ...]   … |
| 2 | tests/unit/test_parser.py::TestParser::test_compact_binary_expr_with_call | AssertionError: 'n乘阶乘' == 'n乘阶乘' |
| 3 | tests/test_stdlib_phase3.py::Test网络请求::test_HTTP错误响应 | AssertionError: <bound method 响应.是否成功 of <网络请求.响应 object at 0xc08342046e0>> is not false |
| 4 | tests/test_stdlib_phase3.py::Test网络请求::test_URL编码解码 | AssertionError: '???world' != '你好 world' - ???world + 你好 world |
| 5 | tests/test_stdlib_phase3.py::Test网络请求::test_响应对象 | AssertionError: <bound method 响应.文本 of <网络请求.响应 object at 0xc08362ad340>> != '{"key": "val… |
| 6 | tests/test_stdlib_phase3.py::Test网络请求::test_拼接URL | TypeError: 拼接URL() takes 2 positional arguments but 4 were given |
| 7 | tests/test_stdlib_phase3.py::Test网络请求::test_解析查询串 | NameError: name '新建字典' is not defined |
| 8 | tests/_test_null_safety.py::TestNullSafetyBasic::test_unwrap_on_nullable_variable | AssertionError: unexpectedly None |
| 9 | tests/unit/test_原生腿_R13C_对拍扩展.py::test_URL编码解码 | Failed: 实际=['a%20b%26c%3D1', 'a b&c=1', 'path/to?q=光明'] 期望=['a%20b%26c%3D1', 'a b&c=1', 'p… |
| 10 | tests/_test_null_safety.py::TestNullSafetyArithmetic::test_operation_without_unwrap | AssertionError: False is not true : 期望可空值参与运算时报错，但得到: [] |
| 11 | tests/unit/test_原生腿_R13B_能力扩展.py::Test行政区划扩展::test_O0_行政区划代码_对拍与扩展 | AttributeError: 'ChinaRegion' object has no attribute '_region_code_map' |
| 12 | tests/test_parser.py::TestFunctionCall::test_call_in_expression | assert False  +  where False = isinstance(《设结果为段落计算》(甲, 乙), VarDecl) |


### 词法层-切词行为（8 条）

建议动作：词法轮：与 R57 任务1 同族，逐条归因（含 R36 钉现状对表）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_lexer.py::TestLexer::test_chinese_number | AssertionError: 0 != 2 |
| 2 | tests/unit/test_lexer.py::TestLexer::test_number_prefix_still_split_when_rest_is_keyword | AssertionError: Tuples differ: ('IDENTIFIER', '那么大') != ('KEYWORD', '那么')  First differing… |
| 3 | tests/unit/test_lexer.py::TestLexer::test_simple_tokenize | AssertionError: <TokenType.CHINESE_NUM: 5> not found in [<TokenType.KEYWORD: 7>, <TokenTyp… |
| 4 | tests/test_lexer.py::test_basic_keywords | AssertionError: R36 钉现状失败：无空格 设甲为三 应整体成一个标识符，得到 ['设', '甲为三', '。'] assert ['设', '甲为三', '。']… |
| 5 | tests/unit/test_lexer_p0a_deterministic.py::TestP0A复合词压力::test_六雷区_整体成词 | AssertionError: Lists differ: [('KEYWORD', '导出'), ('IDENTIFIER', '事件表')] != [('IDENTIFIER'… |
| 6 | tests/unit/test_lexer_p0a_deterministic.py::TestP0A复合词压力::test_同构复合词_整体成词 | AssertionError: Lists differ: [('KEYWORD', '外部'), ('IDENTIFIER', '命令')] != [('IDENTIFIER',… |
| 7 | tests/unit/test_lexer_p0a_deterministic.py::TestP0A复合词压力::test_清空白名单后仍整体成词 | AssertionError: Lists differ: [('KEYWORD', '导出'), ('IDENTIFIER', '事件表')] != [('IDENTIFIER'… |
| 8 | tests/unit/test_lexer_perf.py::TestLexerPerformance::test_lexer_correctness_smoke | AssertionError: '为' not found in ['设', '甲为三', '。', '打印', '甲', '加', 5, '。', None] |


### 词法层-单字保护/安全表（8 条）

建议动作：需归因：8 条断言 frozenset() 为空，疑运行期表构造/加载问题，词法轮处置

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_lexer_compound_safe_alignment.py::TestDropSignaturesFixed::test_除类型错误 | AssertionError: ('IDENTIFIER', '除') not found in [('KEYWORD', '捕'), ('IDENTIFIER', '除类型错误'… |
| 2 | tests/unit/test_match_elif_import_aliases.py::TestMatchSingleCharAliases::test_pi_is_compound_safe | AssertionError: '匹' not found in frozenset() |
| 3 | tests/unit/test_l0_char_alias_async_yi.py::TestAsyncCharAliasTables::test_异_进复合词保护表 | AssertionError: '异' not found in frozenset() |
| 4 | tests/unit/test_l0_char_alias_const_chang.py::TestConstModifierTables::test_常_进复合词保护表 | AssertionError: '常' not found in frozenset() |
| 5 | tests/unit/test_modifier_await_aliases.py::TestAliasTableMembership::test_等_已进复合词安全表 | AssertionError: '等' not found in frozenset() |
| 6 | tests/unit/test_break_continue_aliases.py::TestBreakContinueAliasTables::test_断_跃_已进复合词安全表 | AssertionError: '断' not found in frozenset() |
| 7 | tests/unit/test_interface_aliases.py::TestImplementsAliasTables::test_现_已进复合词安全表 | AssertionError: '现' not found in frozenset() |
| 8 | tests/unit/test_l0_char_aliases_paradigm_ac.py::TestParadigmACTablesUntouched::test_引_本来就是关键字 | AssertionError: '引' not found in frozenset() |


### 解析层-语法错误（7 条）

建议动作：疑与 G5（赋值无空格）同源：R57 任务1 顺带评估后复查，不许扩大改动面

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/_test_null_safety.py::TestBackwardsCompatibility::test_paragraph_call | parser_core.ParseError:  ┌─ 语法错误 │ 原因: 发现 2 个语法错误（下面详列前 2 个，建议从第 1 个开始修）:  错误 1/2:  ┌─ 语法错… |
| 2 | tests/test_parser.py::TestVariableDeclaration::test_variable_with_expression | parser_core.ParseError:  ┌─ 语法错误 │ 位置: 行 1, 列 8 │ 原因: 期望'为'或'等于'，但得到 「。」 │ 附近: '。' │ 建议: 句… |
| 3 | tests/test_parser.py::TestExpressions::test_arithmetic_expression | parser_core.ParseError:  ┌─ 语法错误 │ 位置: 行 1, 列 8 │ 原因: 期望'为'或'等于'，但得到 「。」 │ 附近: '。' │ 建议: 句… |
| 4 | tests/test_parser.py::TestExpressions::test_nested_expression | parser_core.ParseError:  ┌─ 语法错误 │ 位置: 行 1, 列 10 │ 原因: 期望'为'或'等于'，但得到 「。」 │ 附近: '。' │ 建议: … |
| 5 | tests/test_parser.py::TestFunctionDefinition::test_function_with_body | parser_core.ParseError:  ┌─ 语法错误 │ 位置: 行 2, 列 10 │ 原因: 期望'为'或'等于'，但得到 「。」 │ 附近: '。' │ 建议: … |
| 6 | tests/_test_null_safety.py::TestNullSafetyFunctionCall::test_func_non_nullable_param_with_nullable_arg | parser_core.ParseError:  ┌─ 语法错误 │ 原因: 发现 2 个语法错误（下面详列前 2 个，建议从第 1 个开始修）:  错误 1/2:  ┌─ 语法错… |
| 7 | tests/test_parser.py::TestNoSpaceCode::test_no_space_variable | parser_core.ParseError:  ┌─ 语法错误 │ 位置: 行 1, 列 7 │ 原因: 期望'为'或'等于'，但得到 「。」 │ 附近: '。' │ 建议: 句… |


### 语义债-异步修饰符（5 条）

建议动作：语义轮：报错信息质量（未指出「异步被当值用」根因）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用[\u5f02\u6b65\u8bfb\u53d6\u4e8c\u8fdb\u5236] | AssertionError: 报错没指出根因（`异步` 被当值用）:   [运行错误] name '异步读取二进制' is not defined       assert '修… |
| 2 | tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用[\u5f02\u6b65\u5199\u5165\u4e8c\u8fdb\u5236] | AssertionError: 报错没指出根因（`异步` 被当值用）:   [运行错误] name '异步写入二进制' is not defined       assert '修… |
| 3 | tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用[\u5f02\u6b65\u4efb\u52a1\u7b49\u5f85] | AssertionError: 报错没指出根因（`异步` 被当值用）:   [运行错误] name '异步任务等待' is not defined       assert '修饰… |
| 4 | tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用[\u5f02\u6b65\u4efb\u52a1\u53d6\u6d88] | AssertionError: 报错没指出根因（`异步` 被当值用）:   [运行错误] name '异步任务取消' is not defined       assert '修饰… |
| 5 | tests/test_frontend_blockers_run.py::test_p0_异步修饰符不许当值用[\u5f02\u6b65\u53d6\u6570] | AssertionError: 报错没指出根因（`异步` 被当值用）:   [运行错误] name '异步取数' is not defined       assert '修饰符'… |


### 语义债-内置清单同步（3 条）

建议动作：低垂果实：重跑清单再生成脚本对齐 JSON（3 条）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_native_leg_capability.py::test_内置函数清单与代码一致 | AssertionError: 内置函数清单与代码不一致:     代码有但 JSON 没有: ['is_bool', 'is_dict', 'is_float', 'is_int… |
| 2 | tests/unit/test_native_leg_capability.py::test_内置函数证据行号可定位 | AssertionError: 内置函数证据行号问题:   ?.: codegen_typed.py:2912 那一行没有这个名字：   ??: codegen_typed.py:… |
| 3 | tests/unit/test_native_leg_capability.py::test_运行时符号清单与代码一致 | AssertionError: 运行时符号清单与代码不一致:     代码有但 JSON 没有: ['strcmp']     JSON 有但代码没有: [] assert {'_… |


### 文档门债（2 条）

建议动作：文档轮：清理 docs 违规块（ROT/噪声块）后对表

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_doc_examples_gate.py::TestDocExamplesGate::test_不许新增ROT | AssertionError: Lists differ: [] != [('docs/L1_白话体语法规范_v4.0.md', '30b8918966cf[221 chars]6… |
| 2 | tests/unit/test_doc_examples_gate.py::TestDocExamplesGate::test_噪声类总数不许涨 | AssertionError: 19 not less than or equal to 18 : 噪声块从 18 涨到 19：新写的文档又混进了 REPL 记录/伪代码/箭头注解… |


### 性能断言-墙钟（1 条）

建议动作：本轮 R57 任务2 处置（阈值放宽/相对度量，留痕）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_lexer_perf.py::TestLexerPerformance::test_lexer_performance_10000_lines | AssertionError: 2.544814493972808 not less than 2.0 : 词法分析耗时 2.5448 秒，超过 2.0 秒限制 |


### examples 聚合门（1 条）

建议动作：R57 任务1 落地后复查（聚合 9 例 example 异常，含 4 例词法红，可能部分转绿）

| # | 用例 | 报错摘要 |
|---|---|---|
| 1 | tests/unit/test_examples_run.py::TestExampleFilesRun::test_all_examples_output | AssertionError: Lists differ: [] != ["hello.light: 运行异常 -> \n┌─ 语法错误\n│ 位置: 行 [1216 chars]… |
