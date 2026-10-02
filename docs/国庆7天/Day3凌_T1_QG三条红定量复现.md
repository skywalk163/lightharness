# Day3 凌晨 T1 · Quality Gate 三条红的定量复现与根因

> 派单：`Day3凌晨_派单表.md` v1.0 · T1（A 线，诊断）
> 执行时间：2026-10-03 06:2x–06:4x（CST，+08:00）
> 出口 tag：`subtask-T1-done`

---

## 〇、结论速览

一句话：**不是代码回归，是「性能测量被 coverage 插桩污染」+「60s 超时对慢用例没有余量」**。

| 问题 | 定量结论 |
|---|---|
| 三条红是不是回归？ | ✅ 不是。rc1/rc2 两次 **passed 都是 4324**、失败集合一致 |
| `test_package_manager` 为什么撞 60s？ | 本机无 cov **20.42s / 10.00s**；**带 `--cov=src` + `-n 4` 变成 35.47s / 31.75s**（1.7–3.2×）；共享 runner 再抢核 → 撞线 |
| `test_lexer_perf` 为什么超 20s？ | 本机无 cov **1.30s**；**带 cov 4.39s（3.4×）**；runner 上 20.13s(rc2) / 26.72s(rc1) → **绝对秒数预算在共享 runner 上没有意义** |
| 谁放大了？ | **`--cov` 插桩是主放大器**（QG 有 `--cov=src`，ci.yml 没有；ci.yml 因此全绿） |

---

## 一、为什么要先量再改

上一批 T5 只给出了现象（「每次 push 必红同样 3 条」）和失败用例名。
如果直接把阈值往上调，那是**拍脑袋放宽门禁**——和「把断言改成永真」是同一类动作。
所以本批先把三个数测出来，再据此定参数。

---

## 二、实测（本机 Windows，light-merge/.venv）

### 2.1 无 cov（`-o addopts=`，单进程）

```
pytest tests/unit/test_package_manager.py tests/unit/test_lexer_perf.py -v --durations=12 -o "addopts=" --timeout=300
```

| 用例 | 耗时 |
|---|---|
| `test_package_manager::test_build_project_success` | **20.42s** |
| `test_package_manager::test_run_project_success` | **10.00s** |
| `test_lexer_perf::test_lexer_performance_10000_lines` | **1.30s** |
| 合计 | 39 passed in 45.80s |

### 2.2 带 `--cov=src`（复刻 QG 口径；`addopts` 自带 `-n 4 --dist=loadscope`）

```
pytest tests/unit/test_package_manager.py -q --durations=5 --cov=src --cov-report=term --timeout=180
```

| 用例 | 无 cov | 带 cov | 放大 |
|---|---|---|---|
| `test_build_project_success` | 20.42s | **35.47s** | 1.7× |
| `test_run_project_success` | 10.00s | **31.75s** | 3.2× |
| `test_lexer_performance_10000_lines` | 1.30s | **4.39s** | **3.4×** |
| 会话总耗时（单文件） | — | 98.56s（37 passed） | — |

> 单次跑同一用例的对照（更干净）：`test_lexer_perf` 无 cov **1.20s** → 带 cov **4.39s**，
> 且带 cov 时会话总时长从 1.67s 涨到 15.94s（coverage 自身启动/合并开销）。

### 2.3 与 GitHub runner 的三方对照

| 用例 | 本机无 cov | 本机带 cov | runner(QG, 带 cov) | QG 阈值 | 余量 |
|---|---|---|---|---|---|
| `build_project_success` | 20.42s | 35.47s | **>60s（Timeout）** | `--timeout=60` | **负** ❌ |
| `run_project_success` | 10.00s | 31.75s | **>60s（Timeout）** | `--timeout=60` | **负** ❌ |
| `lexer_performance_10000_lines` | 1.30s | 4.39s | **20.13s / 26.72s** | `LEXER_PERF_LIMIT=20.0` | **负** ❌ |

（runner 两列来自上一批 T5 的 Actions 日志：rc1 `26.7172 秒，超过 20.0 秒限制`；rc2 `20.1328 秒`。）

### 2.4 为什么 ci.yml 从不红

`ci.yml` 的单测命令是 `pytest tests/unit/` —— **没有 `--cov`**，
默认预算 `LEXER_PERF_LIMIT=10.0`（`test_lexer_perf.py:90` 的默认值）就能过。
**同一份代码、同一个 runner 规格，只因 QG 多了 `--cov` 就必红** —— 这就是放大器所在。

---

## 三、修复参数裁定（交给 T2）

| 项 | 裁定 | 依据 |
|---|---|---|
| 单元测试超时 | `--timeout=180` | 本机带 cov 最慢 35.47s → 180s ≈ **5× 余量**；仍远小于 job 总时长（QG 单测 job 跑了 ~9 分钟），不是"放宽到永不触发" |
| `test_lexer_perf` | 从 QG 的 coverage 会话里**剔除**（`--ignore`），守护交给 ci.yml 的无 cov 会话 | 性能断言 + coverage 插桩 = **测量被污染**，量到的是"插桩后的性能"不是真实性能；ci.yml 无 cov 会话以默认 10.0s 预算跑，且覆盖 12 份 OS×Python 矩阵。**不删测试、不放宽断言，只换个干净的测量环境** |
| `LEXER_PERF_LIMIT` | **不动**（保留 20.0） | 该用例已被剔除出 QG，QG 侧不再需要动它；ci.yml 侧本来就用默认 10.0 且长期绿 |

**反向说明（避免自欺）**：`--timeout=180` 确实让"单个用例跑满 180s"成为可能，
但这两个用例的真实量级是 20–40s，180s 不会掩盖"它突然慢 5 倍"这种真退化；
而 `test_lexer_perf` 被剔除后**仍有 ci.yml 守着**，不存在"性能门禁消失"。

---

## 四、出口判据回看

| 判据 | 达成 |
|---|---|
| 定量表（本机无 cov / 带 cov / runner / 阈值余量） | ✅ §二 |
| 明确写出 T2 该用什么参数、为什么 | ✅ §三（含反向说明） |
