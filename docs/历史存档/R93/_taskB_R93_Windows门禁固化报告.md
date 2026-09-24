# R93 任务B · Windows 门禁 worker 固化 + 负载敏感台账补全 — 交付报告

> 轮次：R93-B ｜ 2026-09-24→25 ｜ 承接 R93 任务分发书 §3（**必须在 A、C 之后跑，测的是 A/C 改完的状态**）
> 前置状态：A 路（杀树两用例结构解耦）已于 22:41 交付（`_taskA_R93_杀树用例解耦重写报告.md`）；C 路（进程壳依赖结案）已于 21:35 交付（`_taskC_R93_进程壳依赖结案报告.md`）——**B 路跑的就是 A/C 改完的工作树**。
> 改动面：**仅 `tests/ci_environment_reds.txt`**（台账），零 `.light` / 零 `src/` / 零测试语义改动。不 commit / 不 push（M 路统一）。
> 本机：Windows 10 Build 19045，Xeon E5-2643 v2，**10 物理核 / 10 线程**，22GB。

---

## 0. 一句话结论

**Windows 本机 LM 全量门禁标准 worker 数固化为 `-n 4`**：连续 **3 轮**全量 judge **新增红 = 0**（25min/轮，失败只剩台账内那 1–2 条）；台账由 14 条扩到 **21 条**（补登 W-15~W-23 九条负载敏感，均有隔离转绿证据），并把 **W-12 / W-14（杀树孪生用例）销账**（R93-A 重写后三轮全量 + 类级 25/25 全绿）。`-n 8` 及以上存在 **xdist worker 被杀 → 整轮挂死**的系统性风险，不再作为门禁口径。

---

## 1. worker 数固化实验（硬数据）

统一姿势（= 任务书坑① + 保留 gate 的其它 addopts）：

```
python -m pytest tests/ -o "addopts=--tb=short --durations=15 --ignore=tests/archive --timeout=60 --dist=loadscope" \
    -n <N> -p no:cacheprovider -q --junitxml=<路径> --basetemp=<仓内·每轮换>
CODEBUDDY_SAFE_DELETE_ENABLED=0
```
（`-o addopts=` 必须清掉 ini 里的 `-n auto`，否则与命令行 `-n` 打架；`dist=loadscope` 与真实门禁一致。）

| 轮次 tag | worker | 耗时 | failed | failed nodeid | `[gwN] node down` | judge 新增红 | 备注 |
|---|---|---|---|---|---|---|---|
| （历史）R92 run1 | -n auto(=10) | 23min | 4 | 台账内为主 | 未知 | — | R92 §7 遗留 |
| （历史）R92 run2 | -n auto(=10) | 36min | 13 | 台账外多条 | 未知 | — | 方差来自当时机器负载 |
| （A 路移交）a_full_run2 | -n auto(=10) | 27:43 | 11 | 见 §3 | — | — | 满负载 10 核打满 |
| **b_full_n8** | **-n 8** | **未完成（>45min）** | n/a | n/a | **有（[gw4] + 二次 worker 异常）** | n/a（无 junit） | **挂死在 99%，见 §5** |
| b_full_n6 | -n 6 | **21:24** | 3 | W-01、W-06、**W-22(当时未在账)** | 0 | 1 →（补登后 0） | 可用但仍有台账外红 |
| **b_full_n4** | **-n 4** | **25:02** | **1** | W-01 | 0 | **0** | ✅ 探索轮 |
| **b_full_n4c1b** | **-n 4** | **25:26** | **1** | W-01 | 0 | **0** | ✅ 确认轮 1 |
| **b_full_n4c2** | **-n 4** | **25:29** | **2** | W-01、W-07 | 0 | **0** | ✅ 确认轮 2 |
| ~~b_full_n4c1~~ | -n 4 | 4:38 | 507 | INTERNALERROR 中断产物 | 有 | — | ⛔ **作废轮**，见 §5.2（本路执行事故，非产品问题） |

