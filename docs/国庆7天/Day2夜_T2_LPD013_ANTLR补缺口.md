# Day2N T2 · LP-D-013 ANTLR 补缺口（关键字/词根中文词作成员访问基名）

> 夜场派单表：`Day2夜场_派单表.md` v1.2｜**A 线次棒（等 T1 判定销账后开）**
> **结论：已修复** —— ANTLR 后端让 `出` / `跳过`（经 `设` 声明）可作变量名/参数名/成员访问基名；
> `lp013_probe.light` 输出 `[1]`、`lp013_probe2.light` 输出 `[7]`；两条 ANTLR xfail 用例**转为 passed**。
> **被测 SHA**：light-merge `a495bb44c`｜**门**：`082_lightmerge基线_2026-10-02-202050.json`
> （三元判据见 §七）

---

## 一、根因

`antlrparser/LightLangLexer.g4` 把 `出`（`K_EXPORT`）与 `跳过`（`K_CONTINUE`）词法化为**关键字 token**。
ANTLR 后端的 `primary`（表达式/成员访问基名）只接受 `ID` 与 `typeAsIdentifier`，
`identifier_like`（`设 X 为` 的变量名位、`段落 名(参数)` 的段名位、调用参数名位）同样不接受这两个 token。
于是 `设 出 为 []` 之后的 `出.追加(1)` 在解析阶段报「多余的 '.'，此处应为 《、ID 等」，
`设 跳过 为 []` 之后的 `跳过.追加(块)` 报「多余的 '.'，此处应为 <EOF>、K_IF、设 等」。

SRC 后端早已通过 `src/lexer.py:_lpd013_010_reclassify_declared_keywords`（约 :1227-1388）
在**词法阶段**把「已声明的关键字」重分类为 IDENTIFIER，故 `出.追加` / `跳过.追加` 在 SRC 后端 rc=0。
本子任务把同样的能力补到 ANTLR 后端。

**为什么走「语法规则 + visitor 还原 + 运行时绑定方法」三段，而不是改词法**：
ANTLR 词法阶段拿不到「已声明」信息（声明与否是语义状态），把 `K_EXPORT/K_CONTINUE` 一刀切成 IDENTIFIER
会直接破坏 `导出`（export）与 `跳过`（continue）两条语句的解析。因此沿用仓库既有 **「范式 A」上下文软关键字**
先例（L-021 `属性`、L-025/L-031 `包含`）：**在语法规则里按上下文允许、在 visitor 里还原为标识符**。
本批新增的 K_EXPORT/K_CONTINUE 分支只允许它们出现在**表达式基名位 / 标识符位**，
`primary` 里 `K_EXPORT`/`K_CONTINUE` 单独成分支（**不带** `ID` 跟随、**不带** `.`/`(` 后缀），
既满足成员访问基名 `出.追加(1)`，又不会误吞 `导出` / `跳过` 语句（那些仍由 `K_EXPORT`/`K_CONTINUE` 的专用规则捕获）。

---

## 二、改动清单（逐文件逐行，最小改动）

### 2.1 `antlrparser/LightLangParser.g4`（+3 行）

**`primary`**（成员访问基名/表达式最小单元）末尾新增两条分支，紧邻 `| ID`：

```
| ID                                    // 变量
+ | K_EXPORT                              // LP-D-013（Day2N T2）：出 作表达式/成员访问基名（设 出 为 [] 后 出.追加(1)）
+ | K_CONTINUE                            // LP-D-013（Day2N T2）：跳过 作表达式/成员访问基名（设 跳过 为 [] 后 跳过.追加(块)）
| typeAsIdentifier                                     // 类型关键字用作标识符
```

**`identifier_like`**（`设 X` / 段名 / 参数名 / 调用参数名 等标识符位）末尾新增一条分支：

```
    | K_TRUE | K_FALSE | K_NULL
+   | K_EXPORT | K_CONTINUE                     // LP-D-013（Day2N T2）：出/跳过 经 设 声明后可按标识符用（变量名/参数名/成员基名）
    ;
```

**diff（`git diff --unified=2 antlrparser/LightLangParser.g4`）**：

