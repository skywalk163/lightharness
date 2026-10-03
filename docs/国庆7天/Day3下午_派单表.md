# 国庆 Day3 下午场・派单表（v1.0，2026-10-03 12:xx）

> 上一批：`Day3清晨_派单表.md`（T1–T6 全收；light-merge `fa233209f` / lightharness `5c54b32`）
>
> **本批目标**：① rc2 两红（PyPI / 文档站）重跑转绿；② v0.4.0 正式 tag 出口；③ 清 LP-D-019①③ ＋ ANTLR 覆盖面批量补齐；④ 账目/矩阵/总结收口。目标 3–4 小时。
>
> **前置状态（2026-10-03 12:xx）**：
> - 三仓 main：LH `5c54b32` / LM `fa233209f` / LP `62a5961`，全部 0 ahead
> - 门锚点：`reports/082_lightmerge基线_2026-10-03-093246.json` = **8357 / 0 / 121**
> - rc2 run `#37020855509`（tag `v0.4.0-rc2` → `221db4fc6`）唯二红的**处置已就位**：
>   - **发布到 PyPI**：trusted publisher 已关联（用户确认）→ 待重跑
>   - **部署文档站点**：environment `github-pages` 已追加 `v*` tag 策略（id 61812294，main 白名单未动）→ 待重跑
> - **rc2 run 尚未重跑**（截至写表）
> - **VSCE_PAT 暂不配**（本批不碰 VSCE job，它继续 failure 是预期）
>
> **🚫 本批铁律**：
> - **T1 重跑 = 真发 `0.4.0rc2` 上 PyPI**（用户已示意"关联好了"）——这一条就是 T1 的本体，不是诊断
> - 🚫 `v0.4.0` 正式 tag 在 **T1 两红转绿之前**不许打
> - VSCE job 不处理（token 未配，红是预期）
> - 门跑禁 `refresh-local` 自比；`CODEBUDDY_SAFE_DELETE_ENABLED=0` 必加
> - `.env` / GitHub secret / PAT 的值不出现日志报告
> - 🚫 改测试断言来"变绿"
> - B 线（T3/T4/T5）合并跑**一次** full 门（约 50 分钟独占），不是各跑一次
> - push 需用户示意（批次末尾统一）

---

## 二、子任务清单（7 路，4 线）

| # | 任务 | 线 | 仓库/资源 | 需门 | 前置 | 出口 tag |
|---|---|---|---|---|---|---|
| **T1** | **rc2 Re-run failed jobs 盯梢**：重跑 `#37020855509` 的 publish-pypi（真发 `0.4.0rc2`）+ deploy-docs，盯两条转绿；红则按 `Day3清晨_T1/T2` v2 报告的根因清单处置 | A（发布链） | GitHub Actions | 否 | 用户示意（PyPI 已关联 / Pages `v*` 已放开） | `subtask-T1-done` |
| **T2** | **v0.4.0 正式 tag 出口**：pyproject 版本号归位 `0.4.0` ＋ `release.yml` L223 `password:` 行删除（OIDC 单路径化）＋ tag runbook ＋ 打 `v0.4.0` 触发 release 全绿核对 | A（发布链） | light-merge/pyproject.toml + .github | 否（版本号是元数据，不触语义面） | **T1 绿 ＋ B 线收口后**（tag 打在含修复的 commit） | `subtask-T2-done` |
| **T3** | **修 LP-D-019①**：词法关键字 `回调`（K_CALLBACK）作段名/循环变量 → ANTLR `期望 ID，却遇到了 '回调'`。按 LP-D-013 的「范式 A 上下文软关键字」同法 | B（编译器） | light-merge/antlrparser/ | **是** | 无 | `subtask-T3-done` |
| **T4** | **修 LP-D-019③**：索引切片 `"abcdef"[1:3]` → ANTLR `第4行 第13列 语法错误` | B（编译器） | light-merge/antlrparser/ | **是** | T3 收口后串行 | `subtask-T4-done` |
| **T5** | **ANTLR 覆盖面批量补齐**：①判型族整族注册（`是整数`/`是浮点`/`是字符串`/`是列表`/`是字典`/`是空`/`是布尔`/`是函数`，SRC 全有 ANTLR 全缺）；②`列.获取(下标)` 绑定方法（矩阵行 20）；③行 19 组合（循环内裸`跳过`＋`跳过.追加`同文件 → ANTLR `未定义的变量: '自我'`）；④`是数字符("12")` 口径落地（见 §三 T5-④，先给用户三选一） | B（编译器） | light-merge/antlrparser/ | **是** | T4 收口后串行 | `subtask-T5-done` |
| **T6** | **文档线收口**：语言缺陷账 LP-D-019①③ 状态刷新 ＋ 对拍矩阵活账填表（行 19/20 销账）＋ `Day3总结.md` | C（文档） | lightharness/docs/ | 否 | T3–T5 出口后 | `subtask-T6-done` |
| **T7** | **1.5 盒子午后观察**（例行，距上次约 4h）：PID 链 55645/57424/57487、swap、栅栏、温缓存 3 样本 | D（运维） | 192.168.1.5 | 否 | 无 | `subtask-T7-done` |

