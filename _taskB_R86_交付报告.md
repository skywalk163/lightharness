# R86 任务 B 交付报告：套接字平台适配（socketpair 族 + TCP 选项级别）

> 轮次：R86 路 B　｜　日期：2026-09-22　｜　提交：`db164c2`（lightharness）
> 范围：清 0.86 Linux 上 8 条套接字平台差异（socketpair 7 处调用面 + setsockopt 1 处）
> 结论：**0.86 上 7 个受影响 example 全部转绿，0.86 LH 全量 24 红 → 7 红且新增红 0；Windows 不回归（最终 1371 passed / 0 failed / 4 skipped）**

---

## 1. 结论速览

| 项目 | 基线 | 本轮后 | 说明 |
|---|---|---|---|
| 0.86 Linux LH 全量 | 1347 passed / **24 failed** / 4 skipped | 1362 passed / **7 failed** / 6 skipped | 清零 17 条、**新增红 0**；剩 7 条属 A 路（词法 5，在途）与 D 路（沙箱 2，在途） |
| Windows 本机 LH 全量 | 1357 passed / **14 failed** / 4 skipped | **1371 passed / 0 failed / 4 skipped** | 与 A/B/C 三路合流后复跑（`reports/R86_B_Windows_LH基线.json`） |
| 路 B 直接目标（7 个 example） | 0.86 上 7 个全红 | 0.86 与 Windows **7/7 全绿** | 反跑：4 文件整体回退 → 7/7 全红；恢复 → 0/7 全绿（PASS） |

路 B 覆盖的 7 个 example：`test_套接字` / `test_事件循环` / `test_套接字事件循环` / `test_异步PTY` / `test_异步子进程` / `test_lambda_e2e` / `test_R70_交叉验证`。

---

## 2. 根因（0.86 实机一手证据，非推断）

在 0.86 上用**纯 Python 探针**（不经过光明解释器，避免与语言层混淆）实测：

```
sys.platform = linux   uname = Linux-6.8.0-139-generic x86_64   python = 3.12.3   uid=1001
常量：SOL_SOCKET=1  SO_DEBUG=1  SO_REUSEADDR=2  TCP_NODELAY=1  IPPROTO_TCP=6
setsockopt 逐项：
  SET OK   (SOL_SOCKET=1,  SO_REUSEADDR=2, 1)
  SET OK   (SOL_SOCKET=1,  SO_RCVBUF=8, 65536)      # 读回 131072（内核翻倍）
  SET OK   (SOL_SOCKET=1,  SO_SNDBUF=7, 65536)
  SET ERR  (SOL_SOCKET=1,  TCP_NODELAY=1, 1)  => PermissionError errno=13 EACCES
  SET OK   (IPPROTO_TCP=6, TCP_NODELAY=1, 1)  => 正确级别可用
  SET ERR  (SOL_SOCKET=1,  SO_DEBUG=1, 1)     => PermissionError errno=13 EACCES
socketpair 地址族支持面：
  AF_INET  => OSError errno=95 EOPNOTSUPP
  AF_INET6 => OSError errno=95 EOPNOTSUPP
  AF_UNIX  => OK (fd 3,4)
```

### 根因 1：`socketpair(AF_INET)` 在 POSIX 上不支持（7 条中的 6 条）

- `socket.socketpair` 只有 **Windows 支持 AF_INET/AF_INET6**；**POSIX（Linux/FreeBSD/macOS）只支持 AF_UNIX** → `EOPNOTSUPP(95)`。
- 影响面被**放大**：`事件循环.light` 的**跨线程唤醒通道**用它建对，于是「`事件循环()` 建不起来」连带炸掉所有依赖事件循环的用例（异步子进程 / 异步 PTY / 套接字事件循环 / lambda_e2e / R70 交叉验证），**6 条红只有一个根因**。
- R66/R68 起就有此遗留（`docs/多平台差异清单.md` 已登记「事件循环测试 socketpair 改 AF_UNIX」），本轮落地。

### 根因 2：`setsockopt(SOL_SOCKET, TCP_NODELAY, …)` 是**级别用错**，不是 0.86 环境限制

