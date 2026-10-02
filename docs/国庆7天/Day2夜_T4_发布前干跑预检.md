# T4 发布前干跑预检 + 真 LLM smoke（Day2 夜场）

> 派单表：`Day2夜场_派单表.md` v1.2｜契约：`Day2N_契约_T4_rc1干跑预检.md`
> 执行时间：2026-10-02 19:xx｜出口 tag：`subtask-T4-done`
> ⚠️ **全任务零 push**（任何远端、任何形式）；`v0.4.0-rc1` 仅留档，发布物 = `v0.4.0-rc2`；
> 本次用**当前 HEAD 验机制**，**远端此刻不存在 rc2 ref**，故「远端 rc2 已核过」属误读，本报告不持此结论。

## 〇、一句话结论

| 项 | 结论 |
|---|---|
| 本地三仓 tag | `v0.4.0-rc1` **== HEAD**（tracked content 一致） |
| 10 远端落点 | **10/10 逐项复核通过**，token 全部有效（4 走 ls-remote + 6 走 API） |
| 真 LLM smoke | **通过**：`lightharness/.env` 的 `OPENAI_*` 对 `https://api.deepseek.com` 真实流式往返，HTTP 200 + 真实中文回答，0.74s |
| 白天降级根因 | 确为**拿错文件**（根 `.env` 的 `AIStudio_Access_Token` 去打 DeepSeek 端点）；真 key 一直在 `lightharness/.env` |
| §9 反跑 | 3/3 完成（§8.1 / §8.2 / mock 区分） |

---

## 一、本地三仓 tag 一致性（步骤 A）

被测 SHA = `v0.4.0-rc1` 指向的 commit。判据：`tag == HEAD`。

| 仓库 | rc1 commit | HEAD commit | tree | status | 判据 |
|---|---|---|---|---|---|
| light-merge | `a495bb44c46904886b6ebd110dcd004a9325aab7` | 同左 | `ad2b7e8e…` | clean | ✅ tag==HEAD |
| lightharness | `6c291f445c1788ee3f8b99e58e6e5aca5ff414fb` | 同左 | `f745dd9a…` | 仅未跟踪的夜场契约文档 | ✅ tag==HEAD（untracked 不动 tag） |
| lightplugin | `62a596125c96dfd0e8e17963692f687d506441ac` | 同左 | `9f9091b4…` | clean | ✅ tag==HEAD |

> 详细输出见 `logs/day2-night/T4_local_tag.txt`。lightharness 的未跟踪文件是夜场契约文档与 1 个探针，**不改变 rc1 指向**，发布物按 §六-3 应为 rc2。

---

## 二、远端可达性与 token（步骤 B）— 10 落点逐项

方法：gitea / myrepo / LM 本地镜像走 `git ls-remote`（或本地路径）；github / gitcode 走 REST API
（本机对这两端 **git 协议不可达、API 可达**，Day12 已证）。token 来自根 `.env` 的 `GITHUB_TOKEN` / `GITCODE_TOKEN`。

| # | 仓库 | 远端名（实测，按名不准猜） | 方式 | 结果 | SHA / 状态 |
|---|---|---|---|---|---|
| 1 | light-merge | `gitea` (192.168.1.5:3000/skywalk/light.git) | ls-remote | ✅ 可达 | `d6b84a7169b6…` |
| 2 | light-merge | `origin`（=本地 `g:\github\light`） | ls-remote(本地) | ✅ 可达 | `d6b84a7169b6…`（与 #1 一致） |
| 3 | light-merge | `github` (skywalk163/light) | API | ✅ 200 token 有效 | 顶 3 tag：v7.0.0/v5.0.0/v4.2.0 |
| 4 | light-merge | `gitcode` (skywalk163/light) | API `v5/repos` | ✅ 201 + 正确 SHA | `v0.4.0-rc1` → `a495bb44c`（==本地 rc1 ✅） |
| 5 | lightharness | `myrepo`（=192.168.1.5:3000/skywalk/lightharness） | ls-remote | ✅ 可达 | `082255c0b450…` |
| 6 | lightharness | `github` (skywalk163/lightharness) | API | ✅ 200 + 正确 SHA | `v0.4.0-rc1` → `6c291f445c`（==本地 rc1 ✅） |
| 7 | lightharness | `origin`（=gitcode，skywalk163/lightharness） | API `v5/repos` | ✅ 201 + 正确 SHA | `v0.4.0-rc1` → `6c291f445c`（==本地 rc1 ✅） |
| 8 | lightplugin | `gitea` (192.168.1.5:3000/skywalk/lightplugin.git) | ls-remote | ✅ 可达 | `11c78735a81d…` |
| 9 | lightplugin | `github` (skywalk163/lightplugin) | API | ✅ 200 + 正确 SHA | `v0.4.0-rc1` → `62a596125c`（==本地 rc1 ✅） |
| 10 | lightplugin | `gitcode` (skywalk163/lightplugin) | API `v5/repos` | ✅ 201 + 正确 SHA | `v0.4.0-rc1` → `62a596125c`（==本地 rc1 ✅） |

