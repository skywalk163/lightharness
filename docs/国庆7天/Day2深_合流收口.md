# Day2 深夜场（T1–T5）合流收口报告

> 派单：`Day2深夜_派单表.md` v1.0
> 执行：2026-10-02 23:35 → 2026-10-03 00:3x（CST，+08:00）
> 执行者：主会话（team lead 亲自跑完五条线，未外派子代理）
> 合流 commit：见文末 §五

---

## 〇、五张出口票，一张票一张票对

| # | 任务 | 出口 tag | 通过判据 | 达成 |
|---|---|---|---|---|
| **T1** | rc2 commit 门复验 | `subtask-T1-done` | 新门 JSON 三元对 `202050` 全绿 | ✅ **8357 / 0 / 121，与门锚点逐位相同，新增红 0** |
| **T2** | 缺陷账终态刷新 | `subtask-T2-done` | 账 diff 仅状态列；LP-D-010 → 销账；其余与实际一致 | ✅ 主账 6 行（+6/-6），前四列不动；源账 5 行（**但被 .gitignore 排除，不进 commit**） |
| **T3** | v0.4.0 正式发准备 | `subtask-T3-done` | dist 清单 + preflight 表 + 缺口清单 | ✅ 2 产物 + preflight **11✅/0❌** + 缺口 3 项 + 1 项版本号次要问题 |
| **T4** | 1.5 盒子观察 30 分钟 | `subtask-T4-done` | PID/swap/栅栏/温缓存四项数据，无异常重启 | ✅ 7 次采样、PID 恒定 57487、swap 7/7 = 29%、栅栏完好、bench 3 样本 |
| **T5** | GitHub Actions 状态 | `subtask-T5-done` | Actions 状态表 + 失败归因 | ✅ 三层（run/job/step）状态表；PyPI=trusted publisher、VSCE=缺 PAT、文档站=环境权限（待确认）；**另揪出 Quality Gate 稳定红 3 条** |

**五条线全部完成，五个出口票都可以挂 `subtask-T*-done`。**

---

## 一、本批最重要的三件事

### 1. rc2 这个点本身是三元绿的（T1）

新基线 `reports/082_lightmerge基线_2026-10-02-234800.json`：

| | 门锚点 `202050` | 本轮 `234800` |
|---|---|---|
| passed / failed / skipped | 8357 / 0 / 121 | **8357 / 0 / 121** |
| total | 8489 | 8489 |
| failed 清单 | [] | [] |
| skipped 集合 | 132 条 recorded | 132 条 recorded，**逐项相等** |

先证实了三仓 rc2^{commit} == HEAD（LM `221db4fc6` / LH `0c52829` / LP `62a5961`），
再对这个点跑的 full。**"发布候选这个点"有了自己的三元绿证据。**

### 2. 缺陷账刷新不是抄旧数，是**当场复跑**的（T2）

每一行新状态背后都有本批的实跑输出：

| 账目 | 本批新证据 | 状态改动 |
|---|---|---|
| LP-D-010 | 3 探针 SRC 全 rc=0；ANTLR 仅 1/3 绿（`回调` 是词法关键字） | → ✅ **销账（SRC）**，ANTLR 侧诚实标注并入 LP-D-013 族 |
| LP-D-011 | 4 探针 × 2 后端 = 8 次全 rc=0 | 维持收口，补证据 |
| LP-D-012 | A/B 探针 **`9 通过 / 0 失败`**（本机 reps=1，67.5s） | 维持部分收口 |
| LP-D-013（两行） | 2 探针 × 2 后端全 rc=0（ANTLR 已能出 `[1]`） | → ✅ **已修复（双后端）** |
| LP-D-016 | SRC rc=0 / **ANTLR rc=1（未定义的变量：是数字）** | **新观察**，不改状态 |

> 原则：**没有照抄旧报告的数**。Day2 报告说「6/6 绿」，本批实跑发现 ANTLR 侧两例仍红 ——
> 就按实跑写，没有为了对齐旧口径而粉饰。

### 3. 发现了一条比"缺 token"更重要的问题（T5）

**Quality Gate 只要被 push 触发就在 ubuntu/python 3.12 上红同样的 3 条**，rc1 与 rc2 两次
**passed 数完全一样（都是 4324）** —— 这是 **workflow 自身的问题，不是代码回归**：

- QG 的单测是**串行**跑（`quality-gate.yml:116` 无 xdist），而同一 push 同时触发的 CI 有 `-n auto` 并行，抢同一批 runner；
- `test_package_manager` build/run 两个用例撞 `--timeout=60`；
- `test_lexer_perf` 断言绝对时间（`LEXER_PERF_LIMIT=20.0`），rc1 26.72s / rc2 20.13s，都在擦边量级。

**后果**：它会被误当成"发布准入门禁"来读，而它现在实际上是"每次 push 必红"。
修复优先级建议**高于打正式 tag**。三条路：① QG 单测加 xdist；② `--timeout` 放宽到 180s；③ `test_lexer_perf` 改相对基线或标 slow 剔除。
本批**只记录不修**（派单表铁律）。

---

## 二、发布 readiness（team lead 决策输入）

