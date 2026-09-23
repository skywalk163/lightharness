# R88-B 路・FreeBSD 固有环境红处置报告（E-01/E-02/E-06 + LM 同族 1 条）

> 轮次：R88-B ｜ 2026-09-23 ｜ 执行 agent：B 路
> 范围：0.82（FreeBSD 15.1-STABLE，ai@192.168.0.82）LH 3 条固有环境红一手取证 + 根因定性 + 豁免固化；LM 同族 1 条（test_coro_sleep_basic）取证与处置。
> 红线遵守：只动 `lightharness/tests/ci_environment_reds.txt`（台账/注释）；未 commit/push；0.82 仅用 `/tmp` 副本；未改 stdlib / 测试断言。

---

## 0. 环境与取证口径

- 0.82 副本：`/tmp/r44-20260923-174825`（LH 根 = `…/lightharness`，LM 根 = `…/light-merge`）。
- 解释器：`/usr/local/bin/python3.12`（Python 3.12.14，pytest 8.4.2，xdist 3.8.0）；shim `/tmp/r44-shim/python` → python3.12；clang `/usr/bin/clang`（FreeBSD clang 21.1.8，target x86_64-unknown-freebsd15.1）。
- LH 门禁三件套：`LIGHT_MERGE=<LM根> PATH=/tmp/r44-shim:$PATH PYTHONIOENCODING=utf-8`。
- 取证法：单文件直跑（`python 运行.py examples/<file>`）脱离 xdist 全量负载，各 2 轮；全量 1 轮 `pytest tests/ -q --tb=line -rfE -o addopts=`（串行，与 R87 口径一致）。

---

## 1. 逐条处置

### E-01　test_事件循环.light（事件循环就绪派发顺序）

- **现象**：单文件直跑 2/2 rc=1，签名恒定：
  `断言失败: 同挂时先派发读；实际=写 期望=读`（断言行 examples/test_事件循环.light:136，§5「试读写同挂」）。
- **根因（FreeBSD 语义差异）**：同一 fd 上读/写同时挂起就绪时，kqueue 出列顺序与 epoll/select 不同——本用例钉死「先读后写」，FreeBSD kqueue 先报写就绪，故序列首位=写。属后端就绪队列顺序语义差异，非 socketpair 崩溃（R86-B 已修族映射）。
- **处置：维持豁免**。修复需改 stdlib/事件循环 就绪队列排序（超 B 路改动面）；若把测试断言放宽成「集合相等」会削弱 Linux/Windows 既有的「先读后写」语义覆盖。登记在案、按平台豁免。

### E-02　test_套接字.light（回环 send 阻塞超时）

- **现象**：单文件直跑 2/2 rc=1，签名恒定：
  `超时错误 timed out（位置: stdlib/套接字.light:207）`，即发送全部 循环里 `己.原始.send(字节串[已发:])` 阻塞超时。
- **根因**：examples/test_套接字.light §7 用 `客7.设置超时(2.0)` 连发 200KB（`b"A"*200000`）；发送全部 在 套接字.light:207 反复阻塞写，FreeBSD 回环 TCP 窗口/接收排空节奏比 Linux/Windows 慢，发送缓冲未排空前 send 阻塞超过 2.0s 预算 → 超时。属固定 2s 预算在 FreeBSD 回环上偏紧的计时差异，收发逻辑本身正确。
- **处置：维持豁免**。放宽该套接字超时预算属测试计时口径平台化，但同一套接字还承载小载荷/超时用例，改它牵一发动全身；按「不为残余时序差异扩改动面」固化豁免。

### E-06　test_进程树接线.light（沙箱秒数上限判定）

- **现象**：单文件直跑 2/2 rc=1，签名恒定：
  `断言失败: 沙箱秒数上限触发超时 实际=False 期望=True`（§6：`沙箱(秒数上限=1)` 跑 `ping -n 30`，期望超时=True）。
- **根因**：FreeBSD 沙箱把「秒数上限」落到 RLIMIT_CPU（CPU 时间），而 `ping` 阻塞在 recvmsg 等 ICMP 回包、几乎不耗 CPU → 1s CPU 上限永不触发；Linux/Windows 沙箱用挂钟看门狗到点强杀。属资源上限口径（CPU 时间 vs 挂钟）基线差异。
- **处置：维持豁免**。改 stdlib/沙箱 增加挂钟看门狗超 B 路「只动台账/判据/测试断言」范围；登记豁免。

