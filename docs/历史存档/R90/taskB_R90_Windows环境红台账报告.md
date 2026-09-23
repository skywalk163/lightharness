# R90-B · Windows LM 环境红台账 + 判据脚本化

> 承接 R89 §6 遗留 2（环境红登记）；执行顺序 B（在 A 之后，确保台账记的是 A 修完后的状态）
> 新增文件：`light-merge/tests/ci_environment_reds.txt`、`light-merge/tests/ci_judge_env_reds.py`
> 附带修复：`light-merge/tests/test_process_tree_light.py`（A 路的孪生遗漏，见 §4）

---

## 1. 建账依据：本轮 Windows 全量（一手）

```
命令：pytest tests/ -q --tb=line -rfE -p no:cacheprovider -o "addopts="
      -n auto --dist loadscope --basetemp=.pytest_tmp_r90b --junitxml=_r90b_junit.xml
      （CODEBUDDY_SAFE_DELETE_ENABLED=0）
结果：8 failed / 8201 passed / 89 skipped / 12 xfailed / 2 xpassed，19m48s，rc=1
产物：light-merge/_r90b_junit.xml
```

对拍基线 `lightharness/reports/本机lm基线_2026-09-24-003348.json`（R89：8312 用例 / 5 failed）。

## 2. 逐条判定（每条都有隔离复跑证据）

| # | 用例 | 隔离复跑 | 判定 | 入账 |
|---|---|---|---|---|
| 1 | `test_http_client.py::test_connection_error` | **2/2 红** | **环境（确定性）**：本机连 `127.0.0.1:1` 是读超时而非 ConnectionRefused（纯 socket 探针 1.23s TimeoutError），「连接错误」永不触发 | W-01 |
| 2-5 | `test_原生腿_R13C_对拍扩展.py::{test_Base64往返, test_URL编码解码, test_分词族, test_字符串相似度}` | 整文件 **34 passed 全绿** | **负载/flaky**：签名 `llvm.compiler.N…`（原生后端编译竞态），与 R87 起的长期观察一致 | W-02~W-05 |
| 6-7 | `test_T6B_时间系统内建_原生腿.py::{test_time_时间戳对拍_固定字段与格式, test_时间管理_睡眠计时冒烟}` | 整文件 **5 passed 全绿** | **负载/flaky**：时间字段对拍受调度抖动影响 | W-06~W-07 |
| 8 | `test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程` | 修前 2/2 绿（全量下红） | **可修复，不入账**：与 A 路同一根因（超时 800ms 触发杀树时进程树未建立 + 只 `sleep(0.5)` 死等）→ 已修 | ❌ 不入账 |
| — | R89 的 3 条 `test_distributed_eval_light` + 1 条 `test_path_a_process_isolation_light` | 本轮**未复现** | 历史负载红，保留容忍条目（都有明确归因：`_等端口` 15s / 进程强杀面） | W-08~W-11 |

**入账 11 条**：环境类 1（W-01）、负载类 10（W-02~W-11）。
**真回归 0 条** —— 8 条红里没有一条与 R90 改动有因果关系（唯一可修的那条是 A 路孪生遗漏，已修）。

## 3. 判据脚本（新增）

`light-merge/tests/ci_judge_env_reds.py`，对齐 `lightharness/tests/ci_judge_env_reds.py` 的用法：

- `judge --current <junit.xml|json> [--baseline <基线json>]`
  → 新增红 = 本轮失败 − 基线（缺省取台账全集）；新增红 0 → rc 0，>0 → rc 1
- `self-check` → 对 R89 基线重放（须新增红 0）+ 反向演示（注入 1 条合成红必须被识别，证明不是 no-op）

### 实测

```
$ python tests/ci_judge_env_reds.py self-check
  历史基线: 本机lm基线_2026-09-24-003348.json（5 条失败）
  [PASS] 基线自对拍: 失败 5 / 新增红 0
  台账条目数: 11
  [PASS] 反向演示: 注入 1 条合成红 → 正确识别新增红 1 条
  [self-check] 结论: 全部通过                                  rc=0

$ python tests/ci_judge_env_reds.py judge --current _r90b_junit.xml
  本轮失败数 8 / 基线失败数 11 / 命中台账 7 / 已恢复 4
  ** 新增红 ** 1 条：tests/test_process_tree_light.py::Test超时杀树::test_超时杀整棵树含孙子进程
  判据结论: 红（存在新增红）                                    rc=1
```

新增红那 1 条正是 §4 修掉的孪生用例 —— 判据脚本如实把它挑出来了（证明脚本不是 no-op）。

### 踩到的坑（已修进脚本）

junit XML **没有 file 属性**，只有点分的 `classname` + `name`。直接按「前两段拼路径」还原会得到
`tests/unit.py::test_Base64往返` 这种错 nodeid，导致台账永远匹配不上。
修法：按点拆开后**试文件系统**判定最后一段是文件名还是类名
（`tests/unit/test_x.py` 存在 → 模块级函数；否则最后一段是类名，插回 nodeid）。

## 4. 附带修复：`test_process_tree_light.py` 杀树孪生用例（A 路遗漏）

A 路只改了 `test_agent_tools_light.py`，本轮全量暴露出**同名的另一个用例**在
`test_process_tree_light.py::Test超时杀树` 里，构造几乎相同（超时 800ms、孙 `sleep(30)`、
杀完只 `time.sleep(0.5)` 就断言）。同一根因，同一修法：

| 项 | 原 | 改后 |
|---|---|---|
| 触发超时 | 800ms | **1500ms** |
| 杀后等待 | `time.sleep(0.5)` 死等 | **轮询最多 5s**（进程被强杀后 PID 会短暂残留） |

断言语义不变：孙仍必须真死（`assert _进程活(gc_pid) is False`）+ 标记文件不出现。
修后孤立 **3/3 绿**。

## 5. 遗留（交 M）

1. 台账里 W-08~W-11 是「历史上红过、本轮未复现」的容忍条目 —— 若连续两轮不红可考虑销账。
2. `test_connection_error`（W-01）是**环境**而非缺陷：有正常 RST 行为的机器上应绿，不要改用例/stdlib。
3. 判据脚本目前只支持 Windows 本机口径；0.82/0.86 侧仍沿用 lightharness 的台账与判据，两套并存。
