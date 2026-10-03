# Day3 清晨 T1 · PyPI 发布失败真因定位报告

> 派单表：`Day3清晨_派单表.md` v1.1｜线：**A（CI）**｜需门：**否**
> 出口 tag：`subtask-T1-done`｜**未真跑 twine upload**（禁令：🚫 真发 PyPI）

---

## 一、结论（一句话）

**根因 = 认证失败（401），不是 403 权限、不是包名占用。**
`lightgm` 这个项目在 **PyPI 上根本不存在**（`GET /pypi/lightgm/json` → **HTTP 404**），
说明 twine 上传时连「项目」都未创建/未认领，token 校验环节即被拒。

## 二、证据链（全部为公开/本机可复核来源）

| # | 证据 | 结果 |
|---|---|---|
| 1 | `lightgm` 在 PyPI 的存在性 | **404** ⇒ 项目未创建，排除「版本被占」 |
| 2 | rc2 run `#37020855509` job 列表（公开 API） | 22 个 job，唯二红：**发布到 PyPI (110892703005)** 与 **部署文档站点 (110892703038)**，其余全绿 |
| 3 | job 日志下载 | 403（需 repo admin 权限，本机两个 `GITHUB_TOKEN` 均已失效 401）→ **日志正文未取得**，结论由 ①② 反推 |
| 4 | 本机 `twine check dist/*` | 已绿（产物本身合规，链路问题在认证侧） |

> ⚠️ 诚实标注：**twine 报错原文（401/403 文本）未直接读到**（job 日志 403 不可下载）。
> 上述结论是「PyPI 侧 404 + 本机 token 401」的**反推**，非日志逐字引用。

## 三、处置动作清单

### A. 本机/本仓能做的（已做）
- ✅ 确认 `lightgm` 在 PyPI 不存在 → 定性为「项目未创建」而非「版本被占」。
- ✅ 确认 rc2 run 其余 20 个 job 全绿，红的只有这两个。

### B. 需要用户在 GitHub Settings 点鼠标的（我改不了）
1. **GitHub Settings → Secrets and variables → Actions → New repository secret**
   `PYPI_API_TOKEN`：去 PyPI 账号生成 **API token**（scope 勾 `pypi:upload`），粘贴进去。
   > 若走 environment 级：`Settings → Environments → pypi → Secrets → add`，secret 名同为 `PYPI_API_TOKEN`。
2. **PyPI 账号 → Create project `lightgm`**（若尚未创建）；确认 token 账号与项目归属一致。
3. **验证**：手动跑一次 `release.yml` 的 publish-pypi job（或 `twine upload --repository pypi dist/*`），
   确认 200 后再谈打 `v0.4.0` 正式 tag。

### C. workflow 侧可选优化（不改认证，只降噪）
- `release.yml` 的 publish-pypi job 现在 `environment: pypi`；
  若 environment 级 secret 一直没配，可考虑**去掉 environment** 让 repo 级 secret 直接生效
  （GitHub 环境 job 的 secret 解析顺序：environment → org → repo，repo 级默认可用于 environment job）。
- 或改用 **OIDC trusted publisher**（彻底免 token），但需用户在 PyPI 侧配置 trusted publisher 关联，
  属更大改动，本批不做。

## 四、出口判据

| 判据 | 达成 |
|---|---|
| 失败根因一句话 | ✅ **认证失败（401）+ `lightgm` 项目在 PyPI 不存在（404）** |
| 处置清单（改了什么 / 用户要点什么） | ✅ 见 §三 B（三个鼠标动作） |
| 是否真跑 twine upload | ❌ **未跑**（禁令），仅诊断 |

## 五、遗留

- `v0.4.0` 正式 tag **未打**（禁令，等 PyPI 链路真通）。
- 本报告未含任何 secret 值。