- POSIX 上 `SOL_SOCKET == 1` **且** `TCP_NODELAY == 1` → `setsockopt(1, 1, 1)` 被内核解析成 **`SO_DEBUG`**（需要 `CAP_NET_ADMIN`）→ **EACCES(13)**；探针里 `(SOL_SOCKET, SO_DEBUG, 1)` 报同一个错，**直接指认**了这次误解析。
- Windows 上 `SOL_SOCKET == 0xffff`，同一 optname 虽然也落 SO_DEBUG，但**不校验权限** → 静默通过。这就是「本机一直绿、Linux 红」的原因。
- 因此按分发书 §B 的三分支裁决：**不是「0.86 特定选项受限」→ 不降级断言；是 stdlib/调用面缺陷 → 修 stdlib + 调用点**。

### 附带发现（写入 skill，避免下轮再踩）

1. **`空` 编译成 Python `None`**（`cli.light._compile_src` dump 实证：`新建套接字对(None, True)`）。
2. **Linux 的 `socket.socketpair(None, SOCK_STREAM)` 会静默落到 AF_UNIX（实测 OK，fd 3/4）**，而 Windows 抛 `ValueError`。→ 反跑时**只回退 stdlib 会得到假绿**（新调用点传 `空` 在老 stdlib 上照样能跑），必须**受影响文件整体回退**（见 §4 反跑）。

---

## 3. 改动清单（4 文件 / +98 −15，全部 lightharness）

### `stdlib/套接字.light`（+56 −2）
- 新增 `导入 sys`、常量 `IPPROTO_TCP`。
- 新增 **`平台是否Windows()`**（`getattr(sys,"platform","")=="win32"`，兜底不炸）。
- 新增 **`套接字对可用族(地址族)`**：win32 原样（`空`→AF_INET，`AF_UNIX` 为空 → AF_INET）；POSIX 上 `空`/`AF_INET`/`AF_INET6` → `AF_UNIX`；其余原样返回。平台差异**在 stdlib 收口**，不外溢到业务。
- `新建套接字对(地址族, 是否非阻塞)` 先 `设 用族 为 套接字对可用族(地址族)` 再建对。
- 选项区加 **level 语义警示**（SO_* → SOL_SOCKET；TCP_* → IPPROTO_TCP；含 SO_DEBUG/EACCES 的解释）。
- 新增 **`设置不延迟(是否启用)` / `读取不延迟()`**（固定走 IPPROTO_TCP，常量缺失时静默降级）。
- 导出 `IPPROTO_TCP` / `平台是否Windows` / `套接字对可用族`。

### `stdlib/事件循环.light`（+3 −2）
- 唤醒通道 `新建套接字对(AF_INET, 真)` → **`新建套接字对(空, 真)`**（平台默认）；去掉不再需要的 `AF_INET` 导入。

### `examples/test_事件循环.light`（+9 −5）
- 4 处 `新建套接字对(AF_INET, 真)` → **`新建套接字对(空, 真)`**；导入区加平台默认族说明。

### `examples/test_套接字.light`（+30 −5）
- 选项组：`TCP_NODELAY` 改用 **`IPPROTO_TCP` 级别**；补 `设置不延迟/读取不延迟` 往返断言；
  `SO_REUSEADDR` 读回断言从「`== 1`」改为**开关语义可往返**（`设 1 → !=0`、`设 0 → ==0`、再置开），因为读回值是实现定义（**Linux=1 / FreeBSD=4**，R68 实测）。
- 套接字对组：**保留 `AF_INET`** 以验证兼容映射（三平台都合法），并**补 `空`（平台默认）路径**的建对+收发断言与 `套接字对可用族(空) != 空` 断言。
- 头注释与尾行输出口径同步。

**文件面**：与 A（`tests/test_R*_token.py`）、C（`examples/test_async_await.light`）、D（`src/沙箱*.light` + `examples/test_沙箱*.light`）**零重叠**。

---

## 4. 判据自检

### 4.1 双平台复跑