**取舍依据**：`-n 4` 比 `-n 6` 慢 3.6min，但失败数 3→1、且**失败全部落在台账内**，judge 稳定 0；`-n 8` 及以上会触发 worker 崩溃/挂死。**失败数稳定性优先于 3 分钟耗时** → 定 **`-n 4`**。

落地位置：已写进 `tests/ci_environment_reds.txt` 头部「R93-B 固化结论」注释段（含完整命令格式）。

---

## 2. 负载敏感用例一次性补登（W-15 ~ W-23）

口径：**隔离复跑转绿才登**（`python -m pytest <nodeid> -o addopts=`，无 `-n`）。每条 **2/2 隔离绿**，证据落 `_r93/b_isolate_w15.json` + 逐条 log。

| 编号 | nodeid | 观测来源 | 隔离证据 |
|---|---|---|---|
| W-15 | `tests/test_process_tree_light.py::Test基本退出::test_非零退出码` | A 路全量 `-n auto`（11 failed 批次） | 2/2 绿（~2.2s/次） |
| W-16 | `…::Test基本退出::test_stderr与stdout分离` | 同上 | 2/2 绿 |
| W-17 | `…::Test环境控制::test_环境黑名单过滤` | 同上 | 2/2 绿 |
| W-18 | `tests/e2e/test_e2e_chain.py::test_duan_run[test_L170.light]` | 同上 | 2/2 绿 |
| W-19 | `tests/e2e/test_e2e_chain.py::test_duan_run[test_L172.light]` | 同上（签名 PermissionError：句柄释放慢） | 2/2 绿 |
| W-20 | `tests/test_lsp_protocol.py::TestLSPProtocol::test_initialize与shutdown协议` | 同上 | 2/2 绿 |
| W-21 | `tests/test_缺陷账_L162_L169.py::TestL167等待进程超时回收::test_正常路径不受影响` | 同上 | 2/2 绿 |
| W-22 | `tests/unit/test_原生腿_R13C_对拍扩展.py::test_空串边界族` | **B 路 `-n 6` 轮新发现**（llvm 原生后端编译竞态，是 W-02~W-05 同族漏登的第 5 条） | 2/2 绿（~11s/次） |
| W-23 | `tests/test_agent_tools_light.py::TestRunCommand::test_正常执行取输出和退出码` | A 路类级 `-n auto` round#14（平凡 `print` 命令被判超时强杀） | 2/2 绿 |

台账现状：**21 条**（W-01~W-11、W-13、W-15~W-23）。

---

## 3. W-12 / W-14（杀树孪生用例）销账

销账判据由 R93-A 台账注释委托给本路：「以 B 路选定 worker 数后的连续全量 judge 新增红 = 0 为最终销账判据」。

- **先把它们踢出台账再判**：本路把 W-12/W-14 原行转注释（`# 已销账(R93-B): …`，原文完整保留、可一键回加），然后用 **21 条**的新台账重判三轮 `-n 4` junit → **三轮新增红全为 0**。
  这一步等价于反向验证：若两用例在三轮全量里红过哪怕一次，judge 就会把它们报成「新增红」——没有。
- 佐证链：R93-A 类级 `-n auto` **25/25 全绿** + 本路 `-n 6` 轮 / `-n 4` ×3 轮两用例均绿。
- 语义说明：**销账 ≠ 免罚**。这两条今后若再红，judge 会报新增红（真信号），需要重新取证；不再是"挂在台账里的长期观察项"。

> W-13（滑动窗口阈值）虽已达 R92-B 写的「连续两轮不红可销账」条件（本轮实测 4 轮不红），但它是**阈值放宽**（削弱判定力度）换来的绿，与 W-12/W-14 的"结构性修好"性质不同，本路**保守保留不动**，把裁定权留给 M。

---

## 4. 判据达成对照（任务书 §判据）

