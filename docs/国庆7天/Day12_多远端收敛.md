# Day2 · S5 交付报告 · 多远端收敛 + API 复核 10 落点 + 发布脚本入库

> 派单表：`docs/国庆7天/Day2_派单表.md`｜契约：`docs/国庆7天/Day2_契约_S5_多远端收敛API复核.md`
> 执行时间：2026-10-02｜执行者：team lead（直接执行 S5）
> **出口 tag**：`subtask-S5-done`
> **铁律**：全程只读复核 + 本地文件处置；**零 `git push`**；token 值未出现在本文件与任何日志（日志只记键名）。

---

## 〇、结论速览

1. **10 落点 v0.3.0 悬案已闭合**：10/10 全部确认 v0.3.0 到位。
   - **7/10 字节一致**（commit SHA 完全相等）：lightharness(gitcode/origin)、lightplugin(gitea/gitcode)、light-merge(gitea/origin-本地/gitcode)。
   - **3/10（全部 github）commit SHA 不同、但 tree 内容等价**（CRLF / 历史分叉 → 内容 100% 一致）：lightharness、lightplugin、light-merge 的 github。
   - **0/10 未能复核**。
2. **gitcode fork 追平**：memory 记录的「fork 滞后 gitcode alpha.2 162 提交」**无法复现**——其目标 `dsh-v0.1.7-alpha.2` tag 在 gitcode 上已不存在（162 为过期记录）；light 三仓 gitcode 镜像本身**零滞后**。给出追平方案（见 §二）。
3. **LP github SHA 分叉裁决**：3 个 github 仓的 v0.3.0 与本地**树内容等价**，分叉仅在 commit-history 层（API 推送产生独立 commit 对象，父链不同）。**裁决：接受差异并文档化**，指定 local + gitea + gitcode 为规范源。
4. **发布脚本入库/清理**：`tree_sync` 入库 `lightharness/`；`multi` + 3 个历史残留 move 归档 `_archive/`；根目录临时文件全部清空（全 move、零删除）。

---

## 一、10 落点复核表（逐项）

> 方式：`ls-remote` = git ls-remote（本机对 192.168.1.5 / 本地路径可达）；`API` = GitHub/GitCode REST API（本机对这两家 git 协议不可达，API 恒通）。
> 本地 v0.3.0：`lightharness=082255c0b450da4ae3bcd5ad672b4df327abae15`、`lightplugin=11c78735a81d32673d880e44a264d6ffada179b4`、`light-merge=d6b84a7169b645231d89e1f27ba20321a148d603`。

| # | 仓 | 远端 | 方式 | 远端 SHA / 结果 | annotated | 结论 |
|---|---|---|---|---|---|---|
| 1 | lightharness | `myrepo` (192.168.1.5:3000) | ls-remote | `082255c0b450da4ae3bcd5ad672b4df327abae15` | — | ✅ **SHA 匹配** |
| 2 | lightharness | `github` | API | commit `a5c837e9d7d67fb0f4fdc216b65f984fd9cf0520`；tree 内容等价 | lightweight | ⚠️ commit SHA 不符，但 **tree 内容等价**（CRLF/历史分叉）→ 内容到位 |
| 3 | lightharness | `origin` = gitcode.com/skywalk163/lightharness | API | `082255c0b450da4ae3bcd5ad672b4df327abae15` | — | ✅ **SHA 匹配** |
| 4 | lightplugin | `gitea` (192.168.1.5:3000) | ls-remote | `11c78735a81d32673d880e44a264d6ffada179b4` | — | ✅ **SHA 匹配** |
| 5 | lightplugin | `github` | API | commit `8501ba0522b5f19828dce64494f789f37d984aa4`；tree 内容等价 | lightweight | ⚠️ commit SHA 不符，但 **tree 内容等价** → 内容到位 |
| 6 | lightplugin | `gitcode` | API | `11c78735a81d32673d880e44a264d6ffada179b4` | — | ✅ **SHA 匹配** |
| 7 | light-merge | `gitea` (192.168.1.5:3000) | ls-remote | `d6b84a7169b645231d89e1f27ba20321a148d603` | — | ✅ **SHA 匹配** |
| 8 | light-merge | `origin` = `g:\github\light`（本地路径） | ls-remote | `d6b84a7169b645231d89e1f27ba20321a148d603` | — | ✅ **SHA 匹配** |
| 9 | light-merge | `github` | API | commit `eb1164f4e3acda166a5c8c40527e3268139bca71`；tree 内容等价 | lightweight | ⚠️ commit SHA 不符，但 **tree 内容等价** → 内容到位 |
| 10 | light-merge | `gitcode` | API | `d6b84a7169b645231d89e1f27ba20321a148d603` | — | ✅ **SHA 匹配** |

**汇总**：字节一致 7/10｜commit SHA 不符但 tree 内容等价 3/10（全 github）｜未能复核 0/10。

