# T4 契约 · 发布前干跑预检（对象 `<TAG>`，发布物 = `v0.4.0-rc2`）+ 真 LLM smoke

> 夜场派单表：`Day2夜场_派单表.md` **v1.2**｜行：**B（远程线）／5 路并行之一**
> **资源型**：网络·等｜**需门**：否｜**预计**：约 1–1.5 小时
> **前置**：**无**（v1.2 起**不再等 T1/T2** —— 干跑验的是机制，不是那个 tag 本身）
> **出口 tag**：`subtask-T4-done`
> **🚫 绝对禁止 `git push`**（任何远端、任何形式）——本子任务最容易越界的地方

---

## 一、目标

1. **本地三仓 tag 一致性**（当前为 `v0.4.0-rc1`；**发布物将是 `v0.4.0-rc2`**）
2. **远端可达性与 token 有效性**（github / gitcode 走 API；gitea / myrepo / 本地镜像走 ls-remote）
3. **干跑 runbook**（逐命令 + 预期输出 + 失败模式 + 回滚点），**tag 用 `<TAG>` 变量**，**不真推**
4. **真 LLM smoke** —— ✅ **v1.2：key 已定位，本项从「条件式」升为「应跑」**

## 二、⚠️ 两条 v1.2 的关键更正（先说清楚，避免走白天的弯路）

### 2.1 LLM key **在 `lightharness/.env`，不在工作区根 `.env`**

| 文件 | 与模型相关的键 | 说明 |
|---|---|---|
| **`lightharness/.env`** | **`OPENAI_API_KEY`**、**`OPENAI_BASE_URL`**、**`OPENAI_MODEL`** | `L9` 注释「**Deepseek官方站点**」、`L13` 注释「官方 DeepSeek 端点 `https://api.deepseek.com`：deepseek-chat…」；`L10`/`L14` 生效，`L2`/`L3` 另有注释掉的备用配置 |
| `light-merge/.env` | 只有 `AIStudio_Access_Token` | **不是** DeepSeek 的凭据 |
| 工作区根 `.env` | 18 个键，模型相关只有 `AIStudio_Access_Token` | SSH 主机（`15/86/82SSH_HOST`）、`SUDO_PASS`、`TWINE_*`、`GITHUB_TOKEN`、`GITCODE_TOKEN` |

> **白天为什么降级**：`Day14 §3.1` 记「`.env` 与模型相关的只有 `AIStudio_Access_Token`」→ 拿它去打 DeepSeek/aistudio 端点，得 **401 / 404**，于是判「无凭据 → 降级」。
> **实际是找错了文件**（根 `.env` vs `lightharness/.env`）。→ 本子任务**要顺带把这个结论纠正过来**，并在报告里写明「用了哪个文件 + 哪个键名」。

### 2.2 ⚠️ 先确认没被「强制 mock」的开关挡住

跑 smoke 前**必须**确认这两个开关的当前取值（在 `light-merge/.env` 与运行环境里）：
- **`LIGHT_NO_LLM`** —— 若为真值，LLM 路径会被短路成 mock，**你会拿到一个假的"成功"**
- **`LIGHT_EVAL_REAL`** —— 决定是否走真实评测路径

→ 报告里**贴出这两个键的取值**（值可脱敏，但真假必须写清）。这是「别把 mock 当 real」的第二次机会。

## 三、⚠️ 范围界定（**不得重复劳动**）

| 已由白天完成 | 结论 | 本子任务 |
|---|---|---|
| **v0.3.0 的 10 落点复核**（`Day12_多远端收敛.md`） | **10/10 到位**；7/10 commit SHA 字节一致；**3/10（全部 github）commit SHA 不同但 tree 内容等价**（CRLF/历史分叉）；**0/10 未能复核** | **引它，不重做**（引用 `Day12:12-17`） |
| LP github SHA 分叉裁决 | 已裁决：接受「tree 等价、commit 层分叉」 | 沿用，**不要另起裁决** |

**本子任务的对象是「即将切出的 `<TAG>`（默认 `v0.4.0-rc2`）」，而它此刻还不存在** → 所以：
- **用当前 HEAD（等价 rc1）验机制**：本地一致性、token 有效性、逐项枚举、runbook 编排；
- runbook 里所有的 tag 名写成 **`<TAG>` 变量**，并注明「rc2 切出后只需替换变量重跑（预计 15 分钟）」；
- 报告**必须显式写明**「远端此刻不存在 rc2 ref，本次验的是机制」——避免读者误以为「远端 rc2 已核过」。

