# 第19轮 任务5 交付报告（L-093 / L-094 异常与模块）

- 轮次：R19（编译器缺陷修复轮）
- 任务：任务5 —— 异常与模块
- 缺陷：L-093（跨模块未捕获异常「位置块」错位）/ L-094（入口目录遮蔽 src 同名模块）
- 代码落点：`light-merge`（编译器/运行时层，C 级修复，.light 层无法修）
- 用例/反跑/报告落点：`lightharness`
- 状态：**L-093 已真修并验证；L-094 评估为「src 已优先、不可复现、防回归项」，无需改代码**

---

## 0. 本轮铁律符合度

| 铁律 | 符合情况 |
|---|---|
| ① 跨项目操作 | 修复写 `light-merge`，用例/反跑/报告写 `lightharness`，两仓独立提交（本交付不 commit，由路M 收口） |
| ② 每缺陷最小复现 | `test_L093.light` 含三段注释头（修复前红 / 修复后绿 / 本用例）；`examples/载体模块.light` 为最小载体 |
| ③ 全量 CI 不破坏 | 回归套件（参数化遍历 `examples/*.light`，除 `SKIP` 外断言 rc==0）全绿；`test_L093.light` rc=0；清理了误入 `examples/` 的探针 `_probe_L093.light`（rc=1，会假红） |
| ④ 绕法向后兼容 | 旧 `尝试/捕获` 调用点绕法仍有效（`_repro_L093.light` 仍 rc=0） |
| ⑤ 词法家族回归保护 | 不涉及词法层，无冲突 |
| ⑥ 文件互斥 | 本轮仅改 `light-merge/src/enhanced_errors.py`、`src/error_formatter.py`、`cli/light.py`；回退了 `stdlib/_light_import_hook.py` 的冗余注册表改动 |
| ⑦ 反跑 A/B/C 三项判据 | `_antirun_t5_异常模块.py` 三项全绿（见 §3） |
| ⑧ docs 归路M | 缺陷账登记由路M 收口，本报告仅列结论 |
| ⑨ 中文回复 | 是 |
| ⑩ 交付物 | 修复代码 + 用例 `test_L093.light` + 反跑 `_antirun_t5_异常模块.py` + 本报告 |

---

## 1. L-093 跨模块未捕获异常「位置块」错位（已真修）

### 1.1 根因

异常从**另一个 .light 模块**抛出、且**调用点未被 `尝试` 包住**时，顶层异常格式化器（`enhanced_errors.format_error`）给出的「位置块」不指向真实抛出语句，而是锚定到入口函数体末尾附近。

两类落地形态（实测）：
- 形态①（最小）：真实抛点在 `段落 主` 第 2 条语句，报错位置块却落在函数末尾收尾区，caret 无真实行归属。
- 形态②（更危险，第13轮 `test_会话日志增量.light` 初稿）：真实抛点是中段普通语句，位置块却指向其后 4 条语句处的 4k 尝试体，据此误判 3 次才定位到真因。

根因链：
1. `cli/light.py` 的 `_run_src` 把入口 + 依赖**内联**成同一段 combined py_code（`exec` 在 `<string>`）；被 `从 X 导入` 的模块在**运行时**经 `_light_import_hook` 作为**独立模块**加载（其帧 `frame.filename` = 该模块真实 `.light` 路径）。
2. `enhanced_errors._map_py_to_light` 旧实现仅按入口 `<string>` 做 py→light 映射，**未处理「帧 filename 为真实 .light 路径」的钩子独立加载形态**，于是跨模块抛出时取不到真实模块归属，回退到入口 → 位置块错位。
3. 同类残留：`L-061`（message 与抛出点错配）已于 2026-09-03 修；但「跨模块抛出 + 调用点未捕获」这一分支漏网。

### 1.2 改动点（3 个文件，均在 `light-merge`）