**GitHub 三项补充说明**（tree 内容等价已实测）：对每个 github 仓取 `v0.3.0` 指向的 commit，再取其 `tree.sha` 与本地 `v0.3.0^{tree}` 比对，三者均 `tree_match=True`。即 github 上 v0.3.0 的**文件树与本地逐字节一致**，仅 commit 对象本身因「API 推送产生独立父链」而 SHA 不同——属历史分叉，非内容缺陷。github 三个 v0.3.0 均为 **lightweight tag**（ref 直接指向 commit，无需再解 tag 对象）。

---

## 二、gitcode fork 追平核实（§3.1）

**关键发现**：memory（`MEMORY.md`「fork 滞后 gitcode alpha.2 162 提交」）指向的是 **deepseek-harness FreeBSD fork**（`G:/github/deepseek-harness`），**不是** light 三仓。本任务 10 落点已证明 light 三仓的 gitcode 镜像全部字节一致，**light 项目内无 fork 滞后**。

### 2.1 「162 提交」是否属实 —— 否，无法复现

- 目标 `gitcode dsh-v0.1.7-alpha.2` tag：在 `skywalk163/deepseek-harness` 上 **不存在**（其最新 fork tag 为 `fork-after-upstream-v0.2.0-rc.1`）；`gh_mirrors/de/deepseek-harness` 镜像 API 返回 **404**。
- ⇒ memory 的「162 提交」是**过期记录**，目标 ref 已消失，不能引用、不能复现。

### 2.2 当前真实状态（只读核实，未改任何远端/本地）

| 对象 | SHA / 时间 | 来源 |
|---|---|---|
| dsh fork master（本地 `G:/github/deepseek-harness`） | `e5b5ccbfcb0f618bcbbb519a53c68ac9f8c875f8` | 本地 git |
| dsh fork master（gitea `origin` 192.168.1.5:3000/skywalk/deepseek-harness） | `e5b5ccbfcb…`（与本地一致） | `git ls-remote`（只读）|
| 实时上游（github `deepseek-ai/deepseek-harness` master） | `639ed015397290b3745d163aafe02ffee4aa3f84`（pushed 2026-09-29） | GitHub API（只读）|

### 2.3 追平方案（**只做计划，不执行；push 等用户示意**）

1. 由于目标 `dsh-v0.1.7-alpha.2` 已不存在，「追平到 alpha.2」无意义。应改为**对齐实时上游** `deepseek-ai/deepseek-harness@639ed015397`（或内网 gitea `origin`）。
2. 精确「落后提交数」需一次只读 `git fetch`（github-upstream + origin）后 `git rev-list --count e5b5ccbfcb..<上游HEAD>` 得出 —— **本子任务不越界改 dsh fork 本地对象库**，该步留给用户/专项在信号后执行。
3. 追平动作（rebase/merge）到位后，再 push 到 gitea `origin` + gitcode —— **全程需用户授权，本子任务零 push**。

> 注：此 fork 属 deepseek-harness 项目，与本次 light 三仓 10 落点收敛无耦合；列为 S5 §3.1 的核实项，结论以「memory 过期、目标 ref 消失、提供对齐实时上游方案」为准。

---

## 三、LP github SHA 分叉裁决（§3.2）

### 3.1 事实

- light-merge / lightharness / lightplugin 的 github `v0.3.0`：commit SHA 与本地不同，但 **tree 内容等价**（§一实测 `tree_match=True`）。
- 成因：github 与本地历史分叉，v0.3.0 经 Git Data API 推送时在 github 侧生成**独立 commit 对象**（父链不同）→ commit SHA 不同；修复版 `tree_sync` 已按**原样字节**上传 blob，故 tree 与本地逐字节一致。
- 这与「CRLF 归一」历史问题已解耦：当前分叉是 **history fork**，不是 content corruption。

### 3.2 裁决（三选一，已选 A）

- **A. 接受差异并文档化（采纳）**：github 是「内容等价镜像」，commit SHA 不同不影响发布完整性（v0.3.0 文件树与本地 100% 一致）。
- B. 恢复字节一致（tree-sync 重推）：因历史分叉，重推仍会生成新 commit 对象，commit SHA 依旧不同；tree 维持等价。**不解决 SHA 差异、且需 push**，故不采用。
- C. 指定规范源（采纳，与 A 并用）：**local 仓 + gitea + gitcode 为规范源**（三者字节一致）；github 标记为「内容等价次级镜像」。

### 3.3 铁律重申（S5 已反跑验证，见 §五）

- **§8.1 原样字节**：blob 必须原样上传（`raw = blob_bytes`，**不** `.replace(b"\r\n", b"\n")`）。反跑证明：对已知 CRLF blob（`lightharness/docs/功能对标/语言缺陷账.md`，对象库 `dc1f98b6…`）归一后得到 `6902562a…` ≠ 真实 → tree 不等价；原样上传得 `dc1f98b6…` = 真实 → 等价。
- **§8.2 禁止 `git push | tail` 当复核**：反跑证明 `git push <不通远端> | tail` 中 git 真实 rc=128，但 `$?`＝tail 的 rc=0 → 假成功。必须逐 `(repo, remote)` 用 `git ls-remote` / API 复核远端 refs。

---

## 四、发布脚本入库 / 根目录清理（§四，全 move、零删除）