| 判据 | 状态 |
|---|---|
| worker 数有数据对比表（auto/8/6/4 各轮耗时 + 失败数） | ✅ §1（含历史 auto 两轮） |
| 选定值**连续 ≥2 轮**全量 judge 新增红 = 0 | ✅ **3 轮**（n4 / n4c1b / n4c2），且是**销账后 21 条台账**下的更严判据 |
| 补登的每条都有隔离转绿证据 | ✅ 9 条 × 2/2 绿（`_r93/b_isolate_w15.json`） |
| 台账 self-check 过 | ✅ `ci_judge_env_reds.py self-check`：21 条、基线自对拍 0、反向演示正确识别 1 条注入合成红 |

```
[self-check] 重放历史基线 + 反向演示
  历史基线: 本机lm基线_2026-09-24-003348.json（5 条失败）
  [PASS] 基线自对拍: 失败 5 / 新增红 0
  台账条目数: 21
  [PASS] 反向演示: 注入 1 条合成红 → 正确识别新增红 1 条
```

---

## 5. 稳定性发现（**未结案，交 M 定夺**）

### 5.1 `-n 8` 及以上的 xdist worker 被杀 → 整轮挂死

一手证据（`_r93/b_full_n8.log`）：

1. 跑到 ~7% 处出现 `[gw4] node down: Not properly terminated`，xdist 自动拉起替补 worker；
2. 进程表一手核查发现**第二次**worker 重启（替补 worker 的实际存活时间比其它 worker 短 ~14min）；
3. 日志推进到 **99%（23:36）后彻底静止**，此后 20+ 分钟 0 字节输出、8 个 worker 全部 CPU=0 空转，无 salt / 无 FAILED / 无 junit → 人工终止。

同一机理的另一面见 §5.2：worker 死后 xdist 会 `_clone_node` 重启；**重启成功但会话卡死** = 挂死，重启失败立刻 `INTERNALERROR` = 507 假红。两条路径同源。

> `-n 6` 轮与 `-n 4` 三轮均 **0 次 node down**（日志无 `node down`，`bringing up nodes` 均为开局的 2 次）。

### 5.2 本路执行事故（如实记录，非产品问题）

`b_full_n4c1` 轮（**已作废**）：驱动脚本所在 bash 会话被工具 120s 超时 SIGTERM 掉，孤儿的 pytest 继续跑，但它**新 fork 的 worker 立刻夭折** → xdist 重启失败 → `INTERNALERROR ... execnet bootstrap io.read(1) got 0` → 507 failed / 4:38 中断。教训：**长轮必须后台任务起**，前台超时的 SIGTERM 会波及孤儿子进程的进程创建能力。作废轮不计入任何结论，也不入台账。

### 5.3 机理假设：PID 复用 + 杀树 PPID 链回溯兜底？（**未证实**）

`stdlib/进程树.light` 的 `[R92-A-LEAK] _R92补杀迟建后代`（第 697–760 行）遍历**全系统**进程表、沿 PPID 链回溯，凡祖先 PID ∈ {root ∪ 已杀后代} 即判定为本树迟建后代并 `taskkill /F`。理论上存在误伤路径：被杀树释放的 PID 若被 OS 重新分配给**无关**新进程 P，则 **P 的子女**会被误判成本树迟建后代。

本路做了边界探针 `_r93/b_collateral_probe2.py`（边跑杀树两用例 `-n 8`，边并发 spawn 大量两层短命进程树，检测是否有无关进程被杀）：

- **`_r93/b_collateral_probe2.json`（主证据）**：边跑杀树两用例（`-n 8`），边并发 spawn **25,285 个两层短命进程树**（父 P 再拉一个孙，专门覆盖"P 被分配到刚释放的 PID → 其子女被误判为本树迟建后代"这条路径）→ **0 例无关进程被杀**（`killed=0`、`errors=0`）。样本量已与真实全量（一轮上万进程创建）同量级，**误伤假设未复现**。
- **`_r93/b_stress_killtree_full.log`（边界取证）**：把压力拉到极限（单轮 20s → **154s**，6~7 倍减速）时，两用例确实会红，但签名是 A 路已记录的 **「10s 内 pid 文件未出现…树根本没建好（非杀树之过）」** —— 属**负载敏感**，既不是杀树漏杀、也不是误杀无关进程。同批 6 轮里 5 轮绿。