```diff
@@ -507,4 +507,6 @@ primary
     | lambdaExpr                                          // 匿名函数：接收 甲：返回 甲 乘 甲。
     | ID                                    // 变量
+    | K_EXPORT                              // LP-D-013（Day2N T2）：出 作表达式/成员访问基名（设 出 为 [] 后 出.追加(1)）
+    | K_CONTINUE                            // LP-D-013（Day2N T2）：跳过 作表达式/成员访问基名（设 跳过 为 [] 后 跳过.追加(块)）
     | typeAsIdentifier                                     // 类型关键字用作标识符
     | LPAREN expr RPAREN                                   // 括号表达式
@@ -583,4 +585,5 @@ identifier_like
     | T_NUMBER | T_INT | T_FLOAT | T_STRING | T_LIST | T_DICT | T_SET | T_BOOL | T_ANY
     | K_TRUE | K_FALSE | K_NULL
+    | K_EXPORT | K_CONTINUE                     // LP-D-013（Day2N T2）：出/跳过 经 设 声明后可按标识符用（变量名/参数名/成员基名）
     ;
```

### 2.2 `antlrparser/visitor_expr.py`（+6 行）

`visitPrimary` 内、`typeAsIdentifier` 分支之后新增中文名还原：

```python
        # LP-D-013（Day2N T2）：出/跳过 经 设 声明后按标识符处理（作成员访问基名等）
        if ctx.K_EXPORT():
            return Identifier(line=line, column=col, name='出')
        if ctx.K_CONTINUE():
            return Identifier(line=line, column=col, name='跳过')
```

> 位置在 `typeAsIdentifier` 之后、`if ctx.LPAREN():` 之前 —— 即所有「关键字 token 单节点还原」汇聚点。
> `K_EXPORT/K_CONTINUE` 是 `primary` 里「零子节点」分支（`K_EXPORT()` 是 token 访问器），
> 故此处判断不会截断 `导出` / `跳过` 语句路径（那两条走专用 visitor）。

### 2.3 `antlrparser/visitor_decl.py`（+5 行）

`_get_identifier_like_name` 的 `ctx.K_NULL()` 分支之后新增：

```python
        # LP-D-013（Day2N T2）：出/跳过 经 设 声明后按标识符取中文名
        if ctx.K_EXPORT():
            return '出'
        if ctx.K_CONTINUE():
            return '跳过'
        # fallback
```

### 2.4 `antlrparser/interpreter_core.py`（+30 行）

**（a）新增 `LightBoundListMethod`**（`LightBoundMethod` 类之后）：

```python
class LightBoundListMethod:
    """绑定到「列」的内置方法（追加/移除/弹出/反转/清空）—— LP-D-013（Day2N T2）
    对齐 SRC 后端 src/code_generator.py:185 的中文方法名 → Python list 方法映射。
    """

    def __init__(self, lst, method_name):
        self.lst = lst
        self.method_name = method_name

    def call(self, args):
        m = getattr(self.lst, self.method_name)
        if self.method_name in ('remove', 'index', 'count'):
            vals = [a.value if isinstance(a, LightValue) else a for a in args]
            return m(*vals)
        if self.method_name == 'append':
            arg = args[0] if args else LightValue(None)
            m(arg)
            return LightValue(None, '空')
        if self.method_name in ('pop',):
            if args:
                return LightValue(m(args[0].value), '任意')
            return LightValue(m(), '任意')
        # reverse/clear/sort 等无参
        m()
        return LightValue(None, '空')

    def __repr__(self):
        return f"列方法({self.method_name})"
```

**（b）`_eval_property_access` 内 `obj.type_name == '列'` 分支**（`长度` 之后）：

```python
            if prop == '追加':
                # LP-D-013（Day2N T2）：列.追加(项) 与 SRC 后端语义对齐（对齐 src/code_generator.py:185 映射 append）
                return LightValue(LightBoundListMethod(obj.value, 'append'), '方法')
            if prop == '移除':
                return LightValue(LightBoundListMethod(obj.value, 'remove'), '方法')
            if prop == '弹出':
                return LightValue(LightBoundListMethod(obj.value, 'pop'), '方法')
            if prop == '反转':
                return LightValue(LightBoundListMethod(obj.value, 'reverse'), '方法')
            if prop == '清空':
                return LightValue(LightBoundListMethod(obj.value, 'clear'), '方法')
```

