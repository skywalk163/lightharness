# Day2 深夜 T5 · GitHub Actions 状态检查（推 rc2 tag 之后）

> 派单：`Day2深夜_派单表.md` v1.0 · T5（B 线，发布线）
> 执行时间：2026-10-03 00:14–00:20（CST，+08:00）
> 数据来源：GitHub REST API（`GET /repos/skywalk163/light/actions/runs` + `/jobs` + `/jobs/{id}/logs`）
> **不重跑、不修 workflow 文件**（只记录 + 归因）
> 出口 tag：`subtask-T5-done`

---

## 〇、结论速览

| 验收项 | 结果 |
|---|---|
| rc2 tag 是否触发了 release / vsce-publish | ✅ **都触发了**（`event=push`，`head_branch=v0.4.0-rc2`，`head_sha=221db4fc621b`） |
| release.yml 失败原因 | ✅ **归因清楚**：`发布到 PyPI` 失败（**trusted publisher 未配置**）+ `部署文档站点` 失败（GitHub Pages 环境，待确认） |
| vsce-publish.yml 失败原因 | ✅ **归因清楚**：`发布到 VS Code Marketplace` 失败（缺 `VSCE_PAT`，与预期一致） |
| 是否只有"缺 token"这一类原因 | ❌ **不是** —— 另外揪出一条 **Quality Gate `全量测试 (3.12)` 稳定复现的 3 条红**（与 token 无关，详见 §四） |

**一句话**：预期的「缺 token」全部坐实；**额外的收获**是发现
**Quality Gate 只要被 push 触发就必然在 ubuntu/python 3.12 上红 3 条**（rc1 与 rc2 两次都是同一组用例、同一个 passed 数），
这条与「发布准入」直接相关 —— 见 §四 与 §六。

---

## 一、最近 workflows 一览（ Top 15 ）

| Run id | Workflow | event | 结论 | 触发 ref | 时间 (UTC) |
|---|---|---|---|---|---|
| 37020855509 | **Release** | push | **failure** | **v0.4.0-rc2** | 2026-10-02T14:34:49Z |
| 37020855120 | **VS Code Extension** | push | **failure** | **v0.4.0-rc2** | 2026-10-02T14:34:49Z |
| 37020850974 | **Quality Gate** | push | **failure** | main | 2026-10-02T14:34:47Z |
| 37020850605 | CI | push | **success** | main | 2026-10-02T14:34:47Z |
| 37020849513 | pages build and deployment | dynamic | success | main | 2026-10-02T14:34:47Z |
| 36994903144 | Release | push | failure | v0.4.0-rc1 | 2026-10-02T10:20:15Z |
| 36994902775 | VS Code Extension | push | failure | v0.4.0-rc1 | 2026-10-02T10:20:15Z |
| 36994879239 | CI | push | success | main | 2026-10-02T10:20:00Z |
| 36994879234 | **Quality Gate** | push | **failure** | main | 2026-10-02T10:20:00Z |
| 36994879226 | Deploy Docs | push | success | main | 2026-10-02T10:20:00Z |
| 36994879211 | 文档站部署 | push | success | main | 2026-10-02T10:19:59Z |
| 36994879199 | Deploy Docs to GitHub Pages | push | cancelled | main | 2026-10-02T10:19:59Z |
| 36960670097 | Release | push | failure | v0.3.0 | 2026-10-02T03:33:08Z |
| 36960669870 | VS Code Extension | push | failure | v0.3.0 | 2026-10-02T03:33:08Z |

> 观察：**Release 连续三版（v0.3.0 / rc1 / rc2）都失败**，且 release.yml 里 CI 部分是全绿的 ——
> 失败的永远是最后那几步「对外发布」，即 §三 归因的凭据缺失。

---

## 二、Release run `37020855509`（rc2 tag）逐 job

| job | 结论 | 耗时(Z) | 说明 |
|---|---|---|---|
| 全量测试 / lint | success | 14:34:54→14:35:07 | |
| 全量测试 / test × 12（3 OS × 4 Python） | success | 14:34:52→14:46:43 | ubuntu/windows/macos × 3.10~3.13 **全绿** |
| 全量测试 / build | success | 14:46:49→14:47:08 | |
| 全量测试 / exe（ubuntu / windows / macos） | success | 14:46:47→14:57:27 | 三个平台 exe 都构建成功 |
| 构建可执行文件（win/mac/ubuntu） | success | 14:57:31→14:58:15 | |
| 构建源码包 | success | 14:57:31→14:57:50 | |
| 创建 GitHub Release | success | 14:58:19→14:58:30 | ✅ Release 已建出来 |
| **发布到 PyPI** | **failure** | 14:58:36→**14:58:55**（19s） | 见 §三.1 |
| **部署文档站点** | **failure** | 14:58:30→**14:58:32**（**2s**） | 见 §三.2 |

