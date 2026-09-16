# 第44轮 任务5 交付报告 —— 跨平台 CI 门固化

> 日期：2026-09-16 ｜ 优先级 P1 ｜ 修改区域：**只改 `scripts/`**

## 一、结论

`scripts/多平台矩阵.py` 由 R41 的「平台能力探测 + 4 个核心用例」升级为**跨平台回归门**：

- 核心用例 **4 → 12**（补齐 R41~R43 全部真实链路：文件/网络/fetch/webhook/bash/工具链/LLM往返/agent循环）；
- 新增 `--mode pytest`：两平台各跑全量 pytest，比对**失败用例集合**（而非仅 rc），
  避免「都非零退出但失败项不同」被误判为一致；
- 远端执行**复用** `scripts/同步0.82.py`（paramiko + 只读 `/tmp` 副本 + python 垫片），不重复造传输层；
- **硬判据**：两平台每个用例 rc 相等（pytest 模式为失败集合相等）→ 退出码 0。

实测：**12/12 双平台 rc=0，门 PASS ✅（退出码 0）**。

## 二、用法

```bash
python scripts/多平台矩阵.py --mode core                     # 只跑本机核心用例
python scripts/多平台矩阵.py --mode core --remote             # 本机 + 0.82 比对（本次实跑）
python scripts/多平台矩阵.py --mode pytest --remote --sync    # 两平台全量 pytest 比对（先重同步）
python scripts/多平台矩阵.py --mode core --output reports/X.json
```

退出码 `0` = 门通过；`1` = 用例红或两平台不一致。可直接挂 CI。

## 三、设计要点

| 点 | 说明 |
|---|---|
| 用例集 | `CASES` 常量，12 项；全部为跨平台语义稳定的真实链路样例，不含平台专属断言 |
| 远端复用 | 用 `importlib` 动态加载 `同步0.82.py`（文件名含点，不能常规 import），取 `connect/run_remote/load_remote_dir/ensure_shim/PY` |
| 判据升级 | core 模式比对 **rc 字典全等**；pytest 模式用正则抓 `FAILED/ERROR <id>` 比对**失败集合全等** |
| 输出 | `--output` 写 JSON（schema 2，含双方平台指纹、逐用例耗时/输出摘要、门结论） |
| 超时 | 单用例 600s（core）/ 1800s（pytest），防挂死 |

## 四、实测（改 src 之后）

```
=== 本机（Windows 10）mode=core ===
PASS cli 4.55s | r39-system-prompt 1.94s | r39-scope 1.91s | r40-integration 2.46s
PASS r41-file-io 8.64s | r41-net-io 7.86s | r42-fetch 4.33s | r42-webhook 3.79s
PASS r42-bash-cross 2.50s | r42-toolchain 4.60s
PASS r43-llm-roundtrip 2.86s | r43-agent-loop 5.43s
=== 0.82（FreeBSD 15.1）===
12/12 全部 rc=0（0.80s ~ 2.81s）
=== 门 === PASS ✅   （GATE_EXIT=0）
```

**关键信号**：`r43-llm-roundtrip` 与 `r43-agent-loop` 是 R44 **去掉装配层绕行后**
（直接用 `启动Mock服务` + `注册bash工具`）的版本，在 0.82 同样 rc=0
→ L-162 / L-163 / L-164 / L-165 的修复在 POSIX 下成立，不是 Windows 单方面通过。

## 五、真·平台差异（已写入 `docs/多平台差异清单.md`，如实记录不修）

1. `test_子进程后台.light`：本机 pytest 下**偶发红**，单跑 rc=0 → flaky（后台子进程时序），非平台语义差异。
2. `test_R21_词法确定性_超集` 2 条：0.82 **ERROR**（`FileNotFoundError: 'git'`）→ 0.82 未装 git，环境缺失，不擅自装包。
3. 耗时差异：本机 733~846s vs 0.82 338s，非功能差异。

其余：两平台失败清单**逐条一致（7 条既有存量红）**，基线外零新增平台红。

## 六、交付物

- `lightharness/scripts/多平台矩阵.py`（升级，schema 2）
- `lightharness/reports/R44_跨平台门_core.json`（实测结果）
- `lightharness/docs/多平台差异清单.md`（追加 R44 回归门章节 + 真平台差异表）
- 本报告

## 七、约束核对

- **只改 `scripts/`**（另改 docs 与 reports，属交付物非代码）。
- 结果全部基于实测，无推测、无代填。
