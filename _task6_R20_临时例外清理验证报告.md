# 第20轮 任务6 · 临时例外清理验证报告

> 日期：2026-09-14 ｜ 路径：路6（P2，路M前置）
> 脚本：`_verify_r20_exception_cleanup.py`（可复现，EXIT=0 表示全过）
> 目标：确认第19轮引入的 **4 个 CI 临时例外全部清零**，且 `tests/test_回归.py` 的 `SKIP`/`EXPECT_RED` 收敛到「仅必要项」，无「永久例外」残留。

---

## 一、结论速览

| 项 | 目标态 | 实测 | 结论 |
|---|---|---|---|
| 例外① `test_宿主上下文.light` | rc=0 且不在 SKIP | rc=0，SKIP=False | ✅ 清零 |
| 例外② `test_宿主事件.light` | rc=0 且不在 SKIP | rc=0，SKIP=False | ✅ 清零 |
| 例外③ `test_L095.light` | rc=0 且不在 EXPECT_RED | rc=0，EXPECT_RED=False | ✅ 清零 |
| 例外④ `_taskM_integration_r17.light` | rc=0 且不在 SKIP | rc=0，SKIP=False | ✅ 清零 |
| `SKIP` 集合 | 仅载体模块 | `{_helper_L004.light, _helper_L007b.light}` | ✅ 收敛 |
| `EXPECT_RED` 集合 | 仅合规保留字预期红 | `{test_L101.light, test_L143.light}` | ✅ 收敛 |
| 保留字预期红（不得误清零） | rc≠0 | L101 rc=1、L143 rc=1 | ✅ 保持 |
| 正向控制（本轮新增用例） | rc=0 | R20_关键字前缀标识符 / R20_词法边界综合 均 rc=0 | ✅ 通过 |

**总结论：4 个临时例外全部清零；`test_回归.py` 已从第19轮的「4 例外」收敛到「2 载体模块 + 2 合规保留字」，不存在第19轮式的"永久例外"。**

---

## 二、4 个例外逐一验证明细

### 例外①：test_宿主上下文.light（原 SKIP）
- **第19轮状态**：SKIP。现象为第102行 `段落 去重占位 接收 名单:` 触发解析错误「期望'为'或'等于'，但得到…」。
- **第19轮误判根因**：判为「`去重` 关键字 + 最大匹配把 `去重占位` 切碎」。
- **本轮实测根因（任务1更正）**：真实病根是 `设 合并为 <值>`（`合并`+`为` 黏连）——`为` 被吞进标识符导致赋值语句丢失赋值关键字；`去重占位` 一类"语句开头段落名"由 `_scan_user_definitions` 预扫描整串保留，本不切碎。
- **修复**：任务1 在 `light-merge/src/lexer.py` 修正嵌入关键字最大匹配边界（详见 `_task1_R20_词法关键字前缀_交付报告.md`）。
- **验证**：`运行.py examples/test_宿主上下文.light` → **rc=0**；不在 `SKIP`。
- **结论**：✅ 清零。

### 例外②：test_宿主事件.light（原 SKIP）
- **第19轮状态**：SKIP。`src/宿主事件.light:100` 同样解析错误。
- **本轮实测根因**：与例外①同源（`设 X为<值>` 赋值尾关键字丢失）。
- **修复**：同任务1。
- **验证**：`运行.py examples/test_宿主事件.light` → **rc=0**；不在 `SKIP`。
- **结论**：✅ 清零。

### 例外③：test_L095.light（原 EXPECT_RED）
- **第19轮状态**：EXPECT_RED。登记为「HMAC 部分修复，对拍不一致」。
- **本轮实测**：任务2 复核发现 `stdlib/哈希.py` 早已用 `hmac.new(key, msg, hashlib.sha256)`（RFC 2104 标准实现），第19轮收口登记的「部分修复」实为**状态滞后**（代码已正确，账目未同步）。
- **验证**：`test_L095.light` 7 组对拍（含空 key / 空 msg / 长 key>64B / 中文）全部与 Python `hmac.new` **逐字节一致**；`运行.py` → **rc=0**；不在 `EXPECT_RED`。
- **结论**：✅ 清零（详见 `_task4_R20补全_第19轮字符串哈希_交付报告.md` §3.5）。