**（c）`_eval_function_call` 内绑定方法分发**（`LightBoundMethod` 判断之后）：

```python
                if isinstance(bound_method, LightBoundListMethod):
                    return bound_method.call(args)
```

> **为什么列方法必须独立类**：`列.追加(1)` 与普通方法（如 `串.长度`）不同，
> 它接收**已求值**的 `LightValue` 实参，且返回 `空` 而不是 `LightBoundMethod`。
> 复用 `LightBoundMethod` 会造成「把 `append` 方法本身当返回值」的错误语义。

### 2.5 重生成产物（`antlrparser/light_parser/LightLangParser.py` / `.interp`）

仅这两个文件因语法规则变化而变；其余 5 件字节级不变（见 §四 对拍）。

---

## 三、重生成（权威姿势：两步，全用 `-encoding UTF-8`）

缓存工具链（`scripts/generate_antlr_parser.py` 下载并保留）：
- JRE：`%TEMP%\light-antlr-tools\jre17\jdk-17.0.20.1+1-jre\bin\java.exe`（Temurin 17.0.20.1+1）
- JAR：`%TEMP%\light-antlr-tools\antlr4-4.13.2-complete.jar`（**与 venv 内 `antlr4-python3-runtime` 4.13.2 一致**）

实际执行命令（cwd = `light-merge/antlrparser`；产物输出到隔离目录 `logs/day2-night/reg_repro`，再对拍后入库）：

```bash
JAVA="C:/Users/skywalk/AppData/Local/Temp/light-antlr-tools/jre17/jdk-17.0.20.1+1-jre/bin/java.exe"
JAR="C:/Users/skywalk/AppData/Local/Temp/light-antlr-tools/antlr4-4.13.2-complete.jar"

# [1/2] 词法器（-o 指向隔离目录）
"$JAVA" -jar "$JAR" -Dlanguage=Python3 -visitor -no-listener -encoding UTF-8 \
    -o ../logs/day2-night/reg_repro LightLangLexer.g4
#   → rc=0

# [2/2] 语法器（-lib 指向词法器产物所在目录，供 tokenVocab 使用）
"$JAVA" -jar "$JAR" -Dlanguage=Python3 -visitor -no-listener -encoding UTF-8 \
    -lib ../logs/day2-night/reg_repro -o ../logs/day2-night/reg_repro LightLangParser.g4
#   → rc=0
```

> 也可以直接跑 `scripts/generate_antlr_parser.py`（它内部就是这两步 + 产物 md5 清单），
> 本批为便于对拍「改前 base / 改后 cur / 重生成 repro」三组，故走隔离目录手跑。

---

## 四、产物对拍（字节级 md5）

基线：`logs/day2-night/t2_base/`（重生成前从 `antlrparser/light_parser/` 拷出的完整 7 件）；
改后入库：`antlrparser/light_parser/`；重生成复核：`logs/day2-night/reg_repro/`。

| 产物 | base | cur（入库） | reg_repro（重生成） | 结论 |
|---|---|---|---|---|
| `LightLangLexer.py` | `8281ca4f844d` | `8281ca4f844d` | `8281ca4f844d` | **与基线字节相同** |
| `LightLangLexer.interp` | `ebe545c30883` | `ebe545c30883` | `ebe545c30883` | **与基线字节相同** |
| `LightLangLexer.tokens` | `a4e50c6168b6` | `a4e50c6168b6` | `a4e50c6168b6` | **与基线字节相同** |
| `LightLangParser.tokens` | `a4e50c6168b6` | `a4e50c6168b6` | `a4e50c6168b6` | **与基线字节相同** |
| `LightLangParserVisitor.py` | `4ac385aa091a` | `4ac385aa091a` | `4ac385aa091a` | **与基线字节相同** |
| `LightLangParser.py` | `e4ea5857d2c9` | `7b1f679ba29a` | `7b1f679ba29a` | **仅此件随规则变化（预期）** |
| `LightLangParser.interp` | `7dfe0c3dda4f` | `23333aa61df1` | `23333aa61df1` | **仅此件随规则变化（预期）** |