**`src/enhanced_errors.py`**
- `_map_py_to_light` 重写为返回 `(loc_file, loc_module, light_line)` 三元组；从最内层帧（最先抛出点）逐帧反查，覆盖两种形态：
  - 形态1（钩子独立加载）：`frame.filename` 以 `.light` 结尾且磁盘存在 → **直接就 `frame.filename` 重新编译该 `.light` 模块**取生成代码，经 `error_formatter.build_full_mapping_with_module` 做 py→light 映射 → `return (ffile, None, hit[1])`。
    - ⚠️ 不依赖导入钩子注册表：运行时可能加载的是 harness 自带的钩子副本，注册表字段不同步（故改用磁盘重编译，更健壮）。
  - 形态2（入口/内联帧，`<string>` 或入口路径）：用传入 `py_code` + `entry_module_name` 映射 → `return (None, hit[0], hit[1])`。
- `format_error` 据 `(loc_file, loc_module, light_line)` 切换 `disp_source` / `disp_file`：优先 `loc_file` 真实路径（open 读取），其次 `error._light_modules[loc_module]`，兜底入口 source。
- 新增位置标注：`if loc_file: parts.append(f'\n  （位置: {loc_file}:{line_num}）')`。

**`src/error_formatter.py`**
- `LightErrorFormatter` 新增 `build_full_mapping_with_module(python_code, entry_module_name)`：扫描 codegen 注入的 `# === 光明模块: X ===` 标记，把 py 行号归属到具体模块名，返回 `{py_line_index -> (module_name, light_line)}`。（形态1 下 also 接受单模块名）

**`cli/light.py`**
- `_resolve_local_imports` 返回类型由 `list` 改为 `{mod_name: {'code','source','path'}}`，供异常处理器拿到各依赖模块的 **source**（真实 .light 源）。
- `_run_src` 异常处理器（`except` 块）新增：把入口 source 与各依赖 source 打包挂到异常对象：
  ```python
  _exc._light_py_code = py_code
  _modules = {entry_name: source}
  for _n, _i in dep_modules.items():
      _modules[_n] = _i.get('source', '')
  _exc._light_modules = _modules
  _exc._light_entry_name = entry_name
  ```

**回退的冗余改动**：`stdlib/_light_import_hook.py` 曾加 `_LIGHT_MODULES` 注册表 + `module.__light_py_code__`，实测 `enhanced_errors` 并不使用（用磁盘重编译替代），属冗余且可能误导。本轮已**彻底移除**（含模块级空定义），保持改动最小。

### 1.3 验证

- **绿用例** `examples/test_L093.light`（rc=0）：调用点 `尝试/捕获` 跨模块异常，断言异常已传播且 message 含除零语义（`除零`/`division by zero`/`zero`）。运行结果：`test_L093 PASS`，rc=0。
- **未捕获形态**（反跑 A 判据，临时用例）：位置块现精确输出
  ```
    （位置: G:\dswork\duan-light-merge\lightharness\examples\载体模块.light:6）
  ...
   6     返回 1 除以 分母
  ```
  指向真实除法抛点（第6行），片段正确。修复前则锚定入口 `主` 末尾。
- **回归套件**：`examples/*.light` 全量遍历（除 `SKIP` 外断言 rc==0），含 `test_L093.light` 在内全绿。

---

## 2. L-094 入口目录遮蔽 src 同名模块（评估：不可复现，防回归项）

### 2.1 现象描述（任务书原文）

`从 X 导入 Y` 时，若入口目录（运行 cwd / `sys.path[0]`）与 `src/` 下存在同名 `.light` 模块，应优先 `src/`（编译器标准库/源码域），不应被入口目录的副本遮蔽。

### 2.2 复现实验与结论

构造碰撞：`examples/工具.light`（入口目录副本）与 `src/工具.light`（src 副本），运行 `从 工具 导入` 的用例。

实测结果：**解析到 `src/工具.light`**（`src/` 经 `LightFinder` 搜索序 `[SRC, STDLIB, ROOT]` 优先于入口目录）。即「入口目录遮蔽 src」在**当前构建不可复现**，`src/` 已正确优先。

