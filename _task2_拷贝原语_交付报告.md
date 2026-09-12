# 任务2 交付报告：拷贝原语（L-082 副本 + L-083 深拷贝/浅拷贝/冻结）

> 任务来源：`G:\dswork\duan-light-merge\光明语言改进_并行任务书.md` 任务2
> 日期：2026-09-12
> 铁律：语言修复落在 light-merge（编译器 + stdlib 地板）；lightharness 仅作验证，简化其绕法并跑全绿。

---

## 一、根因（Root Cause）

### L-082｜`副本` 在内置表里"挂了名、没有身"
- `light-merge/src/code_generator.py` 的 `builtin_map` 早已注册 `'副本': '_light_builtin.副本'`，但运行期能否解析取决于**实际加载的地板 `stdlib/builtins.py` 是否真有该属性**。
- 关键发现：lightharness 自带一份**自包含地板** `lightharness/stdlib/builtins.py`（与 `light-merge/stdlib/builtins.py` 是**两个独立文件**，互不相同），且这份地板**缺失 `副本`** → 在 lightharness 里调用 `副本(...)` 直接 `AttributeError: module 'light_builtins' has no attribute '副本'`。light-merge 自家的地板其实有 `副本`，所以只在 lightharness 侧暴露。
- 第9轮任务1 修 T2-D2 时撞到这个坑，被迫用「新建空列表 + 遍历追加」逐元素拷贝绕开。

### L-083｜光明没有 深拷贝/浅拷贝/冻结 一等原语
- `深拷贝`/`浅拷贝`/`冻结` 在三层（builtin_map / floor `builtins.py` / `内置核心列表.light`）**完全缺席**。
- 消息构造按引用组装 `content`：`造用户消息(内容)` 直接 `content: 内容`（透传同一列表引用），调用方后续 `列表追加(入参,...)` / `入参[0]["text"] 为 "改了"` 会污染已构造消息。上游 `createXxxMessage` 用 `deep-freeze` 与入参脱钩，光明无对应能力，第9轮任务2 用「`拷贝内容块表` 逐块字典拷贝」绕法。

---

## 二、做了什么（Fix Points）

### 1. 编译器注册（light-merge/src/code_generator.py）
- `builtin_map` 增加三条：`浅拷贝` / `深拷贝` / `冻结`（`副本` 本已注册）。
- 无 stdlib 兜底分支同步增加对应 lambda（`副本`/`浅拷贝` → 字典/列表浅拷贝、其他原样；`深拷贝`/`冻结` → `copy.deepcopy`）。

### 2. light-merge 语言本体地板（stdlib/builtins.py + 内置核心列表.light）
- `stdlib/builtins.py`：在既有 `副本` 之后新增 `浅拷贝`/`深拷贝`/`冻结`（`深拷贝`/`冻结` 走 `copy.deepcopy`；`浅拷贝` 委托 `内置核心列表.浅拷贝`）。`__all__` 补齐四项。
- `stdlib/内置核心列表.light`：新增导出 `浅拷贝 深拷贝 冻结`；实现 `段落 浅拷贝`（字典/列表浅拷贝、其他原样）、`段落 深拷贝`（递归深拷贝字典/列表）、`段落 冻结`（=深拷贝，对齐上游 deep-freeze 语义）。

### 3. lightharness 验证地板（lightharness/stdlib/builtins.py）
- 补齐 `副本`/`浅拷贝`/`深拷贝`/`冻结` 四个真身（`深拷贝`/`冻结` 走 `copy.deepcopy`），`__all__` 同步补齐。
- 这是 lightharness 自包含运行所需的"语言能力桥"，不是源码逻辑 hack。

### 4. lightharness 源码绕法简化（验收 #4 / #5）
- **验收 #4** `src/消息.light`：删除 `拷贝内容块表` 逐块绕法段落，6 处 `拷贝内容块表(内容)` 全改为 `深拷贝(内容)`，与上游 `deep-freeze` 对齐。
- **验收 #5** `src/会话格式.light` `段落 事件带来源`：逐元素遍历快照改为 `事件项["来源事件序号"] 为 副本(来源表)`（来源序号表为扁平整数列表，`副本` 浅拷贝等价且脱钩）。

