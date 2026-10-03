# Day3 清晨 T2 · 文档站部署失败真因定位报告（v2 修正版）

> 派单表：`Day3清晨_派单表.md` v1.1｜线：**A（CI）**｜需门：**否**
> 出口 tag：`subtask-T2-done`｜只处理 rc2 run #37020855509 里红的那条（`release.yml` 内 deploy-docs job）

---

## 一、结论（一句话）

**根因 = environment `github-pages` 的保护规则（Deployment branches and tags）拒绝了 tag 触发的部署。**
Pages 本身**已启用**（`https://skywalk163.github.io/light/` → HTTP 200，用户现场确认设定过）。

GitHub 官方失败注解（check-run `110892703038`，日志级证据）：
> `Tag "v0.4.0-rc2" is not allowed to deploy to github-pages due to environment protection rules.`
> `The deployment was rejected or didn't satisfy other protection rules.`

## 二、v1 诊断修正（重要，防同类误判）

| | v1 结论 | v2 结论 |
|---|---|---|
| 根因 | ~~Pages 未启用（API 404）~~ | **environment `github-pages` 保护规则拒绝 tag 部署** |
| 证据 | 匿名 `GET /repos/.../light/pages` → 404 | **官方失败注解逐字引用** + Pages 站点 HTTP 200 |

**误判根因**：GitHub API 对**无权限访问的资源返回 404 而非 403**（隐藏资源存在性）。
匿名请求查 `/pages` 得 404 **不能证明** Pages 未启用。⇒ 以后凡「资源存在性」结论，
必须拿到**日志级/注解级证据**或有效凭据，匿名 404 只能当线索。

## 三、证据链

| # | 证据 | 结果 |
|---|---|---|
| 1 | check-run 注解（匿名可拉，日志级） | **`Tag "v0.4.0-rc2" is not allowed to deploy to github-pages due to environment protection rules`** |
| 2 | `https://skywalk163.github.io/light/` | HTTP **200** ⇒ Pages 已启用、站点在线 |
| 3 | `release.yml` deploy-docs job（L230–279） | `environment: github-pages` + `actions/deploy-pages@v4`，入口核对无误 |
| 4 | workflow/branch | run 由 **tag `v0.4.0-rc2`** 触发（`head_sha 221db4fc6`）⇒ 撞上保护规则的正是 tag ref |

## 四、处置动作清单

### A. 用户侧（Settings 点鼠标，API 无有效凭据改不了）

1. 仓库页 → **Settings → Environments → github-pages**
2. 找到 **Deployment branches and tags**（保护规则）
3. 两种改法二选一：
   - 放宽：选 **No restriction**（任何 ref 都可部署）——文档站通常无敏感面，推荐；
   - 收窄但放行 tag：选 **Selected branches and tags**，加 tag 模式 **`v*`**（或显式 `v0.4.0-rc2`）
4. **Save** → 重跑 `release.yml` 的 deploy-docs job（Actions → Run workflow / Re-run failed jobs）
5. 验证：`部署文档站点` 转绿，站点内容更新。

### B. workflow 侧（可选，本批不改）
- 若想永久避免撞保护规则，可把 deploy-docs 拆成独立 workflow 由 `workflow_run`/push main 触发，
  与 tag Release 解耦——属架构改动，需用户拍板，本批不做。

## 五、出口判据

| 判据 | 达成 |
|---|---|
| 失败根因 | ✅ **environment `github-pages` 保护规则拒绝 tag 部署**（注解级证据） |
| 用户侧动作清单（按钮级） | ✅ 见 §四 A（5 步） |
| 是否改了 workflow | ❌ 未改（根因不在 workflow） |

## 六、遗留

- v1 报告的错误结论已在本文件 §二 修正，不删除（留档防再犯）。
- 本报告未含任何 secret 值。