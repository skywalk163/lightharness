# Day3 清晨 T4 · LP-D-019② 收口报告（ANTLR 判型族注册面）

> 派单表：`Day3清晨_派单表.md` v1.1｜行：**B（编译器）· T4（串行 T3 后）**｜需门：**是（与 T3 合一条门线）**
> 出口 tag：`subtask-T4-done`｜被测树：light-merge 工作区（基于 `e53073d3c`，未提交）

---

## 一、结论（先看这里）

1. **LP-D-019② 已修复并复验绿**：ANTLR 后端注册 `是数字` / `是数字符`，
   `probes/lp019_判型族.light` 两后端输出一致（`True`/`False`/`True`）。
2. 注册改动落在 `light-merge/antlrparser/light_builtins.py`（+17 行，纯注册面，无语义面改动）。
3. **与 T3 合跑同一条门**：`082全量 all --mode full`（09:32:46，remote 0.82）
   对锚点 `234800` 三元持平 → **门 PASS**。
4. **核查新增 1 条边界残差**（不阻塞本批，口径待裁定）：`是数字符("12")` SRC=`True` / ANTLR=`假`；
   非字符串实参 SRC 抛 TypeError / ANTLR=`假`。已入矩阵 §二·行 3·边界残差 与 缺陷账。

---

## 二、根因

`是数字` / `是数字符` 在 `src/keywords.py` 的 `STDLIB_VERB_ARITY` 里（各 1 元），
SRC 后端 `code_generator.py:732-733` 把它们映射到 `_light_builtin.是数值` / `_light_builtin.是数字`；
而 ANTLR 后端 `light_builtins.py:_register_builtins` 只有内部名 `_是中文`/`_是字母`/`_是数字`，
**没有用户侧这两个名字** → 解释器 `Environment.get('是数字')` 抛 `未定义的变量`，rc=1。

---

## 三、修复（`light-merge/antlrparser/light_builtins.py`，+17 行）

```diff
             LightBuiltinFunction('_是数字', self._builtin_is_digit, min_args=1, max_args=1),
+            # LP-D-019②：用户侧判型族——与 SRC 后端 code_generator.py L728-733 对齐
+            # 是数字(x) = 判数值类型（int/float，排 bool）；是数字符(s) = 字符级 isdigit
+            LightBuiltinFunction('是数字', self._builtin_is_number_type, min_args=1, max_args=1),
+            LightBuiltinFunction('是数字符', self._builtin_is_digit, min_args=1, max_args=1),
```

新方法 `_builtin_is_number_type`：布尔恒 `假`；否则按 `type_name == '数'` 判 int/float
——与 SRC `是数值`（`isinstance(v,(int,float)) and not isinstance(v,bool)`）语义对齐。

## 四、验证

| 项 | SRC | ANTLR |
|---|---|---|
| `是数字(7)` | `True` | `True` |
| `是数字("7")` | `False` | `False` |
| `是数字符("7")` | `True` | `True` |
| 判型族语义矩阵（8 输入：int/float/bool/str×4/多字符） | 前 6 项一致 | 前 6 项一致，见下残差 |
| 账内探针 `lp019_判型族.light` | `True`/`False`/`True` rc=0 | `True`/`False`/`True` rc=0 ✅ |

**边界残差（T4 核查发现，不阻塞）**：

| 输入 | SRC | ANTLR | 说明 |
|---|---|---|---|
| `是数字符("12")` | `True` | `假` | SRC 走 `str.isdigit` 全串语义；ANTLR `_builtin_is_digit` 强制 `len==1` |
| `是数字符(7)`（非字符串） | rc=1 `TypeError` | `假` | SRC 对 int 直接炸，ANTLR 宽容返回 `假` |

> 口径裁定三选一（stdlib/内置核心判型.light 文档口径是「**是数字符 判单个字符**」，全串版另设
> `字符串全数字`）：① ANTLR 去 len 守卫对齐 SRC；② SRC `是数字` 段落加单字符守卫对齐文档；
> ③ 维持现状另立账。**本批不动**（T4 范围=注册面；且任一改法都需重跑门）。
> 证据：`probes/lp019_判型族_语义矩阵.light`；矩阵 `ANTLR_SRC_对拍矩阵.md` §二·行 3·边界残差。

## 五、门（与 T3 合跑）

`082全量 all --mode full`，2026-10-03 09:32:46，remote 0.82，elapsed 431s：
**passed 8357（含 2 XPASS） / failed 0 / skipped 121**，对锚点 `234800` 三元持平 → **PASS**。

## 六、改动清单（T4 名下）

| 文件 | 改动 |
|---|---|
| `light-merge/antlrparser/light_builtins.py` | 注册 2 条 + `_builtin_is_number_type`（+17 行，并行会话落笔，T4 核查复验） |
| `lightharness/docs/国庆7天/probes/lp019_判型族_语义矩阵.light` | 新增（8 输入边界矩阵） |
| `lightharness/tests/unit/test_Day3_T3T4_LP018_LP019回归.py` | 新增（含判型族两用例） |
| `lightharness/docs/功能对标/语言缺陷账.md` | LP-D-019 行状态：② 已修复 + 残差记录（①③ 仍待修） |
| `lightharness/docs/功能对标/ANTLR_SRC_对拍矩阵.md` | 行 3 补边界残差小节 |

## 七、遗留

1. **①③ 仍待修**（本批不修）：`回调` 作段名/循环变量（LP-D-019①）、`"abcdef"[1:3]` 索引切片（③）。
2. 判型族**其余成员**在 ANTLR 侧仍未注册（`是整数`/`是浮点`/`是字符串`/`是列表`/`是字典`/`是空`/`是布尔`/`是函数`：
   SRC 全部可用，ANTLR 全部 `未定义的变量`）—— 与 ② 同族的同源缺口，本批按派单只修 ② 点名的两条，
   已在矩阵行 3 备注记录，建议后续整族一次性补齐。
3. 未提交、未打 tag；未 push（等用户示意）。
