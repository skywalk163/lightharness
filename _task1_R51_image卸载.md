# 任务1（R51/P0）交付报告 —— image/offload 事件 + 图像卸载投影

> 日期：2026-09-17 ｜ 第51轮（上游 0.1.6-alpha.1 增量跟随）｜ P0 硬兼容项
> 上游基线：`G:\github\deepseek-harness`，上游 release 提交 `ea53423b60`（0.1.6-alpha.1），
> fork 合并提交 `c47b24803e`（tag `fork-after-upstream-v0.1.6-alpha.1`）
> 交付物：`src/会话格式.light`、`src/压缩.light`、`src/会话日志增量.light`（1 处词汇补登）、
> `examples/test_R51_image卸载.light`、`examples/test_会话日志增量.light`（计数断言同步）、本报告

---

## 1. 为什么是 P0（先把根因说清）

上游 0.1.6 的持久化变更登记条目 `docs/persistence-changes/2026-09-14-image-offload.zh.md` 原文：

> **新事件在读取时必须被识别：不认识 `image/offload` 的旧版本拒绝读取这些日志**，
> 当前读取器需要对应的消息投影。事件信封和结构性的 Session 格式版本不变。

而「拒绝」的机制在上游 `packages/core/session/src/known-event-types.ts` 的头部注释里写得更硬：

> The persistence read path **refuses to interpret a log containing a type outside this set**
> unless the event carries the envelope's `ignorable` marker … such a log was likely written by a
> newer harness, and silently skipping a required event would **reconstruct a wrong session**.

**实测核对（本轮的硬证据）**：把上游 0.1.6 的 `KNOWN_SESSION_EVENT_TYPES`（57 项）
与本仓 `src/会话日志增量.light` 的 `已知事件类型集`（原 56 项）做集合差——

```
上游有本仓无: ['image/offload']
本仓有上游无: []
```

即：0.1.5-rc.2 → 0.1.6-alpha.1 的事件词汇表**只多了 `image/offload` 一项**，
其余 56 项我们已完全对齐。这一项不做，就是「词汇表不完整 → 读取路径按未知类型处理 →
（上游语义下）重建出错误的会话」。

---

## 2. 做了什么

### 2.1 `src/会话格式.light`（+约 300 行，§2 词汇 + §16 全节）

| 项 | 内容 | 对齐上游 |
|---|---|---|
| 事件词汇 | `定词汇("image/offload", ["targets"], [])`——**键名保持英文 wire 形状** | `SessionEventMap['image/offload'] = { targets }` |
| `取事件序号(事件表, 序号)` | 线性取事件 | `session.eventAt(seq)` |
| `当前表面节点(事件表)` | 遮蔽跳过 + 表面可入类型 → 节点序号表 | 投影上下文 `context.nodes` |
| `是图像块 / 是工具结果块` | 深度优先两分支判据 | `block.type === 'image' / 'tool-result'` |
| `图像身份(块)` | `attachment.name` → `attachmentId` → 本地 `名称/标识` → `"image"` | `imageIdentity(ref)` |
| `卸载占位文本(块)` | `[image omitted to fit request image limits; <身份>. No local normalized image path is available; ask the user to attach it again if needed.]` | `offloadedImageText(ref)` 的无 access 分支 |
| `替换卸载图像 / 替换消息卸载占位` | 递归（含 tool-result）把 `offloaded=真` 的出现位置换成占位文本 | `replaceOffloadedImages` / `projectOffloadedImages` |
| `卸载块表 / 卸载消息图像` | 深度优先计数标记 `offloaded=真`；已卸载→抛、下标越界→抛 | `offloadMessageImages` |
| `校验图像卸载载荷(数据, 节点表, 事件表)` | 原子校验：仅 `targets` 键、非空、每目标仅 `seq/imageIndexes`、seq 为「当前表面节点」且源事件为 user/message 或 tool/result、事件内不得重复 seq、索引严格递增非负安全整数 | `imageOffloadProjection.project` 的校验段 |
| `投影图像卸载(事件表)` | 按事件顺序**叠加**每个决策，返回 `{序号: 投影后消息}` | `imageOffloadProjection.project` + fold |
| `投影消息产生带卸载(事件表)` | 模型可见消息表（投影 + 占位渲染）= 读 0.1.6 日志的正式入口 | fold + `projectOffloadedImages` |
| `投影表面消息 接收 事件表, 覆盖表 = 空` | **加性**参数：命中序号即用投影消息替换派生消息；缺省 空 → 行为与 R47/R48 完全一致 | fold 优先取用 `projectedMessages` |

