# Day2 夜场 T6 交付 · 发布 runbook 收尾

> 派单表：`Day2夜场_派单表.md` **v1.2**｜契约：`Day2N_契约_T6_发布runbook.md`
> 执行时间：2026-10-02 夜｜执行线：**C（账与文档线）／5 路并行之一**
> 资源型：纯文档｜需门：否｜**出口 tag**：`subtask-T6-done`
> **🚫 零真推**：本子任务只产出「等示意即可执行」的 runbook，未执行任何 `push` / 打标 / 切 tag / PyPI / VSCE 动作。

---

## 一、改了什么

向 `lightharness/docs/国庆7天/Day11_发布管线.md` **追加** 4 节（§〇–§七 原有结论**一行未改**）：

| 节 | 内容 | 对应契约 |
|---|---|---|
| **§八 打标流程** | 发布物归属（rc2）+ 切出时机 + 三仓命令 + annotated 选择理由 + 已存在 tag 处置铁律 | 契约 §4.1 |
| **§九 远端 tag 推送 runbook** | **10 落点逐项**（每项：推送动作 / 预期输出 / 失败模式 / 复核命令）+ `<TAG>` 变量 + push\|tail 铁律 + 通道选型（git 直达 / GitHub API / GitCode API） | 契约 §4.2 |
| **§十 回滚预案** | 4 类失败（推错远端 / 错 commit / CRLF 回归 / PyPI 占用）逐类：可回滚性 + 动作 + 验证命令 + 铁律 | 契约 §4.3 |
| **§十一 发布前检查单** | 9 步顺序检查单（每步：通过判据 + 不通过怎么办），**第 1 步 = 校验发布物是否包含 T1/T2（硬性）** | 契约 §4.4 |

**未做**（契约明确引用不重写）：Day11 §5.1–5.4 的 PyPI/VSCE 待执行命令（引用）；T4 的预检命令表（交叉引用，不复制）；Day12 的十落点复核表（引用）。

## 二、rc2 归属与第一步校验（核心约束）

- **发布物 = `v0.4.0-rc2`**；**`v0.4.0-rc1` 仅留档、不作发布物**（T1/T2 收口后 rc1 不再是「已验证冻结基底」，推 rc1 = 推修复前编译器）。
- runbook 全程用 **`<TAG>`** 变量（默认 rc2），rc1/rc2 复用同一份 runbook。
- **检查单第 1 步（硬性）**：`git log --oneline -1 <TAG>^{commit}` 确认 `<TAG>` 指向 **T1（LP-D-010）+ T2（LP-D-013）收口后**的 commit；不包含 → **停下回报**，不得推。

## 三、10 落点逐项点名（远端名与实测一致）

来自干跑日志 `logs/day2-night/T6_dryrun.log` §1（`git remote -v` 逐仓实测）：

| 仓 | 落点 × 4/3 | 远端名（实测） | 通道 |
|---|---|---|---|
| **LH** `lightharness` | github / myrepo / **origin(=gitcode)** | `github.com/skywalk163/lightharness`、`http://192.168.1.5:3000/skywalk/lightharness`、`https://gitcode.com/skywalk163/lightharness` | API / git / **API（GitCode）** |
| **LP** `lightplugin` | github / gitcode / gitea | `github.com/skywalk163/lightplugin`、`gitcode.com/skywalk163/lightplugin.git`、`http://skywalk@192.168.1.5:3000/skywalk/lightplugin.git` | API / API / git |
| **LM** `light-merge` | github / gitcode / **origin(=本地 `g:\github\light`)** / gitea | `github.com/skywalk163/light`、`gitcode.com/skywalk163/light`、`g:\github\light`（本地路径）、`http://skywalk@192.168.1.5:3000/skywalk/light.git` | API / API / git / git |

> ⚠️ 两处反直觉点已在 runbook 显式点名：**LH 的 gitcode 落点远端名是 `origin`，不是 `gitcode`**；**LM 的 `origin` 是本地裸仓路径，不是任何托管平台**。

## 四、干跑自检（契约 §六.3，原始输出见 `logs/day2-night/T6_dryrun.log`）

