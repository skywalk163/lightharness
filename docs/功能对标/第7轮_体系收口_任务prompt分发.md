# 第7轮 任务书：体系收口第二轮 —— 事件循环×套接字收敛 + 宿主面可调用化

> 对标窗口：上游 0.2.0-rc.1（`e5b5ccbfcb`，与 R103/R104/R6 同一锚点）
> 现状（R6 已合流，LH `67aea3d`；第6轮五线 A/B/C/D/E + 清单 #254–#290 已 done；github 后台 API 续推中）
> 本轮目标：**收口两大真实缺口**——① #274 事件循环×套接字（light-merge stdlib 跨仓，R6 遗留占位、从未建卡）；② 让「登记」的宿主面单元从「死代码」变「可调用/可测」（E 线第二批：宿主桩出口）。desktop / 真实 OS 内核真执行留第8轮。
> 派单方式：每段「—— 任务线 X ——」下方引号块整体作为派给执行代理的任务正文（`-Task` / 子代理 prompt）。

---

## 0. 实证比对结论（基于当前清单实测，回答「第7轮到底还剩什么」）

对 `对标清单.json` 全量 283 条做状态分类（以状态前缀 `done/已完成/已移植/已核对` 判收口）：

1. **纯逻辑岛屿已基本接完**：R6 + 后续轮的回填使 #255–#290 全部 `done`；开放卡仅 **12 张**。
2. **12 张开放卡结构**：8 张是**宿主登记类**（`#10` hooks 事件 / `#12` 子进程 / `#13` 沙箱 / `#17` 用户审批交互 / `#19` 遥测 / `#20` 代码运行时 / `#21` e2b 云沙箱，外加 `#11` CLI 宿主层 / `#71` webhook 宿主胶水）；其余 4 张为 `#197`（lexer 跨仓，进行中）+ 3 张空条目（`#198–#200`）。
3. **结论**：剩下的「未收口」基本都是**宿主面真实 OS 能力**（真实子进程 spawn / sandbox namespace / e2b / 凭据提供方 / telemetry），按纪律继续以「宿主桩 + 接口契约」存在、**不伪造 OS 能力**。
4. **因此第7轮焦点收敛为两大真实缺口**：
   - **缺口一（跨仓）**：`#274` 事件循环×套接字集成回归——R66/R67/R69 已在 light-merge stdlib 建好 `事件驱动/异步运行时/选择器/伪终端/进程树/并发/流式` 七件套，但散落、跨平台语义未收敛、未被 harness 真正架用，且**从未建卡**。
   - **缺口二（宿主面可调用化）**：R6 的 B/E 线给宿主面单元加了「接桩出口」段，但出口背后**没有可注入的宿主实现**——单元仍是死代码。本轮提供 `宿主桩.light`（内存/事件总线/受控子进程桩），让 `#10/#12/#13/#17/#19/#20/#21` 从「登记不移植」翻成「宿主桩已接(可测)」。
5. **本轮不渝越红线**：真实 OS 执行（真实子进程 / 真实沙箱 namespace / e2b / 凭据提供方）仍以宿主桩存在；`宿主桩.light` 提供的是**内存模拟 + 受控桩**，非真实内核，fail-closed 语义不变。

---

## 1. 线别总览

| 线 | 仓库 | 类型 | 目标 | 落点（新建/接线） | 卡号 |
|---|---|---|---|---|---|
| A | light-merge | 跨仓/stdlib 集成回归 | `#274` 事件循环×套接字：把七件套收敛为统一跨平台 I/O 底座并回归 | `stdlib/lightpub/事件驱动.py`+`异步运行时.py`+`stdlib/选择器.light`+`伪终端.light`+`进程树.light`+`并发.light`+`流式.light` + 测试 | #274（新建） |
| B | lightharness | 宿主面可调用化（E 线第二批） | 提供 `宿主桩.light` 内存/事件总线/受控子进程桩，让「登记」宿主单元可调用可测 | `src/宿主桩.light`（新）+ `src/宿主IO.light`/`钩子.light`/`子进程.light`/`沙箱.light` 接桩出口 | #291（新建）+ 回填 #10/#12/#13/#17/#19/#20/#21 |
| 路M | 两仓 | 收口 | 波及核对 + 跨仓全量门禁 + 对标清单回填 + 交付报告 + github 续推 | `docs/功能对标/第7轮_体系收口_交付报告.md` | — |

卡号自 290 续：A=#274（R6 占位名复用），B 新建模块=#291；B 线其余为回填既有卡。

---

## 2. 文件互斥表（合入零冲突约束）

