# 任务C 交付报告：`映射网络消息` / `块文本拼接` 缺键 / 空值防护（遗留修复）

- 分支/位置：`lh-map` worktree（`git worktree add -b lh-map ../lh-map HEAD`，基线 ebd6905「翻译流判空挡住 JSON null」）
- 改动文件：仅 `src/客户端.light`（未 commit，交由分发者合流）
- 状态：修复绿 → 反跑红 → 复跑绿；四件定向测试全 EXIT=0

## 1. 根因（文件：行 + 触发条件）

上次任务（HEAD ebd6905）只在 `翻译流` 的**读侧**（增量字段）判了空；消息**写出侧** `映射网络消息` / `块文本拼接`
仍是消息块的裸下标直读，缺键 / 空值会击穿：

| 位置（修复前行号） | 表达式 | 触发条件 | 现象 |
|---|---|---|---|
| `src/客户端.light:173`（assistant 分支） | `文本 + 块["text"]` | text 块**缺 `text` 键** | `键错误: 'text'` |
| `src/客户端.light:175`（assistant 分支） | `推理 + 块["text"]` | reasoning 块 text 为 null | `TypeError: can only concatenate str (not "NoneType") to str` |
| `src/客户端.light:177`（assistant 分支） | `块["id"]`/`块["name"]`/`块["arguments"]` | tool-call 块缺键或 null | 缺键 KeyError；null 原样落进 wire（`id:null`/`arguments:null`） |
| `src/客户端.light:193`（`块文本拼接`） | `结果 + 块["text"]` | text 块缺键 / text 为 null | 缺键 KeyError；null → str+None |
| `src/客户端.light:160/172/192` | `块["type"]` | 块**整体缺 `type` 键** | `键错误: 'type'` |

另：assistant 分支对非 text/reasoning/tool-call 类型的块是**静默丢弃**，原代码无任何注释说明（本次补齐显式注释，语义不变）。

## 2. 关键 diff（`src/客户端.light`，+19/−10）

```diff
+# ---- 消息块字段安全取值（任务C）----
+段落 取块串 接收 块, 键:
+  如果 块.包含(键) 且 块[键] != 空:
+    返回 块[键]
+  返回 ""
```

- 3 处 `块["type"] == …` 判等前加 `块.包含("type") 且`（tool-result 扫描 / assistant 三类 / `块文本拼接`）——缺 type 键即跳过，与「未知类型静默跳过」既有语义一致；
- assistant text/reasoning/tool-call 与 `块文本拼接` 的字段直读改经 `取块串`：缺键 / None → 空串；正常字段原样返回；
- tool-call 入网 dict 改为 `["id": 取块串(块, "id"), …, "function": ["name": 取块串(块, "name"), "arguments": 取块串(块, "arguments")]]`——null 不再落进 wire；
- assistant 分支补注释：非三类块（含缺 type）静默跳过为显式约定。

## 3. mock 触发：修复前后对比（`_taskC_复现.light`，收尾已删）

| 用例 | 修复前 | 修复后 |
|---|---|---|
| 拼接：text 块缺 `text` 键 | CRASH `'text'` | PASS → `""` |
| 拼接：`text` 值为 null | CRASH `str (not "NoneType")` | PASS → `""` |
| 拼接：块缺 `type` 键 | CRASH `'type'` | PASS → `""`（跳过） |
| 拼接：正常 text+reasoning+tool-call | PASS → `"你好"` | PASS → `"你好"`（逐位不变） |
| 映射：助手混合退化（text 缺键/reasoning null/tool-call 全 null/tool-call 全缺键） | CRASH `'text'` | PASS → `content:"好"` + 两条 `{id:"",name:"",arguments:""}` 工具调用 |
| 映射：助手正常（含中文 JSON arguments） | PASS → 见右 | PASS → 输出逐位不变 |
| 映射：系统 / 工具结果消息 | PASS | PASS（不变） |

## 4. 反跑判据

守卫还原（`git show HEAD:src/客户端.light`）→ 复现脚本 **EXIT=1**，日志 4 处 CRASH：
`'text'` ×2、`str (not "NoneType")`、`'type'`，末行「存在 4 处崩溃」。
恢复修复版复跑 → EXIT=0、全 PASS。**守卫改回去立即立红** ✔

## 5. 定向测试输出（修复版）

```
[0] examples/test_消息.light      :: --- 消息模块测试通过 ---
[0] examples/test_客户端.light    :: --- 客户端离线测试通过 ---
[0] examples/test_客户端深化.light :: --- 客户端深化测试通过 ---
[0] examples/test_联调CLI.light   :: === test_联调CLI PASS ===
```

（仅定向，未跑全量回归——按任务红线。）

## 6. 边界与说明

- 正常输入语义逐位不变：`取块串` 对存在且非空字段原样返回，非字符串值透传（与直读一致）。
- 范围外未动：`映射网络消息` 中 `消息["role"]`、`工具块["toolCallId"]`/`工具块["content"]`、`消息["content"]` 本身的缺键仍保持原 KeyError（任务枚举的缺键字段为 `text`/`id`/`name`/`arguments`，未纳入）。
- 与上次 HEAD 提交衔接：该提交挡的是 `翻译流` 读侧空值，本任务补的是 `映射网络消息`/`块文本拼接` 写侧，二者无重叠。
