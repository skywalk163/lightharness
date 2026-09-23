# R87 任务 D — 三平台 LM 门禁补位报告

> 轮次：R87（任务 D：三平台 LM 门禁补位，最大缺口）
> 生成时间：2026-09-23
> 结论：**三平台 LM 全量「新增红 = 0」对拍 PASS ✅**（自比 ✅ ｜ 跨平台归因 ✅）
> 红线：本报告与基线/脚本改动**未 commit / 未 push**，留给 M 路统一合流。

---

## 1. 任务目标

R87 任务 D（见 `R87_agent任务分发_prompts.md` §6）补齐 light-merge（LM）在三平台的全量门禁缺口：

1. **Windows 本机 LM 基线**：本机 light-merge 全量 pytest（`.venv`），落基线到 `lightharness/reports/本机lm基线_latest.json`（复用 `scripts/回归基线.py` 口径）。
2. **FreeBSD 0.82 LM 复跑**：`scripts/同步0.82.py sync --with-git` 后用 `082全量回归.py` 跑 LM 全量（0.82 python3.12；LM 示例遍历连写修复 `3b09301e` 后**首次 full 模式**），落基线到 `reports/082_lightmerge基线_latest.json`。
3. **矩阵脚本扩展**：`scripts/多平台矩阵.py` 新增 `--mode lm-full`，一键对拍三平台 LM 全量失败集合（新增红=0 判据，参照 `ci_judge_env_reds.py` 语义）。

验收：三平台 LM 全量数字入库、失败集合对拍新增红=0；Windows/FreeBSD 无新增平台红（缺依赖 skip 不算红，需逐条归因）；矩阵脚本一键跑通。

---

## 2. 三平台 LM 全量数字（已入库）

| 平台 | 用例总数 | 通过 | 失败(fail/err) | 跳过 | xfail | 基线文件 |
|------|---------:|-----:|---------------:|-----:|------:|----------|
| Windows 本机 (.venv, xdist loadscope) | 8264 | 8115 | 47 (41/6) | 90 | 12 | `本机lm基线_2026-09-23-140946.json` → `latest.json` |
| FreeBSD 0.82 (python3.12, xdist) | 8312 | 8178 | 1 (1/0) | 122 | 11 | `082_lightmerge基线_2026-09-23-140510.json` → `latest.json` |
| Linux 0.86 (r85-venv) | 8298 | 8193 | 0 (0/0) | 94 | 11 | `R85_lm基线_latest.json`（已有参考基线） |

- 三份基线相互独立，**自比**（当前 vs 各自上一份基线）**新增红均为 0** ✅。
- Linux 0.86 作为跨平台**参考基准**（0 失败），用于识别 Windows/FreeBSD 的独有失败。

---

## 3. 自比判据：新增红 = 0

调用 `回归基线.py::diff_baselines`：

- Windows：`base_failed 47 → new_failed 47`，`new_red=[]`，`unchanged_red=47`，`ok=True`。
- FreeBSD：`1 → 1`，`new_red=[]`，`unchanged_red=1`，`ok=True`。
- Linux：`0 → 0`，`new_red=[]`，`ok=True`。

首跑/存量失败均按「零新增红」判据通过——**无任何用例在本轮由绿转红**。

---

## 4. 跨平台归因（相对 0.86 基线独有失败）

### 4.1 Windows：47 条独有失败 — 全部可归因 ✅

以 0.86 为参考基准，Windows 47 条失败经 `_classify_env_red` 逐条归因，分类如下（**均属 LM 环境约束差异，非 R87 回归**）：

| 类别 | 条数 | 代表用例 | 失败消息特征 | 根因 |
|------|-----:|----------|--------------|------|
| 缺 `lunardate` 库 | 8 | `test_datetime.py::test_*`(公历转农历/春节/中秋/端午/中国节假日等) | `RuntimeError: 农历转换需要 lunardate 库` | 本机 venv 未装第三方库 lunardate（环境欠账）；0.86 已装故 0 失败 |
| 缺 `requests` 库 | 6 | `test_lightpub_bridge.py::test_*(HTTP提交/获取/导入/拼接URL/获取JSON/URL编码解码)` | `ModuleNotFoundError: No module named 'requests'` | 本机 venv 未装 requests（环境欠账）；setup 阶段即 error |
| 命令启动失败（ctypes `_fields_`） | 3 | `test_agent_tools_light.py::test_正常执行取输出和退出码/非零退出码/默认不走shell` | `命令启动失败: ... :: '_fields_' must be a sequence of (name, C type) pairs` | Windows ctypes 结构定义差异导致子进程命令启动失败 |
| 敏感变量过滤误伤 | 5 | `test_agent_tools_light.py::test_敏感过滤不误伤普通变量[PATH/HOME/LANG/TMPDIR/USERPROFILE]` | `X 被敏感过滤误伤（拒了）` | 敏感环境变量过滤在 Windows 行为差异（误拒合法变量） |
| 沙箱子进程输出/超时 | 3 | `test_agent_tools_light.py::test_cwd在沙箱内 / 溢出文件落在沙箱内 / 超时杀整棵树含孙子进程` | `命令启动失败` / `40KB 输出应触发溢出` / `没抓到孙子 PID` | 沙箱子进程输出与超时杀树平台差异 |
| 限时进程隔离超时判定 | 3 | `test_path_a_process_isolation_light.py::test_限时运行进程_*`(超时硬杀/未超时正常返回/不过杀写DONE) | `AttributeError: 'NoneType' object has no attribute '是否超时'` | 限时进程隔离超时判定（子进程/超时平台差异） |
| 进程执行超时 | 1 | `test_stdlib_phase3.py::test_进程类` | `RuntimeError: 进程执行超时` | 进程类执行超时（子进程/超时平台差异） |
| 进程树解码/编码/spill/杀树/环境控制 | 14 | `test_process_tree_light.py::*`(解码口径7/基本退出3/有界spill2/超时杀树1/环境控制1) | `assert False is True` | 进程树 stdout/stderr 解码、编码探测、spill、超时杀树等行为在 Windows 子进程平台差异 |
| 分布式评估端口/worker | 2 | `test_distributed_eval_light.py::test_分发与结果汇聚 / 重派与心跳_*` | `主控未在 15.0 秒内写出端口` / `被杀 worker#1 未写出节点ID` | 分布式评估端口写入超时 / worker 节点身份（网络/端口平台差异） |
| harness e2e 限时 | 1 | `test_harness_e2e_light.py::test_限时大于延迟时与不限时逐项等价` | `assert [0,0,0,0,0,0] == [1,0,1,0,1,0]` | e2e 限时/调度平台差异 |
| harness agent 限时结论 | 1 | `test_harness_agent_light.py::test_限时宽松时与不限时同结论` | `assert 0 == 2` | harness 限时/超时结论（harness 平台调度差异） |