### 2.2 `src/压缩.light`（+约 80 行）

| 函数 | 内容 | 对齐上游 |
|---|---|---|
| `收集块图像索引(块表, 状态)` | 深度优先收集**未卸载**出现位置下标；`计数` 含已卸载、`剩余` 只减未卸载 | `visit` 闭包 |
| `卸载最旧图像(会话对象, 源事件序号表, 需要数)` | 按源顺序逐事件取「最旧 N 个」出现位置 → 落盘 `image/offload {targets}`；无可卸载 → 返回 假 且不落盘；落盘前调 `校验图像卸载载荷` 原子校验 | `offloadOldestImages(session, sourceEventSeqs, count)` |

**关键实现点（不这么做必然错位）**：扫描用的消息必须是**已应用前序卸载决策的投影消息**
（先 `投影图像卸载(事件表)` 取覆盖表，命中则用覆盖表的消息，否则退回 `投影节点消息`）——
对齐上游 `session.deriveEventMessage`。用原始消息会把已卸载的出现位置再选一遍，
二次卸载必然取错下标（本用例 §5b 就是这个判据，实测第一版即因此红）。

### 2.3 `src/会话日志增量.light`（+1 项，词汇补登）

`已知事件类型集` 插入 `"image/offload"`（插在上游同一位置：`hook/result` 与 `llm/retry` 之间）。
新增 `examples/test_会话日志增量.light` 三条判据（计数 56→57、含该项、该类型不走 `ignorable` 分支）。

> ⚠️ 这是**超出任务书「任务1 改 会话格式+压缩」声明范围的第 3 个源文件**，理由：本仓存在
> **两份**事件词汇镜像（`会话格式.事件词汇表` 与 `会话日志增量.已知事件类型集`），
> 只补一份会出现「同一构建里对同一事件两种认知」。改动为纯追加 1 项 + 同步 1 条计数断言。

### 2.4 与本仓的刻意差异（登记为行为差异）

| 项 | 上游 | 本仓 | 影响 |
|---|---|---|---|
| 不可变性 | `deepFreeze` 深冻结投影消息 | 返回浅拷贝（`副本`）且**不原地改写原消息** | 不可变性由「不原地写」保证，非 `Object.freeze` 保证；无法用 `isFrozen` 断言 |
| 「当前表面节点」的判定 | `surface.nodes`（含 replace 遮蔽语义） | 本仓用 `遮蔽` 标记 + 表面可入类型推算 | 语义等价（R47/R48 已对齐的同一套规则） |
| 投影注册表 | `registerMessageProjection` 插件注册、fold 组合 | 显式函数 `投影图像卸载` + `投影表面消息` 的 `覆盖表` 参数 | 无插件系统，改显式传参（同 R47/R48 的既有取舍） |

---

## 3. 实测证据

### 3.1 新用例（51 条断言：35 条正判 + 16 条拒绝判据，全绿）

```
cd G:/dswork/duan-light-merge/lightharness
../light-merge/.venv/Scripts/python.exe 运行.py examples/test_R51_image卸载.light
→ test_R51_image卸载: 全部用例通过   rc=0
```

覆盖矩阵：