**结论：10/10 落点可达 + token 有效。** 注意：github / gitcode 上的 `v0.4.0-rc1` tag 已存在且 SHA 与本地一致 → 说明 rc1 此前已推到这两端（与 Day12 十落点复核一致）。**本次不 push**，仅核验机制。

> GitCode API 端点：`https://gitcode.com/api/v5/repos/{owner}/{repo}/tags`（实测返回 201 + 正确 tag/commit；
> 另试的 `v5/projects/{enc}/repository/tags` 返回 404，弃用）。原始响应见 `logs/day2-night/T4_api_verify.json`（脱敏）。

---

## 三、干跑 runbook（步骤 C，`<TAG>` 变量版）

默认 `<TAG>` = `v0.4.0-rc2`。rc2 切出后把 `<TAG>` 替换为真实 tag 重跑（预计 15 分钟）。
**本 runbook 不真推**，仅供用户示意后逐条执行。

### 第一步（固定）：校验发布物是否包含 T1/T2
> 派单表 §六-3 硬性要求：runbook 首步必须校验「发布物 ref 指向的 commit 是否包含 T1/T2」。

```bash
cd lightharness
# T1/LP-D-010（缩进不正确修复）、T2/LP-D-013（ANTLR 中文关键字作成员基名）的提交须已并入 <TAG>
git log --oneline <TAG> | grep -E "LP-D-010|LP-D-013|缩进不正确|ANTLR|成员访问"
# 若看不到 T1/T2 的提交 → 停止，回报 team lead：rc2 不含 T1/T2，不能发
```

### A 组：原生 git push（gitea / myrepo / LM 本地镜像）
```bash
export PATH="/c/Users/skywalk/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Windows/System32:/c/Windows:$PATH"
GCM='!"C:/Users/skywalk/.workbuddy/binaries/PortableGit/versions/1.2.0/mingw64/bin/git-credential-manager.exe"'
# 落点 #1 LM gitea / #2 LM origin(本地镜像) / #5 LH myrepo / #8 LP gitea
git -c credential.helper= -c "credential.helper=$GCM" push <REMOTE> <TAG>^{commit}:refs/heads/main
# 失败模式：rc 非零 / 网络超时 / 远端无写权限 → 先 git ls-remote <REMOTE> refs/heads/main 比对 SHA 是否前进
# 复核：git ls-remote <REMOTE> refs/heads/main
# 回滚点：原生 push 走 FF；若误推 → git push <REMOTE> <OLD_SHA>:refs/heads/main（先确认无他人并发写）
# ⚠️ 禁止 git push <REMOTE> | tail（§8.2 假成功陷阱，见第五节）
```

### B 组：Git Data API 推送（github / gitcode，含 tag）—— 本机 git 协议对这两端不可达
```bash
# 脚本：lightharness/_push_github_tree_sync.py（以远端 HEAD tree 为基座，按 blob SHA 比对本地 release 树，
#       仅传变化 blob（原样字节），建 tree→commit(parent=远端 HEAD)→FF PATCH main + 建 tag）
python lightharness/_push_github_tree_sync.py skywalk163/lightharness  G:/dswork/duan-light-merge/lightharness  <LH_RELEASE_SHA> tag=<TAG>   # 落点 #6 #7
python lightharness/_push_github_tree_sync.py skywalk163/light         G:/dswork/duan-light-merge/light-merge   <LM_RELEASE_SHA> tag=<TAG>   # 落点 #3 #4
python lightharness/_push_github_tree_sync.py skywalk163/lightplugin   G:/dswork/duan-light-merge/lightplugin   <LP_RELEASE_SHA> tag=<TAG>   # 落点 #9 #10
# gitcode 同形（脚本内 API 基址切到 gitcode，或另存一份 gitcode 版）
# 失败模式：blob 上传 401(token 失效) / tree 创建 422(base_tree 过期→重取 HEAD 重试) / PATCH 422(非 FF)
# 复核：curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/repos/<REPO>/git/refs/heads/main
#       → 比对脚本输出的 NEW_GH_HEAD 是否 == 本地 <RELEASE_SHA> 的 tree（内容等价，commit SHA 因 CRLF/重建而不同）
# 回滚点：PATCH 前记下 old main SHA；如需回退 PATCH 同 ref 回 old SHA（force=false 须先确认无并发）
```

### 远端名铁律（按名猜会推错）
- **LH 的 gitcode 在本地叫 `origin`**（不是 `gitcode`）；
- **LM 比另两仓多一个 `origin` = 本地 `g:\github\light`**；
- github / gitcode 走 API，远端名不影响，但仓库 full name 必须写对（`skywalk163/xxx`）。

> 逐落点 10 项清单见第二节表格的「远端名」列；每条命令的「预期输出 / 失败模式 / 复核 / 回滚点」已附。

---

## 四、真 LLM smoke（步骤 D）结论

### 4.1 开关取值（§2.2）
| 键 | 位置 | 取值 | 含义 |
|---|---|---|---|
| `LIGHT_NO_LLM` | `light-merge/.env` L65 | **空（falsy）** | 未把 LLM 路径短路为 mock |
| `LIGHT_EVAL_REAL` | `light-merge/.env` L68 | **空（falsy）** | — |

