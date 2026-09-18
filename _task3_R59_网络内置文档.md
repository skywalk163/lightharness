# R59 任务3 报告：stdlib 网络请求 + 内置清单 + 文档门（共 10 条）

> 执行：本机 Windows（.venv py3.13）定向 + 0.82（/usr/local/bin/python3.12）定向复核
> 工作目录：`light-merge` ｜ 未 commit、未 push（只改工作树）
> 结果：**10/10 目标条全绿；三个目标文件合计 54 passed，零新增红**

---

## 一、结论速览

| 子项 | 目标条数 | 结果 |
|---|---|---|
| 3A 网络请求（test_stdlib_phase3.py） | 5 | 实测已绿，**未改源码**（与 R58 归因有出入，见下） |
| 3B 内置清单（test_native_leg_capability.py） | 3 | 修 JSON 后全绿 |
| 3C 文档门（test_doc_examples_gate.py） | 2 | relabel 围栏后全绿 |

- 本机 py3.13：`tests/test_stdlib_phase3.py tests/unit/test_native_leg_capability.py tests/unit/test_doc_examples_gate.py` → **54 passed**。
- 0.82 py3.12（最新副本 `/tmp/r44-20260918-145026`）：同上三文件 → **54 passed，__RC__=0**。
- 一致性核验：本地与远程 `src/llvm/codegen_typed.py` md5 完全相同（`dbe9787b…2839c`），故 3B 的 evidence 行号在两端一致可信。

---

## 二、3A 网络请求 5 条（以实测为准，与归因有差异）

任务书归因称 `stdlib/网络请求.py` 有 5 个缺陷（`响应.是否成功`/`响应.文本` 是方法非 property、URL 编码 ASCII、拼接URL 只收 2 参、解析查询串调 `新建字典` 未导入）。

**实测**：当前工作树（与 HEAD R58 一致，`git diff` 为空）的 `stdlib/网络请求.py` 已全部具备正确形态：

- `class 响应` 的 `是否成功`、`文本` 均已是 `@property`；
- `编码URL` 走 `urllib.parse.quote(文本, safe='')`（UTF-8 百分号转义）；
- `拼接URL(*部分)` 已是变长参数；
- `解析查询串` 内联 `urllib.parse.parse_qs`，无 `新建字典` 依赖。

定向跑 5 条目标（URL编码解码/拼接URL/解析查询串/响应对象/HTTP错误响应）：**5 passed**。
全文件 `test_stdlib_phase3.py`：37 条全过。

**差异说明**：R58 归因来自 13:29 的远程旧快照 `/tmp/r44-20260918-132918`（早于 R58 commit 13:43）。当前工作树该文件已是修复后形态（最后一次改动为品牌清理 commit，非本任务引入）。按通用纪律第 7 条「以实测为准」，**本任务未改动 `stdlib/网络请求.py`**。建议路M 全量对拍时确认该 5 条在新鲜同步副本上为绿。

---

## 三、3B 内置清单 3 条（改 `docs/原生腿能力清单.json`）

### 3B-1 `test_内置函数清单与代码一致`
`codegen_typed.py::_gen_typed_builtin` 新增 20 个判型内置，JSON `builtin_functions` 未收录：
`is_bool / is_dict / is_float / is_int / is_integer / is_list / is_map / is_number / is_str / is_string` + `是列表 / 是数组 / 是字典 / is_dict / is_map / 是字符串 / is_str / is_string / 是数值 / 是数字 / is_number / 是整数 / is_int / is_integer / 是浮点 / 是浮点数 / is_float / 是布尔 / is_bool`（去重后 20 个）。
→ 已全部补录，`category=Type`。

### 3B-2 `test_内置函数证据行号可定位`
全部 413 条 builtin 的 evidence 行号集体漂移（codegen_typed.py 后续编辑所致）。
→ 脚本重定位：在 `_gen_typed_builtin` 行区间 **1851..3295** 内，按 `'name'`（带引号）首次出现行重写 evidence。**413/413 全部可定位，0 条落空**。判据要求「该行文本含该内置名」，首现行即满足。

### 3B-3 `test_运行时符号清单与代码一致`
代码新增 `strcmp`（`codegen_typed.py:686` `declare i32 @strcmp(ptr, ptr)`）未入 JSON。
→ 补录 `runtime_symbols`：`name=strcmp`、`evidence_declare=src/llvm/codegen_typed.py:686`、`evidence_define=C library (not in runtime_typed.c)`（strcmp 为 libc，runtime_typed.c 内仅调用无定义，与 `_setjmp`/`strlen` 同处理）、`category=String`。

