# 国庆 Day3 清晨场・派单表（v1.1，2026-10-03 08:18）

> 上一批：`Day3凌晨_派单表.md`（T1–T5 全收，light-merge `e53073d3c` / lightharness `30bc4ee`）
>
> **本批目标**：① 把 rc2 Release 还红的两步（PyPI / 文档站）真正打通；② 修 LP-D-018/019；③ 排一份 ANTLR↔SRC 系统性对拍清单。目标 2–3 小时。
>
> **前置状态（2026-10-03 08:18）**：
> - 三仓 main：LH `30bc4ee` / LM `e53073d3c` / LP `62a5961`，全部 0 ahead
> - 门锚点：`reports/082_lightmerge基线_2026-10-02-234800.json` = 8357/0/121
> - rc2 Release workflow 实测（run #37020855509）：**测试×12 / build / exe×3 / 源码包 / GitHub Release 全绿**；
>   唯二红 = ①「发布到 PyPI」job（产物已下载好，twine upload 步红）；②「部署文档站点」job
> - **VSCE_PAT 暂不配**（本批不碰 VSCE job，它继续 failure 是预期）
>
> **🚫 本批铁律**：
> - 不打 `v0.4.0` 正式 tag（等 PyPI 链路真正通了再议）
> - VSCE job 不处理（token 未配，红是预期）
> - 门跑禁 `refresh-local` 自比；`CODEBUDDY_SAFE_DELETE_ENABLED=0` 必加
> - `.env` / GitHub secret 的值不出现日志报告
> - 编译器修复后必须跑门（T3/T4 合一条门线，串行，独占跑门约 50 分钟）

---

## 二、子任务清单（6 路，3 线）

| # | 任务 | 线 | 仓库/资源 | 需门 | 前置 | 出口 tag |
|---|---|---|---|---|---|---|
| **T1** | **PyPI 发布失败真因定位 + 修**：拉 run #37020855509 的「发布到 PyPI」job 日志，twine 到底报什么（401/403？两级 secret 未配？包名占用？）。按结论处置（改 workflow / 提示用户在 environment 补 secret / 改包名） | A（CI） | light-merge/.github/workflows + GitHub Settings API | 否 | 无 | `subtask-T1-done` |
| **T2** | **文档站部署失败定位 + 修**：拉 deploy-docs job 日志（⚠️ 先确认是 release.yml 内那条，非独立 deploy-docs.yml）。预期原因 = repo Settings → Pages 未启用 / environment `github-pages` 未配置。给出修复动作清单（哪些要用户点鼠标，哪些 workflow 能改） | A（CI） | light-merge/.github/workflows | 否 | 无 | `subtask-T2-done` |
| **T3** | **修 LP-D-018**：SRC 后端 `返回 <关键字词变量名>` 静默返回 None（`返回 跳过` → None，ANTLR 得 [7]）。根因在 SRC 后端返回语句的取值逻辑，把已声明关键字变量当未定义。配探针 + 两后端对拍 | B（编译器） | light-merge/src/ | **是** | 无（探针凌晨已落，直接复用） | `subtask-T3-done` |
| **T4** | **修 LP-D-019②**：ANTLR 后端判型族内置 `是数字`/`是数字符` 未注册（纯注册面补齐，最便宜） | B（编译器） | light-merge/antlrparser/ | **是** | T3 收口后串行 | `subtask-T4-done` |
| **T5** | **ANTLR↔SRC 系统性对拍清单**：不只修 018/019，而是列一份「两后端行为差异矩阵」骨架（按语句类别：赋值/返回/调用/成员访问/判型/切片/回调/并发…），018/019 填前两行，其余留空待填 | B（文档） | lightharness/docs/功能对标/ | 否 | 无 | `subtask-T5-done` |
| **T6** | **1.5 盒子晨间观察**（距上次约 0.5–1h，晨间快速确认）：PID 链是否仍稳定、swap、栅栏、抽 3 样本温缓存（不补 10，只确认未退化） | C（运维） | 192.168.1.5 | 否 | 无 | `subtask-T6-done` |

