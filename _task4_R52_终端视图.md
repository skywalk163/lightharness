# 任务4（R52·P2）交付报告 —— terminal-controller 视图状态机

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：`src/终端.light`（追加 §第52轮 段）、`examples/test_R52_终端视图.light`、本报告
> 上游基线：deepseek-harness 0.1.6-alpha.1（ea53423b60）
> `packages/api/terminal-controller/src/client/model.ts` + `src/stream.ts` + `src/client/close-requests.ts`
> 铁律遵守：不接真实 PTY/宿主；既有终端测试不破（test_终端 / test_终端PTY 全 rc=0）。

---

## 一、上游对照（只读）

| 上游文件 | 对齐面 |
|---|---|
| `client/model.ts` | `TerminalViewIssue`（五值）、`TerminalViewState.phase`（九相位）、`TerminalRenderFrame`、`consume` 的帧校验状态机（代切换须以 snapshot 开场 / output 序号严格 +1 / 同代中途 snapshot 非法 / 非 output 帧 patch info+可写 / 非 state 帧渲染修订）、`fail` 的错误→相位/问题映射、`write` 的准入三条件与 `maxInputBytes` 配额（inputFull）、`resize` 的相同忽略与环境钳制 |
| `stream.ts` | `TerminalFollower`：有界字节输出队列——慢消费者显式失败（超预算 → 失败+关闭，"Terminal output consumer exceeded its buffer; reconnect to recover the current screen"）、完结后推入忽略、读循环（队首/等待/完/失败在排空后上抛） |
| `client/close-requests.ts` | `TerminalCloseRequest`（sessionId 非空 + id `^[\w-]{1,128}$` + title）、`TerminalCloseRequests`：键前缀 `dsh.terminal.close.v1.`、每请求独立键、save/pending/remove、load 的形状+键 id 一致性校验（"Invalid terminal cleanup request"） |

## 二、修改（src/终端.light 末尾追加，全部为加性段，既有 终端会话/伪终端会话 零改动）

- **词表与形状**：`视图问题表`/`视图相位表`/`是渲染帧`/`是视图状态`/`是终端信息`/
  `判数值宽`/`是无损JSON宽`（本地实现避免跨模块耦合）；
- **帧消费状态机**（consume 纯化）：`造帧消费机`/`帧消费机吃帧`——机内累积补丁表，
  返回 `{机, 失败}`；四种非法输入（代切换遇 output、序号缺口、同代中途 snapshot、非字典帧）
  统一记 `invalidOutput`；非 output 帧 patch `{info, title, phase: connected,
  writable: state==running 且 controllerId==挂载标识}`；非 state 帧 render.revision 递增；
- **失败映射**：`视图失败映射`——`terminal/control-unavailable` 仅失写不改相位、
  `terminal/limit-reached` → `terminalLimit`、流载具错误 → `disconnected`、其余 → `failed`；
- **写入**：`写入准入`（非 writable/无 info/无挂载标识 → 忽略）+ `输入配额判定`（排队+新增
  > 上限 → `inputFull`）；
- **尺寸**：`尺寸未变`/`尺寸钳制`（列/行钳到环境 maxCols/maxRows，无环境用原值）；
- **跟随器**：`造视图跟随器`/`跟随器推入`/`跟随器完结`/`跟随器关闭`/`跟随器读一步`
  （字节由调用方传入，与上游 `{frame, bytes}` 载荷一致；字节计算是宿主面）；
- **关机请求簿**：`关机键前缀`/`造关机请求簿`/`是关机请求`/`关机簿保存`/`关机簿移除`/
  `关机簿待办`/`关机簿载入`（localStorage 宿主面剔除 → 纯内存表）。

## 三、验证结果

| 项 | 结果 |
|---|---|
| `python 运行.py examples/test_R52_终端视图.light` | **rc=0，全断言通过** |
| 判据规模 | 7 大组约 85 组断言 |
| 既有回归 | test_终端 / test_终端PTY / test_R52_远程mock / test_mock大模型服务器 全 rc=0；pytest 子集 846 passed / 3 failed = 基线存量，零新增红 |

判据覆盖要点：词表精确值；形状谓词真假例（含 129 位 id 拒绝的边界）；帧消费四类非法
输入全命中 + 连续 output/快照开场/state 无渲染/异挂载不可写/exited 不可写等合法路径；
失败映射四支；写入准入三条件与配额两态；尺寸忽略与钳制；跟随器字节累计扣减/超预算
失败+关闭/完结后忽略/失败排空后上抛/等待与关闭态；关机簿保存/待办/移除/载入键一致性。

## 四、已登记偏差

- **D-1**：`SnapshotStore`/`AbortController`/`Promise` → 纯字典状态机；`consume` 的
  「等 xterm 回调再放行流项」压缩为同步补丁累积（渲染确认是 DOM 宿主面）；
- **D-2**：`TerminalView` 的 refresh/connect/write/rename/close 远程调用编排属宿主面，
  本轮只取其纯决策核（校验、配额、映射、钳制），编排层不移植；
- **D-3**：跟随器帧字节由调用方传入（上游 `Buffer.byteLength(JSON.stringify(frame))`
  是 Node 宿主面）；光明侧按字符/字节等价由调用域决定；
- **D-4**：关机请求簿的 `localStorage` 持久化剔除为纯内存表；键前缀与每请求独立键的
  语义在 `关机簿载入` 的键 id 一致性校验中保留；
- **D-5**：`frame.info.state` 为上游终端状态字符串（running/exited），谓词按字符串接受。
