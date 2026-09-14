# 任务2 交付报告：上下文敏感切词（非语句起始位置最大匹配）

> 任务来源：`复刻_第21轮_任务prompt分发_词法确定性切词重构轮.md` 任务2（P0，核心）
> 日期：2026-09-14
> 修改文件：`light-merge/src/lexer.py` — `_OPERATOR_KEYWORDS`（新增集合）+ 新增辅助方法 `_at_statement_start` + `_tokenize_chinese_sequence` 内新增分支（互斥区域内，未修改预扫描与保护表）
> 状态：**实现完成；反跑 ALL OK；语句起始/运算符/整串关键字三条闸门不变**

---

## 一、现状与缺口

- 第19/20轮已落地 **P0-A 确定性模式（`deterministic=True` 默认）** 与 `_EMBED_MAX_MATCH_KEYWORDS={'为','返回','尝试'}` 嵌入最大匹配；`_scan_user_definitions` 已登记的名字（段落名/设名/导出名）整体成词。
- **剩余缺口**：**未登记**的关键字前缀标识符（如独立表达式里的 `去重占位`）在表达式上下文中仍会被按关键字边界切碎 → `KEYWORD:去重` + `IDENTIFIER:占位`。
- 第20轮已验证：把合并泛化到「全部非运算符关键字」会引发 **104 个解析回归**（`接收参数`/`如果条件` 等合法「关键字+名」结构被误并）——故必须做**上下文敏感**而非无脑泛化。

## 二、实现（三处改动）

### (1) 新增 `_OPERATOR_KEYWORDS`（表达式中仍须按运算符切分的关键字）

```python
_OPERATOR_KEYWORDS = frozenset(OPERATOR_VERBS) | frozenset({
    '与', '或', '且', '非',            # 逻辑
    '在', '为', '之', '于',            # 关系/连接
    '等于', '不等于', '大于', '小于', '大于等于', '小于等于', '不大于', '不小于', '包含',
})
```

### (2) 新增 `_at_statement_start(source, pos)`

语句起始位置 = 向左跳过**行内空白**后落在 文件开头 / 换行 / 冒号（`:`/`：`）。
**刻意不含** `{` `[` `(` `,` —— 这些是**表达式语境**（`{去重占位:1}` 的字典键、`[筛选器]` 的列表元素），须允许整体成词。

### (3) `_tokenize_chinese_sequence` 内新增「关键字前缀标识符整体成词」分支

位置条件**二选一**：整串后紧随 `(`（函数调用语境，与第20轮 `_emb_iscall` 同口径）**或** 非语句起始位置。三条闸门缺一不可：

```python
if (len(full_identifier) > 1
        and full_identifier not in _ALL_KEYWORDS_WITH_VERBS      # ① 整串恰是关键字 → 不处理
        and full_identifier not in user_definitions             #    已登记名 → 交既有分支
        and full_identifier not in _common_compounds):          #    复合词 → 交既有分支
    _ctx_tail = pos + len(full_identifier)
    _ctx_call = _ctx_tail < n and source[_ctx_tail] == '('
    if _ctx_call or not self._at_statement_start(source, pos):
        _lead_kw, _lead_len = _match_kw(source, pos)
        if (_lead_kw and 0 < _lead_len < len(full_identifier)    # ② 确有「更短关键字前缀」
                and _lead_kw not in _OPERATOR_KEYWORDS):         # ③ 前缀不是运算符关键字
            _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col)); …
            continue
```

**设计取舍（与任务书「先保守后扩大」一致）**：本实现比任务书描述的「非语句起始位置一律最大匹配」**更保守**——额外要求「词首存在关键字前缀」。理由：
- 无关键字前缀的汉字串，基础扫描本就不会拆分，无需本条兜底（避免扩大影响面）；
- 有前缀且前缀为运算符（`甲加乙` 的 `加`、`甲与乙` 的 `与`）时必须切分，故设第③闸门；
- 第20轮「104 回归」的教训表明**扩大合并范围是高危动作**，本轮严守窄口径，扩大留待后续轮次按需评估。

实现位置落在任务书建议的**第二处**（`_tokenize_chinese_sequence` 分支），未改 `_tokenize_identifier_or_keyword` 主流程。

## 三、验证标准逐条对齐

| 验证标准 | 结果 | 证据 |
|---|---|---|
| 1. 表达式上下文关键字前缀标识符不被切碎（`去重占位(名单)`/`作用域匹配(...)`/`断言为真(...)`） | **PASS** | pytest `tests/test_R21_上下文敏感切词.py` A判据 7 例；`examples/test_R21_上下文敏感切词.light` rc=0 |
| 2. 语句起始位置关键字不受影响（`如果条件`/`接收参数`/`返回值`） | **PASS** | B判据 4 例（`如果条件:`/`当条件:`/`遍历甲之列表:`/`否则若条件:`）+ 无空格写法 `设x为10`/`打印甲` |
| 3. 运算符关键字在表达式中仍按关键字切分（`甲与乙`/`甲或乙`/`非甲`） | **PASS** | C判据 6 例（与/或/加/减/在/大于） |
| 4. 全量 CI 无回归 | **PASS** | 见第六节 |
| 5. 第19/20轮反跑 ALL OK | **PASS** | 见第五节 |