> **并行拓扑**：
> - **T1 ∥ T2 ∥ T5 ∥ T6** 四路完全独立，同时起跑
> - **T3 → T4 串行**（同编译器树，且都要门）；T3 可在 T1/T2/T5/T6 跑的同时开干
> - **T3/T4 串行快门**：两者都改完后跑一次 full 门（约 50 分钟独占，不是各跑一次），门过即收口
> - T5 写文档不碰代码，与 T3/T4 零互踩

---

## 三、各任务要点

### T1 · PyPI 失败真因（A 线）

**背景**：rc2 Release 的「发布到 PyPI」job，产物下载 OK，twine upload 步红。workflow `release.yml` publish-pypi job（L201–231，`uses:` 在 L223）用 `pypa/gh-action-pypi-publish@release/v1` + `password: ${{ secrets.PYPI_API_TOKEN }}`，job `environment: pypi`。

**要做**：
1. 用 GITHUB_TOKEN 拉 run #37020855509 → job「发布到 PyPI」→ step「发布到 PyPI」的完整日志（`actions/runs/{id}/jobs/{job_id}/logs` 或 jobs API）
2. 逐行看 twine 报错：
   - 若 `401 Unauthorized / Invalid username or password` → 两级 secret 未配或 token 失效（GitHub 环境 job 的 secret 解析顺序：**environment → org → repo**，repo 级 secret 默认可用于 environment job，仅环境级同名时覆盖；**不存在** "Allow secrets from base" 开关）→ 用 API 查 repo / environment 两级 `PYPI_API_TOKEN` 是否已配、值是否还有效
   - 若 `403 Forbidden / The user 'xxx' isn't allowed to upload to project 'lightgm'` → token 对但权限/包名不对
   - 若 `File already exists` → 包版本已被占
3. 按结论处置：
   - 能 workflow 改的（比如去掉 environment、或换 OIDC trusted publisher）就改
   - 需要用户在 GitHub Settings 点鼠标的（补 environment secret / Pages 开关）→ 列清单给用户，不假装自己能改
4. **不真跑 twine upload 到 PyPI**（避免 rc2 真发上去）；只在本机 `twine check dist/*` 已绿的基础上诊断链路

**出口**：失败根因一句话 + 处置动作清单（改了什么 workflow / 用户要点什么鼠标）

### T2 · 文档站失败（A 线）

**背景**：deploy-docs job `environment: github-pages`，用 `actions/deploy-pages@v4`。Day2深夜报告说"待用户现场确认"。**先确认红的入口**：light-merge 有两套部署文档线——`release.yml` 内的 deploy-docs job（rc2 run 这条）与独立 `deploy-docs.yml`；⚠️ 只处理 rc2 run #37020855509 里红的那条，别改独立 `deploy-docs.yml`（另还有 docs-deploy.yml / docs.yml，疑似 stale，顺手确认即可，不动）。

**要做**：
1. 拉 rc2 run #37020855509 内 deploy-docs job 日志，看红在哪一步（通常是 `Get Pages site failed` / `Get Pages environment failed`）；先用 jobs API 按 run 定位真实 job id，勿凭名字猜
2. 结论大概率是：repo Settings → Pages 没设为 "GitHub Actions" source，或 environment `github-pages` 未建
3. 同样：workflow 能改的改，需要用户点鼠标的列清单

**出口**：失败根因 + 用户侧动作清单（截图级步骤）

### T3 · 修 LP-D-018（B 线编译器）

**背景**：`返回 跳过`（跳过是已声明关键字词）在 SRC 后端返回 None，ANTLR 后端正确返回 [7]。静默错值比报错危险。