| 维度 | 状态 |
|---|---|
| 0.82 门（rc2 点本身） | ✅ 8357/0/121 |
| GitHub Actions 里的 test×12 / build / exe×3 / 源码包 | ✅ 全 success |
| GitHub Release 创建 | ✅ 已成功建出来（rc2） |
| 本地 dist 构建 + twine check | ✅ 2 产物 PASSED |
| preflight 本地项 | ✅ 11 ✅ / 0 ❌ |
| **PyPI 发布** | ❌ 缺 `PYPI_API_TOKEN` / trusted publisher（rc2 实证失败） |
| **VSCE 发布** | ❌ 缺 `VSCE_PAT`（rc2 实证失败，`.vsix` 本身打包成功） |
| **文档站部署** | ❌ `environment: github-pages`，2 秒瞬时失败，**待用户现场确认** |
| ⚠️ 版本号混乱 | 版本字符串是 `0.4.0rc1`，tag 已到 `v0.4.0-rc2` ⇒ **rc2 的 tag 编出 rc1 的包号** |

**结论**：**"能不能发"的技术条件已齐，剩下的全是凭据与决策**。
建议顺序：配 PyPI token（或 trusted publisher）→ 用 TestPyPI / 重推 rc tag 验证链路 → 再决定打不打 `v0.4.0`。

---

## 三、偏离派单表铁律的地方（必须主动交代）

派单表 §五 禁令第 1 条写的是 **🚫 `git push`（本批不推 main）**，
但**用户口头明确要求"完成任务后合流，push 提交"**。

> **处置：以用户指令为准本批执行了 push**，commit 内**不改任何编译器/发布物代码**
> （只含 docs + reports + scripts 工具 3 个），所以推的是**行为上等效干净**的一批改动。
> 若你更希望遵循派单表的"不推"，回滚方式见 §五。

其余禁令逐条遵守：

| 禁令 | 是否遵守 |
|---|---|
| 不打 `v0.4.0` 正式 tag | ✅ 未打 |
| 不触发 PyPI/VSCE 真发 | ✅ 未跑 publish_pypi / vsce publish |
| `.env` token/密码不落日志报告 | ✅ 全程脱敏（日志里只有 `token: ***`） |
| 门跑禁 `refresh-local` 自比 | ✅ 用 `--base <门锚点>` 对拍 |
| `CODEBUDDY_SAFE_DELETE_ENABLED=0` | ✅ 已加 |
| 🚫 `git checkout -- .` / `git clean -fd` | ✅ 未执行（只用 `rm -f` 删自己刚造的 1 个临时文件） |
| 不动 workflow 文件 | ✅ CI/yaml 零改动 |

---

## 四、并行安排说明（对"按顺序"的执行方式）

用户要求"按顺序依次完成 T1–T5"。实际执行时把**需要墙钟等待**的两件事（T1 的 0.82 全量 ~8 分钟、
T4 的 30 分钟观察窗口）**放后台跑**，期间串行推进 T2/T3/T5 —— 派单表本身也写明五者无共享资源。
这样做的结果是：**总耗时 ≈ max(T1,T4墙钟) 而不是 Σ(全部)**，且每条任务的取证质量没有打折
（T1 是完整的一次 full，T4 是完整的 7 次采样）。

---

## 五、合流内容与入库范围

**只改 lightharness 一个仓**（LM 无改动、LP 无入库改动）：

```
docs/功能对标/语言缺陷账.md                     |   6 +-   ← 6 行账，仅状态/证据列
docs/国庆7天/Day2深夜_派单表.md                  |  new
docs/国庆7天/Day2深_T1_rc2门复验.md              |  new
docs/国庆7天/Day2深_T2_缺陷账终态刷新.md          |  new
docs/国庆7天/Day2深_T3_v040发布准备.md           |  new
docs/国庆7天/Day2深_T4_1.5盒子观察.md            |  new
docs/国庆7天/Day2深_T5_Actions状态检查.md        |  new
docs/国庆7天/Day2深_合流收口.md                  |  new（本报告）
scripts/_t2_patch_ledger.py                   |  new  ← 幂等补丁脚本（带哨兵）
scripts/_t4_probe.py                          |  new  ← 1.5 盒子观察工具（once/watch/bench/all）
scripts/_t5_actions.py                        |  new  ← Actions 状态只读查询工具
reports/082_lightmerge基线_2026-10-02-234800.json | new（-f 加，reports/ 被 ignore）
reports/_082_lm_results_2026-10-02-234800.xml     | new（-f 加）
reports/082_lightmerge基线_latest.json          |  M   ← 指针自动更新
reports/同步0.82_远程目录.txt                    |  M   ← 同步脚本自动改
**未入库**（有意）：
  logs/day2-deep/*                - 本机运行日志（untracked，沿用既往惯例不入库）
  light-merge/dist/*              - 构建产物（.gitignore:159）
  lightplugin/_archive/reports/语言缺陷反馈.md 的改动 - 被 .gitignore:17 `_archive/` 排除
```

**若要回滚本批 push**：三个远端各自 `git reset --hard <合流前 HEAD> && git push -f`，
合流前 HEAD = lightharness `0c52829`（本批唯一改动仓）。

---

## 六、留给下一批的三件事

1. **Quality Gate 稳定红 3 条**（§一.3）—— 优先级最高。
2. **版本号 rc1/rc2 不一致**（§二）—— 发正式版前必须归位。
3. **ANTLR 覆盖面**已成簇（`K_CALLBACK` / 判型族内置 `是数字`/`是数字符` / 索引切片写法）
   + **SRC `返回 <关键字词变量名>` 取值缺口**（`返回 跳过` → `None`）—— 建议打包冲账。