> ⚠️ **重要澄清（纠正契约 §2.2 的假设）**：`LIGHT_NO_LLM` / `LIGHT_EVAL_REAL` **只出现在 `light-merge/.env`（段言/DUAN 运行时）**，
> harness 源码（`lightharness/src`、`stdlib`）**完全不引用**这两个键。harness 的「mock 模式」触发条件是
> 「`.env` 里没有 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY`」（见 `运行Web服务器.light:126`），而非 `LIGHT_NO_LLM`。
> 故契约 §2.2「把 LIGHT_NO_LLM 置真 → 走 mock」的设想在 harness 路径上不成立；本子任务改用「**假 key → 401**」做 real/mock 区分反跑（见 4.3）。

### 4.2 真值 run
- 文件：**`lightharness/.env`**；键名：`OPENAI_API_KEY` / `OPENAI_BASE_URL`=`https://api.deepseek.com` / `OPENAI_MODEL`=`deepseek-flash`（值不出现）。
- 结果：**HTTP 200**，流式 **23 个 content chunk** + 246 字推理流，**0.74s**，真实回答：
  > 「递归是指一个函数或过程通过直接或间接调用自身来分解问题，并在满足终止条件时停止。」
- rc=0，**REAL_OK**。日志：`logs/day2-night/T4_llm_smoke.log`。

### 4.3 反跑（mock 区分，§9 第 3 条）
- 用假 key 跑同一条 → **HTTP 401** `Authentication Fails`，rc=1，**HTTP_FAIL**。
  日志：`logs/day2-night/T4_llm_smoke_badkey.log`。
- 证明 smoke 判据能区分 real（200+真实内容）vs not-real（401），**没有把失败当成功**。

### 4.4 踩坑记录（供后续避坑）
首跑误加 `Accept: text/event-stream` 头，DeepSeek 返回**无 content** 的响应（推理流有内容、最终 content delta 缺失）→ 误判 `EMPTY_CONTENT`。
去掉该头后 content 正常到达。根因：该头改变了 DeepSeek 的流式封装。**smoke 脚本已去掉此头并注释说明。**

### 4.5 白天 401/404 降级根因纠正
白天 S6/Day14 拿**根 `.env` 的 `AIStudio_Access_Token`**（非 DeepSeek 凭据）去打 DeepSeek 端点 → 401/404 → 误判「无凭据→降级」。
真 key 一直在 **`lightharness/.env` 的 `OPENAI_*`**。本次用对了文件，真 LLM 通行，降级结论作废。

---

## 五、§9 反跑（验证 runbook 铁律）

| 项 | 做法 | 结果 | 日志 |
|---|---|---|---|
| §8.1 原样字节 | 已知 CRLF blob `lightharness/docs/功能对标/语言缺陷账.md`（1756 个 CRLF 行）：原样 hash-object = `241fe491…` == 本地树 blob SHA（等价）；LF 归一 = `72db6512…`（不同） | 证明「归一上传会破坏 tree 等价」，已复现 | `T4_anti_run_81.log` |
| §8.2 git push\|tail 假成功 | 对假远端 `this_remote_does_not_exist_T4` push：git 真实 rc=128，但 `git push \| tail` 的 `$?` 取 tail 恒 0 → 假成功 | 陷阱已复现，**禁止用 `git push \| tail` 当复核** | `T4_anti_run_82.log` |
| mock 区分 | 4.3 假 key → 401 vs 真 key → 200 | smoke 判据可区分 real/mock | `T4_llm_smoke_badkey.log` |

> §8.1 仅做本地哈希对照，**不发起任何推送**；§8.2 仅对**假远端**演示，不触碰任何真实远端。

---

## 六、rc1 / rc2 归属（派单表 §六-3）

- `v0.4.0-rc1`：已打、== 三仓当前 HEAD、**仅留档，不作发布物**。
- 发布物 = **`v0.4.0-rc2`**：在 T1/T2 收口、屏障式复核通过之后切出（**当前不存在**）。本子任务用当前 HEAD 验机制；rc2 切出后把 runbook 的 `<TAG>` 替换重跑（≈15 分钟）。
- 推送（T8）**等用户明确示意**；本子任务**零 push**。

---

## 七、四件套（证据）

- **命令 + 退出码**：见各节；smoke 见 `T4_llm_smoke.log`（rc=0）/ `T4_llm_smoke_badkey.log`（rc=1）。
- **日志**：`logs/day2-night/T4_local_tag.txt`、`T4_api_verify.json`、`T4_llm_smoke.log`、`T4_llm_smoke_badkey.log`、`T4_anti_run_81.log`、`T4_anti_run_82.log`。
- **被测 SHA**：三仓 tag SHA（第一节）；远端 SHAs（第二节）。
- **脱敏**：所有日志与本报告仅出现**键名 + 文件路径 + 端点 + 模型**，token / 密码值**零出现**（含 `OPENAI_API_KEY`）。