**要做**：
1. **复用**已有探针 `probes/lp018_返回关键字词变量.light` ＋ `probes/lp018_对照_普通名.light`（凌晨场已落盘），两后端各跑一次确认现状；如需细化直接改已有探针，不新建英文名双份
2. 定位 SRC 后端 `返回` 语句的取值逻辑——它大概在 `src/` 某个 visitor/interpreter 里，对"已声明关键字词变量"走了未定义分支
3. 修到两后端一致（SRC 应与 ANTLR 对齐）
4. **不碰 ANTLR 侧**（它是对的）
5. 探针两后端 rc=0 且输出一致

**出口**：探针 + SRC 修复 diff + 两后端输出对比表

### T4 · 修 LP-D-019②（B 线编译器，串行 T3 后）

**背景**：ANTLR 判型族内置 `是数字`/`是数字符` 未注册（SRC 有，ANTLR 没有）。纯注册面。

**要做**：
1. 写探针复现
2. 在 ANTLR 后端（visitor_expr 或内置函数注册表）注册这两个判定函数
3. 两后端输出一致

**出口**：探针 + ANTLR 注册 diff

### T3+T4 合并门（B 线独占）

T3/T4 都改完后跑一次 `082全量 all --mode full`：
- 对门锚点 `234800`（8357/0/121）三元判据：failed 新增 0、skipped 不增、passed 不降
- T3/T4 各新增 1–2 条用例 → passed 应略升

### T5 · ANTLR↔SRC 对拍清单骨架（B 线文档）

**要做**：在已存在的 `docs/功能对标/` 下新建 `ANTLR_SRC_对拍矩阵.md`（落笔前先扫一眼同目录 `行为差异清单.md` / `语言缺陷账.md` 的口径，避免重复立账形态）：
- 行 = 语句/表达式类别（赋值、返回、调用、成员访问、判型族、切片、回调/段名、并发原语、异常、导入…）
- 列 = 现状（SRC ✓/✗ / ANTLR ✓/✗ / 探针路径 / 账目编号 LP-D-xxx）
- 已填：LP-D-018（返回类）＋ LP-D-019①回调段名（**待修**）/②判型族（**本批修**）/③索引切片（**待修**）——按语句类别共 4 行
- 其余留空，作为后续每修一条填一行的活账

**出口**：矩阵文件骨架 + 已填两行证据

### T6 · 1.5 盒子晨间观察（C 线）

**要做**：SSH 192.168.1.5
- PID 链（daemon/pnpm/node）是否仍 = 55645/57424/57487
- swapinfo 对比基线
- loopback 栅栏
- 温缓存 3 样本（只确认未退化，不补 10）

**出口**：观察报告（4 项数据）

---

## 四、出口判据

| # | 通过判据 |
|---|---|
| T1 | 失败根因一句话（401/403/包占用/两级 secret 未配）+ 处置清单；若是用户侧动作，列到"点哪个按钮" |
| T2 | 失败根因 + 用户侧动作清单 |
| T3 | 探针两后端输出一致；SRC diff 最小；门三元绿 |
| T4 | 探针两后端输出一致；ANTLR 注册 diff 最小 |
| T3+T4 门 | full 门对 `234800` 三元绿 |
| T5 | 对拍矩阵 md 落盘，填 4 个类别行（LP-D-018 ＋ LP-D-019①②③）；①③ 标 **待修**、② 经 T4 修掉 |
| T6 | 4 项数据落报告；elapsed ≥ 12h 延续零重启 / swap 零漂移延续（未退化） |

**收口后决策点**：
1. PyPI 链路真通了吗？通了 → 是否打 `v0.4.0` 正式 tag？
2. VSCE 何时配 PAT？
3. 文档站 Pages 开关用户点了吗？

---

## 五、附录 · 禁令

1. 🚫 打 `v0.4.0` 正式 tag
2. 🚫 真发 PyPI（T1 只诊断，twine upload 真动作等用户示意）
3. 🚫 处理 VSCE（token 未配，红是预期）
4. 🚫 `git checkout -- .` / `git clean -fd`
5. 🚫 `.env` / GitHub secret 值落盘
6. 🚫 改测试断言来"变绿"
7. ✅ 允许：编译器修复 + 门跑 + push（用户已授权本批末尾 push）