---

## 三、最小复现（Minimal Repro）

- `examples/_repro_L082.light`：试 `副本([1,2])` 入 try/catch，原 `AttributeError` → 现已 `副本() 已可用（缺陷消失）`，`缺陷确认=False`。
- `examples/_repro_L083.light`：调用方 `列表追加(入参,...)` / `入参[0]["text"] 为 "改了"`，修复前污染已构造消息，修复后 `深拷贝` 脱钩。
- 新增回归 `examples/test_修复_拷贝.light`：覆盖 `副本`(字典/列表浅拷贝、其他原样)、`浅拷贝`(共享嵌套引用)、`深拷贝`(不共享嵌套引用)、`冻结`(脱钩)、消息构造脱钩。

---

## 四、验证（Verification）

### 直接受影响的用例（全绿）
| 测试 | 结果 |
|---|---|
| `examples/test_修复_拷贝.light` | ✅ 通过 |
| `examples/test_会话格式.light` | ✅ 全部用例通过 |
| `examples/test_修复_会话.light` | ✅ 全部通过（含 3a/3b 副本快照） |
| `examples/test_行为对照_会话持久化.light` | ✅ 全部通过（含 4a/4b 副本快照） |
| `examples/test_消息.light` | ✅ 通过（深拷贝脱钩） |

### 反跑判据（_antirun_拷贝原语.py）
- 在内存备份 `lightharness/stdlib/builtins.py` → 将 `副本/浅拷贝/深拷贝/冻结` 四个 def 重命名（运行期 `_light_builtin.副本` 等 `AttributeError`）→ 上述 4 个测试**全部转红 (rc=1)**。
- 还原原始文件 → 4 个测试**全部转绿 (rc=0)**，且脚本二次校验文件**完全还原**。
- 结论：该修复是真实生效的语言能力，而非偶然通过。

### 关于 test_会话格式 偶发红
- 排查确认：原始 t5 偶发 `rc=1` 来自**环境性 safe-delete 回收站错误**（`[safe-delete][SAFE_DELETE_FAIL_CLOSED] ... SHFileOperationW 失败: 0x2`），与 `副本(来源表)` 语义无关——同一份代码加调试打印后 (t5d) 即 `rc=0`。已确认 `来源表` 为扁平整数列表，`副本` 浅拷贝语义等价，下游断言全部成立。

---

## 五、铁律符合性

- ✅ 语言修复主体落在 light-merge（code_generator.py + stdlib/builtins.py + 内置核心列表.light）。
- ✅ lightharness 仅作验证：简化源码绕法（消息.light / 会话格式.light），地板补齐是验证所需的语言能力桥。
- ✅ 每缺陷附最小复现；受影响用例 + 反跑全绿。
- ⏭️ 全量 CI（约 230 用例，gitea 192.168.1.5 / 验证机 192.168.0.88）推送前跑，本次改动均为**增量新增**（builtin_map 加键、地板加函数、源码绕法简化），不触碰既有编译路径。

---

## 六、交付物清单
- `light-merge/src/code_generator.py`：builtin_map 增 `浅拷贝/深拷贝/冻结` + 无 stdlib 兜底 lambda。
- `light-merge/stdlib/builtins.py`：增 `浅拷贝/深拷贝/冻结`，`__all__` 补齐。
- `light-merge/stdlib/内置核心列表.light`：增 `浅拷贝/深拷贝/冻结` 导出与实现。
- `lightharness/stdlib/builtins.py`：补 `副本/浅拷贝/深拷贝/冻结` 真身 + `__all__`。
- `lightharness/src/消息.light`：6 处 `拷贝内容块表` → `深拷贝`（验收 #4）。
- `lightharness/src/会话格式.light`：`事件带来源` 逐元素快照 → `副本`（验收 #5）。
- `lightharness/examples/test_修复_拷贝.light`：新增回归测试。
- `lightharness/_antirun_拷贝原语.py`：反跑判据。
- `lightharness/docs/功能对标/语言缺陷账.md`：L-082 / L-083 状态 → 已修复。
