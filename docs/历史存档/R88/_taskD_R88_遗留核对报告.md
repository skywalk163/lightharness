# R88 D 路・其它遗留核对与补账报告

> 轮次：R88 D 路 ｜ 2026-09-23
> 范围：核对 R85/R86/R87 收口报告全部遗留项销账状态；回填 docs/多平台差异清单.md R88 结论；核对 docs/宿主面登记清单.md 完整性；核对环境固化脚本与台账互引。
> 红线遵守：只读 + 文档，未改任何 src/ 逻辑；未 commit/push；未清理临时文件。
> 依赖报告：A 路 `_taskA_R88_alpha2差量清单.md`（已交付）、B 路 `_taskB_R88_FreeBSD环境红处置报告.md`（已交付）、C 路 **尚未产出**（Windows LM 47 条清零报告缺失，相关章节标注为待回填）。

---

## 0. 核对总览

| 核对项 | 结果 |
|--------|------|
| R85/R86/R87 全部遗留项 | ✅ 全部有明确状态（详见 §1） |
| docs/多平台差异清单.md R88 回填 | ✅ 已回填（详见 §2，文件已更新） |
| docs/宿主面登记清单.md 完整性 | ⚠️ R87-A 部分已覆盖；R88-A alpha.2 新增 3 项需补充登记（详见 §3） |
| 环境固化脚本与台账互引 | ✅ 互引完整（详见 §4） |
| C 路本机 venv 补库固化 | ⏸ C 路报告未产出，固化建议见 §4.3 |

---

## 1. 遗留清单状态表

### 1.1 R85 收口报告遗留（8 项）

| # | 遗留项 | 当前状态 | 证据/说明 |
|---|--------|----------|-----------|
| 1 | **F 批2 收尾**：0.86 无 sudo 装不了 bwrap/landlock → 沙箱真后端 e2e fail-closed | **✅ 已销账** | R86-D 已修（方案 b）：Linux 链加 rlimits 无特权兜底后端（纯 Python resource.setrlimit）；0.86 实测三态 e2e 通过。见 `_taskM_R86_收口报告.md` §6.2.1。 |
| 2 | **R66/R68 socketpair 遗留上桌**：7 条 Linux 红（socketpair(AF_INET) → EOPNOTSUPP） | **✅ 已销账** | R86-B 已修：`stdlib/套接字.light` 新增 `套接字对可用族()` 平台映射（win32=AF_INET / POSIX→AF_UNIX）；0.86 与 Windows 7/7 全绿。0.82 全量复跑坐实 1372/0/0。 |
| 3 | **setsockopt EACCES（test_套接字）+ async_await 并发耗时**：Linux 平台差异 | **✅ 已销账** | R86-B 已修 setsockopt（TCP_NODELAY 改走 IPPROTO_TCP 级别 + SO_REUSEADDR 断言改开关语义）；R86-C 已修 async_await 阈值（0.18→0.35）。0.86 双平台 1371/0/4。 |
| 4 | **沙箱探测测试适配**：无后端平台应断言「探测=不可用」而非 rc=1 | **✅ 已销账** | R86-D 已修：沙箱统一已实现分支真执行 + 三态 e2e；0.86 实测通过。 |
| 5 | **github push 补推**：网络恢复后补推（当时落后到 55191fc） | **✅ 已销账** | R86 已补推成功：`09ceb73..ac4be9d main -> main`。三远端全部同步到 ac4be9d。 |
| 6 | **词法红另开轮** | **✅ 已销账** | R86-A 已修：14 条词法断言对齐，Windows 与 0.86 双平台 LH 全量 1371/0/4。 |
| 7 | **宿主面登记清单汇总** | **✅ 已销账** | R87-C 已产出 `docs/宿主面登记清单.md`（53 条：已坐实 11 / 登记 41 / 下轮 1）。D 路本轮核对见 §3。 |
| 8 | **上游跟踪锚点**：以新 release 为准 | **✅ 已销账（R88 A 路）** | R87 覆盖至 alpha.1（fork HEAD 877717787c）；R88 A 路追平至 alpha.2（upstream 00102833df），本地合入验证通过（merge commit 6bf98a4370）。fork push 权在 M 路。 |

### 1.2 R86 收口报告遗留（4 项）

| # | 遗留项 | 当前状态 | 证据/说明 |
|---|--------|----------|-----------|
| 1 | **0.82 FreeBSD 复跑** | **✅ 已销账** | R86 已完成（2026-09-22）：1372 passed / 0 failed / 0 errors / 3 skipped（537.86s）；台账 8 条全部销账并归档。R87-M 复核发现 R86 销账依据无效，回补 3 条（E-01/E-02/E-06）→ R88 B 路已处置。 |
| 2 | **0.86 LM 15 条环境红** | **✅ 已销账** | R86 已完成：full 口径 0 failed（8191 passed / 94 skipped）；15 条 = aiohttp×2 + sympy×5（venv 缺依赖）+ e2e_chain×8（示例语法 bug）。 |
| 3 | **github push** | **✅ 已销账** | 同 R85 第 5 项。 |
| 4 | **上游跟踪锚点**：以新 release 为准 | **✅ 已销账** | 同 R85 第 8 项。 |