| 线 | 仓库 | 独占文件 | 共享只读（不得改控制流） |
|---|---|---|---|
| A | light-merge | `stdlib/lightpub/事件驱动.py`、`stdlib/异步运行时.py`、`stdlib/选择器.light`、`stdlib/伪终端.light`、`stdlib/进程树.light`、`stdlib/并发.light`、`stdlib/流式.light`、`tests/test_async_io_light.py`（及新增跨平台矩阵测试） | light-merge 既有其他 stdlib 模块（仅加接口对齐，不改既有纯逻辑） |
| B | lightharness | `src/宿主桩.light`（新）、`examples/test_宿主桩.light`（新） | `src/宿主IO.light`、`src/钩子.light`、`src/子进程.light`、`src/沙箱.light`、`src/交互命令.light`、`src/反馈.light`、`src/远端总线.light`、`src/抓取策略.light`、`src/真实抓取提供.light`、`src/webhook会话.light`（仅加「接桩出口」段，不改既有纯逻辑） |

> 跨仓约束：A 在 light-merge 仓、B 在 lightharness 仓，两仓独立提交、互不冲突。B 内部按段落分区：宿主桩提供方（`宿主桩.light`）与宿主面调用方（`宿主IO/钩子/子进程/沙箱` 的接桩段）分离，互不覆盖。

---

## —— 任务线 A：事件循环×套接字集成回归（light-merge stdlib，跨仓） ——

```
你在 G:\dswork\duan-light-merge\light-merge 工作（注意是 light-merge 仓，不是 lightharness）。上游 deepseek-harness 用 Node 事件循环 + net 套接字做全部 I/O；光明侧已用纯光明/Python 等价实现了一套 I/O 底座（R66/R67/R69 落地），但散落、跨平台语义未收敛、且从没被 harness 真正架用。本线把这套底座**收敛为统一、跨平台、可回归**的 I/O 地基。

【先读】
- 现有底座（已提交，HEAD ca1c93b5，无 WIP）：
  - stdlib/lightpub/事件驱动.py（事件循环：注册读/写、等待、回调派发、取消定时器、跨线程唤醒）
  - stdlib/lightpub/异步运行时.py（async/await 一等等价实现：pending 表/取消信号/flush/流挂接）
  - stdlib/选择器.light（fd 级多路复用：注册/注销/等待/探测就绪，封装 Python selectors）
  - stdlib/伪终端.light（异步 PTY：输出轮询 + 完成回调 + 写输入 + 设窗口大小）
  - stdlib/进程树.light（进程树：有界输出/spill/超时杀树，R64 已补测试）
  - stdlib/并发.light、stdlib/流式.light（非阻塞读原语据此下沉到 selector）
  - stdlib/HTTP服务端.light（非阻塞 TCP 上跑的 HTTP 服务端原型）
- 测试：tests/test_async.py、test_async_io_light.py、test_concurrency_light.py、test_http_server_light.py、test_llvm_net.py、test_harness_e2e_light.py、test_harness_real_channel_light.py。先全跑一遍定位现状绿/红。
- 上游参考（如本地有）：packages 内 event-loop / net socket 用法（仅作语义对齐，不强求改写 harness）。

【收敛任务】
1. 生命周期与取消语义统一：事件循环 / 选择器 / 异步运行时 / 流式 / 伪终端 / 进程树 的「中止令牌」必须贯穿一致（沿用 src/中止.light 的中止令牌），任一层取消都向上冒泡清理 pending 并抛明确取消异常；消除各模块自行其是的取消实现。
2. 跨平台门：
   - Windows 下 ConPTY 管道句柄**不能进 select** → 统一事件源：R66 已用 socketpair 唤醒通道 + 立即调度跨线程投递（queue.Queue + socketpair 非阻塞唤醒），确认四平台（Windows/Linux/macOS/FreeBSD）行为一致。
   - AF_UNIX 仅 POSIX（Windows 置空）已处理，补一条 macOS/Linux/FreeBSD 的 AF_UNIX 回环测试 + Windows 置空断言。
   - 明确不做 HTTP/TLS 之上的业务封装（网络请求.py 已有 HTTP，TLS 移交后续）。
3. 套接字集成回归：非阻塞 TCP/UDP echo（含并发 3 客户端回显一致）、HTTP 服务端（stdlib/HTTP服务端.light）跑通请求/响应帧；验证「远端总线未来可走 socket」的可行性原型（**只出原型 + 基准测试，不强求改写 lightharness 远端总线**）。
4. 文档：在 stdlib 对应模块顶部补「跨平台支持矩阵」注释（各能力在四平台的支持度 + 不支持时的 fail-closed 行为）。

【测试】新增 tests/test_第7轮_io矩阵.py（或并入既有）：
- 正例：事件循环驱动非阻塞 TCP echo（并发 N 客户端一致）、UDP 收发、流式非阻塞读、异步子进程经事件循环输出回调+超时杀树、伪终端增量输出、AF_UNIX 回环（POSIX）/ Windows 置空断言、HTTP 服务端请求响应。
- 跨平台：在 0.82 FreeBSD（192.168.1.5，/usr/local/bin/python3.12）与本机 Windows 各跑一遍，记录绿/红。
- 反跑 3 组：① 事件循环 去掉 socketpair 唤醒通道 → 跨线程 IO 事件丢失用例立红；② 选择器 等待 改成「抛异常替代返回 []」→ 超时语义用例立红；③ 进程树 去掉超时杀树 → 超时用例立红。逐组记「改了什么 → 哪条红 → 已还原」。

【门禁】light-merge 全量（scripts/082全量回归.py 或等价，去 0.82 跑）passed/failed 记录，新增用例全绿；对标清单.json 追加 #274 卡（原版包=core/event-loop + net/socket；光明模块=stdlib/lightpub/事件驱动.py+异步运行时.py+stdlib/选择器.light+伪终端.light+进程树.light+并发.light+流式.light；状态=done；本轮目标=跨平台 I/O 底座收敛+回归；反跑判据=上述 3 组）。**不 commit**（等路M 统一合流）。
```

