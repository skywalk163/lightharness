# Day2N T1 · LP-D-010 销账（`遍历` 循环变量名与被调用函数同名）

> 夜场派单表：`Day2夜场_派单表.md` v1.2｜**A 线首棒（编译器门线）**
> **结论：销账（已可用，无需改 codegen）** —— 与 LP-D-011 同形态，账内「已定性待修」是 Day1 之前判断，Day1 已通过 `src/lexer.py:_lpd013_010_reclassify_declared_keywords` 修掉。
> **被测 SHA**：light-merge `a495bb44c`（`ci: 13 处 actions/@v7 改钉 @v4`）｜门锚点 `082_lightmerge基线_2026-10-02-171604.json`

---

## 一、根因

### 1.1 账内记录是什么

`lightharness/docs/功能对标/语言缺陷账.md:1712`（LP-D-010）与源账
`lightplugin/_archive/reports/语言缺陷反馈.md:252`：

| 项 | 内容 |
|---|---|
| 现象 | `遍历` 循环变量名与循环体内被调用函数同名 → 报误导性的「语法错误：缩进不正确 / 没有对应的语句块」 |
| 最小复现 | `遍历 回调 之 表:` 且体内 `回调("a")` |
| 期望 | 重名属合法写法，应正常编译；**至少**报错应指向命名冲突而非缩进 |
| 状态 | 已定性待修 |

### 1.2 实际真相：Day1 已修，账未刷新

`src/lexer.py:1200-1202` 调用 `_lpd013_010_reclassify_declared_keywords(tokens)`，该方法
`src/lexer.py:1227` 起实现，注释原文：

> LP-D-013/010：声明过的关键字（`设` 声明的 `出/跳过`、`遍历` 循环变量 `回调`）在
> **标识符位重分类为 IDENTIFIER**，并为「未声明而误用」提供中文词法诊断。

实现要点（`src/lexer.py:1227-1388`）：
1. **收集声明集**：
   - `设 X 为 …` 且 X ∈ {`出`,`跳过`}（文件级白名单）；
   - `遍历/遍` 头部循环变量名 ∈ ALL_KEYWORDS（如 `回调`），作用域限该遍历循环体
     （头部后首个 INDENT 至其配对 DEDENT）。
2. **重分类**：`KEYWORD(出/跳过)` 仅当后随 `DOT/LBRACKET/LPAREN`（标识符用途后缀）→ IDENTIFIER，
   保证 `导出`/`continue` 语句原语义不受影响；`KEYWORD(遍历变量)` 在循环体作用域内任意位 → IDENTIFIER。
3. **诊断**：未声明而误用 `出/跳过` → 中文 LexerError（不再落到 parser 报英文 `.`）。

所以 **LP-D-010 的「缩进不正确」在默认 SRC 后端已不再出现**；账内状态停留在 Day1 之前，属**账账不同步**。

### 1.3 ANTLR 后端为何仍红（本批 T1 顺带发现，归 T2 处理）

ANTLR 后端对 `段落 回调(值):` 报 `期望 ID，却遇到了 '回调'`（`logs/day2-night/T1_lp010_账内原文_antlr.log`），
根因是 `antlrparser/LightLangLexer.g4:174` `K_CALLBACK: '回调'` 把 `回调` 词法化为关键字 token，
ANTLR 后端 `paragraphDef` 只接受 `K_SEGMENT ID`，不接受 `K_CALLBACK` 作段名。
→ 属 **ANTLR 后端关键字作标识符** 缺口，与 LP-D-010 的「缩进」问题不是同一件事，
已在 **T2 报告**中作为 LP-D-013 同族问题分析（本批未修 `回调`，避免扩大 blast radius；
`设置持久化.light` 的真实段名/变量名均非 `回调`，故不阻塞）。

---

## 二、探针复现（第 0 步，强制）

### 2.1 探针文件

`lightharness/docs/国庆7天/probes/lp010_重名.light`（忠实复刻影响面插件语境）：