> **并行拓扑**：
> - **T1 ∥ T3 ∥ T6（骨架部分）∥ T7** 四路同时起跑
>   - T6 可先做骨架（Day3 总结框架、账目扫描），销账部分等 B 线出口
> - **T3 → T4 → T5 串行**（同编译器树），全改完后跑**一次** full 门（约 50 分钟独占），门过即 B 线收口
> - **T2 串行于 T1 + B 线**：tag 必须打在「PyPI 真通 ＋ 含 T3/T4/T5 修复」的 commit 上
> - T6 销账在 B 线门过之后；T7 全程独立
> - T5 写 antlrparser，与 T6（lightharness/docs）、T7（1.5）、T1（Actions）零互踩

---

## 三、各任务要点

### T1 · rc2 Re-run failed jobs 盯梢（A 线）

**背景**：rc2 run `#37020855509` 唯二红，处置已就位（见前置状态）。GitHub **无单 job 重跑端点**，
`Re-run failed jobs` 会同时重跑 publish-pypi（**真发 `0.4.0rc2`**）+ deploy-docs + VSCE（红是预期）。

**要做**：
1. `POST /repos/skywalk163/light/actions/runs/37020855509/rerun-failed-jobs`（需 admin 凭据；
   本机 git 凭据管理器的 PAT 已验证有 admin 权限——`Day3清晨_T2` 报告同款通道）
2. 盯两条：`发布到 PyPI` → success（PyPI 上 `lightgm 0.4.0rc2` 出现）、`部署文档站点` → success
3. 若仍红：用 **check-run annotations**（匿名可拉）拿日志级红因，按 v2 报告根因清单处置：
   - PyPI：`invalid-publisher` → 用户核对 5 项（lightgm/skywalk163/light/release.yml/pypi）
   - Pages：`environment protection rules` → 确认 `v*` 策略生效（id 61812294）
4. VSCE 红了**不处理**（预期）
5. **出口**：两条转绿与否 + PyPI 项目 URL + 处置清单

**铁律**：这一条**就是真发**，不要再加"只诊断"步骤；红了的处置也不含"真发第二次"。

### T2 · v0.4.0 正式 tag 出口（A 线，串行 T1 + B 线）

**要做**：
1. **前置核对**：T1 两绿 ＋ B 线门过（`082` 对锚点 `093246` 三元判据）；tag 打在**含 T3/T4/T5 修复**的 LM HEAD
2. pyproject.toml `version = "0.4.0rc2"` → `"0.4.0"`（`src/version.py` 已是 0.4.0，核对一致）
3. `release.yml` L223 删 `password: ${{ secrets.PYPI_API_TOKEN }}` 行（OIDC 单路径化；
   防 secret 一旦配上静默抢走 trusted publisher 路径）
4. 两个改动**提交 + push**（需用户示意）后，打 `v0.4.0` tag（**真发 0.4.0 正式版**，同样需用户示意）
5. 盯 release 全绿（test/build/exe/publish-pypi/deploy-docs）；VSCE 红不处理
6. **出口**：`v0.4.0` tag + PyPI `lightgm 0.4.0` URL + Pages 站点版本 + 五远端一致性核对

### T3 · 修 LP-D-019①（B 线）

**背景**：`probes/lp010_重名_严格.light`（段名与循环变量都叫 `回调`）→ ANTLR `解析失败：期望 ID，却遇到了 '回调'`。SRC 正常。

**要做**：
1. **复用**探针 `probes/lp010_重名_严格.light`，两后端各跑一次确认现状（SRC rc=0 / ANTLR rc=1）
2. 按 LP-D-013 的「范式 A 上下文软关键字」同法：`回调` 在 ANTLR 侧允许作段名/循环变量
   （参照 `221db4fc6` 那次对 出/跳过 的改法：`identifier_like` / `primary` 分支 + visitor 中文名还原）
3. **不碰 SRC 侧**（它是对的）
4. **⚠️ 硬规程**：改 g4 必须**重生成 parser**，姿势照 `Day2夜_T2_LPD013_ANTLR补缺口.md` §三
   （两步 + `-encoding UTF-8` + `-lib light_parser`，产物对拍逐字节一致才许继续；
   本机 java 不可用时先用该报告的自动下载脚本确认工具链，**别在没有 JRE 的机器上硬生成**）
5. 探针两后端 rc=0 且输出一致

**出口**：探针 + g4 diff + 重生成命令全文 + 产物对拍结论

### T4 · 修 LP-D-019③（B 线，串行 T3 后）

**背景**：`probes/lp019_索引切片.light`：`打印("abcdef"[1:3])` → ANTLR `第4行 第13列 语法错误`。SRC 输出 `bc`。

**要做**：
1. 复用探针复现，两后端各跑一次
2. ANTLR 语法/visitor 补索引切片产生式（SRC 口径：止为开区间）
3. 重生成同 §三 T3-4 硬规程
4. 探针两后端输出一致（`bc`）

**出口**：探针 + g4/visitor diff + 重生成 + 对拍结论