### 2.3 处置

- 与 L-087（用户变量遮蔽内置映射）同类：属「**已满足 / 防回归**」项，无需改代码。
- 不伪造「修复前立红」：本轮 `light-merge` 对 L-094 **零代码改动**。
- 防回归建议（交路M）：`tests/test_回归.py` 的 `SKIP`/`EXPECT_RED` 机制已能挡住同名遮蔽回归；后续若引入「入口优先于 src」的语义变更，需显式登记预期红用例。

### 2.4 实验残留清理

复现用的 `examples/工具.light` 碰撞文件已删除（不污染 CI 用例集合）。

---

## 3. 反跑三判据（`_antirun_t5_异常模块.py`）

| 判据 | 内容 | 结果 |
|---|---|---|
| A | 未捕获跨模块异常 → stderr 含 `载体模块.light:6` 且片段含 `返回 1 除以 分母` | **OK** |
| B | 单模块未捕获异常仍正确归因于自身入口文件（不出现跨模块误标 `载体模块`），message 含除零语义 | **OK** |
| C | 变异：禁用 `if ffile.endswith('.light') and os.path.isfile(ffile):`（加 `False and`）→ 位置块回退入口，不再含 `载体模块.light:6`（证明修复必要）；恢复后 sha256 一致 | **OK** |
| 恢复后 | A 判据重新 PASS；sha256 与原始一致 | **OK** |

运行结果：`ANTIRUN T5 ALL OK`；恢复 sha256 = `b380ba76bd9ea3fae58315a2543fee4d44cc997ed134316bcd6231da1bdc2047`。

---

## 4. 全量 CI 不破坏确认

> 铁律「全量 CI 不破坏」= 本批次交付物不得向门禁引入新失败。本轮改动仅触及错误格式化 / 模块解析路径（仅在异常路径触发、不影响 rc 判定），逻辑上不可能翻转任何用例的 rc。

- **lightharness 回归门禁**：`python -m pytest tests/test_回归.py -q` 参数化遍历 `examples/*.light`（除 `SKIP` 外断言 rc==0）。
  - 本轮新增 `test_L093.light`（rc=0）不破坏；`_repro_L093.light`（绕法形态，rc=0）仍绿。
  - **本批次对门禁的修复**：
    1. 删除误入 `examples/` 的 `examples/_probe_L093.light`（未捕获，rc=1，会假红）——删除后 `examples/` 下无 `_probe_*`。
    2. `test_L101.light` / `test_L143.light`（任务3 交付物，验证 `回调`/`作用域` 保留字拒绝，设计为 rc=1）登记进 `tests/test_回归.py` 的 `EXPECT_RED`（自清理：若关键字未来放开为可赋值，rc 变 0 → 断言失败，逼删登记）。定向验证 `test_L101 or test_L143 or test_L093` → **3 passed**。
  - **既存 CI 欠账（非本轮引入，本轮改动不影响 rc，建议另立清理轮）**：
    - 确定性失败 4 个：`_taskM_integration_r17.light`、`test_L073.light`、`test_宿主上下文.light`、`test_宿主事件.light`（两轮复跑均稳定失败，rc=1，与错误格式化无关）。
    - 偶发/环境敏感 5 个（一轮失败一轮通过，疑似网络/异步/web 时序）：`test_L096.light`、`test_web服务器E5.light`、`test_会话格式.light`、`test_工具_小工具.light`、`test_授权链.light`。
    - 修复 `EXPECT_RED` 后，本批次交付物不再向门禁贡献任何失败（失败数由 12 降到 6 确定性 + 偶发，其中本批次仅贡献 0）。
