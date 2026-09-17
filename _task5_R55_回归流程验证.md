# 第55轮任务5交付：完整回归流程验证

> 日期：2026-09-18 ｜ 目标：跑一遍完整回归流程，验证任务2/4 的脚本真的能用
> 结论：**双平台回归门 PASS ✅ rc=0**（本机 ✅ ｜ 0.82 ✅，端到端 1426s）

---

## 一、验证跑的命令与结果

```bash
cd G:/dswork/duan-light-merge/lightharness
python scripts/多平台矩阵.py --mode gate --remote \
  --local-xml reports/_本机lh_results_2026-09-18-000509.xml \
  --timeout 1800 --remote-timeout 2700 \
  --output reports/R55_跨平台门_gate.json
```

```
=== 跨平台回归门 gate（本机 lightharness + 0.82 light-merge）===
[本机] 复用已有 junitxml：reports/_本机lh_results_2026-09-18-000509.xml
[本机] 基线写入 本机lh基线_2026-09-18-004347.json
[本机] 摘要：共 1272 用例，通过 1262，失败 7，跳过 3，pytest 自报 1494s
[本机] 失败数 7 → 7（1272 → 1272 用例）
[本机] 新增红 0 ｜ 已修复 0 ｜ 持平 7
[本机]   ✅ 零新增红（含 7 条存量失败）

[0.82] 调用：082全量回归.py test --mode fast --timeout-sec 2700
[0.82] 对比：082_lightmerge基线_2026-09-18-005728.json  ⟵  082_lightmerge基线_2026-09-18-002428.json
[0.82] 失败数 117 → 116（7806 → 7806 用例）
[0.82] 新增红 0 ｜ 已修复 1 ｜ 持平 116
[0.82]   已修复样例：['tests/test_distributed_eval_light.py::test_重派与心跳_杀节点后重派且无静默丢条']
[0.82]   ✅ 零新增红（含 116 条存量失败）

=== 门 === PASS ✅ （本机 ✅ ｜ 0.82 ✅，总耗时 1426s）
RC=0
```

**这次 0.82 第二次全量跑，是一次真正的 diff 验证**（不是自己跟自己比）：
7806 用例两轮跑出 117 → 116，失败集合只在一条上不同，且是**往好里变**（第一条跑红、第二条跑绿）——
这一条就是 flaky，见下。

---

## 二、抓到一个真东西：`test_distributed_eval_light.py` 是 flaky

| 轮 | 用例 | 结果 |
|---|---|---|
| 第 1 轮（00:24 基线） | `test_重派与心跳_杀节点后重派且无静默丢条` | ❌ 失败 |
| 第 2 轮（00:57 回归） | 同上 | ✅ 通过 |

用例名里写得很清楚：**「杀节点后重派 + 心跳」**——依赖真实子进程/端口/时序，
在 8 核机上串行跑有竞态。**两轮就能触发抖动，说明它不适合进硬判据**。

处置建议（本轮未做，登记）：
1. 给它打 `@pytest.mark.flaky` 或在 0.82 全量跑时 `--deselect`；
2. 或者干脆在 `tests/test_distributed_eval_light.py` 里放宽心跳超时阈值。

在它稳定之前，`light-merge` 全量基线里这 116 条要当成「包含 1 条 flaky 的基线」，
不要在 review 时因为它红了就判定回归。

---

## 三、顺带验证过的其他入口

| 入口 | 结果 | 备注 |
|---|---|---|
| `082全量回归.py all --mode fast` | ✅ rc=0 | 同步 + 全量 + 首跑 baseline + diff，一条龙跑通，27 分钟 |
| `082全量回归.py test` | ✅ | 由上面的 gate 调用，产出第二份 082 基线 |
| `082全量回归.py show` | ✅ | 列出基线摘要 |
| `082全量回归.py diff` | ✅ | 新增红 / 已修复 / 持平三分类正确 |
| `多平台矩阵.py --mode gate --local-only` | ✅ | 本机快门单跑，会真实起 pytest 并写基线 |
| `多平台矩阵.py --mode gate --local-only --local-xml <xml>` | ✅ | 秒级复算（本次验证用，避免白等 25 分钟） |
| diff 三语义单元求证 | ✅ | 首跑→记基线通过 / 二跑→零新增红 / 注入假红→FAIL 并点名 |

注入假红的自证输出：

```
[本机] 失败数 7 → 8（1272 → 1272 用例）
[本机] 新增红 1 ｜ 已修复 0 ｜ 持平 7
[本机]   ❌ 新增红清单：tests/test_X.py::test_new_break
```

---

## 四、验证过程中修掉的 3 个真 bug（不是凑数）

| # | 问题 | 处置 |
|---|---|---|
| 1 | **首次跑语义不一致**：`082全量回归.py all` 认为「没历史 → 记为基线」放行，`多平台矩阵.py gate_local` 却把首跑 7 条失败当成 7 条新增红判 FAIL | 统一到 `回归基线.diff_baselines()`：`base is None` → `first_run=True`、`new_red=[]`、`ok=True`，并把失败放进 `recorded_as_baseline` 打印出来。理由：不然换机器 / 清一次 reports 就「首跑必红」，门没法用 |
| 2 | **`-o addopts=` 把超时保护一起清了**：本机 lightharness 跑到 84% 卡住 8 分钟不动 | `多平台矩阵.LOCAL_PYTEST` 在 `-o addopts=` 之后显式补回 `--timeout 60`（见 `_task3` §二） |
| 3 | **两侧共用一个 `--timeout`**：默认 1800s 会把 0.82 的 light-merge 全量掐死 | 新增 `--remote-timeout`（默认 2700），与本机的 `--timeout` 分开 |

---

## 五、已知的、本轮没修的事

1. **长跑期间终端无实时输出**：`gate_local/gate_remote` 用 `subprocess.run(capture_output=True)`，
   pytest 的进度点到结束时才一次性吐出来。功能不受影响，但「跑起来不知道跑到哪」。
   → 建议下一步改成 `subprocess.Popen` + 逐行转发（未做）。
2. **本机重跑一次要 25 分钟**：这也是 `--local-xml` 存在的理由，
   但正式回归时该花还得花。
3. **0.82 全量期间本机不能干别的远程活**：同一份 `/tmp/r44-*` 副本被串行占用，
   期间别同时发起第二个远端任务（本轮踩过一次，两个任务进度点互相拖慢）。
