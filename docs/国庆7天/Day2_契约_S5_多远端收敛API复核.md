# S5 契约 · 多远端收敛 + API 复核 10 落点 + 发布脚本入库

> 派单表：`Day2_派单表.md`｜计划：`docs/国庆day2计划.md` v1.1 §四 轨道A + §六 清理 + §8.1/8.2/8.3
> **资源型**：网络·等｜**需门**：否｜**预计**：约 2–3 小时（大量等待，适合作 B 路的槽 1）
> **出口 tag**：`subtask-S5-done`｜**⚠️ 本子任务独占工作区根目录的写权**
> **🚫 绝对禁止 `git push`**（任何远端、任何形式）——推送等用户示意。本子任务只做**只读复核**与**本地脚本处置**。

---

## 一、目标（三件）

1. **关掉「10 个远端落点是否真的都有 v0.3.0」这个悬案**——本机可核实的 4 个已验，剩下 6 个走 **API**。
2. **gitcode fork 追平** + **LP github SHA 分叉裁决**（CRLF 内容等价）。
3. **发布脚本入库/归档** + 工作区根目录残留清理。

## 二、10 个落点与已核实的部分（别重复劳动）

| 仓 | 远端 | 状态（本轮实测） |
|---|---|---|
| lightharness | `myrepo`（192.168.1.5:3000） | ✅ **已核实 = `082255c`** |
| lightharness | `github` | ❌ `unable to access` → 走 API |
| lightharness | **`origin`（=gitcode.com/skywalk163/lightharness）** | ❌ 走 API（**注意：LH 的 gitcode 远端名叫 `origin`，不是 `gitcode`**） |
| lightplugin | `gitea` | ✅ **已核实 = `11c7873`** |
| lightplugin | `github` / `gitcode` | ❌ 走 API |
| light-merge | `gitea` | ✅ **已核实 = `d6b84a7`** |
| light-merge | `origin`（**本地路径 `g:\github\light`**） | ✅ **已核实**：`v0.3.0` = `d6b84a7` = 其 HEAD（分支 `main`） |
| light-merge | `github` / `gitcode` | ❌ 走 API |

**凭据**：`.env` 里有 **`GITHUB_TOKEN`** 与 **`GITCODE_TOKEN`**（本轮实测确认）。`git ls-remote` 对 github/gitcode 不通（网络层），**但 API 通**。

### API 复核做法

- **GitHub**：`GET https://api.github.com/repos/skywalk163/{lightharness|lightplugin|light}/git/ref/tags/v0.3.0`（`Authorization: Bearer $GITHUB_TOKEN`）。
  ⚠️ **若是 annotated tag**，ref 指向 **tag 对象**而非 commit → 需再 `GET /git/tags/<sha>` 取 `object.sha` 才是 commit，**再与本地 `git rev-parse v0.3.0^{commit}` 比对**。报告里写明「annotated / lightweight」。
  💡 参考实现：`_push_github_tree_sync.py` 里已有 GitHub API 调用与 token 处理，直接复用其姿势，别从零写。
- **GitCode**：查其 OpenAPI（v5）的 tags/refs 端点。**若找不到可用端点 → 在报告里明写「未能复核」**，不得默认成功。
- 每次 API 调用间隔 3–5s，避免速率限制。

## 三、另外两件

### 3.1 gitcode fork 追平

- 依据：`MEMORY.md:85`「fork 滞后 gitcode alpha.2 **162 提交**」——**这是 memory 记录，不是事实**。
- 要做：用 1.5/gitea 或 API **核实真实落后提交数**，再决定 fetch + rebase/merge 的追平策略。
- 报告里写「核实后的实际数」，**不要直接引用 162**。
- ⚠️ 追平是**改远端状态的操作** → 若需要 push，**停下来问用户**；本子任务先交「核实结果 + 追平方案」。

### 3.2 LP github SHA 分叉裁决

- 背景：v0.3.0 发布时 **LP 的 github 与本地 SHA 因 CRLF 分叉（内容等价）**。
- 要做：定策略并写清——恢复字节一致（用 tree-sync 重推）／接受差异并文档化／指定哪个 ref 为规范源。
- ⚠️ **铁律 §8.1**：脚本上传 git blob 必须**原样字节**（`raw = blob_bytes`，**不** `.replace(b"\r\n", b"\n")`）。v0.3.0 已修（LH 侧 `a5c837e9d7` 的 tree = 本地 `082255c` tree = **`a5c0b0a969795d…`**，本轮已实测逐字对上）。
- ⚠️ **铁律 §8.2**：**禁止只看 `git push | tail`**（`$?` 是 tail 的退出码恒 0 → 「空输出 + rc=0 但远端无 refs」的假成功）。必须逐 `(repo, remote)` 复核。

