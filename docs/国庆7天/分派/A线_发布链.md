# Day3 下午场 · A 线子任务书（发布链）

> **派发对象**：Agent A
> **线**：A（发布链）
> **父派单**：`../Day3下午_派单表.md` v1.1
> **你的领地**：GitHub Actions / `.github/workflows/` / `pyproject.toml` / git tag
> **你的禁区**：`light-merge/src/`、`light-merge/antlrparser/`、`lightharness/docs/`（除本任务书自身）、192.168.1.5

---

## 一、你要做什么

### 阶段 1（立刻开始）：T1 重跑 rc2 盯梢

rc2 Release run `#37020855509`（tag `v0.4.0-rc2` → commit `221db4fc6`）有三条失败：
- `发布到 PyPI`（twine upload 步）
- `部署文档站点`
- `Quality Gate`

处置已就位（dumate 清晨场做完）：
- PyPI trusted publisher 已关联（用户确认）
- Pages environment `github-pages` 已追加 `v*` tag 策略（id 61812294）

**动作**：
1. 用本机 git 凭据管理器的 PAT（admin 权限）POST `https://api.github.com/repos/skywalk163/light/actions/runs/37020855509/rerun-failed-jobs`
2. 盯三条 job：`发布到 PyPI`、`部署文档站点`、`Quality Gate` 全部 success
3. **VSCE job 红是预期**（VSCE_PAT 未配），不许处理
4. 若仍红：用 check-run annotations 拉日志级红因，按 `Day3清晨_T1/T2 v2 报告` 根因清单处置：
   - PyPI `invalid-publisher` → 提示用户核对 5 项（lightgm/skywalk163/light/release.yml/pypi）
   - Pages `environment protection rules` → 确认 v* 策略生效
5. **铁律**：这一步就是真发 `0.4.0rc2` 上 PyPI，不要再加"只诊断"

### 阶段 2（等信号）：T2 v0.4.0 正式 tag

**⚠️ 阶段 2 不许立刻开始**。必须同时满足：
- T1 三条绿（你自己盯完）
- **B 线 agent 报"full 门三元绿"**（他会在群里/会话里说）

两个信号都到了，才做：
1. `light-merge/pyproject.toml` 版本号 `0.4.0rc2` → `0.4.0`
2. 核对 `src/version.py` 也是 `0.4.0`
3. `.github/workflows/release.yml` L223 删 `password: ${{ secrets.PYPI_API_TOKEN }}` 行（OIDC 单路径化）
4. 提交 + push（commit message 格式：`chore(release): 版本号归位 0.4.0 + OIDC 单路径化`）
5. push 后打 tag `v0.4.0`（**真发正式版**），推到 origin
6. 盯新 release run 全绿（除 VSCE）
7. 核对：PyPI `lightgm 0.4.0` 出现、Pages 站点版本更新

---

## 二、绝对禁止

1. 🚫 B 线跑门期间（约 50 分钟）改任何 `light-merge/src/` 或 `light-merge/antlrparser/` 文件
2. 🚫 在 T1 三条绿之前打 `v0.4.0` tag
3. 🚫 处理 VSCE job
4. 🚫 `git add -A` / `git commit -a`——只 add 你自己改的文件
5. 🚫 force push / `git reset --hard`
6. 🚫 把 PyPI API token / PAT 值写进任何报告或日志

---

## 三、出口判据

| 项 | 通过标准 |
|---|---|
| T1 | publish-pypi / deploy-docs / QG 三条 success；PyPI 出现 `lightgm 0.4.0rc2` |
| T2 | `v0.4.0` tag 打在含 B 线修复的 commit；新 release 全绿（除 VSCE）；PyPI `0.4.0` URL 可访问 |

---

## 四、关键路径

- 根目录：`G:\dswork\duan-light-merge`
- light-merge：`G:\dswork\duan-light-merge\light-merge`（当前 HEAD `fa233209f`）
- GitHub repo：`skywalk163/light`
- rc2 run id：`37020855509`
- 凭据：本机 git 凭据管理器已存 PAT，`git push` 即可用；API 调用从 `.git/config` 或 git credential 取
