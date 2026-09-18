# 第 60 轮 路M 收口总报告（_taskM_R60）

> 轮次：R60 · 主 agent（豆包）路M 收口
> 模式：用户「你写我发」→ WorkBuddy 跑任务1-4 → 用户「任务1-4完成，你来收口」→ 本报告
> 基线链：133701（R58）→ **172617（R59 终跑，13 红）** → **201545（R60 终跑）**
> 硬约束遵守：整轮仅 1 次全量（0.82 fast，py3.12 绝对路径）；未并行全量；本机未跑全量；取退出码未接管道；未 push。

---

## 一、门结果（对拍 172617）：**FAIL（3 新增红，均已处置并双端验证，未重跑全量）**

```
0.82 全量（唯一一次，fast，py3.12）：7871 用例
13 → 4 红 ｜ 新增红 3 ｜ 已修复 12 ｜ 持平 1
门 === FAIL（新增红 3）  rc=0（pytest 进程退出码；红以 diff 对拍为准）
```

- **已修复 12**（任务书预期全部达成）：R59 已修 3（钉桩 R19 / T6C 参数解析 / T6C URL）+ 任务2 异步 5 + 任务1 compact 1 + examples 连带 1 + 任务3 地板 1 + **4A-2 func_non_nullable 连带 1**（任务书未列，白赚）。
- **持平 1 = 存量剩红**：`tests/_test_null_safety.py::test_paragraph_call`（旧式语法，归因 R61）。
- **新增红 3（均非回归，逐一定向处置，见 §二）**：身份证校验_O0对拍、钉桩 R22_接收字合并、钉桩_全角逗号。

## 二、3 个新增红：归因 + 处置 + 验证

### 1. `test_身份证校验_O0对拍` —— **LLVM 后端 `截取` 语义缺陷（真 bug，已修）**

**链条**：任务3 按 .light 官方语义（`截取(文本,起始,结束)` = `文本[起始:结束]`，内置核心字符串.light L13-15）把身份证校验.light 8 处 `截取` 改 end → 全量对拍红 `valid[110101199001011237]` → 定向追查发现 **LLVM 后端 `截取` 把第三参（end）直传给 dv_substr 的 len**（`src/llvm/codegen_typed.py:2467-2473`；`runtime_typed.c:1117` `en = st + len`）——与 .light 官方语义不一致。旧 len 语义下「改前的 (start,len) 写法碰巧对」，改 end 后全错。

**修复**（路M，src 层）：
- `src/llvm/codegen_typed.py`：`截取` 改传 `end - start` 给 dv_substr，负值 clamp 为 0（对齐字符串切片 4223-4235 的处理，Python `s[start:end]` 在 start>end 时为空串）。
- 连带暴露 **`stdlib/颜色.light` RGB解析 2 处 (start,len) 误用**（原 len 语义下碰巧对）：L201 `截取(干净,1,长(干净)-1)`→`长(干净)`（去掉 `#` 取到末尾）、L222 `截取(干净,左括+1,右括-左括-1)`→`右括`（取 `(` `)` 之间）——已修。

**验证**：本机身份证/手机号对拍 2 passed + 颜色 2 passed；0.82 全定向（身份证/手机号/颜色/编码解码/参数解析/向量）**165 passed / 0 failed**。

> 至此三后端 `截取` 语义一致：src 后端 lambda `s[start:end]`、unified `_light_builtin.截取`、LLVM `end-start→dv_substr`，均对齐 .light 官方 [start:end]。

### 2 & 3. 钉桩 R22 × 2（`test_现状钉桩_R22_接收字合并`、`test_现状钉桩_全角逗号不是这两个回归的原因`）—— **钉桩过期，转正（正向变化）**

任务1 修复 B 把 `段落加法接收甲，乙：` 正确切为 `段落/加法/接收/甲/，/乙/：`（`接收甲` 不再合并）→ R40 两枚「现状钉桩」（断言合并仍在）过期 → **转正更新**（docstring 记录转正原因、断言反转、缺陷关闭），同 R59 钉桩 R19 先例。