| 组 | 判据 |
|---|---|
| §1 词汇 | `已知事件类型("image/offload")==真`；合法载荷过严格校验；未知类型仍 `unsupported event type` 拒绝 |
| §2 节点 | 3 张图（含嵌套 tool-result）深度优先下标 0/1/2；当前表面节点 = 系统头 + 用户消息 |
| §3 决策 | 首次 `卸载最旧图像(…, 2)` → 真；落盘 seq=2 的 `image/offload`；`targets[0].imageIndexes == [0,1]` |
| §4 投影 | 标记 `[真,真,假]`；消息标识不变；**原事件与原始图像块逐字节不变**；2 条占位文本；占位含附件身份 |
| §5 叠加 | 二次卸载取到下标 `[2]`（已卸载的仍计入计数）；两决策叠加后 `[真,真,真]`，3 条占位 |
| §6 空手 | 无可卸载 → 假且不落盘（事件数不变）；空源序号表 → 假 |
| §7 校验 | 空 targets / 非数组 / 非对象 / 载荷多余键 / 空 imageIndexes / 目标多余键 / 非数字 seq / 负 seq / 非表面节点 seq / 负索引 / 非整数索引 / 非递增 / 重复索引 / 事件内重复 seq / 助手目标 / 被遮蔽节点 —— **16 条拒绝判据全部命中指定文案** |
| §8 边界 | 重复卸载 → `already offloaded`；越界下标 → `does not exist` |
| §9 渲染 | 已卸载全渲染占位；未卸载图像原样保留；无卸载时返回原消息；无 `image/offload` 的日志不产占位、覆盖表长度 0 |

### 3.2 既有用例回归（相关面）

```
examples/test_会话.light                        rc=0
examples/test_会话深化.light                    rc=0
examples/test_会话格式.light                    rc=0
examples/test_会话格式冒烟.light                rc=0
examples/test_会话V3迁移.light                  rc=0
examples/test_R48_会话V3迁移.light              rc=0
examples/test_R48_surface消息投影.light         rc=0
examples/test_R47_会话surface深化.light         rc=0
examples/test_压缩.light                        rc=0
examples/test_压缩E5.light                      rc=0
examples/test_压缩自动.light                    rc=0
examples/test_压缩配套.light                    rc=0
examples/test_会话日志增量.light                 rc=0（含新增 3 条判据）
examples/test_会话日志深化.light                 rc=0
---- 失败 0 / 共 14 ----
```

### 3.3 全量测试门禁

`pytest tests/test_回归.py`（examples 全量门禁）与 `pytest tests/`（含词法套件）结果见 §5「回归」——
本机既有红集（7 条存量词法红）未新增。

---

## 4. 顺带发现的语言缺陷（本轮新登记，建议下一轮修）

### L-170（新）：核心动词关键字用作变量名 → 下标赋值被**静默**编译成比较表达式

**症状**：源码

```light
设 映射 为 {}
映射[序号] 为 取两(源消息, 目标["imageIndexes"])
```

被编译成

```python
映射 = {}
(映射[序号] == 取两(源消息, 目标["imageIndexes"]))   # ← 赋值变成比较，且整个表达式无副作用
```

运行期表现：`映射` 恒为空 → 后续 `映射[序号]` 抛**键错误**；**编译期零告警、零报错**。

**根因**：`映射` 是 `keywords.py` 里的 **arity-2 核心动词**（`VERB_ARITY['映射'] == 2`，
分类 `functional`）。当它被当作变量名出现在「下标赋值语句」左侧时，语句被当作表达式解析，
`为` 被降级成 `==`。

**最小复现**（已固化）：`lightharness/_probe_r51_L170最小复现.light`（甲形非关键字正常 / 乙形关键字抛键错误，实测段）：

```light
  设 覆盖表 为 {}          # 非关键字名 → 正确
  覆盖表[1] 为 取两(7, [0])   # 实测 覆盖表={1: 7}
  设 映射 为 {}            # 关键字名 → 静默降级
  映射[1] 为 取两(7, [0])     # 实测 抛「键错误」
```

**影响面**：本轮为查此问题额外花了多次探针（首轮 `test_R51_image卸载` 全红即它所致）。
既有代码里 `文本/构造/严格/保护/输出/步/替换` 等 `ALL_KEYWORDS` 成员作标识符**正常工作**
（它们不是 arity-2 动词），所以这是「核心动词专用」的坑。

**建议**：编译器在 `设 <名>` / 形参 / 循环变量处，对 `VERB_ARITY` 成员给出**编译期告警或报错**
（同 L-166 影子变量告警的机制即可，`LIGHT_WARN_*` 开关）；本仓侧已加 `_probe_r51_kwname.py`
扫描器（可移档为工具）。