## 四、已核实的事实（直接用）

| 项 | 值 |
|---|---|
| rc1 tag 指向 | lightharness **`6c291f4`** / lightplugin **`62a5961`** / light-merge **`a495bb44c`** —— 三仓 **tag == HEAD**，工作树干净 |
| 发布脚本位置 | **`lightharness/_push_github_tree_sync.py`**（已提交；在**仓根**，不在 `scripts/`）、留档 `_archive/_push_github_multi.py`、`_push_github_delta.py` 亦在 `lightharness/` |
| ⚠️ 工作区根 | **已无任何 `_push_*.py`**（夜场 v1.0 写的「工作区根」已过时） |
| token | `lh/.env` 的 `OPENAI_*`（模型）；根 `.env` 的 **`GITHUB_TOKEN`** / **`GITCODE_TOKEN`**（代码托管） |
| 协议可达性 | 本机对 github/gitcode 的 **git 协议不可达、REST API 可达**（`Day12:24` 已证） |
| **§8.1 铁律** | 上传 git blob 必须**原样字节**（`raw = blob_bytes`，**不** `.replace(b"\r\n", b"\n")`）；白天已修，`a5c837e9d7` 的 tree = 本地 `082255c` tree = `a5c0b0a969795d…` |
| **§8.2 铁律** | **禁止** `git push \| tail`（`$?` 是 tail 的 rc 恒 0 → 「空输出 + rc=0 但远端无 refs」的假成功）；必须逐 `(repo, remote)` 枚举复核 |
| 远端名（10 落点） | LH：`github` / `myrepo` / **`origin`(=gitcode)**；LP：`github` / `gitcode` / `gitea`；LM：`github` / `gitcode` / **`origin`(=本地 `g:\github\light`)** / `gitea` |

## 五、文件白名单 / 黑名单

| | 路径 |
|---|---|
| **可写** | `lightharness/_push_github_tree_sync.py`（**独占**）、`docs/国庆7天/Day2夜_T4_发布前干跑预检.md`、`logs/day2-night/T4_*` |
| **只读** | `.env`（两个：根与 `lightharness/`）**只读键名与取值用于调用，值不得落盘**；三仓 git 元数据；`_archive/` |
| **禁止** | **任何 push**；`light-merge/src/`、`antlrparser/`；`语言缺陷账.md`（T5）；`Day11_发布管线.md`（T6）；1.5 盒子（T3） |

## 六、步骤

### A · 本地三仓 tag 一致性（只读）

1. 三仓分别：`git rev-parse v0.4.0-rc1^{commit}` / `…^{tree}` / `git status --short` / `git log -1 v0.4.0-rc1`。
2. 判据：**tag == HEAD**（若不等 → 报告并列两侧，并提示「rc1 已不是干净基底 → 发布物按 §六-3 应为 rc2」）。
3. 落盘 `logs/day2-night/T4_local_tag.txt`。

### B · 可达性与 token（只读，不推）

4. gitea / myrepo / LM 本地镜像：`git ls-remote --tags <remote> refs/tags/v0.3.0` → 记录「可达 + SHA」。
5. github / gitcode：走 **API**（复用 `_push_github_tree_sync.py` 里现成的调用姿势；`Authorization: Bearer $GITHUB_TOKEN`），验证 **token 有效** + 能读到 `refs/tags/v0.3.0`。
   - **annotated tag 注意**：ref 可能指向 tag 对象 → 再取 `object.sha` 才是 commit。
   - 每次调用间隔 3–5s；**找不到 GitCode 可用端点 → 明写「未能复核」**，不得默认成功。
6. 落盘 `logs/day2-night/T4_api_verify.json`（**脱敏**）。

### C · 干跑 runbook（核心交付）

7. 写清**等用户示意后**执行的**逐条命令**：每个 `(repo, remote, ref)` 一条；每条附：**预期输出**、**失败模式**（含「空输出 + rc=0 = §8.2 假成功」）、**复核命令**、**回滚点**。
8. **逐项点名 10 个落点**（**LH 的 gitcode 叫 `origin`**，不许按名字猜）。
9. **tag 一律写 `<TAG>`**（默认 `v0.4.0-rc2`），并写明「rc2 切出后替换变量重跑」。
10. **第一步**固定为：「校验发布物 ref 指向的 commit **是否包含 T1/T2**」（见派单表 §六-3）。

