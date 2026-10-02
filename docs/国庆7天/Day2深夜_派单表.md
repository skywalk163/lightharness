# 国庆 Day2 深夜场・派单表（v1.0，2026-10-02 22:xx）

> 配套：`Day2夜场_派单表.md`（已收，rc2 已切并推 10 落点）
>
> 本批为 **rc2 落地后补刀 + 正式发 v0.4.0 准备**，目标 1.5–2 小时
>
> **前置状态**：
> - 三仓 main 已合流（LH `0c52829` / LP `62a5961` / LM `221db4fc6`），工作树干净（LM 仅 `?? logs/`）
> - `v0.4.0-rc2` annotated tag 已打并推 **10/10 落点**（7 git 协议 + 3 github API，复核全绿）
> - 门锚点：`reports/082_lightmerge基线_2026-10-02-202050.json` = **8357 passed / 0 failed / 121 skipped**
> - 1.5 盒子 dsh-web 已加 `-r` 崩溃拉起（生产运行中，~22s 完整恢复）
>
> **🚫 本批铁律**：
> - 不打 `v0.4.0` 正式 tag（等本批收口后 team lead 单独示意）
> - 不 `git push` main（rc2 刚推，本批不改编译器/发布物代码；T1 只读门，T2/T5 只文档）
> - 不触发 PyPI/VSCE 真发（T3 只构建 + preflight，真发等用户单独示意）
> - `.env` 的 token/密码值不出现在任何日志/报告
> - 门跑禁 `refresh-local` 自比；`CODEBUDDY_SAFE_DELETE_ENABLED=0` 必加

---

## 二、子任务清单（5 路并行，A/B/C 三线）

| # | 任务 | 线 | 仓库/资源 | 需门 | 前置 | 出口 tag |
|---|---|---|---|---|---|---|
| **T1** | **rc2 commit 门复验**（对 rc2^{commit} 重跑 0.82 full，确认 rc2 这个点本身三元绿） | A（门线） | 0.82 远程门机 | 是 | 无 | `subtask-T1-done` |
| **T2** | **缺陷账终态刷新**：LP-D-010 行从「已定性待修」改为「销账（Day1 已修，Day2N 复核）」；LP-D-012/013 行核对；全账终审一遍 | B（文档线） | lightharness/docs/功能对标/语言缺陷账.md | 否 | 无 | `subtask-T2-done` |
| **T3** | **v0.4.0 正式发准备**：`dist/` 构建 + `release_preflight.py` 全 ✅ + 列出 PyPI/VSCE 缺口清单（不真发） | B（发布线） | light-merge/scripts/build_release.py | 否 | 无 | `subtask-T3-done` |
| **T4** | **1.5 盒子 dsh-web 观察**：rcd `-r` 上线后跑 30 分钟，确认无异常重启/无 OOM/温缓存未退化；产出观察报告 | C（运维线） | 192.168.1.5（workbuddy） | 否 | 无 | `subtask-T4-done` |
| **T5** | **github Actions 状态检查**：推 rc2 tag 后 release.yml / vsce-publish.yml 是否触发、失败原因（预期因缺 PyPI/VSCE token 失败，记录而非修） | B（发布线） | github Actions API | 否 | T3 | `subtask-T5-done` |

> **并行关系**：T1 ∥ T2 ∥ T3 ∥ T4 ∥ T5 —— 五者无共享资源。
> T1 占 0.82 门机（独占，串行线快门）；T4 占 1.5；T3/T5 在本机纯脚本；T2 纯文档。
> T5 依赖 T3 的 preflight 结论（同批异步，T5 先拉 Actions 状态不阻塞 T3）。

---

## 三、各任务要点

### T1 · rc2 commit 门复验（A 线，门线独占）

**为什么**：rc2 tag 指向的 commit 是 `221db4fc6`（LM）/ `0c52829`（LH）。门 `202050.json` 跑的是 T2 修复后、合流前的状态。合流后 LH 多了 docs commit（不影响编译器），LM 就是 `221db4fc6`。**必须对 rc2^{commit} 本身重跑一次 full**，确认「发布候选这个点」三元绿，否则打正式 tag 无依据。

- 命令：标准 082 full（`CODEBUDDY_SAFE_DELETE_ENABLED=0` + `--mode full`）
- 判据：对门锚点 `202050.json`（8357/0/121）—— failed 新增 0、skipped 不增、passed 不降
- 出口：新门 JSON 落 `reports/`，报告写差异（预期零差异，因 LH docs commit 不影响编译器面）

