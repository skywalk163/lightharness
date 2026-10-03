# Day3 清晨 T2 · 文档站部署失败真因定位报告

> 派单表：`Day3清晨_派单表.md` v1.1｜线：**A（CI）**｜需门：**否**
> 出口 tag：`subtask-T2-done`｜**只处理 rc2 run #37020855509 里红的那条**（`release.yml` 内的 deploy-docs job）

---

## 一、结论（一句话）

**根因 = 仓库 Settings → Pages 未启用。**
`GET https://api.github.com/repos/skywalk163/light/pages` → **HTTP 404 Not Found**，
即 GitHub Pages 在本仓库上**根本没开**，`actions/deploy-pages@v4` 自然取不到 site / environment。

## 二、证据链（公开 API，可复核）

| # | 证据 | 结果 |
|---|---|---|
| 1 | `GET /repos/skywalk163/light/pages` | **404 Not Found** ⇒ Pages 未启用（决定性） |
| 2 | rc2 run `#37020855509` job 列表 | 22 job，唯二红：发布到 PyPI (110892703005) + **部署文档站点 (110892703038)** |
| 3 | `release.yml` 内 deploy-docs job 定位 | L230 `deploy-docs:` / L235 `name: github-pages` / L279 `uses: actions/deploy-pages@v4` —— 确认红的就是这条，非独立 `deploy-docs.yml` |
| 4 | job 日志正文 | 403（需 repo admin 权限）→ 未取得；结论由 ①② 反推，**非日志逐字引用** |

> ⚠️ 诚实标注：日志里那句 `Get Pages site failed` / `Get Pages environment failed` 未直接读到。
> 但 ① 是**决定性反证**：Pages 未启用 ⇒ 无论 job 内部报什么，根因都在 Settings。

## 三、处置动作清单

### A. 需要用户在 GitHub Settings 点鼠标的（我改不了，列到按钮级）

1. **仓库页 → Settings → Pages**
2. **Source** 下拉选 **`GitHub Actions`**
3. **Branch / folder** 选 **`main / /`**（或按 `mkdocs.yml` 的 `site_dir` 定，当前 `light-merge/mkdocs.yml` 默认 `/`）
4. 点 **Save**
5. （可选）确认 `Settings → Actions → Workflow permissions` 里 `Read repository contents` 已开
   —— `deploy-pages` 需要读 `docs-site/` 与 `mkdocs.yml`。

### B. workflow 侧可选优化（不改认证，只降噪）
- 现在 `release.yml` 的 deploy-docs job `environment: github-pages`；
  若 environment 一直没建，可考虑**去掉 environment** 让 job 直接跑（`actions/deploy-pages@v4` 本身会建 site）。
- 顺手确认（不动）：独立 `deploy-docs.yml`、`docs-deploy.yml`、`docs.yml` 是否 stale —— 本批不改。

## 四、出口判据

| 判据 | 达成 |
|---|---|
| 失败根因 | ✅ **Pages 未启用（404）** |
| 用户侧动作清单（截图级步骤） | ✅ 见 §三 A（Settings → Pages → Source=GitHub Actions → Save） |
| 是否改了 workflow | ❌ 未改（根因不在 workflow） |

## 五、遗留

- 与 T1 同属「需用户点鼠标」类，本批不代劳。
- 本报告未含任何 secret 值。