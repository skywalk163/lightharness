# 第23轮 任务2 交付报告：阶段B——IDENTIFIER_SAFE_KEYWORDS 清表（后缀位置上下文规则替代）

> 日期：2026-09-14 ｜ 任务书：复刻_第23轮_任务prompt分发_保护表通用化替代轮.md ｜ 状态：已完成
> 修改文件：light-merge/src/lexer.py（两张表定义删除 + 三处引用代码替换为通用规则）；
>          light-merge/tests/unit/test_lexer_p0a_deterministic.py（适配性微改，见§六）

---

## 一、清表结论

| 表 | 清表前 | 清表后 | 替代机制 |
|---|---|---|---|
| IDENTIFIER_SAFE_KEYWORDS | 5条（函数/打印/标准库/模块/输出） | **0条（整表删除）** | 后缀位置上下文规则 |
| IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS | 3条（模块/标准库/打印） | **0条（整表删除）** | 规则天然保证（词首不满足scan_pos>0） |

自第22轮继承的5条"真护栏"全部由**上下文规则**覆盖，两张逐词白名单**整表消失**——阶段B目标达成。

## 二、替代规则设计（lexer.py 三处引用 + 两个类别集合）

**后缀位置上下文规则**（替代原 IDENTIFIER_SAFE 三处引用分支，探测循环/输出循环/rematch）：

> 多字、非运算符（∉_P0A_OP）、非排除集（∉_P0A_SUFFIX_SPLIT_KW）的关键字位于汉字词词中/词尾（scan_pos>0）→ 并入标识符。

**词首语义**（语句关键字优先，这是 SUFFIX_ONLY"词首必须作关键字"的通用化）：
- 词首多字**动词**（VERB_ARITY）：并入标识符，**唯一例外** `_P0A_STMT_SPLIT_VERBS = {'打印'}`——`打印` 的无空格 print 语句（打印甲/打印结果）是本语言一等写法（lexer 顶部 docstring「元数驱动参数收集」），词首必须切分；`输出` 等其余动词的语句用法恒带空格（`输出 结果`），词首后随汉字按复合名头并入（语料实证：输出结果 test_hashfs×5、输出格式、输出块表〔_P0A_MERGE_WHOLE 既有〕）。
- 词首**非动词**关键字（模块/标准库/函数…）：第一层最长匹配直接输出 KEYWORD（既有路径，规则未触及）。

**排除集** `_P0A_SUFFIX_SPLIT_KW = (_P0A_HARD_STMT - {'函数'}) | {'定义'}`（= 如果/那么/否则/否则如果/段落/类型/捕获/等待/定义）——这些「硬语句头」在词中/词尾必须保持既有切分，均由单测/语料实证：
- `等于空那么` 的 `那么`（连接词：`若 甲 等于空那么：`，test_lexer_compound_safe_alignment 契约）；
- `除类型错误` 的 `类型`（类型 定义语句头，同上契约）；
- `自定义表` 的 `定义`（lightharness/src/权限.light 语料，`属性 自定义表 等于 空`）。

`函数` 是排除集中唯一例外：`X函数`（处理函数/统计函数增强/回调函数）是高频名词性复合名，后缀必须并入。

## 三、验证结果