### 计数同步
- `builtin_functions.count`：413 → **433**
- `runtime_symbols.count`：262 → **263**
- `test_JSON清单存在且结构完整` 的 count 双向咬合随之通过。
- 结果：`test_native_leg_capability.py` 全文件 **11/11 passed**。

---

## 四、3C 文档门 2 条（relabel 围栏，改 4 个 md）

实测新增 ROT **6 个**（与任务书「L1 有 6 个」略有出入——实为 L1 3 个 + 其余 3 文件各 1）：

| 文件 | 块内容 | 失败原因 |
|---|---|---|
| docs/L1_白话体语法规范_v4.0.md | 若/否 半角冒号单行 if | v7.0+ 不接受半角 `:` |
| 同上 | `遍[1,2,3]之为i:…` | 无「遍…之为」语法 |
| 同上 | FizzBuzz `遍范围…之为n:` 缩进块 | 同上 |
| docs/api/stdlib.md | `段落 声明函数 接收 …：文本…` 类型注解冒号 | 类型注解语法不符 |
| docs/llvm_backend_design.md | `尝试/捕获/异常变量/最终/结束` | 设计草案 try 伪语法 |
| docs/tutorials/进阶教程.md | `并行 { … }` 块 | 设计草案并行伪语法 |

这些块来自 v4.0 **设计草案期**（文档自述「正文写于 v4.0 设计期，当前实现 v7.0+，冲突以编译器为准」），是 Python 风格示意伪代码，并非可编译的 v7.0+ 示例。按门禁自身规约「**非代码块请改用 ` ```text ` 标签**」，将这 6 个块的开围栏由 ` ```light `/` ```光明 ` 改为 ` ```text `。

噪声 18→19：新增 1 个 PSEUDO 块（L1 赋值示例 `设甲=10…`，无扫描器认可的光关键字）。同一处理，relabel 为 ` ```text `。

**共改 7 个开围栏**（L1 4 处 + llvm_backend_design.md 1 + api/stdlib.md 1 + tutorials/进阶教程.md 1），逐行校验原值确为 ` ```light `/` ```光明 ` 后才替换，保留原缩进与行尾。
结果：`test_doc_examples_gate.py` **6/6 passed**（新 ROT=0、噪声回到 18、敌意块守卫、基线不虚高均通过）。

> 备注：未走「按基线登记 ROT」路径——门禁口径要求基线只降不升，relabel 伪代码体裁比新增基线 ROT 更贴合门禁设计意图。

---

## 五、改动文件清单（5 个，均为工作树修改，未 commit）

| 文件（绝对路径相对 light-merge/） | 改动 |
|---|---|
| `docs/原生腿能力清单.json` | 重录 413 条 builtin evidence 行号；补 20 个判型内置（count 413→433）；补 strcmp（count 262→263） |
| `docs/L1_白话体语法规范_v4.0.md` | 4 处开围栏 ` ```light ` → ` ```text `（行 207/229/321/523） |
| `docs/llvm_backend_design.md` | 1 处开围栏 ` ```光明 ` → ` ```text `（行 321） |
| `docs/api/stdlib.md` | 1 处开围栏 ` ```light ` → ` ```text `（行 32） |
| `docs/tutorials/进阶教程.md` | 1 处开围栏 ` ```光明 ` → ` ```text `（行 193） |

`stdlib/网络请求.py` **未改动**（3A 实测已绿）。

探针/脚本/日志已移档至 `lightharness/docs/历史存档/R59探针/`（`_r59_t3_probe.py`、`_r59_t3_update_json.py`、`_r59_t3_relabel.py`、`_r59_t3_remote.py` 及各 `.log`）。

---

## 六、风险与交接

1. **3A 五红**：本任务未改源码。若路M 新鲜同步后 0.82 全量这 5 条仍红，说明远程基线快照与本地工作树确有版本差，需主 agent 核对同步来源（本任务本地与 0.82 最新副本均已验证为绿）。
2. **JSON 重写**：仅动 `evidence` 行号字段 + 追加新条目，未改既有字段结构/顺序之外的语义；`indent=2`、UTF-8、`ensure_ascii=False`，与原文件格式一致。
3. **围栏 relabel**：只改开围栏语言标签，块内正文未动；被 relabel 的块本就是设计草案伪代码，不影响真实示例。
4. 未 commit、未 push；未触碰「不要动清单」中的任何文件。