### 1.3 R87 收口报告遗留（§9.2，4 项）

| # | 遗留项 | 当前状态 | 证据/说明 |
|---|--------|----------|-----------|
| 1 | **内网 fork 滞后 gitcode alpha.2 共 162 提交** | **✅ 本轮处置中（A 路已完成）** | A 路已交付 `_taskA_R88_alpha2差量清单.md`：162 提交 100% 落表（三分类甄别）；本地合入验证通过（merge commit 6bf98a4370，CLEAN）；纯逻辑面 1 项已移植（`溢出保留.light` + 回归用例，本机全绿）。fork push 权在 M 路。 |
| 2 | **FreeBSD 3 条固有环境红（E-01/E-02/E-06）** | **✅ 本轮处置中（B 路已完成）** | B 路已交付 `_taskB_R88_FreeBSD环境红处置报告.md`：3 条均一手取证（各 2/2 rc=1 确定性红复证）+ 根因定性（kqueue 派发顺序 / 回环 send 阻塞时序 / 沙箱 CPU 时间 vs 挂钟）+ 维持豁免（修复超 B 路改动面）；LM 同族 1 条（test_coro_sleep_basic）按 flaky 路径处置（隔离 2/2 绿，非确定性红）；判据接线核对正确，self-check 全 PASS。 |
| 3 | **Windows LM 47 条（14 补库 + 33 平台差异）** | **⏸ C 路报告尚未产出** | C 路报告（`_taskC_R88_WindowsLM47清零报告.md`）不存在。14 条补库（lunardate/requests）可直接执行；33 条归因处置待 C 路完成。本路已确认 0.86 与 FreeBSD LM 基线无新增红（`多平台矩阵.py --mode lm-full` = PASS）。 |
| 4 | **宿主面登记清单 + client UI 保持不移植** | **⚠️ 部分覆盖** | `docs/宿主面登记清单.md` 已在仓，覆盖 R85 遗留 7 号 + R87-A 新增宿主面（53 条）。**R88-A alpha.2 新增 3 项宿主面需补充登记**（详见 §3.3）。client UI 渲染层保持不移植结论不变。 |

### 1.4 跨轮次遗留项（非收口报告登记，但跨轮追踪）

| 来源 | 遗留项 | 当前状态 | 说明 |
|------|--------|----------|------|
| R85 §1 | 0.86 Linux 额外 10 条红归因 | **✅ 已销账** | R86 全部清零（A 词法 14 + B socket 8 + C async 1 + D 沙箱 2）。 |
| R86 §5 | 0.82 FreeBSD 台账修正 | **✅ 已销账** | R87-M 复核发现 R86 销账依据无效，回补 3 条 → R88 B 路已处置并固化根因。 |
| R87 §9.2 | 上游跟踪锚点 | **✅ 已销账** | R88 A 路追平 alpha.2。 |

---

## 2. docs/多平台差异清单.md 回填记录

> 文件：`lightharness/docs/多平台差异清单.md`
> 操作：在文件末尾（R87 §6 之后）追加 R88 增量段。
> 状态：✅ 已执行（见文件最新内容）。

### 2.1 回填内容摘要

| 子项 | 回填要点 | 数据来源 |
|------|----------|----------|
| fork 追平（A 路） | 162 提交差量甄别完成；本地合入验证通过（merge 6bf98a4370）；纯逻辑面 1 项移植（溢出保留.light）；161 条登记/暂缓 | `_taskA_R88_alpha2差量清单.md` |
| FreeBSD 环境红处置（B 路） | E-01/E-02/E-06 维持豁免，根因已定性并写入台账；LM 同族 1 条按 flaky 路径；判据接线不变 | `_taskB_R88_FreeBSD环境红处置报告.md` |
| Windows LM 清零（C 路） | **⏸ 待 C 路完成后回填** | C 路报告缺失 |
| LM 侧环境红台账 | B 路未新建 LM 环境红台账（coro flake 按 flaky 路径）；C 路 Windows 台账待产出 | B 路报告 §1 LM 同族节 |

### 2.2 回填文本（已写入文件）

已在 `lightharness/docs/多平台差异清单.md` 末尾追加 `## R88 增量（2026-09-23）` 段，包含：
- §0 fork 追平（A 路）
- §1 FreeBSD 环境红处置（B 路）
- §2 Windows LM 清零（C 路，待回填）
- §3 LM 侧环境红台账状态

