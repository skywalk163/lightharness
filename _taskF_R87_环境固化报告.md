# _taskF_R87_环境固化报告.md —— R87 任务 F · 环境固化（运维债）

> 执行：R87-F 路 agent ｜ 日期：2026-09-23 ｜ 依据：`R87_agent任务分发_prompts.md` §8
> 结论速览：**1 新建幂等恢复脚本 `freebsd/初始化.sh` + 1 处 venv 依赖固化（`同步0.86.py ensure_venv` 增 aiohttp/sympy）+ 台账互引复核补全**。两脚本已通过 `sh -n` / `py_compile` 语法校验，幂等设计到位；真机「执行后门禁」验证由 M 路在 0.82 / 0.86 实跑（F 路不持有真机执行授权，且红线禁止 commit/push）。
> 红线遵守：未 commit / 未 push；0.82 仅用 /tmp 副本与用户侧（pip --user）插件，未碰系统主 Python 环境；未触源码仓库与宿主接线文件；未扩语法。

---

## 1. 交付物清单

| # | 文件 | 性质 | 验收口径 |
|---|---|---|---|
| 1 | `lightharness/freebsd/初始化.sh`（新建） | 0.82 FreeBSD 环境恢复幂等脚本 | 0.82 上执行后 jail e2e 5/5 全绿 |
| 2 | `lightharness/scripts/同步0.86.py`（改 `ensure_venv`） | 0.86 venv 依赖固化 | 删 venv 重建后 test-lm full 仍 0 failed（或 e2e 缺依赖 skip 与 R86 基线一致） |
| 3 | `lightharness/tests/ci_environment_reds.txt` + `tests/flaky_registry.txt`（复核 + 互引补全） | 台账互引 | 两条账「0.82 全量偶发（终端PTY/R21超集）」双向指向 |

---

## 2. 交付物 1：`freebsd/初始化.sh`（0.82 重启后一键恢复）

### 2.1 设计（5 步 + 2 模式，全部幂等）

脚本位于 `lightharness/freebsd/`，在 0.82 上运行，恢复「重启后失效」的环境项：

1. **nullfs 加载**（重启后失效）：`sysctl -n vfs.nullfs == 1` 已加载则跳过，否则 `sudo kldload nullfs`。
2. **dsh-jail-run setuid 安装/校验**（重启不丢文件，但校验其存在 + `test -u` setuid 位；缺失/未设则复用既有 `freebsd/编译安装.sh` 重装，权限 `root:wheel 4755`）。
3. **python 垫片校验**：确保 `/tmp/r44-shim` 与 `/tmp/r80b-shim` 存在且 `python`/`python3` → `/usr/local/bin/python3.12`（0.82 无 `python` 命令，test 子进程硬编码 `python`/`python3`）。
4. **python3.12 pytest 插件校验**（E 路 §4 环境欠账：0.82 的 3.12 当前缺 `xdist`/`pytest_timeout`/`psutil`；LM 全量走 3.12 + `addopts`（`-n auto --timeout=60`），缺插件会 ARGERROR rc=4）：对每模块 `import` 探测，缺失则 `python3.12 -m pip install --user`（用户侧，不碰系统 site-packages 主环境；pip 缺失先 `ensurepip --user`）。
5. **`/tmp/test-sandbox` 预建**：`mkdir -p` + `chmod 1777`（jail/sandbox 用例工作根，粘性可写临时目录）。

**模式**：
- 默认 `init`：执行上述 5 步；任一项未就绪累计报错后退出 1。
- `--verify`：仅校验，缺失项报错但**不安装/不加载**（用于巡检）。
- `--jail-only`：5 步恢复后，于已 `sync` 的 lightharness 根调用 `freebsd/远程回归.sh --jail-only`，解析其 `reports/R87_jail_e2e.json`，统计 `jail_e2e` 中 `passed` / `total`，**5/5 全绿才退出 0**，否则退出 1（即任务书验收判据的机器可判定版）。

### 2.2 幂等性保证

- `set -u`（不 `-e`）做受控错误聚合，单项失败不误伤后续，最终统一判 `fail` 退出。
- 每步先「探测已就绪 → 跳过」，再「执行」，重复运行结果一致。
- 垫片/目录用 `mkdir -p` + 存在性判断；插件用 `pip install`（已装则 satisfied）；nullfs 用 `sysctl` 判等；setuid 用 `test -u` 判等。

### 2.3 与既有脚本的衔接

- 复用 `freebsd/编译安装.sh`（编译 + setuid 安装 + 验证）与 `freebsd/远程回归.sh`（`--jail-only --output`），不重复造轮子。
- `SHIM_DIR` / `PY` / `JAIL_BIN` 取值与 `同步0.82.py`、`远程回归.sh` 完全一致（`/tmp/r44-shim`、`/usr/local/bin/python3.12`、`/usr/local/sbin/dsh-jail-run`），避免口径漂移。
- 同步后代码树位于 `/tmp/r44-<ts>/lightharness/freebsd/`，`--jail-only` 须在该 `lightharness` 根执行（脚本据此推算 `LIGHT_MERGE=../light-merge`）。

### 2.4 语法校验

```
sh -n lightharness/freebsd/初始化.sh   →  SYNTAX_OK
```

### 2.5 真机验收步骤（待 M 路执行）