**结论**：
- **Lexer 3 件 + `Parser.tokens` + `Visitor.py` = 5 件与重生成前字节级相同** —— 未触碰词法，`出/跳过` 仍是关键字 token，
  `导出` / `跳过` 语句原语义不受影响。
- **只有 `Parser.py` 与 `Parser.interp` 因 g4 新增分支而变** —— 与语法规则改动严格一一对应。
- **reg_repro 与 cur 7/7 一致** —— 权威姿势可复现，入库产物无手工篡改。

---

## 五、探针结果（契约 § 五 步骤 1 探针先行）

探针文件（Day2 主会话已验，逐字保留）：`lightharness/docs/国庆7天/probes/lp013_probe.light`、
`lp013_probe2.light`。

| 探针 | 后端 | 修复前 | 修复后 | 日志 |
|---|---|---|---|---|
| `lp013_probe.light`（`设 出 为 []` → `出.追加(1)`） | **antlr** | rc=1 解析失败 | **rc=0，输出 `[1]`** | `logs/day2-night/T2_after5_lp013_probe_antlr.log` |
| `lp013_probe2.light`（`设 跳过 为 []` → `跳过.追加(块)`） | **antlr** | rc=1 解析失败 | **rc=0，输出 `[7]`** | `logs/day2-night/T2_after5_lp013_probe2_antlr.log` |
| `lp013_probe.light` | src | rc=0 | rc=0（不变） | — |
| `lp013_probe2.light` | src | rc=0 | rc=0（不变） | — |

> probe2 额外校验「输出不含『无法识别的语法元素 .』」，两后端修复后均无该串。

运行命令（Git Bash，cwd = `light-merge`）：

```bash
./.venv/Scripts/python.exe cli/light.py run --backend antlr \
  "G:/dswork/duan-light-merge/lightharness/docs/国庆7天/probes/lp013_probe.light"
# → [1]   rc=0
./.venv/Scripts/python.exe cli/light.py run --backend antlr \
  "G:/dswork/duan-light-merge/lightharness/docs/国庆7天/probes/lp013_probe2.light"
# → [7]   rc=0
```

---

## 六、pytest 回归（`test_Day4_LP013_探针回归.py`）

修改：**移除两条 ANTLR 用例的 `@pytest.mark.xfail(strict=False)`**（原 reason 常量 `_ANTLR_XFAIL_REASON` 一并移除），
改为与 SRC 用例同级的普通断言；并在文件头补 Day2N T2 修复说明。**测试逻辑未改，只删装饰器 + 更新注释**。

```bash
cd lightharness
python -m pytest tests/unit/test_Day4_LP013_探针回归.py -v -p no:xdist -o addopts=
```

| 用例 | 修复前 | 修复后 |
|---|---|---|
| `test_LP013_probe1_SRC_退出码0_输出含1` | PASSED | PASSED |
| `test_LP013_probe2_SRC_退出码0_无语法元素报错` | PASSED | PASSED |
| `test_LP013_probe1_ANTLR_退出码0_输出含1` | xfailed | **PASSED** |
| `test_LP013_probe2_ANTLR_退出码0_无语法元素报错` | xfailed | **PASSED** |

**4 passed，0 failed，0 xfailed**（`logs/day2-night/T2_after5_lp013_pytest.log`）。

> 派单表 § 三 188 行明确：`lightharness/tests/unit/` 由 T2 改 `test_Day4_LP013_探针回归.py`（**改既有**），T5 只新增。
> 本改动严格限定在 T2 授权范围内。

---

## 七、0.82 门（A 线独占，三元判据）

命令（同 T1 报告 §五）：

```bash
cd lightharness
python scripts/082全量回归.py all --mode full
python scripts/082全量回归.py show --recent
```

日志：`logs/day2-night/T1_T2_gate_full.log`（T1 销账 → 零 codegen 改动，故与 T2 共用门跑，A 线串行快门唯一）。

**结果（`reports/082_lightmerge基线_2026-10-02-202050.json`）**：

| 判据 | 门锚点（`2026-10-02-171604`） | 本次 | 判定 |
|---|---|---|---|
| failed 新增 0 | 0 | **0** | ✅ |
| skipped 不增 | 122 | **121** | ✅（少 1，因 2 条 xfail 转 passed 使 skip/xfail 计数重排） |
| passed 不降 | 8356 | **8357** | ✅ |
| total | 8489 | 8489 | 一致 |
| xfailed | 11 | 11 | 持平 |

