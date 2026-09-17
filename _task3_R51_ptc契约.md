# 任务3（R51·P1）交付报告 —— ptc-runtime 保留字表 + PtcRun 契约

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：`src/代码运行时.light`（追加 §第51轮 段）、`examples/test_R51_ptc契约.light`、本报告
> 上游基线：deepseek-harness **0.1.6-alpha.1（ea53423b60）**
> `packages/ptc-runtime/ptc-runtime/src/{index.ts, types.ts}`
> 铁律遵守：#84 已覆盖的 fd-3 线缆帧面（`src/代码运行时协议.light`，protocol.ts）零改动；
> 既有代码运行时测试不破。

---

## 一、上游对照（只读）

0.1.6-alpha.1 将 `packages/code-runtime` 改名为 `packages/ptc-runtime`，其中纯逻辑新增面：

- `index.ts` 词表常量：
  - `PORTABLE_RESERVED_WORDS`：ECMAScript 保留字/严格模式保留名（48 词，含 `arguments`/`eval`/`let`/`static`/`implements` 等）∪ Python 3 关键字与软关键字（23 词，`type`/`_` 按安全口径一并保留）——**71 词一份并集**，保证同一命名空间表在任何后端都合法（per-language 校验会让 `lambda` 过 TS 后端、挂在 Python 后端）；
  - `RESERVED_BINDING_GLOBALS`（5 名）：`console`（Node 日志捕获槽）、`__dsh_main__`/`__builtins__`/`__name__`（Python 引导与模块全局）、`__debug__`（CPython 编译期常量，注入不可达）；
  - `RESERVED_ERROR_MEMBERS`（6 名）：JS `Error` 排除（`name`/`message`/`stack`）+ Python 异常协议成员（`args`/`with_traceback`/`add_note`）；
  - `DUNDER_MEMBER`（`/^__.+__$/`）：对象协议槽位整体按形式拒绝（具体集合是解释器版本细节）；
  - 便携标识符契约：`[A-Za-z_][A-Za-z0-9_]*` 全串。
- `types.ts` PtcRun 契约族：`PtcJsonValue`（无损 JSON）、`PtcBindingNamespace`（`global`/`functions`/`errorClass?`）、`PtcBindingErrorClass`（`name`/`memberNameProperty`）、`PtcRunRequest`（`program`/`bindings`/`cwd?`/`timeoutMs?`/`sandboxPolicy?`/`signal?`）、`PtcRunSpec`（cwd 必填、timeoutMs 必填 number|null）、`PtcRunSandbox`（`mode`/`denied`/`enforcement?`）、`PtcRunFailure`（**八类正交终态**：exception/timeout/abort/worker-exit/invalid-output/output-limit/protocol/sandbox-unavailable——预算过期不是异常、中止不是超时、底座死亡二者皆非）、`PtcRunResult`（错误是**字段**而非拒绝路径）。

## 二、修改（src/代码运行时.light 末尾追加，全部为加性段）

| 段落 | 对齐 |
|---|---|
| `便携保留字表` / `保留全局表` / `错误成员保留表` | 三个词表常量，逐词对齐 |
| `是dunder成员` | `/^__.+__$/` 语义（首尾 `__` + 中间非空；`____` 不匹配） |
| `是便携标识符` | 锚定正则全串匹配 |
| `校验命名空间名` / `校验错误类名` | 三支分立诊断：`invalid portable identifier` / `reserved word` / `reserved binding global`（空串 = 合法） |
| `校验错误成员名` | 四支拒绝：非串 / 空串 / 保留成员 / dunder 形式 |
| `是无损JSON值` / `是无损JSON深层` / `是有限浮点` | PtcJsonValue 无损递归谓词（有限浮点拒绝 inf/nan；防御性深度上限 128） |
| `是错误类形状` / `是绑定命名空间` | 契约形状谓词（errorClass 可选） |
| `是运行请求` | Request 形状（program 非空串、bindings 全为合法命名空间、timeoutMs 数值或空） |
| `造运行规约` | `resolve` 纯化：缺 cwd 拒绝（spec 绝不带缺省目录）；timeoutMs 缺省 → 提供方默认；null → 无限期；数值须正有限且 ≤ 上限（返回 `{"规约", "错误"}`） |
| `运行失败种类表` / `是运行失败` / `是运行沙箱` / `是运行结果` | Failure 八类 taxonomy + Sandbox/Result 形状谓词（错误是字段） |

与既有面分工：`代码运行时.light` 既有子进程执行类不动；`代码运行时协议.light`（#84）fd-3 帧语义不动——本节是 0.1.6 新增包的**词表 + 执行缝契约**纯逻辑面。

## 三、验证结果

| 项 | 结果 |
|---|---|
| `python 运行.py examples/test_R51_ptc契约.light` | **rc=0，全断言通过** |
| 判据规模 | 7 大组约 90 组断言 |
| 既有回归 | test_代码运行时 / test_代码运行时协议 / test_代码运行时深化 / test_宿主运行时 / test_R38_工具展示 / test_R38_集成测试 全 rc=0 |
| pytest 子集（除 examples 回归门外 23 文件） | 846 passed / 3 skipped / **3 failed = R50 基线同名存量词法红**（R31 EMBED×2 + R32×1），零新增红 |
| 本机全量 pytest（examples 回归门） | 归路M收口统一执行（任务6） |

判据覆盖要点：71 词规模与关键成员抽查（`lambda`/`type`/`_` 软关键字在表、`console` 只在保留全局不在保留字）；dunder 八例边界（`____` 空中段不匹配）；命名三支/成员四支拒绝全分支；无损 JSON 递归与非 JSON 类型（函数对象）拒绝、超深拒绝；resolve 六分支（默认/无限期/零/负/超帽/缺 cwd）；八类 taxonomy 全遍历；结果「错误是字段」语义。

## 四、已登记偏差

- **D-1**：`PtcBindingFunction` 为宿主异步函数引用，跨语言不可判型——纯逻辑化按
  「`functions` 为字典且键为非空串」的键形状校验（上游由类型系统承担）；
- **D-2**：`SandboxMode`/`SandboxEnforcement` 来自上游 sandbox 包，光明侧按字符串词汇接受；
- **D-3**：`PtcJsonValue` 深度上限 128 为光明实现防御（上游 TS 递归无显式上限），
  防循环结构递归爆栈；
- **D-4**：`resolve` 的数值预算校验规则（正/有限/≤cap）自上游 provider 契约提炼为纯函数；
  抛错改为 `{"规约", "错误"}` 诊断返回（与 R48 校验载荷风格一致）；
- **D-5**：`signal`/`sandboxPolicy` 为宿主运行期对象，不进纯逻辑谓词面。
