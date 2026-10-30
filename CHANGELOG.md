# 更新日志

本项目的所有值得记录的变更都写在这里。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号以轮次发布 tag 为准（如 `r95-dev`）。

## [未发布]

### 2026-10-30 · T-0180 合流 + 编译器路径探测

- **合流 GitCode `23f7cfa`**（T-0180 工作目录集中化：cwd 收拢为会话状态 + originCwd 派生 + 运行时断言）。
  与本地 `e097a99`（stdlib 同步：`原子写入` / `皆空` 自包含 / 删重复定义）改动的文件集合不重叠
  （`src/*.light` vs `stdlib/*`），`--no-ff` 合并零冲突。
- **`运行.py` / `scripts/互举反跑.py`：`LIGHT_MERGE` 默认值改为探测链。**
  原默认值是写死的 `G:\dswork\duan-light-merge\light-merge`，只有原作者那台 Windows 恰好命中；
  换机器（Linux / CI / 别人的 Mac）只要不显式设环境变量，就一律「找不到光明编译器」退出 ——
  表现是整套 `.light` 用例集体飘红，**看着像代码坏了，其实只是路径不属于这台机器**
  （本次合流后 `tests/test_T0180_工作目录集中化.py` 5 条全红就是这么来的）。
  现在按顺序探测 `$LIGHT_MERGE` → `../light` → `../light-merge` → `../duan-light-merge/light-merge`
  → `../../light` → 原 Windows 路径（兜底），显式环境变量仍最优先。
- **`tests/conftest.py`（新增）：收集前统一探测编译器路径。**
  13 个词法/回归测试文件各自写了 `LIGHT_MERGE = os.environ.get(..., r"G:\dswork\...")`
  + `sys.path.insert(0, <LM>/src)`，缺环境变量时在**收集期**就
  `ModuleNotFoundError: No module named 'lexer'`，21 个测试模块集体 ERROR。
  这 13 个文件写法本身没错（只是默认值不该写死），所以不改它们：conftest 在收集前
  把探测结果写回 `os.environ`，它们原样读到正确值。探测口径与 `运行.py` 一致。
- **`stdlib/列表工具.light` 同步（`builtins.求和` 的转发目标）。**
  `builtins.求和(数据)` 转发时传 **4 个位置参数**（数据 / 长整上限 / 启用补偿 / 整数进补偿），
  而本仓那份是 **3 参旧版**，于是 `求和() takes from 1 to 3 positional arguments but 4 were given`。
  只要 example 里出现 `求和([...])` 就炸 —— `test_R72_C_推导式`、`test_R20_词法边界综合`
  两条**由绿转红**（用 `git worktree` 在 `be7da46` 上对照确认，不是环境问题）。
  修法不是手改这份拷贝：把 `列表工具.light` 加进 light 侧 `sync_builtins.py` 的
  `LH_LIGHT_SYNC`（原先只登记 `内置核心判型.light`），由脚本机械同步；自检也改成
  **按文件各自的「必须含」判据**（原来一份判型判据套所有同步文件，加文件必误报）。
  教训：`builtins` 的**转发目标**签名必须与真源刚性咬合，这类关系要机械化，不能靠人记。

### 环境说明（不是代码问题）

- **缺 `lightplugin` 仓会让几十个 example 集体红**：`src/总入口.light` 的
  `从 生产挂载 导入 挂载全部插件` 报 `No module named '生产挂载'`，而 `运行.py` 对缺
  `LIGHTPLUGIN` 是**静默容忍**的（路径表返回空），不会告诉你缺的是哪个仓。
  已在本仓 README 的「环境准备」写明目录布局与该症状。
- 补齐依赖后仍红的 6 条属**平台能力差异**（`沙箱统一` 缺 landlock/bwrap、
  `事件循环` 的同 fd 读写派发顺序依赖 selector 实现），在基线 `be7da46` 上同样红。