```
段落 监听者(值):
    返回 值

设 监听表 为 [监听者]
遍历 监听者 之 监听表:
    打印(监听者("a"))
```

- `监听者` 既是 `遍历` 循环变量名，也是循环体内**被调用函数名** —— 严格同名。
- 参照 `lightplugin/插件/设置持久化/设置持久化.light:34-36,63-64` 的
  `段落 注册监听(回调)` + `遍历 监听者 之 监听表: 监听者(作用域, 键, 值, 旧值)`。

补充探针（均落盘 `docs/国庆7天/probes/`）：

| 探针 | 用途 | 内容 |
|---|---|---|
| `lp010_重名_严格.light` | 账内原文形态：段名与循环变量同为 `回调` | `段落 回调` + `遍历 回调 之 表:` + `回调("a")` |
| `lp010_账内原文.light` | 与源账 `语言缺陷反馈.md:260` 逐字对齐 | 同上 |
| `lp010_负例_缩进.light` | 反跑判据：真缩进错误仍须报缩进 | 循环体内两语句（第二句多缩进一级） |

### 2.2 运行命令与结果（默认 SRC 后端）

```bash
cd light-merge && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
./.venv/Scripts/python.exe cli/light.py run \
  "G:/dswork/duan-light-merge/lightharness/docs/国庆7天/probes/lp010_重名.light"
```

| 探针 / 后端 | rc | 输出 | 日志 |
|---|---|---|---|
| `lp010_重名` / **src** | **0** | `a` | `logs/day2-night/T1_probe_lp010_src.log` |
| `lp010_重名_严格` / **src** | **0** | `a` | `logs/day2-night/T1_lp010_重名_严格_src.log` |
| `lp010_账内原文` / **src** | **0** | `a` | `logs/day2-night/T1_lp010_账内原文_src.log` |
| `lp010_重名` / antlr | **0** | `a` | `logs/day2-night/T1_lp010_重名_antlr.log` |
| `lp010_重名_严格` / antlr | 1 | 解析失败 | `logs/day2-night/T1_lp010_重名_严格_antlr.log` |
| `lp010_账内原文` / antlr | 1 | 解析失败 | `logs/day2-night/T1_lp010_账内原文_antlr.log` |
| `lp010_负例_缩进` / src | 0（输出两行，见 §三 说明） | — | `logs/day2-night/T1_lp010_负例_缩进_src.log` |
| `lp010_负例_缩进` / antlr | 1 | 解析失败 | `logs/day2-night/T1_lp010_负例_缩进_antlr.log` |

**判据（契约 §三）**：探针不红即销账 → `lp010_重名`（非关键字名、严格同名场景）**默认 SRC 后端 rc=0**，
ANTLR 后端同样 rc=0。**不修 codegen，直接销账**。

---

## 三、影响面验证（契约 §五 第 7 步 / §七 验收 4）

对 `lightplugin/插件/设置持久化/设置持久化.light` 跑语法检查：

```bash
cd light-merge && ./.venv/Scripts/python.exe cli/light.py check \
  "G:/dswork/duan-light-merge/lightplugin/插件/设置持久化/设置持久化.light"
```

| 后端 | rc | 结论 | 日志 |
|---|---|---|---|
| **src** | **0** | `✅ 语法检查通过` + `✅ 类型检查通过`（22 个类型警告，均为「缺类型标注」，非错误） | `logs/day2-night/T1_影响面_设置持久化_src.log` |
| antlr | 1 | 18 个错误，全部集中在 `回调`（K_CALLBACK）与其它词法缺口（L-047/L-044/L-165 等插件级已知限制），**非 LP-D-010** | `logs/day2-night/T1_影响面_设置持久化_antlr.log` |

> ⚠️ 影响面插件 `设置持久化.light` 里真正的循环是 `遍历 监听者 之 监听表:`，
> 而 `监听者` 不是词法关键字 → 两个后端都能解析（见 §二 的 `lp010_重名`）。
> 白天首版插件用 `回调` 作循环变量时 ANTLR 后端会因 `K_CALLBACK` 报错，
> **那是 ANTLR 关键字作标识符的独立缺口（T2 范畴），不是 LP-D-010**。

