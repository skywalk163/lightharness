# 第44轮 任务2 交付报告 —— 0.82 完整 pytest 回归（全量重同步后干净对比）

> 日期：2026-09-16 ｜ 优先级 P0 ｜ 只同步/验证，**不改源**
> 0.82：192.168.0.82（FreeBSD 15.1-STABLE，ai，`/tmp` 只读临时副本）

## 一、结论

- **0.82 全量重同步完成**：`/tmp/r44-20260916-232020`，97.4 MB，远端 `examples` = **402**（与本机一致）。
- **0.82 完整 pytest**：**7 failed / 1230 passed / 3 skipped / 2 errors，338.03s**。
- **与本机对比**：本机基线 8 failed / 1231 passed / 3 skipped（845.67s）。
  两平台**共同红 7 条，清单逐条一致**；差异仅 3 条（本机 1 条 flaky + 0.82 2 条环境缺失）。
- **基线外零新增平台红 ✅**。

## 二、0.82 全量重同步（任务1 产出，本任务依赖）

| 项 | 值 |
|---|---|
| 远端副本 | `/tmp/r44-20260916-232020`（含 `lightharness/` + `light-merge/`） |
| 包体 | 97.4 MB（排除 `.git`/`__pycache__`/`.venv`/`build`/`dist` 等） |
| 上传耗时 | 4.9s |
| examples 校验 | **402 = 402（本机）** ✅ |
| 垫片 | `/tmp/r44-shim/python{,3}` → `exec /usr/local/bin/python3.11 "$@"` |

> 打包用 Python `tarfile`（不用 Git-Bash tar：GNU 1.35 会把 `C:\` 当远程主机 exit 128；
> 也不用 `--force-local`：FreeBSD bsdtar 不认）。

## 三、0.82 全量 pytest 结果

```
cd /tmp/r44-20260916-232020/lightharness \
  && LIGHT_MERGE=/tmp/r44-20260916-232020/light-merge \
     PATH=/tmp/r44-shim:$PATH /usr/local/bin/python3.11 \
     -m pytest tests/ -q -p no:cacheprovider --tb=no

→ 7 failed, 1230 passed, 3 skipped, 1 warning, 2 errors in 338.03s
```

### 3.1 7 failed（与本机逐条一致，既有存量）

| # | 失败项 | 0.82 | 本机 |
|---|---|---|---|
| 1 | `test_R31_…flaky修复_token.py::test_fanhui_embedded_scan_triggered` | 红 | 红 |
| 2 | `test_R31_…flaky修复_token.py::test_fanhui_return_value_merged` | 红 | 红 |
| 3 | `test_R32_OPERATOR+MERGE_WHOLE精简_token.py::test_deleted_return_code_still_merged` | 红 | 红 |
| 4 | `test_回归.py::…[test_R22_嵌入关键字冗余验证.light]` | 红 | 红 |
| 5 | `test_回归.py::…[test_R26_词首并入反向.light]` | 红 | 红 |
| 6 | `test_回归.py::…[test_R26_词首并入混合.light]` | 红 | 红 |
| 7 | `test_回归.py::…[test_R27_词首并入反向.light]` | 红 | 红 |

均为既有词法/样例基线红（`'返回值'` 被切为 `返回`+`值` 等），**非平台差异、非本轮引入**。

### 3.2 2 errors（0.82 环境缺失，如实归因，不修）

```
ERROR tests/test_R21_词法确定性_超集.py::test_definitions_superset
ERROR tests/test_R21_词法确定性_超集.py::test_definitions_growth_on_l152_file
FileNotFoundError: [Errno 2] No such file or directory: 'git'
```
0.82 未安装 `git`，这两个用例依赖 git 取基线。属**环境缺失非代码缺陷**；不在他人机器擅自装包。

### 3.3 本机独有 1 条（flaky，已复跑定性）

```
FAILED tests/test_回归.py::test_example_exit_code[test_子进程后台.light]
```
单独复跑 `python 运行.py examples/test_子进程后台.light` → **rc=0 PASS**。
故为 pytest 并发/时序下的**偶发红**（后台子进程时序敏感），非稳定红、非平台语义差异。如实记录，不修。

## 四、⚠️ 对「400 failed 归因」的实证更正（重要）

任务书背景称：*0.82 全量 pytest 400 failed 是「副本不全（/tmp/r41-\* 是 R41 快照）」所致*。
本轮实测**不支持该归因**，证据如下：

1. **R43 任务3** 已做过一次**全量**同步（32.2 MB）到 `/tmp/r43-20260916`；
2. 随后 **R43 任务4** 在同一份全量副本上跑出 **402 failed**，报告记为
   *「首轮全量 402 failed 系垫片初版损坏（参数被置空）所致，修复后即 7 failed」*；
3. **本轮（R44）** 第二次**全量**重同步（97.4 MB，examples=402 已校验）+ 正确垫片
   （`exec … "$@"`），结果仍是 **7 failed** —— 与 R43 修垫片后完全一致。

**⇒ 结论**：副本完整时也曾出现 402 failed，且副本换更大的全量包后结果不变，
说明**副本完整性不是 400/402 failed 的原因**；真正根因是 **R43 首轮 python 垫片参数被置空**（子进程拿到空参数）。
任务书该前提未获证据支持，**如实更正**（不掩饰、不伪造）。
该结论同步写入 `reports/R44_freebsd_pytest.json` 的 `attribution_of_r43_400failed` 字段。

> 说明：本轮重同步本身仍有价值——它把「副本不全」这一变量彻底排除，使 7 failed 成为可信的真值。

## 五、交付物

- `lightharness/reports/R44_freebsd_pytest.json`（结构化实测报告，含双平台对照与归因更正）
- 本报告 `lightharness/_task2_R44_0.82完整回归.md`

## 六、约束核对

- 0.82 **只读执行**：仅 `/tmp` 临时副本；未改远端源仓库、未装系统包、未用 sudo。
- 凭据只从工作区 `.env` 读（`SSH_USER_AI`/`SSH_PASS_AI`），**值不入档**。
- 差异逐条归因，无掩饰、无伪造；真平台红（缺 git）如实记录不修。
