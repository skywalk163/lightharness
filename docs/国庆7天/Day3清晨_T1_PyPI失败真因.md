# Day3 清晨 T1 · PyPI 发布失败真因定位报告（v2 修正版）

> 派单表：`Day3清晨_派单表.md` v1.1｜线：**A（CI）**｜需门：**否**
> 出口 tag：`subtask-T1-done`｜**本批未真跑 twine upload / 未重跑发布 job**（禁令）

---

## 一、结论（一句话）

**根因 = PyPI 侧 trusted publisher 配置与 job 的 OIDC claims 不匹配（当时未配/配错）。**
workflow **已在走 OIDC trusted publisher 路径**（非 token 模式红因），PyPI 拒绝换 token：
`invalid-publisher`（valid token, but no corresponding publisher）。
用户已把 GitHub 与 PyPI 关联好 → **重跑 publish-pypi job 即可验证**（真发需用户示意）。

GitHub 官方失败注解（check-run `110892703005`，日志级证据）：
> `Trusted publishing exchange failure: Token request failed: invalid-publisher:
>  valid token, but no corresponding publisher (Publisher with matching claims was not found)`

## 二、v1 诊断修正

| | v1 结论 | v2 结论 |
|---|---|---|
| 根因 | ~~认证失败（401）+ `lightgm` 在 PyPI 不存在（404）~~ | **trusted publisher claims 不匹配**（PyPI 侧当时没配对） |
| 证据 | PyPI 侧 404 + 本机 token 401（反推） | **官方注解逐字引用**（日志级） |

v1 的「PyPI 侧 404 ⇒ 项目未创建」仍成立（本批复查仍 404），但它**不是** job 红因——
OIDC 交换失败发生在「找 publisher 配置」这一步，与项目是否存在是两回事。

## 三、关键证据：OIDC claims（job 实际发的）

| claim | 值 |
|---|---|
| `sub` | `repo:skywalk163@1298682/light@1328710154:environment:pypi` |
| `repository` | `skywalk163/light` |
| `workflow_ref` | `skywalk163/light/.github/workflows/release.yml@refs/tags/v0.4.0-rc2` |
| `environment` | `pypi` |

⇒ **PyPI 侧 trusted publisher 必须逐项匹配上表**。workflow 已用 `environment: pypi`
（`release.yml` L203-206），`gh-action-pypi-publish@release/v1` 自动走 OIDC。

> ⚠️ 附带发现：workflow L223 仍写着 `password: ${{ secrets.PYPI_API_TOKEN }}`——
> 在 trusted publisher 生效时该参数被忽略；但若哪天 secret 配上了，会**抢走 OIDC 路径**
> （action 优先用 password）。两套凭据并存是隐患，见 §四 B-3。

## 四、处置动作清单

### A. 用户侧核对（PyPI 点鼠标，已做一半）
1. PyPI 账号 → **Publishing → Add a new pending publisher**（或项目 → Settings → Publishing）
2. 逐项核对与 §三 claims 一致：
   - **PyPI project name**: `lightgm`
   - **Owner**: `skywalk163`
   - **Repository**: `light`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
3. 任一项对不上（尤其 Environment 留空 / Workflow 写错大小写）都会复现 `invalid-publisher`。

### B. 重跑与验证
1. **重跑**：Actions → rc2 run `#37020855509` → `发布到 PyPI` → **Re-run failed jobs**
   —— 这会**真发 `0.4.0rc2` 上 PyPI**，属真动作，**等你示意**再执行。
2. 通了 → 收口决策点 1（是否打 `v0.4.0` 正式 tag）。
3. **建议（本批不改，防隐患）**：`release.yml` L223 的 `password:` 行删掉，
   让 job 只走 OIDC（否则 secret 一旦配上会静默抢走 trusted publisher 路径）。

### C. 本机/本仓已做
- ✅ 注解级根因定位（本报告）
- ✅ rc2 run 其余 20 个 job 全绿复核
- ✅ `lightgm` 在 PyPI 仍 404（复跑确认，未上传过）

## 五、出口判据

| 判据 | 达成 |
|---|---|
| 失败根因一句话 | ✅ **trusted publisher claims 不匹配（invalid-publisher）** |
| 处置清单 | ✅ §四 A（核对 5 项）+ §四 B（重跑等示意） |
| 是否真发 PyPI | ❌ **未发**（禁令 + 等示意） |

## 六、遗留

- v1 的错误结论已在本文件 §二 修正，留档。
- 本报告未含任何 secret 值；claims 为调试信息，非凭据。