**验证**：本机 4 钉桩（R22 接收字 / 全角逗号 / 己字 / R19）passed；0.82 同批 passed。

## 三、路M 收窄（防门 FAIL 于未然的关键动作）

**任务1 报告预警坐实**：任务2 的 parser_expr.py 拦截（IDENTIFIER 形态 `异步*` 当值一律报错，白名单仅 4 个异步原语名）误伤 3 条**合法已定义名**——合并树互举反跑 677 新增 3 条解析失败：`stdlib/并发.light:81`（`异步信号量`）、`stdlib/HTTP服务端.light:451`（`异步接受`）、`examples/test_R21_L152家族嵌套形参.light:66`（`异步作用域`）。

**处置**：拦截条件补「放行 `lexer.user_definitions` 已定义名」（`异步` 开头且**已定义** = 合法值；未定义 = 修饰符误用仍拦截）→ **互举反跑复跑 0 新增解析失败（绿）**，5 条目标红仍编译期拦截（本机 + 0.82 定向 6 passed）。

## 四、任务1-4 交付核实结论

| 任务 | 交付 | 核实 |
|---|---|---|
| 任务1 compact 词法 | src/lexer.py 修复 A/B + src/code_generator.py 修复 C | 目标红 2 转绿；全语料 token A/B 38091 文件仅 6 变化逐条取证；互举反跑隔离口径 0 新增 |
| 任务2 异步拦截 | src/parser_expr.py + code_generator(_unified).py | 6 passed；初版误伤已修；self 去重三态验证；**白名单未含 3 合法名 → 路M 收窄（§三）** |
| 任务3 地板+截取族 | 内置核心列表.light + 身份证校验.light 8 处 + 中文数字转换.light 3 处 + 17 定向用例 | 3A 128 passed；3B 反跑非空转；**LLVM 后端缺陷暴露 → 路M 修（§二.1）** |
| 任务4 只读归因 | _task4_R60_其余归因.md/json | 4A-1 仍红（R61）、**4A-2 连带转绿**、4B 三处绿 |

## 五、交付物与提交

- **light-merge**（commit，未 push）：`src/lexer.py`、`src/code_generator.py`、`src/code_generator_unified.py`、`src/parser_expr.py`、`src/llvm/codegen_typed.py`、`stdlib/内置核心列表.light`、`stdlib/身份证校验.light`、`stdlib/中文数字转换.light`、`stdlib/颜色.light`、`tests/test_R40_语言支撑配套.py`、`tests/unit/test_R60_截取语义误用族.py`、`_task1/2/3_R60_*.md`。
- **lightharness**（commit，未 push）：`_task4_R60_其余归因.md/json`、基线 `082_lightmerge基线_2026-09-18-201545.json` + `_082_lm_results_2026-09-18-201545.xml`、diff `082_diff_2026-09-18-203010.json`、对标清单 **#199**、R60 探针移档 `docs/历史存档/R60探针/`、`_taskM_R60_收口总报告.md`。
- 未提交（历史不提交清单）：`_ssh_*`/`_tmp_*`/`_taskR11B_test_*/`/`.blocking_backup/`/`.bugfix/`/`tests/_temp_cbackend/`/R21-R28 遗留 `_ctx_*/_diag_*/_evt_*/_sweep_*/_taskM_*` 等。

## 六、R61 待办（下轮输入）

1. **全量确认**：本轮 3 新增红已处置 + 收窄，下轮全量预期 **0 新增**、剩 **1 存量红** `test_paragraph_call`（旧式语法，R61 底表已就位）。
2. 截取族三后端已对齐——新增覆盖建议：把 `tests/unit/test_R60_截取语义误用族.py` 的 LLVM 对拍口径扩展为三后端（当前原生腿 O0 已含）。
3. 中文数字转换.light 缺口（裸名 `去除空格` 在 Python hook 腿 NameError，原生腿 OK）已登记，非本轮引入，留待后续。