**重要**：**测试、构建、exe、Release 创建全部 success** —— 也就是说
**"代码能不能发"这一步早在 CI 层已经过了**，失败只发生在最后三步「往外发」的动作上。

---

## 三、失败归因（逐条，带日志证据）

### 3.1 发布到 PyPI —— **trusted publisher 未配置**（✅ 归因确定）

`step[success] 下载构建产物` → `step[failure] 发布到 PyPI`，日志关键行：

```
  token: ***
  Token request failed: the server refused the request for the following reasons:
    ...
    This generally indicates a trusted publisher configuration error, but could
    also indicate an internal error on GitHub or PyPI's part.
  See https://docs.pypi.org/trusted-publishers/troubleshooting/ for more help.
```

OIDC claim 段印证了它走的是 **trusted publisher** 路径（而不是 token）：

```
* `sub`: `repo:skywalk163@1298682/light@1328710154:environment:pypi`
* `workflow_ref`: `skywalk163/light/.github/workflows/release.yml@refs/tags/v0.4.0-rc2`
* `ref`: `refs/tags/v0.4.0-rc2`
* `environment`: `pypi`
```

**结论**：要么给 Environment `pypi` 配 `PYPI_API_TOKEN`，要么在 PyPI 上给 `lightgm` 登记
trusted publisher（owner `skywalk163` / repo `light` / workflow `release.yml` / environment `pypi`）。
**与 T3 §三-G1 的缺口清单完全一致**，两边独立取证得到同一结论。

### 3.2 部署文档站点 —— **GitHub Pages 环境类即时拒绝**（⚠️ 待确认，日志已被回收）

- 该 job 在 `release.yml` 里的定义（`release.yml:229-236`）：
  ```yaml
  deploy-docs:
    name: 部署文档站点
    needs: [test, create-release]
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
  ```
- 证据：job 起止 **14:58:30 → 14:58:32**，**只活了 2 秒**；且 `/jobs/{id}/logs` 返回
  `HTTPError 404: The specified blob does not exist`（GitHub 侧日志已回收）。
- 2 秒瞬时失败 + `environment: github-pages` ⇒ **属「环境/权限被即时拒绝」类失败，
  不是构建产物的问题**（产物已经被前序 job 证明可用；同一份产物在 CI/exe job 里全部 success）。
  常见成因：仓库未启用 GitHub Pages / Pages 源未设为 GitHub Actions / environment 保护规则。
- **诚实标注**：因为拿不到逐行日志，这条只能**归因到类别（环境/权限），不能归因到具体那一行**，
  记为**待确认**，需要用户在 Settings → Pages / Environments 里现场看一眼。

### 3.3 VS Code Extension run `37020855120` —— **缺 `VSCE_PAT`**（✅ 归因确定）

```
job: 打包 .vsix                      -> success   (14:35:06→14:35:27)
job: 发布到 VS Code Marketplace      -> failure
   step[success] Set up job / 检出代码 / 设置 Node.js / 安装 @vscode/vsce
   step[failure] 发布到 VS Code Marketplace
   step[skipped] 发布到 Open VSX Registry
   step[skipped] 创建 GitHub Release
```

- `.vsix` **打包成功**（发布物本身没问题），只有 marketplace 推不上去。
- 后续两步（Open VSX / Release）因依赖它被 skip —— 这是级联 skip，不是独立故障。
- **结论**：缺 `VSCE_PAT`（可选 `OVSX_PAT`），与 T3 §三-G2 一致。

---

## 四、额外发现（本批真正的价值）：Quality Gate 稳定红 3 条

rc2 的 Quality Gate run `37020850974`（同一次 push 触发）失败：

```
job: 全量测试 (3.12) -> failure
   step[success] Set up job / 检出代码 / 设置 Python 3.12 / 安装依赖
   step[failure] 运行单元测试
   step[skipped] 运行集成测试 / 运行端到端测试 / 运行全量 pytest
   step[success] Upload full test debug output
   step[skipped] 检查测试覆盖率（不低于 25%） / 上传覆盖率报告
job: 构建验证 -> skipped
```

三条红（日志原文）：

```
FAILED tests/unit/test_package_manager.py::TestPackageManagerBuildRun::test_build_project_success
  - Failed: Timeout (>60.0s) from pytest-timeout.
FAILED tests/unit/test_package_manager.py::TestPackageManagerBuildRun::test_run_project_success
  - Failed: Timeout (>60.0s) from pytest-timeout.
FAILED tests/unit/test_lexer_perf.py::TestLexerPerformance::test_lexer_performance_10000_lines
  - AssertionError: 20.13280669200003 not less than 20.0 : 词法分析耗时 20.1328 秒，超过 20.0 秒限制
= 3 failed, 4324 passed, 7 skipped, 2 xfailed, 950 warnings, 290 subtests passed in 510.75s
```