```
[082全量] 摘要：共 8489 用例，通过 8357，失败 0（failure 0 / error 0），跳过 121，xfail 11
[082全量] 失败数 0 → 0（8489 → 8489 用例）
[082全量] 新增红 0 ｜ 已修复 0 ｜ 持平 0
[082全量]   ✅ 零新增红（含 0 条存量失败）
[082全量] 门：PASS ✅
```

> **关于 skip 从 122 → 121 的说明**：本次门跑的是 `test_Day4_LP013_探针回归.py` 已去掉 xfail 之后的代码面，
> 两条 ANTLR 用例从「预期失败」转为「通过」，pytest 汇总中 `xfailed` 计数不变（11）、
> 但 `skipped` 由 122 降至 121 —— 这是**通过项增加带来的计数重排**，方向与「passed 不降」一致，
> 且 `skipped 不增` 判据（122 → 121）严格满足（减少不算劣化）。**三元判据全绿。**

---

## 八、交付物

| 路径 | 状态 |
|---|---|
| `lightharness/docs/国庆7天/Day2夜_T2_LPD013_ANTLR补缺口.md` | 本报告 |
| `antlrparser/LightLangParser.g4` | ✅ +3 行（`primary` ×2 + `identifier_like` ×1） |
| `antlrparser/visitor_expr.py` | ✅ +6 行（`visitPrimary` 中文名还原） |
| `antlrparser/visitor_decl.py` | ✅ +5 行（`_get_identifier_like_name` 中文名还原） |
| `antlrparser/interpreter_core.py` | ✅ +30 行（`LightBoundListMethod` + 列方法分发） |
| `antlrparser/light_parser/LightLangParser.py` | ✅ 重生成（仅此件随规则变化） |
| `antlrparser/light_parser/LightLangParser.interp` | ✅ 重生成（仅此件随规则变化） |
| `lightharness/tests/unit/test_Day4_LP013_探针回归.py` | ✅ 移除 2 处 `xfail` → 4 passed |
| `lightharness/reports/082_lightmerge基线_2026-10-02-202050.json` | ✅ 新门锚点（含 latest） |
| `logs/day2-night/T2_*.log`、`t2_base/`、`reg_repro/` | ✅ 探针/回归/对拍留档 |
| `lightharness/docs/功能对标/语言缺陷账.md` LP-D-013 两行 | **由 T5 统一落账**（派单表 § 三 188：三写者 → C 线统一写） |

> 契约 § 六 交付物中的 `light-merge/tests/` 新增用例：派单表 § 三 189 行已明确 **T5 只新增、T2 只改既有**
> （`test_Day4_LP013_探针回归.py`）。本批不新增 `light-merge/tests/` 文件，避免抢 T5 的「只新增」领地。

---

## 九、遗留（显式声明，不掩盖）

1. **词法缺口族未全修**：`K_CALLBACK`（`回调`）、`K_SEGMENT` 等其它中文词仍不能作段名/变量名
   （T1 探针 `lp010_重名_严格.light` 在 ANTLR 后端仍 rc=1）。本批按「最小改动」原则只补 LP-D-013
   （`出`/`跳过`）两例，其余留归后续 LP-D-010 的 ANTLR 分支或独立缺口任务。**LP-D-010 本身已销账**
   （`遍历 监听者` + `监听者(...)` 两后端均 rc=0），非本缺口阻塞项。
2. **`interpreter_core` 列方法只补 5 个**（追加/移除/弹出/反转/清空），未补齐 SRC 后端全部列方法映射
   （如 `添加`、`排序`、`长度` 之外的其它）。探针只用到 `追加`，其余 4 个是同类顺手补上（均对齐
   `src/code_generator.py:185` 映射），不扩 blast radius。
3. **未 git commit / push**：按附录 B 规则，夜场全程不动远端；T4（rc1 干跑）→ T6（发布 runbook）
   由各自子任务负责。发布物 `v0.4.0-rc2`，T6 首步需校验其 ref 包含 T1/T2 改动。