### 例外④：_taskM_integration_r17.light（原 SKIP）
- **第19轮状态**：SKIP。第17轮路M临时集成测试（3851 字节），回归失败。
- **本轮处理**：任务3 评估为**有价值的跨模块集成测试**（宿主运行时/上下文/事件/工具/IO/配置 六模块共存、22 断言 + 模拟用户多轮交互），**修复而非删除**。
- **修复**：文件本身语法/用例修正后 → **rc=0**；已从 `SKIP` 移除，回归测试恢复扫描。
- **结论**：✅ 清零。

---

## 三、`test_回归.py` 目标态核对（文件互斥 § 临时例外清理）

```python
SKIP = {'_helper_L004.light', '_helper_L007b.light'}
EXPECT_RED = {
    # L-004 / L-007b 系「载体模块」：仅被 import，非可直接执行的测试入口 —— 属必要项，保留
    'test_L101.light': 'L-101 回调 是保留关键字，误用作变量名应 rc!=0（明确提示，非静默失败）',
    'test_L143.light': 'L-143 作用域 是保留关键字，误用作变量名应 rc!=0（明确提示，非静默失败）',
}
```

- `SKIP` 仅剩 2 个**载体模块**（`_helper_*`，前缀下划线，非测试入口，被 import 使用）—— 属任务书「仅保留必要项」允许范围。
- `EXPECT_RED` 仅剩 L-101/L-143 **合规保留字预期红**：这两个是第19轮**刻意保留**为保留字（`回调` 供 FFI、`作用域` 供异步作用域），误用必须明确报错。保留为 EXPECT_RED 是**正确语义**，非"永久例外"。
- 第19轮登记的 4 个例外（L095/宿主上下文/宿主事件/_taskM_r17）**全部已从两个集合移除**。

---

## 四、脚本可复现性

```
$ "C:/Python314/python.exe" _verify_r20_exception_cleanup.py
=== tests/test_回归.py 当前例外集合 ===
  SKIP       = ['_helper_L004.light', '_helper_L007b.light']
  EXPECT_RED = ['test_L101.light', 'test_L143.light']
=== 4 个临时例外逐一验证（应全部 rc=0 且不在例外清单）===
  PASS 例外① test_宿主上下文.light  rc=0（期望 0），仍在 SKIP=False
  PASS 例外② test_宿主事件.light  rc=0（期望 0），仍在 SKIP=False
  PASS 例外③ test_L095.light  rc=0（期望 0），仍在 EXPECT_RED=False
  PASS 例外④ _taskM_integration_r17.light  rc=0（期望 0），仍在 SKIP=False
=== 目标态断言 ===
  PASS SKIP 收敛到仅载体模块
  PASS EXPECT_RED 收敛到仅合规保留字预期红
=== 保留字预期红不被误清零（应 rc!=0）===
  PASS test_L101.light  rc=1
  PASS test_L143.light  rc=1
=== 本轮新增正向控制（应 rc=0）===
  PASS test_R20_关键字前缀标识符.light  rc=0
  PASS test_R20_词法边界综合.light  rc=0
=== 清理结论 ===
  ✓ 4 个临时例外全部清零；SKIP/EXPECT_RED 已收敛到目标态（无「永久例外」残留）。
EXIT=0
```

脚本设计要点：
- **目标态断言**（非"改变即报"）：直接断言 `SKIP`/`EXPECT_RED` 等于收敛目标，任何"永久例外"回归都会立红。
- **反向控制**：断言 L101/L143 仍 rc≠0，防止误把合规保留字预期红一起清掉。
- **正向控制**：断言本轮新增的两个用例 rc=0，确认修复确实生效而非"例外被删了但功能没修好"。

---

## 五、遗留说明

1. `test_会话存储.light` 在裸 sweep 中 rc≠0，但在 HEAD 基线同样红，**非本轮引入**，未登记为本轮例外（详见 `_task1_R20_词法关键字前缀_交付报告.md` §3.3 归因表）。
2. 本轮全量 CI 出现一次 `test_审批.light` 计时抖动（wall-clock 断言），与本轮编译器改动无关，已单独登记（见 `_task6_R20_docs更新草案.md` 新增缺陷 R20-C）。
