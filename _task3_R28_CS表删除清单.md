# 第28轮 任务3：CS表残部2字（列/类）逐条验证删除清单 —— CS表清零

日期：2026-09-15 ｜ 结论：**列/类 全部移除，CS 表清零（`_COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset()`）**
验证脚本：`lightharness/_antirun_r28_t3_CS表删除.py`（清零确认：场景矩阵 + G1 全语料对照）
证据文件：`lightharness/_task3_R28_CS表2字逐条验证_证据.json`
前置：任务1（列 的 `_P0A_TAIL_CUT_SINGLE` 嵌入输出循环词尾切出反向规则）与
任务2（user_definitions 前缀匹配「余部单字并入」判据扩展至 CS∪HM∪DUAL，
`_R27_BCLASS` 全位置吸收）已落地。

---

## 一、删除字（2 字，G1∧G2∧G3 全通过）

### 列 —— 词尾切出反向规则覆盖

| 项 | 内容 |
|---|---|
| 打红场景 | `bootstrap/release/stdlib/断言工具.light:226` `对于元素在序列:`（无空格 for-in，Python 转译快照） |
| 基线行为 | `IDENTIFIER(序)+KEYWORD(列)+COLON`（列在"序列"词尾**切出** KEYWORD） |
| 撤CS后行为（无规则时） | 列∈F 词尾并入 → `序列` 整词（token 变化） |
| 覆盖规则 | `_P0A_TAIL_CUT_SINGLE = {'列'}`：**嵌入输出循环**（段内命中真关键字分段后）中，列在词尾（`scan_pos+sub_len==len(fi)`）+ 前导汉字 → 不跳过、落出 KEYWORD |
| 关键机制 | 切出只发生在嵌入输出循环（`甲在序列`/`甲之序列` 分段形态）；裸 `序列:`/`甲序列:`/`ESC序列:`（段内无真关键字，`embedded_found=False`）走整词出口不受影响 |
| 词首并入 | `列数/列表/列名` 由 HM 正面类别覆盖（G2 通过） |

### 类 —— 类声明上下文/user_definitions 前缀余部并入覆盖

| 项 | 内容 |
|---|---|
| 打红场景 | `lightharness/examples/test_L013.light:21` `设 独立 为 新建 独立类()`——**使用处**（非声明处） |
| 基线行为 | `IDENTIFIER(独立类)+LPAREN`（整词） |
| 撤CS后行为（无规则时） | 切成 `独立+类(`（词尾类落出 KEYWORD） |
| 覆盖规则 | user_definitions 前缀匹配「余部单字并入」判据从「仅 CS 锚」扩展为「CS ∪ HM ∪ DUAL」：`独立` ∈ user_definitions（段落名/设名预扫描）+ 余部 `类` ∈ 可构词单字 → 不拆分整词 |
| 声明处 | `类 独立类:`/`类 名称:`/`类 子类 继承 基类:` 在探针矩阵全部 OK（KEYWORD(类)+IDENTIFIER 整词），无需额外规则 |
| 词首并入 | `类别/类似` 由 HM 覆盖（G2 通过） |

**注**：R27 时期类 的打红定位为「`类 独立类:` 声明处」，R28 地面真相探针
（`_dbg_r28_ground.py`）逐 token 二分定位修正为「`新建 独立类()` 使用处」——
修正了 R27 删除清单中的场景描述，机制结论以本轮为准。

## 二、清零后自校验断言（lexer.py 文末，全部通过）

| 断言 | R28 口径 |
|---|---|
| ① | `CS == ∅`（空 frozenset） |
| ② | `_TRAILING_ALIAS_CLASS == F`（43 字，不变） |
| ③ | `HM − CS == _R26_CS_REMOVED ∪ _R27_CS_REMOVED ∪ _R28_CS_REMOVED`（= HM 22 字） |
| ④ | `_P0A_TAIL_CUT_SINGLE == {'列'}`（恒 1 字防漂移） |
| ⑤ | `_P0A_HEAD_MERGE_DUAL == 8 字`（恒 8 字防漂移） |

## 三、清零后全量确认

- 场景矩阵 10/10 全过（列三形态 + 类声明/关键字/继承/使用处，含两个打红形态钉）；
- G1 全语料 **839 文件可比（既有失败 2 排除）token 零变化** ✅；
- 3 个 .light 边界测试 rc=0；pytest 38 passed（R26+R27+R28 合跑 319 passed）✅。

## 四、CS 表八轮演化总览（R21→R28）

```
R21 前：52 字 → R22：30 → R23：30（三表白名单清零）
→ R24：30（真护栏确认）→ R25：30（词尾正面类别 F=43，CS 退化为词首锚）
→ R26：16（词首并入正面类别 HM=22）→ R27：2（DUAL=8 + L-119 等价）
→ R28：0（列 词尾切出反向规则 + 类 前缀余部并入扩展）✅ 清零
```