### T2 · 缺陷账终态刷新（B 线，纯文档）

**为什么**：T1 报告说 LP-D-010 已销账（Day1 lexer.py 修掉），但账行 `语言缺陷账.md:1712` 状态列还是「已定性待修」。本批把账刷新到与实际一致。

- 逐项核对 LP-D-001 ~ LP-D-013 每行状态列：
  - LP-D-010 → 「✅ 销账（Day1 lexer._lpd013_010_reclassify_declared_keywords 已修；Day2N T1 复核探针 6/6 绿）」
  - LP-D-011 → 已收口（Day2，核对描述与实际一致）
  - LP-D-012 → 部分收口（Day2N T5，核对探针路径）
  - LP-D-013 → 已修复（Day2N T2，ANTLR 补缺口）
- 不改编译器代码，只改账行状态列与证据指针
- 出口：账 diff 仅状态列/证据列，无逻辑改动

### T3 · v0.4.0 正式发准备（B 线，纯脚本）

**为什么**：rc2 是候选。正式发 `v0.4.0` 前要：① `dist/` 构建出来（K6 之前 ❌）；② `release_preflight.py` 全 ✅；③ 列出还缺什么 token/配置。

- 跑 `python scripts/build_release.py`（light-merge/scripts/）
- 跑 `python scripts/release_preflight.py`（只读）
- 产出：`dist/` 实际产物清单 + preflight 最终表 + **缺口清单**（预期：PYPI_API_TOKEN / VSCE_PAT 用户侧未配）
- **不真发**：不跑 `publish_pypi.py` 正式，不 `vsce publish`
- 出口：报告写明「构建产物 N 个 / preflight ✅X ❌Y / 缺口 Z 项」

### T4 · 1.5 盒子 dsh-web 观察（C 线，SSH）

**为什么**：rcd 加 `-r` 后已跑 ~1 小时。本批观察是否稳定。

- SSH 192.168.1.5（workbuddy，凭据从根 .env 读）
- 查 `ps aux | grep dsh_web` 确认 daemon PID 未变（-r 拉起后 PID 会变，记录当前 PID）
- 查 `/var/log/` 或 daemon 日志有无异常
- `swapinfo` 对比预检基线（10G/可用 7.1G/29%）
- loopback 栅栏复核一次（127.0.0.1:3080 无 token 401，LAN 直连拒绝）
- 温缓存抽 3 样本（不需要 10 个，只确认未退化）
- 出口：观察报告（PID 链 / 异常数 / swap / 栅栏 / 温缓存）

### T5 · github Actions 状态检查（B 线，API）

**为什么**：推 rc2 tag 会触发 `release.yml`（推 `v*` tag 触发 PyPI publish + GitHub Release + exe 构建）。预期因缺 `PYPI_API_TOKEN`/`VSCE_PAT` 失败。记录失败原因，不修（等用户配 token 后重推）。

- 用 GITHUB_TOKEN 查 Actions runs：`GET /repos/skywalk163/light/actions/runs?event=push`
- 找 rc2 tag 触发的 run，看哪些 job 失败、失败日志摘要
- 不重跑、不修 workflow 文件
- 出口：Actions 状态表（job 名 / 结论 / 失败原因摘要）

---

## 四、出口判据

| # | 通过判据 |
|---|---|
| T1 | 新门 JSON 三元对 `202050` 全绿；报告写清差异 |
| T2 | 账 diff 仅状态列；LP-D-010 → 销账；其余行与实际一致 |
| T3 | `dist/` 产物清单 + preflight 表 + 缺口清单三件套 |
| T4 | PID/swap/栅栏/温缓存四项数据落报告，无异常重启 |
| T5 | Actions runs 状态表，失败原因归因（预期 = 缺 token） |

**收口后 team lead 决策点**：
1. T1 门绿 + T3 dist 构建成功 + T5 Actions 失败原因明确 = 是否打 `v0.4.0` 正式 tag？
2. PyPI/VSCE token 谁来配？配好后重推 tag 触发 release？

---

## 五、附录 B · 禁令（沿用）

1. 🚫 `git push`（本批不推 main；T1 只读门）
2. 🚫 `git checkout -- .` / `git clean -fd`
3. 🚫 `refresh-local` 自比当判据
4. 🚫 `.env` token/密码值落盘
5. 🚫 打 `v0.4.0` 正式 tag（等单独示意）
6. 🚫 真发 PyPI/VSCE（T3 只构建）