| 平台 / 口径 | 结果 |
|---|---|
| Windows 本机（合流后全量，`-n auto`，`reports/R86_B_Windows_LH基线.json`） | **1371 passed / 0 failed / 4 skipped**（total 1375，264.6s） |
| Windows 本机（B 目标 7 例，改动后） | **7/7 rc=0** |
| 0.86 Linux（B 目标 7 例，最新树） | **7/7 rc=0**（`test_套接字` 打印「9 组 / …+选项(TCP级别)+…+套接字对(平台自适应)+…」） |
| 0.86 Linux 全量（本路改动 + A 部分在途，`reports/R86_B_0.86_LH基线.json`） | 1362 passed / **7 failed** / 6 skipped；**新增红 0**（7 条全部 ⊆ 基线 24 条） |

0.86 全量剩余 7 条（均非 B 范围，全部在基线 24 条内）：
- `test_R30_零除幂次记录类型通用化_token.py` ×3、`test_R31_EMBED表保留+flaky修复_token.py` ×2 → **A 路词法断言**（本轮在途；A 已提交 `1e10ef5` 对齐 R58 现状）。
- `test_沙箱探测.light`、`test_沙箱统一.light` → **D 路沙箱**（在途）。

> 0.86 全量的**最终 0 红**由 M 路在 A~D 全部合流后复跑认定；本路只对「B 的 7 条」负责，已全部清零且可反跑自证。

### 4.2 中途口径的两条 Windows 红（已归因，非 B 引入）

首次 Windows 全量（12:11 树态，A 路断言改动**部分**在途）为 8 failed / 1363 passed / 4 skipped。其中：
- 6 条 = A 路当时在途的词法红（`test_R21` ×1 / `test_R30` ×3 / `test_R31` ×2），A 合流后已清；
- 2 条 = `test_回归.py::test_example_exit_code[test_会话存储.light]` 与 `[test_进程树接线.light]`：
  **隔离复跑各 2 次全绿**（`rc=0`）→ 并行（xdist 期间出现 `[gw1] node down`）下的**偶发红**，非代码回归；
  `test_会话存储.light` 本就在既有 flaky 名单里。合流后复跑这两条也全绿（0 failed）。

### 4.3 反跑判据（0.86 实机，PASS）

```
断裂态：4 个受影响文件 → git HEAD 版（逐文件 md5 核验）→ 7/7 全红
修复态：4 个文件 → 工作树版（逐文件 md5 核验）      → 0/7 全绿
判据：PASS
```

⚠️ **v1 教训（已固化进 skill）**：只回退 `stdlib/套接字.light` 时，走唤醒通道的 6 条**仍然绿**——因为 Linux 把 `socketpair(None,…)` 当默认族落到 AF_UNIX，而新调用点传的正是 `空`。断裂态必须**整组回退**，否则是**假绿**。

### 4.4 其他判据

- `test_套接字` 9 组断言在 **0.86 全绿**（TCP 阻塞回环 / 非阻塞 accept / 非阻塞 recv / 超时 / 选项(IPPROTO_TCP 级别) / UDP 回环 / 字节层 / 套接字对(平台自适应) / 地址族常量）。
- **事件循环 echo 服务器 e2e 在 0.86 实测可用**：`test_套接字事件循环.light`（4 组：多客户端并发回显 + EOF 拆链 + 定时器清理 + 优雅关闭）绿；**唤醒通道**由 `test_事件循环.light` 第 7 组（跨线程 `立即调度`，依赖 socketpair 唤醒）绿坐实。
- 全仓已无「同一坑」的残留调用点：`grep -rn "socketpair\|TCP_NODELAY\|setsockopt"` 复核——`stdlib/HTTP服务端.light:76-77` 建监听套接字用 `socket.socket(AF_INET, SOCK_STREAM)`、`SO_REUSEADDR` 走 `SOL_SOCKET`（**级别正确**，无需改）；`stdlib/lightpub/*.py`、`src/真实HTTP客户端.light` 均为「AF_INET + SOCK_STREAM 的真实 TCP 套接字」，与 socketpair 无关；`light-merge/tests/*` 里的 `socket.socketpair()` 无参调用（默认族）已是跨平台写法。