附加守卫：整串恰是关键字时仍作 KEYWORD（`打印(甲)`/`返回(甲)`/`如果(条件)` 各 1 例通过）。

## 四、反跑判据（`_antirun_r21_t2_上下文敏感切词.py`）

```
lexer.py 原始 sha256=25b211f64769
[A] 断裂态 表达式切碎 (KEYWORD:去重 出现)  PASS
    KEYWORD:设|IDENTIFIER:结果|KEYWORD:为|KEYWORD:去重|IDENTIFIER:占位|LPAREN:(|LBRACKET:[|…
[C] 断裂态 语句起始仍正确  PASS
[B] 修复态 表达式整体成 IDENTIFIER  PASS
    KEYWORD:设|IDENTIFIER:结果|KEYWORD:为|IDENTIFIER:去重占位|LPAREN:(|LBRACKET:[|…
[C] 正向控制：语句起始/运算符/括号关键字不变  PASS
[D] 运行期 examples/test_R21_上下文敏感切词.light rc=0（期望 0）  PASS
[E] 交叉 examples/test_R21_L152嵌套段落形参.light rc=0（期望 0）  PASS
[恢复] lexer.py sha256=25b211f64769（期望 25b211f64769）  PASS
ALL OK
```

- **[A]** 停用本块（`if (False and …)`）→ `去重占位` 被切成 `去重`+`占位`，本块确为必要。
- **[B]** 恢复后整体成 `IDENTIFIER:去重占位`。
- **[C]** 语句起始 / 运算符 / 括号关键字三类正向控制全部不变。
- **[D]/[E]** 运行期与交叉（任务1 不被破坏）均绿。
- **[恢复]** 字节级 sha256 复原。

## 五、既有修复交叉验证

- **任务5 报告订正**：并行产出的 `_task5_R21_全量回归扫描报告.md` 中 B 判据记为 `WAIT（待任务2）`，其结论写于任务2 落地**之前**。任务2 现已落盘，B 判据应转 PASS；重跑 `_antirun_r21_t5_全量回归扫描.py` 即可自动识别（其 B 判据为软标注）。
- **R20 反跑**：`_antirun_r20_t1_词法关键字前缀.py` / `_antirun_r20_t2_HMAC标准实现.py` 见第六节复跑结果。

## 六、全量 CI（pytest + smoke）与反跑复跑

命令（lightharness 根）：`LIGHT_MERGE=G:/dswork/duan-light-merge/light-merge python scripts/ci_test.py`

| 运行 | pytest | smoke | 结论 |
|---|---|---|---|
| 基线（T1+T2，任务3 精简前） | **1 failed / 475 passed**（1085.4s） | 5/5 | 唯一红 = `test_审批.light` 用例12d **时序 flake（R20-C）**，非本轮引入 |
| T1+T2+T3（精简后，最终态） | **476 passed / 0 failed**（1142.6s，exit 0） | **5/5** | **全部通过** ✓ |

`test_审批.light` 归因：文件未改；单独复跑 20/20 通过；与 HEAD 词法器交错各 10/10 通过 → 负载敏感墙钟断言抖动；精简后那次未复现。

**反跑复跑明细**（全部串行、逐次 sha256 复原）：

| 反跑 | 结果 |
|---|---|
| `_antirun_r21_t1_预扫描重构.py` | **ALL OK** |
| `_antirun_r21_t2_上下文敏感切词.py`（本任务） | **ALL OK** |
| `_antirun_r20_t1_词法关键字前缀.py` | **ALL OK**（本轮订正断裂态锚点，见任务3 报告） |
| `_antirun_r20_t2_HMAC标准实现.py` | **ALL OK** |
| 第19轮 6 反跑 | **ALL OK ×6** |

## 七、交付物

- `light-merge/src/lexer.py`（`_OPERATOR_KEYWORDS` + `_at_statement_start` + `_tokenize_chinese_sequence` 分支 + 注释）
- `lightharness/examples/test_R21_上下文敏感切词.light`（rc=0）
- `lightharness/tests/test_R21_上下文敏感切词.py`（23 passed）
- `lightharness/_antirun_r21_t2_上下文敏感切词.py`（ALL OK）
- 本报告

## 八、遗留与风险

1. **未做「非关键字前缀也整体成词」的泛化**：属任务书「逐步扩大」的下一档，未在本轮执行（扩大范围 = 高风险，第20轮 104 回归为前车之鉴）。
2. `设 X为 Y(`（无空格 `X为` + 调用）形态仍落 `_EMBED_MAX_MATCH_KEYWORDS` 既有路径（R20 已界定：整串后紧随 `(` → 函数名，不切分）；本块不作二次处理，避免互相干扰。用例构建时已规避该形态（改用条件表达式分支）。
3. 任务3 精简 `COMMON_COMPOUND_WORDS` 后，本块第 4 条闸门（`not in _common_compounds`）覆盖范围相应变化——已由任务3 反跑与全量 CI 复验无回归。