- **装了 safe-delete 钩子的环境里，`test_启动配置.py` 会整片假红**（本次实测 12 条）。
  `run_in_repo` 在仓根写 `_unit_tmp_*.light` 并在 `finally` 里 `os.remove` 它；当运行环境
  装了「批量删除确认」守卫（`sitecustomize.py` 里 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`，
  阈值 50 次/轮）时，一轮全量累计到 90 次删除就抛 `SystemExit(1)`，
  表现为 `SystemExit: 1` 且**单跑该文件必过、混跑必红**——因为计数按进程/turn 重置。
  判定方法：看 `Captured stderr` 里有没有 `[safe-delete][...]`。
  这是**执行环境的守卫**，不是本仓缺陷；无守卫的 CI runner 上不会出现。

---

> **R110 收口（2026-10-03，维持 `v0.4.0-rc2`）**：A/C/D 文档交付、B 核实 0 移植、E Windows 本机双全量 0 新增红。零可执行代码改动 → 不 bump 版本号、不新建 tag。lightharness 三远端已推；light-merge 无 R110 改动未推。

### 新增

- 对齐 deepseek-harness 上游 `dsh-v0.2.0-rc.2`（`639ed01539`）相对 rc.1 的增量（**187 commits / 1022 真增量文件 / +33253 / -6141**，三点基准 `rc.1...rc.2`，merge-base `4878cdabd8`）。
- B 路经核实为 **0 移植**（lightharness 无对应纯逻辑层承载 A 清单 §4 的 4 组候选：schedule framing / user-questions 状态机 / tool-ask-user timed / shell 提示词文案）；`对标清单.json` 末位仍 #313，无 R110 新增。

### 修复

- 宿主面增量 15 条 append 进 `docs/宿主面登记清单.md` §7（44→59）：Windows ACL 修复链 / web-desktop UI / whale perf / Cordis inspect / desktop installer / llm pi-ai 升级 / CI 等。
- fork FreeBSD 脚本对账：上游 rc.2 无 freebsd/ 目录，fork 侧 `e5b5ccbfcb..8bf6c9250f` 零改动 → 零同步（`R110_D路_FreeBSD脚本对账.md`）。

### 验证

- LH 本机 Windows 全量 **2074 用例 / 0 failed / 0 new_red**（`reports/R110_lh_windows_latest.json`）。
- LM 本机 Windows 全量 **8489 用例 / 0 new_red**（1 为已知 flaky `test_进程类` 单跑复绿；R55 时代 5 红全清）。
- 锚点修正：分发书 `e5b5ccbfcb..rc.2` 两点口径有误（`e5b5ccbfcb` 是 fork 合流提交，会冒 freebsd 假删除）；真基准三点 `rc.1...rc.2`（merge-base `4878cdabd8`）。
- 遗留：0.86 Linux / 0.82 FreeBSD 基线 JSON 未生成（B=0 代码改动 ⇒ 逻辑上无 R110 新红风险，待补）。

---

## [v0.5.0-rc1] — 2026-10-28

> **0.2.1-rc.3 对齐收口（M 路 T-0179 合流）**：上游 `dsh-v0.2.0-rc.2 → dsh-v0.2.1-rc.3` 增量甄别（A 路）+ 纯逻辑移植（B1-B4 路）+ 宿主面登记（C 路）+ FreeBSD fork 同步（D 路）+ 三平台门禁回归（E 路）+ 新红取证处置（F 路），七路并行、M 路统一收口。版本自 `v0.4.0-rc2` 走 minor 位升 **`v0.5.0-rc1`**（B 路为上游 minor 特性移植，非 patch）。交付报告见 `docs/功能对标/0.2.1-rc.3对齐_交付报告.md`。

### 新增

- **A 路（T-0170）上游增量甄别**：`rc.2...rc.3` 实为「架构收敛 + 平台面扩张」——1487 条非 merge commit 中 feat 仅 146 条；真实代码增量 1047 个 src 文件（+50788/−15773）；纯逻辑可移植面收敛为 **14 项 / 47 文件**；宿主面（登记不移植）约 640 个 src 文件。产出 `docs/功能对标/0.2.1-rc.3增量清单.md`。
- **B1 路（T-0173）llm 簇纯逻辑复刻**：模型列表解码（`src/模型目录.light` +200 行，7 判据）、模型列表缓存（`src/模型列表缓存.light` 新建 142 行：分作用域/单飞/后台刷新/失败保留，6 判据）、令牌计量折叠（`src/令牌计量.light` +200 行：plan/commit 两段式 + O(1) 折叠 + 语境拆解投影，3 组判据）。
- **B2 路（T-0174）会话与存储面**：`src/智能体指令.light` agent-instructions 0.2.1 增量（442→589 行：双用户全局根与候选组去重、dshHome 不可覆盖、项目路径作用域转义等 6 点，19 组判据）。
- **B3 路（T-0175）subagent/workspace 簇**：`src/子代理预设选择.light`（175 行，12 例）、`src/子代理活化.light`（126 行，5 例）、`src/工作区成员.light`（66 行，5 例），端到端判据 `examples/test_R175_B3复刻.light`（34 断言）；B3 簇其余增量定性为 invariant.ts 批量退场 / locale i18n / 注释级，不移植。
- **B4 路（T-0176）typert/credentials/ptc-runtime/jobs 等 12 簇纯逻辑复刻**（对标清单 #334-#345）。
- **C 路（T-0171）宿主面登记扩容**：0.2.1 增量 append 进 `docs/宿主面登记清单.md`。
- **D 路（T-0172）FreeBSD fork 脚本同步**：`lightharness/freebsd/` ↔ fork 16 文件逐一对账（`freebsd/对账记录_rc3.md`），fork 侧 3 文件变动均判定 fork 专属 → 结论零同步（需重编 setuid 0）。

### 修复

- `stdlib/builtins.py`：`列表工具.求和` 调用实参由 1 退化为 4 的同步遗漏补回（E 路，消 `test_R20_词法边界综合` / `test_R72_C_推导式` 两红）。
- `src/钩子.light` 消息钩子判定：空字符串缘由被 `是空(缘由)` 误判为「无拒绝」而放行，改独立 `已拒绝` 标志位（F 路，消 `test_R48_hooks三事件`）。
- `src/字符串替换编辑器.light`：`执行编辑命令` 的 `path=""` 被误判缺参、`必填参数` 的空串 `值` 被误判必填缺失，两处改键存在性 / None 判断（F 路，空文件 `allowEmpty=真` 语义恢复）。
- `tests/test_R21_词法确定性_超集.py`：`者种类` 误报白名单（旧基线 d2857dd5 把形参 `接收者种类` 截头登记，非 lexer 丢名；F 路复核确认为有意豁免）。

### 验证

- **Windows LH 全量**：初刷 2103 用例 / 6 failed（`reports/本机lh基线_latest.json`，R177 首刷）；E 路修复 2 处后复跑绝对红 6 → 3（真红 3 + Windows 环境飘红 5，隔离复跑绿，`R177_E路_三平台门禁回归报告.md`）；F 路修复后 run2 **2085 passed / 1 failed**（唯一余红 `agentE5钩子` 为越界红：根因在 light-merge 编译器 R128 起 `段落 调用()` → `__call__` 映射，非本仓 B 线引入，开卡跟踪）。
- **FreeBSD 0.88 LH 全量** 2103 用例：修复前 6 failed（`R177_LH_0.88基线_20261027-212754.json`，Windows 侧同源）；E 路修复后真红 3，均已修。
- **Windows LM 全量** 9433 用例 / 23 红（`reports/本机lm基线_latest.json`，passed 9276）：21 条新增红经取证与 B 线无因果（lightmem 仓），移交 LM 专项卡。
- **新增 flaky 登记**（`tests/flaky_registry.txt` F-03~F-09）：5 条 Windows xdist 偶发（隔离复跑恒绿）+ 2 条 PTY 环境红（无 console session 下 `CreatePseudoConsole` 稳定 E_INVALIDARG）。
- **Linux 0.86 腿**：机器不可达，本轮阻塞未跑（遗留，见交付报告）。

---

## [r95-dev] — 2026-09-25

R95 收口：**根因战场闭环**（LH `61e004a`，分支 `release/r95`，tag `r95-dev`）。

### 新增

- 发布分支 `release/r95` 与 tag `r95-dev`。
- Job Object 与创建时间闸门：为进程树治理提供可复用的根治判据。

### 修复

- 进程树根因类问题闭环：从"现象修补"推进到"根因可验证"，同类问题不再反复复发。

### 验证

- Job Object 闸门 + 创建时间闸门双证据链，为进程树的根治结论提供端到端验证。
- 远端 FreeBSD 门禁机三平台回归通过。

---

## [r94-dev] — 2026-09-25

R94 收口：**开发冻结收口**（LH `eae81f1`，分支 `release/r94`，tag `r94-dev`）。

### 新增

- 发布分支 `release/r94` 与 tag `r94-dev`，把本轮开发面冻结在一个可回溯的提交上。

### 修复

- 本轮开发面冻结，此后不再接受散乱改动，变更一律走新的发布分支。

### 验证

- 冻结面对应的回归门禁通过，作为 R95 根因战场的基线。

---

## [r87] — 2026-09-23

R87 收口：**上游 0.1.7 纯逻辑面移植**（HEAD `7cc0fa8`）。

### 新增

- 对齐 deepseek-harness 上游 0.1.7 的纯逻辑增量，完成对应区域的移植与落位。
- 移植过程产生的语言侧需求登记进 `docs/功能对标/语言缺陷账.md`。

### 修复

- 移植暴露的 flaky 用例完成根治处置（见 `_taskE_R87_flaky根治报告.md`）。
- 门禁补位：修正 light-merge 侧与本仓之间的回归门缺口（见 `_taskD_R87_LM门禁补位报告.md`）。

### 验证

- 三平台 LH 全量回归：**1400 用例 0 失败**。
- 环境固化项入档（见 `_taskF_R87_环境固化报告.md`），确保不同机器跑出同一结果。
