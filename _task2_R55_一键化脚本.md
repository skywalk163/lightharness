# 第55轮任务2交付：0.82 全量 pytest 一键化脚本

> 日期：2026-09-17 ｜ 目标：把「同步 → 远端跑 light-merge 全量 pytest → 拉回结果 → 对比基线」串成一个命令
> 交付物：`lightharness/scripts/082全量回归.py` + 共用库 `lightharness/scripts/回归基线.py`

---

## 一、为什么需要它

R53~R54 连续两轮出现「小浣熊 / workbuddy 跑 light-merge 全量 pytest 都卡住」，只有主 agent 能跑完回归。
R54 路M 诊断给出根因与方向：

| 维度 | 卡住的做法 | 能跑通的做法 |
|---|---|---|
| 测试对象 | light-merge 全量（**8106** 用例） | lightharness 全量（~1200 用例） |
| 并行 | 默认 xdist `-n auto` → 本机 Windows 上 INTERNALERROR | 串行 `-p no:xdist` |
| 耗时 | xdist 不稳 + 串行 1h+ → 超时 | FreeBSD 串行实测可控 |

本轮把 light-merge 全量**固定搬去 0.82（FreeBSD 15.1）**跑，脚本负责把整条链路自动化。

---

## 二、交付物清单

| 文件 | 作用 |
|---|---|
| `scripts/082全量回归.py` | 一键化脚本，子命令 `sync` / `test` / `diff` / `all` / `show` |
| `scripts/回归基线.py` | 共用库：junitxml 解析 → 基线 JSON → 新增红 diff（任务2/3/4 共用一套口径） |
| `reports/082_lightmerge基线_<日期-时间>.json` | 每轮基线快照 |
| `reports/082_lightmerge基线_latest.json` | 稳定指针，供 gate / diff 复用 |
| `reports/082_diff_<时间戳>.json` | diff 报告 |

---

## 三、用法

```bash
PY="G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe"
cd G:/dswork/duan-light-merge/lightharness

$PY scripts/082全量回归.py all                      # sync + test + diff 一条龙（默认 fast）
$PY scripts/082全量回归.py all --mode full          # 连 slow 用例（303 条）一起跑
$PY scripts/082全量回归.py sync                     # 只同步（--with-git 可连 .git 一起带）
$PY scripts/082全量回归.py test --timeout-sec 3600  # 只跑测试，放宽硬超时
$PY scripts/082全量回归.py test --serial            # 强制串行（默认自动探测 xdist）
$PY scripts/082全量回归.py diff                     # 与上一份基线对比
$PY scripts/082全量回归.py show --recent            # 列最近 3 份基线摘要
```

---

## 四、设计要点与实测踩坑（重要，别踩回去）

### 4.1 远端环境的真实情况（R55 实测）

```
0.82: FreeBSD fb82 15.1-STABLE amd64，8 核，Python 3.11.16
已装：pytest 9.1.1
未装：xdist ❌   pytest-timeout ❌
```

**这不是可以绕过的细节，而是决定整个命令形态的前提**：

* light-merge 的 `pyproject.toml` 里 `addopts = "--tb=short --durations=15 --ignore=tests/archive --timeout=60 -n auto --dist=loadscope"`，
  直接在 0.82 上跑会因为 `--timeout` / `-n` 无对应插件而 **ARGERROR 直接退出**；
* 所以脚本一律用 `-o addopts=` 把 addopts 置空，再按需自己拼参数；
* 没有 pytest-timeout，就用 FreeBSD 自带的 `timeout(1)` 兜一层（先 `command -v timeout` 探测），
  超时 rc=124，脚本识别出来并**拒绝写入不完整基线**——避免把半成品当成基线污染后续 diff。

### 4.2 用 junitxml 而不是解析终端文本

结果用 pytest 内建的 `--junitxml` 结构化落盘，再 sftp 拉回本地解析。
`-rfE` 的 FAILED/ERROR 行 *也* 留着做人工核对，但**判据不依赖它**——
终端 want/宽度、emoji、颜色转义都可能变化，XML 才是稳定的。

### 4.3 判据沿用 CI 口径：新增红

```
新增红 = 本轮失败集合 − 上一轮失败集合
rc = 0 ⟺ 新增红为空
```

和 light-merge 自带 `tests/ci_baseline_failures.txt` 语义一致：**存量欠账不拦，只拦新欠**。
首次跑没有历史基线时，全部失败计为基线（不判红），避免第一跑道必然红灯。

### 4.4 幂等 / 可重复

* 每次 `test` 产出带时间戳的新基线文件 + 覆盖 `latest` 指针，历史不被涂改；
* `diff` 默认取「最新 vs 次新」，也可 `--base/--new` 显式指定任意两份对比；
* `sync` 每次建新的 `/tmp/r44-<时间戳>` 副本，不复用旧目录（`同步0.82.py` 原逻辑）；
* 凭据只从工作区 `.env` 读（`SSH_USER_AI` / `SSH_PASS_AI`），不落日志不落盘。

### 4.5 长连接的两个坑

* 全量跑 20~40 分钟，SSH 空闲容易被中间设备掐断 → `connect()` 后开 `set_keepalive(30)`；
* 远端 command channel 的 stderr 在 paramiko 里默认不合流，`python -c` 报错会「静默 rc=1 无输出」→
  探测能力时一律加 `2>&1`，别对着空输出猜。

---

## 五、基线 JSON 结构（schema 1）

```jsonc
{
  "schema": 1, "round": "R55", "generated_at": "2026-09-17T…",
  "target": {"name": "light-merge", "platform": "0.82 FreeBSD 15.1",
             "host": "192.168.0.82", "remote_dir": "/tmp/r44-…", "cwd": "…/light-merge"},
  "runner": {"mode": "fast", "parallel": false, "timeout_sec": 2700,
             "marker": "not slow", "cmd": "…", "elapsed_sec": …, "pytest_rc": …, "timed_out": false},
  "totals": {"total": …, "passed": …, "failed": …, "failure": …, "error": …,
             "skipped": …, "xfailed": …, "duration_sec": …},
  "failed":  [{"id": "tests/test_x.py::test_y", "cid": "tests.test_x::test_y",
               "status": "failure", "file": "tests/test_x.py", "message": "…"}],
  "skipped": ["tests/test_x.py::test_z", …]
}
```

* `id` = `文件::用例名`（跨平台稳定，含参数化的 `[param]` 后缀）；
* `cid` = `classname::name`，与 light-merge 自带 CI 基线同一口径，方便交叉核对；
* 只存**非通过项明细 + 计数**，8106 用例的基线文件仍在一两百 KB 量级，可读可 diff。

---

## 六、本轮实测结果

见 `_task1_R55_082_lightmerge基线.md`（任务1）与 `_task5_R55_回归流程验证.md`（任务5）。

---

## 七、遗留 / 建议（未做，登记）

1. **0.82 缺 pytest-timeout / xdist**：目前靠 FreeBSD `timeout(1)` + 串行。若后续给 0.82 装上
   `pytest-xdist`（FreeBSD fork 启动模型对 `-n auto` 友好），7800 条快用例有望从 ~25 分钟降到 ~5 分钟。
   已留好开关：`test --parallel` 会自动探测 xdist，装上就能直接用，不用改脚本。
2. **slow 用例（303 条）**：本轮先固化 `-m "not slow"` 的 fast 基线，`--mode full` 已在脚本里，
   下一轮单独评估这 303 条的耗时与必要后再决定是否纳入常态门。