---

## 3. docs/宿主面登记清单.md 核对结果

> 文件：`lightharness/docs/宿主面登记清单.md`
> 基线：R87-C 产出，覆盖 R85 遗留 7 号 + R87-A §2-B 新增宿主面。
> 核对范围：R88-A alpha.2 162 提交中宿主面（宿）增量是否 100% 收录。

### 3.1 现有覆盖确认

| 范围 | 状态 | 说明 |
|------|------|------|
| R85 遗留 7 号宿主面（HTTP/files-api/pi-ai/git/LibreOffice/Node/Cordis/FFI） | ✅ 已覆盖 | §2.1–§2.8 全部收录，每条有现状与三平台列。 |
| R87-A §2-B 新增宿主面（FreeBSD jail/node-pty/ripgrep/terminal-bash/native flock/crypto polyfill/settings-controller/path-opener/CI/host 包） | ✅ 已覆盖 | §3.1–§3.10 全部收录。 |
| R85-E 等额外宿主面登记 | ✅ 已覆盖 | §4 收录 16 条。 |

### 3.2 统计核对

| 状态 | 条数 | 与文件一致 |
|------|------|-----------|
| 已坐实 | 11 | ✅ 一致（§5） |
| 登记 | 41 | ✅ 一致（§5） |
| 下轮 | 1 | ✅ 一致（§5） |
| **合计** | **53** | ✅ |

### 3.3 R88-A alpha.2 新增宿主面（需补充登记）

A 路 R88 在 162 提交差量中识别出 **3 项宿主面增量**，尚未在宿主面登记清单中收录：

| # | 新增宿主面 | 来源提交 | 上游实现面 | lightharness 现状 | 三平台 | 建议状态 |
|---|-----------|---------|-----------|------------------|--------|---------|
| 54 | **plugin-manager 响应式公共注册表**（注册表选择 + 国家镜像 + 记住注册表） | #33/#77/#112 | `packages/plugin-manager/` 注册表选择/镜像/记住逻辑 | 部分：`插件管理.light` 已有纯逻辑（宿主钩子["执行安装"]），注册表选择/镜像/记住逻辑未移植 | Win ✓ / Linux ✓ / FreeBSD ✓ | **登记**（与现有 §2.6 Node 安装同族，可合并坐实） |
| 55 | **subprocess-local spill 失败 containment**（onFailure 回调降级为内存 tail，不 kill host） | #110 | `packages/subprocess/subprocess-local/src/output.ts` | 缺：lightharness 子进程为光明 stdlib 复刻，Node fs 错误模型不同，无对应落点 | Win ✓ / Linux ✓ / FreeBSD ✓ | **登记**（A 路已判定为宿主面，非纯逻辑） |
| 56 | **client-modules 失败批脚本恢复**（recover from failed batch script） | #106 | `packages/client-modules/` 批量脚本恢复 | 缺：无 client-modules 模块 | Win ✓ / Linux ✓ / FreeBSD ✓ | **登记** |

> **建议**：M 路合流时，将以上 3 项追加到宿主面登记清单 §4（或新建 §6「R88-A alpha.2 增量」），保持格式对齐。

### 3.4 client UI 渲染层保持不移植确认

- R87-C 已确认：client UI 渲染层（.tsx/.css/store）不移植，登记为宿主面。
- R88-A alpha.2 差量中 42 条 chat/UI/desktop 变更（#7–#24/#36/#41/#48/#52/#55/#58/#65/#67/#69/#70/#72/#75/#80–85/#88–96/#101/#102/#105/#107/#111/#114/#117/#119/#122/#127/#129–131/#134/#136/#138–143/#147–153/#155–156/#158–162）均为 UI/desktop/client 前端变更 → **保持不移植**，与 R87 结论一致。
- 登记清单 §3.10 已覆盖 host 包 / website 目录（含 frontend-static/open-in-app/webserver/plugin-inventory 等）→ UI 类宿主面已覆盖。

---

## 4. 环境固化脚本与台账互引核对

### 4.1 `freebsd/初始化.sh`（R87-F 产出）

| 核对项 | 结果 |
|--------|------|
| 文件存在 | ✅ `lightharness/freebsd/初始化.sh`（R87-F 环境固化路） |
| 幂等性 | ✅ 已加载的 nullfs / setuid / 垫片 / pytest 插件 / /tmp/test-sandbox 全部已就绪则跳过 |
| 0.82 实跑验证 | ✅ R87-M 已验：`--jail-only` → jail e2e 5/5 全绿 |
| 与 ci_environment_reds.txt 互引 | ✅ 台账 R87-M 节注释指向初始化.sh；初始化.sh 头部注释指向台账 |