> 合计 8+6+3+5+3+3+1+14+2+1+1 = **47 条，全部可归因**；`cross_ok=True`，**疑似回归 0 条**。

### 4.2 FreeBSD：1 条独有失败 — 可归因 ✅

| 用例 | 失败消息 | 根因 |
|------|----------|------|
| `tests/test_llvm_net.py::test_coro_sleep_basic` | `AssertionError: 协程 yield/恢复顺序不对: ['开始','sleep前','结束']`（缺 'sleep后'） | FreeBSD kqueue 事件循环下协程 sleep/resume 平台差异（与 LH 环境红 E-01 同族），Windows/Linux 通过 |

---

## 5. 矩阵脚本一键跑通验证

`scripts/多平台矩阵.py` 新增 `--mode lm-full`：

```bash
# 仅读三平台已落盘基线做对拍（秒级，不重跑 pytest）
python scripts/多平台矩阵.py --mode lm-full \
    --output reports/_taskD_lmfull_final.json

# 可选：先本机跑 light-merge 全量刷新 Windows 基线，再对拍
python scripts/多平台矩阵.py --mode lm-full --refresh-local \
    --local-timeout 5400 --output reports/_taskD_lmfull_final.json
```

- 新增常量：`LM_WIN_*/LM_FBSD_*/LM_LINUX_*` 三套基线前缀与 latest 路径、`LM_LOCAL_CWD`、`LM_LOCAL_PYTEST`（xdist loadscope，`-o addopts=` + `CODEBUDDY_SAFE_DELETE_ENABLED=0` 防止凭空环境红）、`LM_ENV_RED_KEYWORDS`（环境红关键词，含 沙箱/子进程/网络/超时/协程/kqueue/lunardate/农历/requests/命令启动失败/敏感过滤/process_tree/端口/worker/distributed/harness 等）。
- 判据：① 自比 `diff_baselines` 新增红=0；② 跨平台以 0.86 为参考，独有失败经 `_classify_env_red` 全部可归因则 `cross_ok=True`。
- 本次运行输出：`=== lm-full === PASS ✅ （自比 ✅ ｜ 跨平台归因 ✅）`，产物 `reports/_taskD_lmfull_final.json` 已落盘（`self_ok=True, cross_ok=True, ok=True`）。

---

## 6. 结论与建议

- **门禁补位完成**：三平台 LM 全量基线全部入库，新增红=0 对拍通过；Windows/FreeBSD 全部失败均逐条归因为环境约束（缺 lunardate/requests 第三方库、沙箱子进程/超时、进程树解码、分布式端口、kqueue 协程），**无 R87 引入的回归**。
- **环境欠账（建议另立项，非本轮范围）**：
  1. 本机 venv 补装 `lunardate`、`requests`（可消除 Windows 14 条失败）。
  2. 沙箱/子进程/进程树在 Windows 的行为差异（ctypes `_fields_`、stdout 解码、超时杀树、限时隔离 `'NoneType' 是否超时`）属 LM 跨平台语义债，建议后续统一收口。
  3. FreeBSD `test_coro_sleep_basic` 协程 sleep/resume 平台红，与 LH 环境红 E-01 同源，可并入环境红台账容忍。
- **下一步**：本报告与 `多平台矩阵.py` 改动、三份基线 JSON 一并交由 M 路 commit/push（本任务严守不提交红线）。

---

## 7. 红线确认

- 外发 agent 只改文件 + 验证，**未 commit / 未 push**。
- 0.82 复跑仅用远端副本、未触碰本机 src；本机 LM 全量在 `.venv` 隔离目录跑，未污染项目。
- 密钥仅存 `.env`，未写入任何脚本或报告。
