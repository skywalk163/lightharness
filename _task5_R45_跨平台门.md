# 第45轮 任务5：跨平台 CI 门复跑

## 1. 门清单扩充

`scripts/多平台矩阵.py` 的 `CASES` 从 12 条扩到 **15 条**，新增 R45 三项：

| id | 用例 | 纳入理由 |
|---|---|---|
| `r45-shadow-warning` | `examples/test_R45_影子变量告警.light` | L-166 告警载体：需在 POSIX 上同样「stderr 出告警 + rc=0」 |
| `r45-subprocess-bg` | `examples/test_子进程后台.light` | 本轮加固对象（原 flaky），必须证明加固后跨平台都稳 |
| `r45-subprocess-code` | `examples/test_子进程码.light` | 同根因（解释器不再写死 `python`），一起守 |

## 2. 实跑结果

```
=== 本机（Windows）===
PASS cli rc=0 4.29s                 PASS r39-system-prompt rc=0 2.00s
PASS r39-scope rc=0 2.08s           PASS r40-integration rc=0 2.49s
PASS r41-file-io rc=0 8.17s         PASS r41-net-io rc=0 7.57s
PASS r42-fetch rc=0 4.38s           PASS r42-webhook rc=0 3.86s
PASS r42-bash-cross rc=0 2.39s      PASS r42-toolchain rc=0 4.20s
PASS r43-llm-roundtrip rc=0 2.60s   PASS r43-agent-loop rc=0 5.78s
PASS r45-shadow-warning rc=0 1.65s  PASS r45-subprocess-bg rc=0 9.22s
PASS r45-subprocess-code rc=0 5.95s

=== 0.82（FreeBSD 15.1）===
（15/15 全 PASS，rc=0，远端副本 /tmp/r44-20260917-043907）

=== 门 === PASS ✅
```

**15/15 双平台 PASS，门 PASS ✅**（判据：两平台每个用例 rc 相等）。

## 3. 0.82 侧定版全量回归

带 `.git` 的副本上跑全量：

```
7 failed, 1238 passed, 3 skipped in 322.88s
```

与本机（7 failed / 1238 passed / 3 skipped / 927.79s）**完全一致**：

- 失败清单 7 条逐条一致；
- skipped 从 5 降到 3（那 2 条 git 依赖用例真正跑起来了，passed 相应 +2）；
- errors 0（第44轮的 2 条 ERROR 消失）。

⇒ 本机 + 门 + 全量三条线全部对齐，**基线外零新增红**。

## 4. 交付物

- `scripts/多平台矩阵.py`（CASES 12 → 15；文档串同步更新）
- `reports/R45_跨平台门_core.json`
- 本报告