### T5 · ANTLR 覆盖面批量补齐（B 线，串行 T4 后）

**要做**（全在 antlrparser/，注册面/方法面为主）：
1. **判型族整族注册**：`是整数`/`是浮点`/`是字符串`/`是列表`/`是字典`/`是空`/`是布尔`/`是函数`
   （SRC 侧全可用，ANTLR 侧全 `未定义的变量`——证据 `probes/lp019_判型族_语义矩阵.light`
   ＋ `Day3清晨_T4_LPD019注册收口.md` §七-2）。语义对齐 SRC：int/float 排 bool、str 判型、
   容器判型、callable 判定。加回归探针 `lp019_判型族_整族回归.light`
2. **`列.获取(下标)` 绑定方法**（矩阵行 20）：Day2N T2 只补了 追加/移除/弹出/反转/清空，
   `获取` 漏了——SRC 走 `_light_get`（字典 get / 列表下标，缺键缺下标回默认，不抛）。
   加回 1–2 条用例
3. **行 19 组合修复**（LP-D-013 家族延伸）：循环内裸`跳过` ＋ `跳过.追加(0)` 同文件 →
   ANTLR `未定义的变量: '自我'`（探针 `probes/lp013_组合_循环内裸跳过与成员访问.light`，
   两段各自单独跑均过、组合才触发）。先最小化复现再定位
4. **`是数字符("12")` 口径落地**——⚠️ **先给用户三选一**：
   - 方案①（建议默认）：ANTLR 去掉 `len==1` 守卫，对齐 SRC 的 `str.isdigit` 全串语义；
     同时把 `stdlib/内置核心判型.light` 文档注释改准确（「是数字符 判字符串是否全为数字字符」，
     与 `字符串全数字` 的分工说明同步改）→ 一处改动，两后端一致，文档同步
   - 方案②：SRC `是数字` 段落加单字符守卫对齐文档口径（"判单个字符"）→ 改 stdlib 语义，
     有既有守卫，影响面更大
   - 方案③：维持现状，矩阵行 3 残差标"口径分歧已知"→ 两后端一致破着
5. 重生成同 §三 T3-4 硬规程（若动 g4）
6. **出口**：探针 + 注册/绑定 diff + 口径裁定记录

### T6 · 文档线收口（C 线）

**要做**：B 线门过后
1. 语言缺陷账：LP-D-019①③ 状态刷新（已修复 + commit + 证据）；判型族整族/列.获取/行19
   若立过新账一并销账
2. 对拍矩阵：行 2/3/4/19/20 销账；新差异行照实填（有探针才收信）
3. `docs/国庆7天/Day3总结.md`：清晨＋下午两场合流（修复清单 / 门锚点演进 / 新账）
4. **出口**：三件套落盘

### T7 · 1.5 盒子午后观察（D 线）

照 `Day3清晨_T6_1.5盒子晨间观察.md` 同款口径：PID 链 55645/57424/57487、swap 对比基线、
loopback 栅栏、温缓存 3 样本（只确认未退化）。**出口**：4 项数据落报告。

---

## 四、出口判据

| # | 通过判据 |
|---|---|
| T1 | publish-pypi 与 deploy-docs 双双 success；PyPI 出现 `lightgm 0.4.0rc2`；VSCE 红属预期不处理 |
| T2 | `v0.4.0` tag 打在含 B 线修复的 commit；release 全绿（除 VSCE）；PyPI `0.4.0` + Pages 版本一致 |
| T3 | 探针两后端一致（rc=0）；g4 diff 最小；重生成产物对拍逐字节一致（除刻意修改的规则） |
| T4 | 探针两后端输出 `bc` 一致；重生成同上 |
| T5 | 判型族 8 个两后端一致；列.获取/行19 各 1–2 条用例两后端一致；口径裁定已落地或留档 |
| T3+T4+T5 合并门 | full 门对锚点 `093246`（8357/0/121）三元绿：failed 新增 0、skipped 不增、passed 不降 |
| T6 | 三件套落盘；矩阵销账与代码实际一致 |
| T7 | 4 项数据落报告；零重启/零漂移延续 |

**收口后决策点**：
1. rc2 两红转绿了吗？绿了 → `v0.4.0` 何时打（T2 已含）？
2. `是数字符("12")` 口径三选一（T5-④，默认方案①）
3. VSCE PAT 何时配（继续悬）

---

## 五、附录 · 禁令

1. 🚫 `v0.4.0` 正式 tag 在 T1 转绿前打
2. 🚫 处理 VSCE（token 未配，红是预期）
3. 🚫 门跑 `refresh-local` 自比；`CODEBUDDY_SAFE_DELETE_ENABLED=0` 必加
4. 🚫 `git checkout -- .` / `git clean -fd` / force push
5. 🚫 `.env` / GitHub secret / PAT 值落盘
6. 🚫 改测试断言来"变绿"
7. 🚫 在没有 JRE 的机器上硬生成 ANTLR parser（先按 Day2夜 T2 §三确认工具链）
8. ✅ 允许：编译器修复 + 门跑 + push（本批末尾，用户示意后）