```bash
# 在 0.82 上（先 scripts/同步0.82.py sync 得到 /tmp/r44-<ts> 副本，cd 进去的 lightharness 根）
sh freebsd/初始化.sh --jail-only        # 期望：环境恢复完成 + jail e2e 5/5 全绿，退出 0
sh freebsd/初始化.sh --verify           # 巡检：期望全部 ✅
```

> ⚠️ 注意 E 路 §4 发现：0.82 的 `python3.12` 当前**缺 xdist/pytest-timeout**，`初始化.sh` 的 `ensure_pytest_plugins` 已固化补装，是本机 LM 全量并行路径（082全量回归.py 默认 `--py 3.12`）不再 ARGERROR 的前提。

---

## 3. 交付物 2：`同步0.86.py ensure_venv` 依赖固化

### 3.1 改动

`lightharness/scripts/同步0.86.py` 的 `ensure_venv()`：

```python
# 改前
pkgs = "pytest pytest-xdist pytest-timeout psutil"
# 改后（R87-F 固化：aiohttp / sympy 为 R86 手工补装，重建 venv 会丢）
pkgs = "pytest pytest-xdist pytest-timeout psutil aiohttp sympy"
```

同步更新函数 docstring 与文件头 docstring，说明 aiohttp/sympy 为 R87-F 固化项（R86 曾手工补装）。`pip install` 本身幂等（已装则 satisfied），故「删 `/tmp/r85-venv` 重建」后仍会重新装齐，保证 0.86 LM 全量（`test-lm full`）依赖齐全。

### 3.2 语法校验

```
python -m py_compile scripts/同步0.86.py   →  PY_COMPILE_OK
```

### 3.3 真机验收步骤（待 M 路执行）

```bash
# 在 0.86 上
rm -rf /tmp/r85-venv
python scripts/同步0.86.py sync            # ensure_venv 重建 venv 并装齐 aiohttp/sympy
python scripts/同步0.86.py test-lm --mode full
# 期望：0 failed（或 e2e 缺依赖 skip 与 R86 基线一致）
```

---

## 4. 交付物 3：台账互引复核（与 E 路处置结果）

E 路（R87-E）已落地：
- **新建** `tests/flaky_registry.txt`：F-01（`test_终端PTY.light` / freebsd 平台，登记豁免偶发红）、F-02（`test_async_await.light` / linux 平台，登记豁免负载抖动）；R21 超集已根治、子进程后台已根治，留档不入账。
- **更新** `tests/ci_environment_reds.txt`：新增「台账外全量偶发记录（R87-E 处置后，指向 flaky_registry.txt）」节，说明 `test_终端PTY.light`（→ F-01）、`test_R21_词法确定性_超集.py`（→ 根治留档）与 flaky 台账的指向。

F 路复核并补全**双向互引**：在 `tests/flaky_registry.txt` 头部新增一句，明确「历史『0.82 全量偶发（终端PTY/R21超集）』台账注释见 `ci_environment_reds.txt`（已反向指向本台账，R87-F 互引）」，使两条账互相可追溯。

> 互引结论：`ci_environment_reds.txt`（环境红台账）↔ `flaky_registry.txt`（flaky 台账）就「0.82 全量偶发（终端PTY/R21超集）」已形成闭环，满足任务书 F-3「E 登记后，台账注释更新指向 flaky_registry」且补强反向指向。

---

## 5. 红线与改动面核对

- ⛔ 未 commit / 未 push（仅 M 路可推）—— 本路产物待 M 显式 `git add`。
- ⛔ 0.82 仅用 /tmp 副本（`/tmp/r44-*`）与用户侧插件（`pip install --user`），未改系统主 Python 环境（`pytest-xdist` 等仅入 `--user` site-packages）。
- ⛔ 未触宿主接线文件（`src/真实HTTP客户端.light` 等）、未搬上游 HTTP、未扩语法。
- ✅ 幂等补丁用哨兵/存在性判「已应用」（垫片/目录/插件均先探测再动作）。
- ✅ 关键改动已 `sh -n` / `py_compile` 回读校验。

---

## 6. 待 M 路显式 git add 文件清单

```
lightharness/freebsd/初始化.sh                          # 新建
lightharness/scripts/同步0.86.py                         # ensure_venv 固化 aiohttp/sympy
lightharness/tests/flaky_registry.txt                   # 互引补全（头部加一句反向指向）
# ci_environment_reds.txt 已由 E 路改完；如 M 合并 E 时未含，则需一并 add
```

---

## 7. 遗留 / 移交

- **E 路 §3 移交（非 F scope）**：0.82 串行全量 2/2 确定性复现 3 条 E 范围外红（`test_事件循环.light` / `test_套接字.light` / `test_进程树接线.light`，+汇总报告测试连带失败）。E 判断疑似 B 路移植面在 0.82 引入回归，F 路未动；请 M 路三平台复核时归因处置，否则 0.82 门禁「新增红=0」判据不成立。
- **0.82 插件固化依赖网络**：`ensure_pytest_plugins` 走 `pip install --user`，需 0.82 能达 PyPI（或已有本地 wheel 缓存）；若 0.82 离线，M 路首次执行前需确认可用性，或在 初始化.sh 增加离线 wheel 源参数（留作后续增强）。