| 干跑项 | 结果 | 说明 |
|---|---|---|
| 三仓 `remote -v` 逐项点名 | ✅ 10 落点全部存在且 URL 正确 | 反向自检的直接依据 |
| rc1 == HEAD 一致性 + tag 类型 | ✅ 三仓 rc1 均 == HEAD（LH `6c291f445c…` / LP `62a596125c…` / LM `a495bb44c4…`），均 annotated | 打标流程 §8.3 的参照命令跑通 |
| 工作树干净度 | ✅ LP / LM 零脏；LH 仅 10 个 `??`（本批契约/探针文档，`M` 为 0，不阻塞打标） | runbook §8.3「行首 M 即停下」判据采用 |
| 复核命令 ls-remote（myrepo / gitea / origin 本地） | ✅ 4 条均 rc=0，远端 rc1 tag 对象 SHA 与本地一致 | §九复核命令逐一可执行、预期输出准确 |
| **github git 协议失败模式** | ✅ 实测 `git ls-remote github` 超时 rc=124（连接挂起）→ 铁律成立：github 必须走 API | 失败模式「真会出现」且与 Day12 结论一致 |
| **push\|tail 掩码实测** | ✅ 修正姿势后：git 真实 rc=128，`| tail` 后 `$?`=0 → 假成功实锤 | §九铁律有直接反跑证据（最初姿势对不存在 remote 名解析有歧义，已换零歧义绝对路径重跑） |
| rc2 不存在确认 | ✅ 三仓 rc2 refs 均 = 0 | 起点干净，切 rc2 无冲突 |

## 五、反向自检（契约 §六.4）

**故意把 LH 的 gitcode 远端按「想当然」写成 `gitcode`**：

```
$ git -C lightharness remote get-url gitcode
error: No such remote 'gitcode'
rc=2   ← 暴露
```

- 结论：runbook 的「逐项点名」机制**有效**——执行者只需按 §九表格核对 `git remote -v`，LH 下根本不存在名为 `gitcode` 的远端，该错误写法会在第一步复核中被拦截（正确名 = `origin`）。过程已记录在 `T6_dryrun.log` §8。
- 同机制覆盖 LM `origin`=本地路径的反直觉点（§九 9.x 逐条点名 URL 实测值，不靠猜）。

## 六、交叉引用

- **T4（同批）**：github/gitcode 的 token 就绪与 API 端点细节，runbook §九表格**显式标注「占位 → 取决于 T4」**，检查单第 4 步**不许默认通过**；T4 收口后按 T4 报告回填即可执行。
- **T5（同批）**：语言缺陷账由 T5 统一落账，本子任务未碰 `语言缺陷账.md`。
- **Day12**：github 3 落点 tree 等价判据、GitCode API「HTTP 201 即成功」、`tree_sync` 原样字节铁律均引自 Day12 已实测结论（runbook 标注出处，不重写证据）。

## 七、四件套

1. **命令**：全部命令已在 `Day11_发布管线.md` §八–§十一 落盘（可复制粘贴，含环境变量前缀）；未执行任何写远端命令。
2. **退出码**：`T6_dryrun.log` 逐条记录（ls-remote rc=0 ×4；github 超时 rc=124；push\|tail 掩码 git rc=128 vs `$?`=0；反向自检 rc=2）。
3. **日志路径**：`logs/day2-night/T6_dryrun.log`（原始输出 + rc）。
4. **被测 SHA**（三仓 rc1 tag 与 HEAD）：
   - LH `lightharness`：HEAD = rc1 = **`6c291f445c1788ee3f8b99e58e6e5aca5ff414fb`**
   - LP `lightplugin`：HEAD = rc1 = **`62a596125c96dfd0e8e17963692f687d506441ac`**
   - LM `light-merge`：HEAD = rc1 = **`a495bb44c46904886b6ebd110dcd004a9325aab7`**

## 八、验收对照（契约 §八）

1. ✅ 10 落点逐项出现在 runbook，远端名与实测一致（LH `origin`=gitcode 显式体现，§三/§九）。
2. ✅ 每条推送命令带预期输出 + 失败模式 + 复核命令；`push | tail` 禁止项显式列出并有干跑反跑证据。
3. ✅ 回滚预案覆盖 4 类失败（§十），逐类可/不可回滚 + 验证命令。
4. ✅ 发布物 = `v0.4.0-rc2` 写明；rc1 标注「仅留档、不作发布物」；检查单第一步 = 校验发布物是否含 T1/T2。
5. ✅ 干跑自检（§四）+ 反向自检（§五）均有记录（`T6_dryrun.log` + 本文档）。
6. ✅ 全程未出现任何 token / 密钥值（文档只出现键名与文件路径；干跑日志未读取 `.env`）。
7. ✅ 四件套齐全（§七）。

## 九、待办（不属于本子任务的边界）

- 真推 / 切 rc2 / 远端 push → **T8，等用户明确示意**。
- github/gitcode API 端点与 token 确认 → **T4 收口后回填占位**。