1. **全语料token零变化**：断裂态（git HEAD e99bdb80，含两张表）vs 修复态（无表），765个.light文件token序列**逐文件零差异**（初版规则曾有1文件差异——`权限.light` 的 `自定义表`，HEAD下被切成 自+定义+表 三段，新规则合并为整词；经编译管线验证**AST完全一致**后，通过把 `定义` 纳入排除集收敛为严格零变化）。
2. **单测契约全过**：tests/test_lexer.py + tests/unit/test_lexer*.py 五文件 = **9 failed / 58 passed / 140 subtests，与 HEAD 基线完全一致**（9个失败为既有噪音）；其中 identifier_safe 四个契约测试（test_identifier_safe_module_print_merged_inside_word / in_real_statements / still_keyword_at_word_start / merge_keeps_embedded_keyword）**4 passed / 15 subtests 全绿**——`我的标准库` 单测契约由规则天然满足。
3. **反跑 ALL OK**：lightharness/_antirun_r23_t2_IDENTIFIER_SAFE清表.py —— A 基线自检 / B 断裂态vs修复态语料零变化 / C 契约正向控制（并入6词+词首切分4词+嵌入守卫3例）/ D 打印语句词首，ALL OK（输出 _r23_t2_antirun_out.txt）。
4. **运行期自校验**：lightharness/examples/test_R23_IDENTIFIER_SAFE后缀位置.light **rc=0**（后缀并入6形态+词首切分+嵌入运算符+字典键/列表/嵌套形参/ASCII混合边界）。
5. **全量CI**：lightharness pytest 全量 **552 passed**（含本轮新增 5 个 .light 用例与 2 个 pytest 文件，8分50秒）+ **冒烟 5/5**（test_会话/代理/工具/消息/流），全部通过（2026-09-14 22:01，日志 _r23_pytest_v.log；ci_test.py 整合模式曾因同机并发进程堆积挂起一次，终止后直跑 pytest+smoke 复核通过）。注：合并态含任务1（TAM清表）与任务3（CCW 184→37 内建名迁移）变更，合并态下全语料 token 仍与 HEAD 零差异（反跑 B 判据）。

## 四、逐条验证结果表（5条 → 规则覆盖路径）

| 条目 | 依赖场景（第22轮证据） | 规则覆盖路径 |
|---|---|---|
| 函数 | F3示例.light 导出名 统计函数增强（词尾） | 后缀规则（函数∉排除集） |
| 打印 | L2_wenyan 主程序/学生模块、test_iface：可打印（词尾） | 后缀规则（打印∉排除集；词首由 _P0A_STMT_SPLIT_VERBS 切分） |
| 标准库 | 单测契约 我的标准库（词中） | 后缀规则 |
| 模块 | L2_wenyan 主程序：学生模块（词尾） | 后缀规则（词首非动词→第一层切分，模块甲 契约 ✓） |
| 输出 | test_hashfs：输出结果（词首动词复合名头） | 词首动词合并分支（输出∉_P0A_STMT_SPLIT_VERBS） |

SUFFIX_ONLY 3条：词首切分语义由"词首不满足 scan_pos>0"天然保证，词中/词尾并入由后缀规则保证，无需单独表。

## 五、设计权衡记录（供路M审阅）

- **`打印` vs `输出` 的词首分歧是不可消解的词汇事实**：两者同为 print 语句动词（code_generator.builtin_map 均映射 print），但语料要求 `输出X`（输出结果/输出格式）词首合并、`打印X`（打印甲，一等无空格语句）词首切分。任何位置/长度/语义判据都无法区分二者，故以**单词类别集合** `_P0A_STMT_SPLIT_VERBS={'打印'}` 落地——这是从"5词白名单"到"1词语句动词标记"的收敛，且语义明确（"无空格语句一等写法的动词"）。若后续轮次希望彻底归零，需语言层面裁决 `输出X` 无空格形态的合法性。
- **初版宽规则的两个教训**（已收敛）：①排除集缺 `那么`/`类型` → 3个单测契约立红（`如果…那么…` 连接词、`类型` 定义头）；②`定义` 未排除 → 权限.light 1文件token漂移（AST等价但破坏零变化判据）。最终排除集 9 词全部有测试/语料实证。
- 与任务1（_TRAILING_ALIAS_MERGE 清表）区域相邻不重叠：本任务未触碰 `己` 的引用分支（行2742/2893 附近 TAM 引用保持原状，由任务1处置）。

## 六、测试适配说明（mutex 边界披露）

tests/unit/test_lexer_p0a_deterministic.py::test_清空白名单后仍整体成词 直接 monkeypatch `lexer.IDENTIFIER_SAFE_KEYWORDS`，集合删除后 AttributeError。已做最小适配（删去对该集合的清空/恢复，保留 CCW 清空与全部断言）——该文件不在任何任务的互斥区内，且此改动是清表的必然伴随。diff 共 2 处 6 行。