### L-171（新）：`写 X + Y` 会静默丢弃实参

`写 转字符串(甲) + "\n"` → 报「不能对 空值 与 字符串 做 加 运算」。
即 `写` 只吃**单个字面量/变量**，实参被丢弃后返回 `空`，导致与后续 `+` 拼接。
与既有 L-055（`写 f(x)` 丢实参）同源，但表现为「空值参与加法」，误判方向不同。
**建议**：`写` 接受表达式并返回 `空`，或在编译期拒绝 `写 a + b`。本轮规避方式：拆成两句。

---

## 5. 回归

### 5.1 examples 全量门禁（`tests/test_回归.py`，本仓主门禁）

```
../light-merge/.venv/Scripts/python.exe -m pytest tests/test_回归.py -q -rf -n 4 --basetemp=.pytest_r51tmp
→ 4 failed, 412 passed in 285.91s
```

4 条红（**全部为存量词法红，与本轮改动面零交集**）：

| 红例 | 判定依据 |
|---|---|
| `test_R22_嵌入关键字冗余验证.light` | 该文件**无任何 import**，也不引用 `会话格式/压缩/mcp客户端/会话日志增量`；失败原因是词法器把 `段落 测试_返回真:` 里的 `真` 切开 → `name '真' is not defined` |
| `test_R26_词首并入反向.light` | 同上 |
| `test_R26_词首并入混合.light` | 同上 |
| `test_R27_词首并入反向.light` | 同上 |

这与既有基线口径一致（R47/R48 报告均记「7 failed 全是 R22/R26/R27/R31/R32 存量词法红」；
其中 4 条落在 examples 门禁、其余落在词法 token 套件）。**本轮新增 0 条红**，且 examples 通过数
= 基线 + 本轮新增 2 个用例。

### 5.2 其余套件 + 改动面

```
../light-merge/.venv/Scripts/python.exe -m pytest tests/ -q -rf --tb=no --ignore=tests/test_回归.py -n 4
→ 3 failed, 846 passed, 3 skipped in 23.23s
```

3 条红：`test_R31_EMBED表保留+flaky修复_token.py`（2 条）+ `test_R32_OPERATOR+MERGE_WHOLE精简_token.py`（1 条）
—— 同属存量词法红家族（R31/R32），与本轮改动面无关。

**两段合计：7 failed / 1258 passed / 3 skipped**，与既有基线完全同构
（R48 报告：`7 failed, 1254 passed, 3 skipped`，7 条红 = R22/R26/R27/R31/R32 存量词法红）。
通过数 1254 → 1258 的增量 = 本轮新增 2 个用例 + 前几轮已加未计入的用例。**零新增红。**

- 本轮改动面：`src/会话格式.light`（加性）、`src/压缩.light`（加性）、`src/会话日志增量.light`（+1 项）、
  `examples/` 新增 1 个用例 + 既有 1 个用例计数断言同步。**未改任何既有函数语义**；
  `投影表面消息` 的新参数带缺省值，既有调用方不传第二参 → 行为不变（§3.2 的 14 条相关用例已证）。
- ⚠️ 本机 `pytest tests/` 全量直跑（`-n auto`，不拆）实测会出现 `node down: Not properly terminated`
  且**最终汇总行丢失**，宿主同时抛 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`（pytest 临时目录批量清理被拦）
  → 稳妥跑法：**拆成 `tests/test_回归.py` 与其余两段**，并把 `--basetemp` 指向仓库内目录。
  该现象登记为环境/工具链问题，与代码无关。
- 证据日志：`_r51_regress.log`（examples 门禁）、`_r51_lex.log`（其余套件）。

---

## 6. 结论

`image/offload` 事件在本仓**已被显式认识**（两份词汇镜像一致，57 项 = 上游 0.1.6 全集），
其**投影语义逐条对齐**（原子校验 + 叠加投影 + 占位渲染），
`offloadOldestImages` 决策函数已复刻并**用「重复卸载取错下标」判据锁死**。
0.1.6 会话日志在本仓可读、可投影、可校验。验收标准第 1 项达成。