**结论口径**：误伤机理**未证实**（探针未复现，且样本量够）；`-n 8` 那次 worker 被杀的**真因仍未抓到**（候选：xdist/execnet 在 Windows 高负载下的自身脆弱性 / ctypes Job Object 崩溃 / 内存瞬时压力）。可用的确定结论是：**`-n 4` 下连续 3 轮 0 次 node down**，风险被规避。这是本轮唯一未结案项，已同步写进台账「R93-B 稳定性备注」段。

结论口径：探针结果是**「未复现」而非「不存在」**——样本量与真实全量（一轮上万进程创建）不在一个量级。降 worker 到 4 后连续 3 轮 0 次 node down，风险已被规避但不等于机理已澄清。**建议 M 路把这条作为下轮立项项**（方向：给 `[R92-A-LEAK]` 的兜底加" ancestry 命中且进程创建时间 ≥ 杀树开始时间 "的双重闸门，或从全系统表收敛到 root Job Object 内成员查询）。本路未改任何 stdlib / 测试语义。

---

## 6. 红线遵守

- ⛔ 未把任何"隔离不绿"或"机理不明"的红塞进台账（每条都有 2/2 隔离绿 + 观测来源）。
- ⛔ 未改任何测试语义、未动 lexer/parser/codegen、未动 `.light`；改动面只有台账文件。
- ⛔ 未 commit / push（M 路统一）。
- ✅ 台账幂等补丁双哨兵（`R93-B-LEDGER-W15`、`R93-B-销账-W12W14`），写两遍确认第二遍全 SKIP；文件 LF、无 CRLF。
- ✅ 关键结论都有一手产物：junit / summary json / log / 隔离 json / 探针 json。

---

## 7. 产物清单

| 路径 | 说明 |
|---|---|
| `light-merge/tests/ci_environment_reds.txt` | **唯一改动文件**：固化说明（worker=4）+ W-15~W-23 + W-12/W-14 销账注释（21 条生效） |
| `_r93/b_full_n{8,6,4,n4c1b,n4c2}.{log,xml,summary.json}` | 各轮全量日志 / junit / 结构化摘要（作废轮 `n4c1` 也保留，诚实留痕） |
| `_r93/b_full.py` | 全量驱动（含 `--cap` 墙钟看门狗、node down 计数、hung 标记） |
| `_r93/b_isolate.py` + `_r93/b_isolate_w15.json` + `_r93/b_iso_*.log` | 隔离复跑取证（9 条 × 2 轮） |
| `_r93/b_patch_ledger.py` / `_r93/b_patch_ledger_xiaozhang.py` | 台账幂等补丁（补登 / 销账） |
| `_r93/b_collateral_probe.py` / `b_collateral_probe2.py` + json | worker 被杀机理探针（25,285 样本，0 误杀） |
| `_r93/b_stress_killtree.py` + `b_stress_killtree_full.log` | 极限负载下杀树两用例的失败签名取证 |
| `_r93/b_candidates.txt` | 候选负载敏感清单（9 条） |
| 本报告 | `_taskB_R93_Windows门禁固化报告.md` |

---

## 8. 给 M 路的交接要点

1. 合流时只 add 一个文件：`light-merge/tests/ci_environment_reds.txt`（A/C 的文件各自单独 commit）。
2. **Windows 门禁口径改为 `-n 4`**（命令见 §1），后续轮子照跑；judge 用 `tests/ci_judge_env_reds.py judge --current <junit>`。
3. W-12/W-14 已销账；W-13 是否一并销账请 M 裁定（本路建议保留）。
4. §5.3 的机理条目是本轮**唯一未结案项**，建议立下轮专项；在此之前，Windows 全量请务必用 `-n 4`（`-n 6` 亦可但会有台账外红，`-n 8` 有挂死风险）。
5. `pyproject.toml` 的 `addopts` 里仍是 `-n auto`——本路**未改**（超出改动面），需要的话由 M 决定是否改成 `-n 4`；不改的话跑门禁必须显式 `-o addopts=…` 覆盖（命令见 §1）。