### D · 真 LLM smoke（**v1.2：应跑**）

11. 确认 §2.2 的两个开关（`LIGHT_NO_LLM` / `LIGHT_EVAL_REAL`）→ 贴出取值。
12. 用 **`lightharness/.env` 的 `OPENAI_*` 三件套**跑一条真实问题：落盘 **请求/响应片段（脱敏）、流式行为、耗时、rc**。
13. 若**确实**失败（如 401 余额/权限、网络）→ **如实记录失败原因与完整证据**，并说明与白天 401/404 的区别（是同一个错还是不同）。
    - **绝不**用 mock 结果冒充 real；**绝不**因为「白天已经降级过」就直接沿用降级结论。
14. 报告里写明：**用了哪个文件 + 哪个键名**（不写值）。

## 七、交付物

| 路径 | 内容 |
|---|---|
| `docs/国庆7天/Day2夜_T4_发布前干跑预检.md` | 三段式：① 本地 tag 一致性 ② 可达性/token 表（10 落点逐项）③ **干跑 runbook（`<TAG>` 变量版）** ④ **LLM smoke 结论 + 开关取值 + 键名出处** ⑤ rc1/rc2 归属 |
| `logs/day2-night/T4_local_tag.txt` | 三仓 tag/tree/HEAD/status |
| `logs/day2-night/T4_api_verify.json` | API 原始响应（**脱敏**） |
| `logs/day2-night/T4_llm_smoke.log` | 真实 LLM 原始输出（脱敏）或失败证据 |

## 八、验收标准（可量化）

1. **本地三仓**有明确结论：`tag == HEAD` 或「不等（列两侧）」。
2. **10 个落点逐项有结论**：`可达 + SHA` / `未能复核（写明原因）`——不允许「大概没问题」。
3. **runbook 可执行**：每条命令都有预期输出与失败模式；覆盖 10 落点且**远端名与实测一致**；tag 为 `<TAG>` 变量。
4. **LLM smoke 已跑**（带日志 + 键名出处 + 开关取值），或**如实记录失败**并有证据——**两种都算通过本项，mock 冒充不算**。
5. **rc1/rc2 归属**写清（rc1 仅留档、发布物 rc2）。
6. 四件套齐全 + **报告与日志中不出现任何 token/密码值**。

## 九、反跑判据

1. **§8.1 反跑**：把 `_push_github_tree_sync.py` 的「原样字节」改回 `CRLF→LF` 归一 → 对 **1 个已知 CRLF blob**（`lightharness/docs/功能对标/语言缺陷账.md`）做对照，**复现 tree 不等价**；改回后恢复等价。两次输出都落盘。
2. **§8.2 反跑**：对**假远端名**演示 `git push <bad-remote> | tail` → 观察 **rc=0 但远端无 refs** 的假成功（**只对假远端做**）。
3. **mock 反跑**：把 `LIGHT_NO_LLM` 置真值跑同一条 smoke → 应观察到「走了 mock」的特征；改回后重跑 → 结果应不同。**这条用来证明你的 smoke 判据能区分 real / mock**。

## 十、砍线与降级

- **150min 上限**。
- API 端点找不到 / token 失效 → 出口降级为「本地一致性 + gitea 系复核 + 逐项标注未能复核」+「待用户补齐 token 的清单」，**不阻塞**；**绝不允许**把未复核写成通过。
- LLM 仍不通 → **如实记录 + 保留可复跑命令**，不再花时间调 key（把结论交回 team lead）。

## 十一、必须带回的证据（四件套）

命令 + 退出码 + 日志路径（`logs/day2-night/`）+ 被测 SHA（三仓 tag 的 SHA 与 tree）。

## 十二、禁止事项

除夜场派单表附录 B 的 10 条外：
1. **禁止 push**（tag/分支一律不推；干跑 = 只读 + 写 runbook）。
2. **禁止重做 `Day12` 已完成的 v0.3.0 十落点复核**（引用即可）。
3. **禁止把 token 值写进报告、日志、提交信息**（含 `OPENAI_API_KEY`）。
4. 禁止用 `git push | tail` 或任何吞掉退出码的管道当复核手段。
5. **禁止用 mock 结果冒充真实 LLM smoke**；也禁止**不确认开关**就跑 smoke。