| 文件 | 处置 | 落点 / 说明 |
|---|---|---|
| `_push_github_tree_sync.py`（7422B，修复版·原样字节） | **入库（首选保留）** | `lightharness/_push_github_tree_sync.py`（与已提交的 `_push_github_delta.py` 同位置，发布工具集中）|
| `_push_github_multi.py`（6055B） | 落选归档 | `_archive/_push_github_multi.py`（它做 CRLF→LF 归一，与 §8.1 铁律冲突，已被 tree_sync 取代）|
| `_day1_hook_A线版.py`（12489B） | 归档 | `_archive/_day1_hook_A线版.py` |
| `_day1_hook_backup.py`（16390B） | 归档 | `_archive/_day1_hook_backup.py` |
| `_day2_antlr尝试_待重做.patch`（566802B） | 归档 | `_archive/_day2_antlr尝试_待重做.patch`（Day2 砍线回退版唯一留档）|
| `_push_github_delta.py` | 无需处置 | 已在 `lightharness/` 且已提交 |

- **根目录临时文件**：执行前 5 个（`_push_github_tree_sync.py` / `_push_github_multi.py` / `_day1_hook_A线版.py` / `_day1_hook_backup.py` / `_day2_antlr尝试_待重做.patch`）→ 执行后**全部清空**（move 至 `lightharness/` 或 `_archive/`）。ls 前后对比见 `logs/day2/S5_cleanup.log`。
- `tree_sync` 已放入 `lightharness/` 工作树，**未提交**（commit/push 受禁令约束，等用户示意）。
- 删除纪律：本次全部为 `mv`（保留字节），未触发任何 `rm`、未触及每 turn 删除上限。

---

## 五、反跑判据（§八，已落盘）

| 判据 | 做法 | 结果 | 日志 |
|---|---|---|---|
| §8.1 原样字节 | 对已知 CRLF blob 分别按原样 / CRLF→LF 归一算 blob SHA，与对象库真实 SHA 比对 | 原样 `dc1f98b6…`=真实（等价）；归一 `6902562a…`≠真实（不等价）| `logs/day2/S5_replay_81.log` |
| §8.2 push\|tail 掩码 | `git push <不通远端> \| tail`，比对 git 真实 rc 与 `$?` | git rc=128，但 `$?`=tail rc=0 → 假成功 | `logs/day2/S5_replay_82.log` |

---

## 六、四件套（证据）

1. **命令**（可直接复制，不含 token 值）：
   - ls-remote 复核：`git -c core.quotePath=false ls-remote <remote> refs/tags/v0.3.0`
   - GitHub API：`GET https://api.github.com/repos/{owner}/{repo}/git/ref/tags/v0.3.0`（带 `Authorization: Bearer $GITHUB_TOKEN`）
   - GitCode API：`GET https://gitcode.com/api/v5/repos/{owner}/{repo}/tags?private_token=$GITCODE_TOKEN`（注意返回 **HTTP 201** 即成功）
   - 脚本化入口：`python logs/day2/S5_verify.py`（复用 `_push_github_tree_sync.py` 的 token/API 姿势，只读）
2. **退出码**：S5 各命令 rc 均落在日志；`S5_verify.py` 整体 `EXIT_RC=0`；§8.2 反跑 git 真实 rc=128（被 tail 掩码为 0，正是反跑要证明的点）。
3. **日志路径**（工作区根 `logs/day2/`，跨仓共用、不进任何仓提交）：
   - `logs/day2/S5_verify.log` + `logs/day2/S5_api_verify.json`（脱敏，仅记键名/HTTP 状态/SHA）
   - `logs/day2/S5_replay_81.log`、`logs/day2/S5_replay_82.log`
   - `logs/day2/S5_cleanup.log`（根目录 ls 前后对比）
4. **被测 SHA**：
   - lightharness `082255c0b450da4ae3bcd5ad672b4df327abae15`（github tree 内容等价，commit `a5c837e9d7`）
   - lightplugin `11c78735a81d32673d880e44a264d6ffada179b4`（github tree 内容等价，commit `8501ba0522`）
   - light-merge `d6b84a7169b645231d89e1f27ba20321a148d603`（github tree 内容等价，commit `eb1164f4e3`）

---

## 七、验收对照（契约 §七）

1. 10/10 逐个明确结论（SHA 匹配 / SHA 不符但 tree 等价 / 未能复核）—— ✅ 7 匹配 + 3 tree 等价 + 0 未复核。
2. API 落点标「API 复核」、ls-remote 落点标「ls-remote」—— ✅ §一表已分列。
3. 发布工具入库决定已落地（保留 tree_sync → lightharness/；multi → _archive/）—— ✅ §四。
4. 根目录残留按 §四处置完毕（ls 前后对比落盘）—— ✅ `logs/day2/S5_cleanup.log`。
5. token 值未出现在任何报告/日志（只出现键名）—— ✅ 已核查。
6. 四件套齐全—— ✅ §六。

> **未执行项（受禁令约束，等用户示意）**：所有 `git push`、dsh fork 的 `git fetch`+精确落后计数、tree_sync 的 commit。本报告严格「只读复核 + 本地文件处置」。