---

## —— 任务线 B：宿主桩出口批量补齐（lightharness，E 线第二批） ——

```
你在 G:\dswork\duan-light-merge\lightharness 工作。R6 的 B/E 线给宿主面单元加了「接桩出口」段，但出口背后没有可注入的宿主实现，单元仍是死代码。本线新建 src/宿主桩.light，提供内存/事件总线/受控子进程三类桩，让 #10/#12/#13/#17/#19/#20/#21 从「登记不移植」翻成「宿主桩已接(可测)」。

【先读】
- 上游 docs/subsystems/{hooks,sandbox,subprocess,interaction,telemetry,credentials,storage}.md 取契约。
- 光明既有宿主面单元：src/宿主IO.light、src/钩子.light、src/子进程.light、src/沙箱.light、src/交互命令.light、src/反馈.light、src/远端总线.light、src/抓取策略.light、src/真实抓取提供.light、src/webhook会话.light。
- 对标清单 #10/#12/#13/#17/#19/#20/#21（状态均为「v2；0.1.5登记：...宿主...维持登记不移植」）。
- R103 求值能力 手法（mock 入参注入）作为桩注入范式。

【新建 src/宿主桩.light】
1. 内存 IO 桩：实现 宿主IO 的「文件 IO / 进程 IO / 网络 IO」内存版（字典路径↔内容、内存字节流、本地回环），供 B/E 线「接桩出口」段注入；fail-closed 不变（越权/超界仍抛错）。
2. hooks 事件总线桩：pre-tool / PostTool / Stop 三域事件在内存桩里可派发、可订阅、可断言（让 #10 从死代码变可测）。
3. 受控子进程/沙箱桩：进程树.light / 沙箱.light 的真实后端用受控桩替代（按退出码/输出模拟），测试中可断言 进程树/spill/超时 行为；绝不触真实 OS，fail-closed 语义不变。

【接线（每张卡仅加「接桩出口」段到调用方）】
- #10 hooks 事件：src/钩子.light 的「经 宿主IO 真正触发宿主钩子」出口改注入 宿主桩.hooks事件总线桩，三域事件在测试中可断言。
- #12 子进程：src/子进程.light / src/异步子进程.light 真实后端经 宿主桩.受控子进程桩 注入。
- #13 沙箱：src/沙箱.light 真实沙箱后端经 宿主桩.受控沙箱桩 注入。
- #17 用户审批/交互：src/交互命令.light / src/反馈.light 经 宿主桩 内存 IO 注入（审批结果/反馈记录可在测试断言）。
- #19 遥测：src/反馈.light 等遥测落点经 宿主桩 内存 IO 注入（非宿主遥测）。
- #20 代码运行时：src/代码运行时.light（如存在接桩段）经 宿主桩 受控子进程桩 注入。
- #21 e2b 云沙箱：src/e2b客户端.light（本地既有实现）经 宿主桩 受控沙箱桩 注入，验证本地等价行为。
- #71 webhook 宿主胶水（如本轮顺带）：src/webhook会话.light 初始模型监听已对齐，事件总线宿主胶水经 宿主桩 注入。

【约束】每张卡仅加「接桩出口」段，改既有纯逻辑须先 grep 确认无重复实现；真实 OS 执行继续以宿主桩存在，不伪造。

【测试】每张受影响卡至少 1 个 examples/test_<模块>_宿主桩.light：纯逻辑段回归绿 + 经宿主桩拿到预期结果（不触真实 OS）。
【反跑】每张卡 2 组（宿主桩出口断 → 调用方用例红；纯逻辑改坏 → 既有用例红），记「改→红→还原」。
【门禁】各 test 退出码 0；对标清单.json 回填 #10/#12/#13/#17/#19/#20/#21 状态 →「宿主桩已接(可测)/维持宿主登记」；新增 #291（src/宿主桩.light，原版包=host-integration-bus；光明模块=src/宿主桩.light；状态=done；本轮目标=宿主面单元可调用可测；反跑判据=上述）。**不 commit**。
```