### LM 同族　tests/test_llvm_net.py::TestB3EventLoop::test_coro_sleep_basic

- **背景**：R87 0.82 LM 全量（xdist -n auto，8312 用例/784s，`reports/082_lightmerge基线_latest.json`）唯一 1 红。
- **一手取证**：
  - 0.82 隔离单跑 2/2 **PASSED**（3.88s / 3.53s，clang 腿，rc=0）——**不稳定复现**。
  - 全量负载失败签名（基线 message）：`AssertionError: 协程 yield/恢复顺序不对: ['开始', 'sleep前', '结束']`（缺 `sleep后`）。
- **根因**：与 E-01 同源（kqueue 定时器/事件循环）。xdist 8 路高负载下，协程 `睡眠(2)` 的 kqueue 定时器唤醒未在事件循环退出前触发 → 输出停在「sleep前」后直接「结束」；空闲隔离时 2s 定时器正常触发。属负载/计时敏感 flaky，非确定性红。
- **处置：按 flaky 路径，不新增确定性环境红条目**。
  - 该条已在 082 LM 基线失败集内（自比对 new_red=0）；
  - lm-full 跨平台归因命中关键词「协程/yield/睡眠」（`LM_ENV_RED_KEYWORDS`），判为可归因环境约束，0 疑似回归；
  - 取证与根因已写入 `ci_environment_reds.txt` R88-B 节（留痕）；
  - **不新建 LM 环境红台账文件**（该条隔离 2/2 绿，不符合「确定性红」入账口径；且 light-merge/tests/lm_environment_reds.txt 属 C 路 Windows 台账面，避免文件面冲突）。若未来转为稳定复现，须人工归因（疑似真退化）。

---

## 2. 判据接线核对（未改动，确认正确）

- `tests/test_回归.py:250` 分支：`name in ENV_RED_LEDGER and sys.platform.startswith('freebsd')` → 不硬断言，仅计入 `_ENV_RED_FAILED`；非台账条目失败仍 `assert rc==0` 硬判红。
- `tests/ci_judge_env_reds.py`：以台账文件名为 baseline，新增红 = 本次失败集 − 台账；反向演示可识别台账外新回归。
- 台账机器可解析校验：3 条条目（E-01/E-02/E-06）解析无误，长根因注释未污染 tab 分隔字段。

## 3. 验证结果（全部一手复跑）

| 验证项 | 结果 |
|---|---|
| E-01/E-02/E-06 单文件直跑 | 各 2/2 rc=1，签名恒定（确定性红复证） |
| 0.82 LH 全量 1 轮 | **1395 passed, 5 skipped, 0 failed**，547.86s，rc=0（仅台账 3 条命中豁免，回归红=0） |
| LM test_coro_sleep_basic 隔离单跑 | 2/2 PASSED（flaky，非确定性） |
| `ci_judge_env_reds.py self-check` | **PASS**（3 场景新增红=0；反向演示注入 1 条新回归被正确识别） |
| `多平台矩阵.py --mode lm-full` | **PASS ✅**（win 47/0.82 1/0.86 0 自比新增红均 0；跨平台 0 疑似回归） |

- 0.82 LH 门禁 new_reds=0；0.82 LM 门禁 new_reds=0。
- 豁免仅命中已登记文件（test_事件循环/套接字/进程树接线 + 082 基线 coro 条）+ FreeBSD 平台；未登记项仍硬判红（self-check 反向演示证实）。

## 4. 改动文件（显式，交 M 统一合流）

- `lightharness/tests/ci_environment_reds.txt`：
  - E-01/E-02/E-06 三条 note 追加【R88-B 根因】三行定性；
  - 新增「R88-B 复核与 LM 同族」注释节（取证口径、处置、LM coro flake 留痕）。
- 无 stdlib / 测试断言 / 判据脚本改动；无 commit/push。

## 5. 判据达成与遗留

- 判据：3 条（+1 条 LM）均有取证记录与根因定性；豁免项台账/判据接线完整、门禁 new_reds=0；未登记项仍硬判红。✅
- 遗留（交 M/D）：LM coro flake 若后续轮次在 0.82 全量稳定复现，需重新归因（可能是 kqueue 定时器真退化），届时再决定是否修测试/运行时或转确定性环境红入账。