## 四、清理处置（工作区根目录，本子任务独占）

| 文件 | 大小 | 处置 |
|---|---|---|
| `_push_github_tree_sync.py` | 7 422 B（10-02 11:46，**修复版**） | **入库为发布工具（首选保留）**；入库位置由你判断并写明（建议随发布流程所在仓的 `scripts/`，或统一 `tools/release/`） |
| `_push_github_multi.py` | 6 055 B | 与上条**二选一**（不是三选一）；落选者归档 `_archive/` |
| `_push_github_delta.py` | — | **已在 `lightharness/` 且已提交** → **无需处置**（§6.2 原「三选一」表述有误） |
| `_day2_antlr尝试_待重做.patch` | **566 802 B** | v0.3.0 Day2 被砍线回退的那版 → **优先归档 `_archive/`**（不要直接删：它是那次尝试的唯一留档） |
| `_day1_hook_A线版.py` / `_day1_hook_backup.py` | 12 489 / 16 390 B | Day1 import hook 的备份/分支版 → 归档 `_archive/` |

> ⚠️ **删除纪律**：确需删除时，**先核对解析后的绝对路径确实是目标文件**；**不要在一个 turn 里批量 `rm`**（harness 有每 turn 50 次删除上限，顶爆后成片假红）；长跑带 `CODEBUDDY_SAFE_DELETE_ENABLED=0`。

## 五、文件白名单 / 黑名单

| | 路径 |
|---|---|
| **可写（独占）** | 工作区根 `_push_github_*.py`、`_day2_*.patch`、`_day1_hook_*.py`、`_archive/`、`docs/国庆7天/Day12_多远端收敛.md`、`logs/day2/S5_*` |
| **只读** | 三个仓的 git 元数据、`.env`（**只读键名/取值用于调用，禁止把 token 值写进任何报告**） |
| **禁止** | 任何 `git push`；`light-merge/src/`、`antlrparser/`；`lightplugin/集成/`（S2）；`语言缺陷账.md`（S3/S4） |

## 六、交付物

| 路径 | 内容 |
|---|---|
| `docs/国庆7天/Day12_多远端收敛.md` | 三段式：① 10 落点复核表（逐项：远端 / 方式 ls-remote 或 API / 结果 SHA / 是否 annotated / 结论）② fork 追平核实数 + 方案 ③ LP github 分叉裁决 + 脚本入库决定 |
| 入库后的发布工具 + `_archive/` 归档物 | 见 §四 |
| `logs/day2/S5_api_verify.json` | API 原始响应（**脱敏：去掉 token**） |
| `logs/day2/S5_*.log` | 各命令原始输出 + rc |

## 七、验收标准（可量化）

1. **10/10 逐个有明确结论**：`SHA 匹配` / `SHA 不符（列出两侧）` / **`未能复核（写明原因）`**——不允许「大概没问题」。
2. API 走的落点标注「API 复核」；ls-remote 走的标注「ls-remote」。
3. 发布工具入库决定已落地（保留哪个、入库到哪、落选的去哪）。
4. 根目录残留按 §四 处置完毕（`ls` 前后对比落盘）。
5. **token 值未出现在任何报告/日志里**（只可出现键名）。
6. 四件套齐全。

## 八、反跑判据

1. **§8.1 反跑**：把修复版的「原样字节」改回 `CRLF→LF` 归一 → 对 **1 个已知 CRLF blob**（`lightharness/docs/功能对标/语言缺陷账.md`，git 对象库里存的是 CRLF）做对照，**复现 tree 不等价**；改回后恢复等价。两次输出都落盘。
2. **§8.2 反跑**：用一个不通的远端名演示 `git push <bad-remote> | tail` → 观察 **rc=0 但远端无 refs** 的假成功（落盘即可，**不要对真实远端做**）。

## 九、砍线与降级

- **15:00 上限**。API 端点找不到 → 出口降级为「已核实 4 个 + 6 个标注『未能复核』+ 复核脚本就绪」，**不阻塞屏障 D**；**绝不允许**为了凑「10/10 绿」而把未复核写成通过。

## 十、禁止事项

除派单表附录 B 的 7 条外：
1. **禁止 push**（本子任务最容易越界：既不许推 tag、也不许推分支，追平方案只写不做）。
2. 禁止把 `.env` 的 token 值写进报告、日志、提交信息。
3. 禁止用 `git push | tail` 或任何吞掉退出码的管道当复核手段。
