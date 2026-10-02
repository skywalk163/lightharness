# 国庆 Day3 凌晨场・派单表（v1.0，2026-10-03 06:xx）

> 上一批：`Day2深夜_派单表.md` v1.0（T1–T5 五路全完成，已合流 `0df01e7` 并推三远端）
>
> **本批为「把上一批发现的问题真正修掉」的一轮**，目标 1.5–2.5 小时，无人值守
>
> **前置状态**（2026-10-03 06:2x）：
> - lightharness main = `0df01e7`（三远端一致，github 侧为 API 快进 `e44eeb2d`）
> - light-merge main = `221db4fc6`（工作树仅 `?? logs/`）；lightplugin main = `62a5961`
> - 门锚点：`reports/082_lightmerge基线_2026-10-02-234800.json`（8357/0/121）
> - 上一批遗留（本批要处理）：
>   ① Quality Gate 每次 push 必红同样 3 条（**最高优先级**）
>   ② 版本字符串停在 `0.4.0rc1`，tag 已到 `v0.4.0-rc2`
>   ③ ANTLR 覆盖面成簇 + SRC `返回 跳过` 取值缺口（已发现，未立账）
>
> **🚫 本批铁律**：
> - 不打 `v0.4.0` 正式 tag，不触发 PyPI/VSCE 真发
> - **不动 `light-merge/src/` 编译器代码、不动 `antlrparser/`**（T2 只改 workflow，T5 只加探针不修）
> - 不动 `ci.yml`（它是全绿的，别把好的改坏）；T2 只动 `quality-gate.yml`
> - 不改任何测试的**断言逻辑**（T2 用 `--ignore` 剔除而非放宽断言）
> - `.env` 的 token/密码值不出现在任何日志/报告
> - 本批**末尾仍需 push**（用户已授权），push 后必须轮询 Actions 验证 T2 是否真的转绿

---

## 二、子任务清单（5 路）

| # | 任务 | 线 | 仓库/资源 | 需门 | 前置 | 出口 tag |
|---|---|---|---|---|---|---|
| **T1** | **QG 三条红定量复现**：本机量出三条红的真实耗时，定位根因（cov？xdist？runner？），给出修复参数 | A（诊断） | light-merge 本机 | 否 | 无 | `subtask-T1-done` |
| **T2** | **quality-gate.yml 修复**：按 T1 结论做最小改动 + 本机复刻验证 | A（CI） | light-merge/.github/workflows | 否 | T1 | `subtask-T2-done` |
| **T3** | **版本号 rc1→rc2 归位 + preflight 锚点去硬编码** | B（发布） | light-merge | 否 | 无 | `subtask-T3-done` |
| **T4** | **1.5 盒子隔夜观察**（距上次 6 小时）+ 温缓存补到 10 样本 | C（运维） | 192.168.1.5 | 否 | 无 | `subtask-T4-done` |
| **T5** | **新账立账**：LP-D-018（`返回` 关键字词变量）+ LP-D-019（ANTLR 覆盖面簇）+ 探针 | B（文档） | lightharness/docs | 否 | 无 | `subtask-T5-done` |

> **并行关系**：T1→T2 串行（T2 依赖 T1 结论）；T3 / T4 / T5 互相独立，与 T1/T2 无共享资源。
> T4 占 1.5；T3 占 light-merge；T5 占 lightharness/docs；T1/T2 占本机 + light-merge。

---

## 三、各任务要点

### T1 · QG 三条红定量复现（A 线）

**为什么**：上一批 T5 发现 Quality Gate 每次 push 必红同样 3 条，但**只知道现象不知道量**。
不量出「本机多久 / 带 cov 多久 / 阈值是多少」，T2 就是拍脑袋改参数 —— 而拍脑袋改阈值
正是「把门禁改成永绿」的经典走法。

- 在本机跑 `tests/unit/test_package_manager.py` + `tests/unit/test_lexer_perf.py`，
  分别测 **无 cov** 与 **带 `--cov=src`**（复刻 QG 口径，`addopts` 自带 `-n 4`）
- 对照 GitHub runner 上的实测值（rc1 26.72s / rc2 20.13s，来自上一批 T5 的日志）
- 验证 `--timeout=180` 能否覆盖 `addopts` 里的 `--timeout=60`（pytest 选项优先级）
- 出口：一张定量表（本机无 cov / 本机带 cov / runner 实测 / 阈值余量）+ 修复参数裁定

### T2 · quality-gate.yml 修复（A 线）

**为什么**：这是上一批点名「优先级高于打正式 tag」的问题。