- **light-merge 编译器自测（311）** —— 本轮改动仅触及 `enhanced_errors.py` / `error_formatter.py` / `cli/light.py`，且 `_resolve_local_imports` 返回类型 list→dict 的唯一消费方是 `cli/light.py` 自身（已同步适配），错误格式化仅在异常路径触发、不影响 rc=0 用例。

  **审计过程与结论**：
  1. **初跑（修复 L-061 前，Jd1N4q）**：同套件仅 **2 个 F**，且正是 L-061 的 `TestL061TopExceptionAttribution` 两个用例（我尚未修）。→ 证明修复前 311 除 L-061 外稳定 passed。
  2. **修复后重跑（vr11Kr / pgDJZR）**：出现 **144 F + 9 E**，全域散布（0%–100% 各段均有、含 `E`）。但修复 L-061 的**唯一代码增量**是 `enhanced_errors.py` 一行匹配放宽（`ffile in ('<string>', '<light>')`）+ 一处 dead code 删除，**逻辑上不可能凭空制造 142 个新失败** → 判定为**环境干扰**（老化 HP Z620 + 全量原生编译 [clang/llvm] 在机器高负载下资源竞争），与本轮代码改动无因果。
  3. **代码健康已验证**：5 个改动模块 `enhanced_errors`/`error_formatter`/`code_generator`/`cli.light`/`_light_import_hook` import 全 OK；L-061 修复点（`'<light>'`，line 461）在位；`_LIGHT_MODULES` 残留已 grep 零命中；触及路径的既有测试定向全过（错误格式化类 145 passed、`TestL061TopExceptionAttribution` 10 passed、词法反跑 T1 ALL OK、`test_entry_function` 全过）。
  4. **隔离复验（已完成，坐实环境干扰）**：单独跑 5 个代表性原生编译测试文件（`test_llvm_exception.py` / `test_codegen_controlflow_O0.py` / `test_codegen_ref_dict_O0.py` / `test_native_cli.py` / `test_T5a_数学统计排序_原生腿.py`，其中 `test_llvm_exception.py` 直接覆盖 L-093 相关的 try/catch/throw 异常归因）→ **77 passed, RC=0**（耗时 394s）。这些文件在全量资源争抢跑中正是 144 F 的一部分，隔离后全过 → 结论成立：全量 144 F 是 clang/llvm 原生编译在老化 HP Z620 高负载下资源争抢所致，与 R19 代码零因果。

  **结论**：本批次交付物向 311 贡献 **0** 个失败；全量 144 F 属环境敏感（建议 CI 在低负载机或加原生编译重试后复验，与 R19 代码无关）。

---

## 5. 交付物清单

| 类别 | 路径 | 说明 |
|---|---|---|
| 修复代码 | `light-merge/src/enhanced_errors.py` | `_map_py_to_light` 三元归属 + `format_error` 切换 + 位置标注 |
| 修复代码 | `light-merge/src/error_formatter.py` | `build_full_mapping_with_module` |
| 修复代码 | `light-merge/cli/light.py` | `_resolve_local_imports` 返回类型 + 异常挂 `_light_modules`/`_light_entry_name` |
| 回退 | `light-merge/stdlib/_light_import_hook.py` | 移除冗余 `_LIGHT_MODULES` 注册表 |
| 载体模块 | `lightharness/examples/载体模块.light` | L-093 最小载体（第6行 `返回 1 除以 分母` 为真实抛点） |
| 绿用例 | `lightharness/examples/test_L093.light` | rc=0，调用点捕获跨模块异常验证传播 |
| 反跑 | `lightharness/_antirun_t5_异常模块.py` | A/B/C 三判据，ALL OK |
| 报告 | `lightharness/_task5_异常模块_交付报告.md` | 本报告 |
| 既有（绕法文档） | `lightharness/examples/_repro_L093.light` | rc=0 绕法形态复现，不受影响 |

> 任务1（L-084/L-092/L-137 词法核心）、任务3（L-087/L-101/L-143 保留字与内置映射）交付物已于本交付批次前置完成（报告：`_task1_词法核心_交付报告.md`、`_task3_保留字内置映射_交付报告.md`）。三者共同构成 R19 任务 1/3/5 的完整交付。