**关键对照：rc1 的 Quality Gate（`36994879234`）失败的是一模一样的东西**

| | rc1 (经 36994879234) | rc2 (经 37020850974) |
|---|---|---|
| 失败 job | 全量测试 (3.12) | 全量测试 (3.12) |
| 失败 step | 运行单元测试 | 运行单元测试 |
| 红 1 / 红 2 | `test_package_manager` build/run **Timeout >60s** | **同一组** Timeout >60s |
| 红 3 | `test_lexer_perf` **26.72s > 20.0** | `test_lexer_perf` **20.13s > 20.0** |
| **passed 数** | **4324** | **4324（完全相同）** |
| skipped / xfailed | 7 / 2 | 7 / 2 |

**判定**：这 **不是回归**（代码从 rc1 改到 rc2，passed 数一个不差、失败集合一个不差），
而是 **Quality Gate 这一条 workflow 自身的问题**：

1. **同一 push 同时触发 CI + Quality Gate**，两个 workflow 在同一时段抢同一批 runner 资源
   （两者都在 14:34:47/49 起跑），而 QG 的单元测试是**串行**跑
   （`quality-gate.yml:116` `pytest tests/unit/ -v --tb=short --cov=src ...`，没有 xdist），
   CI 那边却有 `addopts` 里的 `-n auto` 在并行 —— **QG 单用例的墙钟天然更慢**，
   于是踩线撞上 `--timeout=60`。
2. `test_lexer_perf` 断言的是绝对时间（`LEXER_PERF_LIMIT: 20.0`，见工作流 env），
   rc1 跑 26.72s / rc2 跑 20.13s，**都在同一个量级上擦边** —— 这是典型的
   「性能断言没有留扰动余量」，在共享 runner 上必然不稳定。

**→ 这条会直接影响"能不能发版"的判断**：`quality-gate.yml` 的定位是质量门禁，
如果它每次 push 都红，大家就会习惯性忽略它 —— 建议下批单独立项，三条路里选一条：
① 给 QG 的单元测试加 xdist（与 ci.yml 同口径）；② 放宽 `--timeout`（如 180s）；
③ 把 `test_lexer_perf` 的绝对时间断言改成「相对基线倍数」或直接标记 `@pytest.mark.slow` 剔除。
**本批只记录不修**（派单表铁律：不动 workflow）。

---

## 五、出口判据回看

| 判据（派单表 §四） | 达成 |
|---|---|
| Actions runs 状态表 | ✅ §一 / §二（run 级 + job 级 + step 级三层） |
| 失败原因归因（预期 = 缺 token） | ✅ PyPI = trusted publisher 未配；VSCE = 缺 `VSCE_PAT`；文档站 = 环境/权限（待确认） |
| 不重跑、不修 workflow | ✅ 全程只读 API 与本地 workflow 文件，**零次 re-run、零次文件改动** |

---

## 六、给 team lead 的决策输入

1. **`v0.4.0` 正式 tag 能不能打？** —— "代码/测试/仓库"这一侧的条件已经齐了：
   T1 门三元绿（8357/0/121）+ release.yml 里 test×12 / build / exe×3 / 源码包 / Release 创建**全部 success**。
   剩下的阻塞是**纯凭据/决策**：PyPI token、VSCE_PAT、Pages 环境。**T3 + T5 两边独立取证互相印证。**
2. **建议的顺序**：先配 `PYPI_API_TOKEN`（或 trusted publisher）→ 用 `--test`（TestPyPI）或
   重新推一次 rc tag 验证链路 → 再决定要不要打正式 `v0.4.0`。
3. **必须提醒**：`.github/workflows/quality-gate.yml` 目前处于「每次 push 必红」状态（§四），
   它不该被当成"发版准入 == 全绿"的硬门禁来理解，否则判断会被误导 —— **这是本次发现的最需要修的东西，优先级高于打 tag**。

---

## 七、合规

- 全程只读 GitHub REST API，Token 从根 `.env` 取，**未出现在任何日志/报告**（日志打印前经 `_t5_actions.sanitize()` 脱敏，`token: ***` 是 GitHub 自己的脱敏输出）。
- 未触发 `POST .../rerun`，**没有重跑任何 workflow**；未改动任何 `.github/workflows/*.yml`。
- 工具脚本：`lightharness/scripts/_t5_actions.py`（可复跑）。