---

## 路M：收口元任务（跨仓波及核对 + 全量门禁 + 对标清单回填 + 交付报告 + github 续推）

```
你在 G:\dswork\duan-light-merge 工作，负责第7轮合流收口（跨 light-merge 与 lightharness 两仓）。

【波及核对】
- 复用/更新 lightharness/scripts/_taskM_波及核对.py：TOUCHED 集合更新至第7轮：
  - light-merge 侧：stdlib/lightpub/事件驱动.py、异步运行时.py、stdlib/选择器.light、伪终端.light、进程树.light、并发.light、流式.light、HTTP服务端.light + tests/test_async*.py / test_concurrency_light.py / test_http_server_light.py / test_llvm_net.py。
  - lightharness 侧：src/宿主桩.light（新）+ src/宿主IO.light、钩子.light、子进程.light、沙箱.light、交互命令.light、反馈.light、远端总线.light、抓取策略.light、真实抓取提供.light、webhook会话.light、e2b客户端.light。
- 预计算上游 git diff 增量包路径（e5b5ccbfcb 锚点），逐卡判定覆盖；输出 _taskM_波及核对_out_r7.txt。

【合入零冲突】
- A 在 light-merge 仓、B 在 lightharness 仓，两仓独立 commit，互不冲突。
- B 内部：宿主桩提供方（宿主桩.light）与宿主面调用方（宿主IO/钩子/子进程/沙箱 的接桩段）按 §2 分区，无覆盖。

【回归门禁】
- light-merge 0.82 权威：scripts/082全量回归.py（去 0.82 跑，--base 用最近基线），记录 passed/failed，新增红 0。
- lightharness 本机全量：python 运行.py 跑 examples/test_* 收口集 + 本机全量口径（约 1996 基线），新增红 0。
- 各线 test 文件退出码 0。

【对标清单回填】
- 第7轮新建/回填卡：#274（A 线）、#291（B 线宿主桩.light）；#10/#12/#13/#17/#19/#20/#21 状态翻「宿主桩已接(可测)/维持宿主登记」；#11/#71 如有顺带回填。
- 字段齐：编号/功能/原版包/光明模块/状态(=done 或 宿主桩已接)/证据/本轮目标/反跑判据/语言缺陷。
- 空条目 #198–#200：确认是否无意义，是则删、否则补 功能/原版包/光明模块。

【交付报告】
- 写 docs/功能对标/第7轮_体系收口_交付报告.md（沿用 R6 结构：目标结果一览/各线摘要/改动文件/回归门禁/路M 合入/波及核对）。
- 含「第8轮展望」：desktop/desktop-host 外壳、真实 OS 执行内核（真实子进程/sandbox namespace/e2b/凭据）真执行、#263–#268 跳号历史遗留卡。

【github 合流续推】
- 两仓分别 commit；推送 myrepo(gitea)/origin(gitcode) 直推；github 走 `python _push_github_api.py`（lightharness 仓保留脚本；light-merge 仓若需推同步用其自身脚本）。推送后 `git ls-remote <remote>` 复核 = 新 HEAD。
```

---

## 3. 本轮不做 / 后续轮展望

- **apps/desktop、apps/desktop-host**：Electron 原生壳 + 原生能力桥，体量巨大且强宿主绑定，留第8轮。
- **真实 OS 执行内核**（真实子进程 spawn / 真实沙箱 namespace-seccomp / e2b 云端 / 凭据提供方 OS 集成）：本轮以**宿主桩**形式可调用可测；真执行后端留平台侧 / 第8轮接真实后端或确认永久宿主绑定。
- **#263–#268 跳号历史遗留卡**（R6 从未分配）：如确需可于第8轮补。
- **github 合流续推**：代理通畅后用 `python _push_github_api.py` 续推（保留脚本）。

> 第7轮定位为「体系收口第二轮」：把 R66/R67/R69 建好的 I/O 底座收敛为跨平台可回归地基（#274），并让此前「接了出口却无后端」的宿主面单元真正可调用可测（宿主桩，#291 + #10/#12/#13/#17/#19/#20/#21）。完整体系复刻（含 desktop 与真实 OS 内核）仍需第8轮。