- **改动 1**：单元测试步显式加 `--timeout=180`（覆盖 addopts 的 60）
- **改动 2**：单元测试步把 `tests/unit/test_lexer_perf.py` 用 `--ignore` 剔除，
  理由必须写进注释：**性能断言 + coverage 插桩 = 测量被污染**，
  其守护交给 ci.yml 的无 cov 会话（`pytest tests/unit/`，默认预算 10.0s，12 份矩阵全覆盖）
- **不动**：ci.yml、测试文件的断言、`--cov`（覆盖率门禁本身要保留）
- **本机验证**：用复刻 QG 口径的命令跑一次，确认不红
- **真实验证**：push 后轮询 Actions，看 Quality Gate 是否由 failure 转 success
- 出口：workflow diff（仅单测那一步）+ 本机验证输出 + push 后的 Actions 结论

### T3 · 版本号 rc1→rc2 归位（B 线）

**为什么**：上一批 T3 记的账 —— 「rc2 的 tag 会编出 rc1 的包号」。发版前必须归位。

- `src/version.py` 的 `VERSION_NAME`、`pyproject.toml`、`vscode-extension/package.json`、`CHANGELOG.md`
  四处 rc1 → rc2
- `scripts/release_preflight.py:139` 的硬编码锚点 `0.4.0rc1` → **改为读本地最新 `v*` tag**
  （避免以后每个 rc 都要手改脚本，也让"版本滞后于 tag"这类问题自己暴露）
- **验证三件套**：`tests/unit/test_version_single_source.py` 全绿 + `release_preflight.py` 仍 11✅0❌
  + 重跑 `build_release.py` 确认产物名变成 `lightgm-0.4.0rc2-*`
- 出口：四处改动清单 + 三件套验证输出 + rc2 产物名

### T4 · 1.5 盒子隔夜观察（C 线）

**为什么**：上一批观察窗口只有 30 分钟（23:43→00:13），且温缓存只跑了 3 样本（证据偏弱）。
现在是 06:2x，距上次观察 6 小时 —— 能验证「长时间无人干预是否稳定」，并把温缓存补到 10 样本。

- PID 链是否与 6 小时前一致（daemon 55645 / pnpm 57424 / node 57487）
- swap / 负载 / OOM
- loopback 栅栏（401 + LAN 000）
- **温缓存 10 样本**（与白天口径对齐，给"是否退化"一个硬结论）
- 出口：观察报告，明确回答「6 小时零重启？温缓存是否退化？」

### T5 · 新账立账（B 线）

**为什么**：上一批 T2 在核对缺陷账时挖出两条**新观察**，当时明确写了「不改状态、建议单独立账」。
不立账就会像 LP-D-010 那样再漂一轮。

- **LP-D-018**：SRC 后端 `返回 <关键字词变量名>` 取不到值（`返回 跳过` → `None`，ANTLR 得 `[7]`）
- **LP-D-019**：ANTLR 后端覆盖面簇 —— ① `K_CALLBACK` 作段名/循环变量；② 判型族内置
  `是数字`/`是数字符` 未注册；③ 索引切片 `"abcdef"[1:3]` 解析失败
- 每条配**可复跑探针**（落 `docs/国庆7天/probes/`），并当场跑出两后端 rc
- 出口：账里新增两行 + 探针文件 + 实测表

---

## 四、出口判据

| # | 通过判据 |
|---|---|
| T1 | 定量表（本机无 cov / 带 cov / runner / 阈值余量）+ 明确写出 T2 该用什么参数、为什么 |
| T2 | workflow diff 仅单测一步；本机复刻绿；**push 后 Actions 的 Quality Gate 结论 = success** |
| T3 | 四处版本号改完；version 单源门禁绿；preflight 仍 11✅0❌；产物名为 rc2 |
| T4 | 6 小时零重启 + 温缓存 10 样本给出明确结论 |
| T5 | 账新增 2 行，每行有探针 + 两后端实测 rc |

**收口后判断点**：
1. Quality Gate 是否真的转绿？没绿就再来一轮（本批留了时间）
2. 版本归位到 rc2 后，是否要直接发 `v0.4.0` 正式？（本批不发，留给用户）

---

## 五、附录 · 禁令（沿用 + 本批新增）

1. 🚫 打 `v0.4.0` 正式 tag / 真发 PyPI/VSCE
2. 🚫 动 `src/` 编译器代码、`antlrparser/`、`ci.yml`
3. 🚫 改测试的断言逻辑来"变绿"（只允许用 `--ignore` 把性能断言移出 cov 会话）
4. 🚫 `git checkout -- .` / `git clean -fd`
5. 🚫 `.env` token/密码值落盘
6. ✅ **允许且需要**：末尾 push 三远端，并轮询 Actions 验证