### 4.2 `scripts/同步0.86.py ensure_venv`（R87-F 固化）

| 核对项 | 结果 |
|--------|------|
| 文件存在 | ✅ `lightharness/scripts/同步0.86.py`（line 252+ ensure_venv） |
| 依赖集完整 | ✅ 13 包锁版本：pytest/xdist/timeout/psutil/aiohttp/sympy/requests/cryptography/numpy/pandas/matplotlib/lunardate/antlr4==4.13.2 |
| 0.86 重建验证 | ✅ R87-M 已验：删 venv 重建 + test-lm full → 8298 收集 / 8193 passed / 0 failed / 94 skipped |
| 与台账互引 | ✅ ensure_venv 注释列出每包对应测试文件（requests→lightpub、lunardate→test_datetime 等） |

### 4.3 Windows 本机 venv 补库固化建议（C 路未产出，本路给出建议）

C 路尚未产出 `_taskC_R88_WindowsLM47清零报告.md`，无法确认 C 路是否已固化本机 venv 补库步骤。本路给出以下固化建议，供 M 路决定是否落脚本：

| 建议 | 内容 | 优先级 |
|------|------|--------|
| **S1** | 在 `light-merge/` 下新建 `scripts/ensure_venv.py`（或并入现有脚本），固化 Windows 本机 .venv 的第三方库安装：`pip install lunardate requests`（14 条补库项） | 高（14 条立即可消） |
| **S2** | 在 `ensure_venv.py` 中锁定版本（对齐 0.86 口径）：`lunardate==0.3.0`、`requests==2.34.2`（0.86 已锁版本，Windows 应同步） | 中 |
| **S3** | 在 `scripts/多平台矩阵.py` 的 `--mode lm-full` 执行前，自动调用 ensure_venv 检查依赖（幂等：已装则跳过） | 中 |
| **S4** | 若 C 路产出新的 Windows LM 环境红台账（`tests/lm_environment_reds.txt`），应将其纳入 `ci_judge_env_reds.py` 或新建判据脚本（参照 FreeBSD 台账模式） | 待 C 路产出后决定 |

> **注意**：以上建议仅为本路核对产出，未执行任何改动。M 路决定是否落脚本。

---

## 5. 判据达成总结

| 判据 | 结果 |
|------|------|
| R85/R86/R87 全部遗留项有明确状态 | ✅ 16 项（R85×8 + R86×4 + R87×4）全部标注状态 + 证据引用 |
| 差异清单已回填 | ✅ `docs/多平台差异清单.md` 已追加 R88 增量段（C 路部分标注待回填） |
| 宿主面登记核对无遗漏 | ⚠️ R87-A 部分完整；R88-A alpha.2 新增 3 项需补充登记（已列明建议） |
| 环境固化脚本与台账互引 | ✅ 完整 |
| 无未授权改动 | ✅ 仅更新 docs/多平台差异清单.md + 产出本报告；未改任何 src/ 逻辑 |

---

## 6. 改动文件与产出

| 文件 | 操作 | 说明 |
|------|------|------|
| `_taskD_R88_遗留核对报告.md` | **新增** | 本报告 |
| `lightharness/docs/多平台差异清单.md` | **追加** | R88 增量段（§7 R88 增量） |
| `lightharness/docs/宿主面登记清单.md` | 未改动（仅核对） | 建议 M 路追加 3 项 R88-A alpha.2 宿主面 |
| `lightharness/tests/ci_environment_reds.txt` | 未改动（仅核对） | B 路已追加 R88-B 根因注释 |
| `lightharness/freebsd/初始化.sh` | 未改动（仅核对） | 互引完整 |
| `lightharness/scripts/同步0.86.py` | 未改动（仅核对） | 依赖集完整 |

---

## 7. 遗留移交 M 路

1. **C 路报告缺失**：`_taskC_R88_WindowsLM47清零报告.md` 未产出 → M 路需确认 C 路是否已完成、是否需补产报告。
2. **宿主面登记清单补充**：建议 M 路将 R88-A alpha.2 新增 3 项（plugin-manager 注册表 / subprocess spill containment / client-modules 恢复）追加到宿主面登记清单。
3. **Windows 本机 venv 固化**：建议 M 路决定是否落脚本（见 §4.3 S1–S3）。
4. **fork push 前置**：M 路 push 前须在 `r88-fork-sync` 分支重新 `pnpm install`（A 路报告 §5.1）。
5. **lightharness 新增 2 文件**：`src/溢出保留.light` + `examples/test_R88_A_溢出保留.light`（A 路产出）需 M 合流入仓。
6. **B 路改动**：`tests/ci_environment_reds.txt` R88-B 注释追加需 M 合流。