---

## 5. 边界与遗留（交 M 路）

1. **文档回填属 M 路**，本轮未动（避免文件面冲突）。建议改动点（已核对行号）：
   - `docs/多平台差异清单.md`：
     - §1 汇总表 `:100`「原生 socket **FAIL**（SO_REUSEADDR getsockopt 平台差异）」→ 本轮已把断言改成不钉死数值，预期 PASS（FreeBSD 待复跑）；`:101`/`:102`「事件循环 / 事件循环+socket **FAIL**（socketpair(AF_INET) 不支持）」→ **PASS（已修复 R86）**。
     - §6 `:165` `SO_REUSEADDR getsockopt` 行、`:166` `socketpair(AF_INET)` 行 → 状态改「已修复（R86）」并补一句修复方式（stdlib `套接字对可用族` 平台映射 + 断言改开关语义）。
     - §8 `:180`「遗留（R66 模块 FreeBSD 适配）… 修复后重跑 `freebsd/远程回归.sh` 预期 13/13 全绿」→ 本轮两项均已处置，**待 0.82 复跑坐实 13/13**。
     - §2.1 `:216`（socketpair 条目）与 `:217`（`test_套接字` setsockopt EACCES 条目）→ 填「R86 已修 + 根因」（后者根因是 **level 用错**，不是 0.86 环境限制）。
   - `docs/功能对标/行为差异清单.md:886`「事件循环 的跨线程唤醒通道用 新建套接字对(AF_INET) 而非 pipe」→ 应改为「用**平台默认族**套接字对（win32=AF_INET / POSIX=AF_UNIX），R86 起由 stdlib 收口」。
2. **FreeBSD（0.82）未跑**：本轮改动对 FreeBSD 同样是「POSIX 分支」（socketpair→AF_UNIX），且顺手把 `SO_REUSEADDR` 读回断言改成不钉死数值（FreeBSD 返回 4），预期 0.82 的 R68 遗留红也会转绿；建议 M 路的三平台复跑带上。
3. `reports/R85_lh基线_latest.json` 被本路 test-lh 覆盖为「B 改动 + A 在途」的中间态（未提交）；M 路收口时会重新生成，无需回填。
4. 本轮临时脚本（均在**仓库根**，不进版本库）：`_r86b_probe086.py`（0.86 环境探针）、`_r86b_patch.py`（带哨兵的幂等补丁）、`_r86b_remote.py`（0.86 单例快跑）、`_r86b_antirun.py`（反跑判据）、`_r86b_diff.py`（双平台对账）、`_r86b_probe.light`（能力探针）。

---

## 6. 提交与证据

- 提交：`db164c2 R86-B: 套接字平台适配 — socketpair 族平台映射 + TCP 选项级别修正（0.86 7 红清零）`（只含 4 个源码文件 + 本报告 + 证据 JSON，未 push）
- 证据：
  - `reports/R86_B_0.86_LH基线.json`（0.86 全量 1362/7/6 口径，含失败清单）
  - `reports/R86_B_Windows_LH基线.json`（Windows 全量 1371/0/4）
  - `reports/_r86b_win_lh.xml`（中途口径原始 junit）、`reports/_r86b2_win_lh.xml`（合流后原始 junit）
- 复现命令：
  ```bash
  # 0.86 同步 + 单例快跑 + 全量
  python scripts/同步0.86.py sync
  python ../_r86b_remote.py            # 7 个受影响 example
  python scripts/同步0.86.py test-lh   # 全量门禁 → reports/R85_lh基线_latest.json
  # 反跑
  python ../_r86b_antirun.py
  # Windows 全量
  CODEBUDDY_SAFE_DELETE_ENABLED=0 \
    ../light-merge/.venv/Scripts/python.exe -m pytest tests/ -q --tb=no -rfE \
    --basetemp=.pytest_tmp_r86b2 --junitxml=reports/_r86b2_win_lh.xml
  ```