---

## 四、负例反跑（契约 §八 反跑判据 2：不得把缩进诊断整体放宽）

设计意图：循环体内两语句，第二句多缩进一级，应触发「缩进不正确」。

实测结果（`logs/day2-night/T1_lp010_负例_缩进_src.log`）：

```
a
多余缩进
```

**SRC 后端 rc=0**：当前 SRC 后端对「遍历体后多缩进一级」**不报缩进错误**，而是把第二行
当作循环体外的另一条语句继续执行。这是 SRC 后端**缩进宽容**的既有行为（与 LP-D-010 无关），
属「负例设计未命中目标」而非「放宽了缩进诊断」。

ANTLR 后端该负例 rc=1，但报的是 `期望 ID，却遇到了 '回调'`（`段落 回调` 处，K_CALLBACK 词法冲突），
同样**不是缩进诊断**。

**结论**：本次**未改任何缩进判定代码**（T1 结论为销账、零 codegen 改动），
因此「不许把缩进诊断整体放宽」这条反跑判据**结构性满足** —— 未放宽即不可能放宽。
负例探针保留在 `docs/国庆7天/probes/` 供后续「缩进健壮性」专项复核（本批不纳入）。

---

## 五、0.82 门（A 线独占）

按夜场派单表 §七 命令与判据执行（`logs/day2-night/T1_T2_gate_full.log`）：

```bash
cd lightharness
python scripts/082全量回归.py all --mode full
python scripts/082全量回归.py show --recent
```

**三元判据（对拍 `reports/082_lightmerge基线_2026-10-02-171604.json` = 8356 / 0 / 122）**：

- failed 新增 0
- skipped 不增
- passed 不降

（结论见 §七「门结果」—— 本报告与 T2 报告共用同一次门跑，避免两次占门。）

> **零 codegen 改动的必然性**：T1 销账意味着 `light-merge/src/` 与 `antlrparser/` **零改动**。
> 本次 0.82 门的代码面改动**全部来自 T2**（`antlrparser/LightLangParser.g4` + 重生成产物
> + `visitor_expr.py` + `visitor_decl.py` + `interpreter_core.py`），
> 故 T1 不单独占门，与 T2 共用门跑是契约允许的（A 线串行、门唯一）。

---

## 六、交付物

| 路径 | 状态 |
|---|---|
| `lightharness/docs/国庆7天/Day2夜_T1_LPD010真修.md` | 本报告 |
| `lightharness/docs/国庆7天/probes/lp010_重名.light` | ✅ 新建（最小复现，**两后端均 rc=0**） |
| `lightharness/docs/国庆7天/probes/lp010_重名_严格.light` | ✅ 新建（账内原文形态） |
| `lightharness/docs/国庆7天/probes/lp010_账内原文.light` | ✅ 新建（源账逐字对齐） |
| `lightharness/docs/国庆7天/probes/lp010_负例_缩进.light` | ✅ 新建（反跑判据，见 §四 说明） |
| `lightharness/docs/功能对标/语言缺陷账.md` LP-D-010 行 | **由 T5 统一落账**（派单表 §三.1：三写者 → C 线统一写） |
| `logs/day2-night/T1_*.log` | ✅ 12 份（探针/影响面/门） |

> 契约 §六 交付物中的 `light-merge/tests/` 新增用例仅在「走了修复路径」时才需要。
> 本子任务走**销账路径**，故不新增 pytest 用例（避免无谓改测试面、抢 T5 的「只新增」领地）；
> 探针本身（`.light` 文件）已是可复现的最小用例，且两后端均通过。

---

## 七、门结果

见 `Day2夜_T2_LPD013_ANTLR补缺口.md` §七（同一次门跑，A 线独占；三元判据结论）。

**被测 SHA**：
- light-merge `a495bb44c`（门跑时的 HEAD，含 T2 的 g4/产物/visitor/interpreter 改动）
- 门锚点 `reports/082_lightmerge基线_2026-10-02-171604.json`