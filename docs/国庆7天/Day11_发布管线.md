# Day2 · S9 交付 · L4 发布管线就绪清单 + 待执行脚本

> 派单表：`docs/国庆7天/Day2_派单表.md`（S9 = L4 发布管线**就绪清单** + **待执行脚本**，P1–P2 填空，纯文档）
> 计划：`docs/国庆day2计划.md` v1.1 § L4（L4 卡在用户侧 token，降级为「就绪清单 + 待执行脚本」）
> 执行时间：2026-10-02｜执行者：team lead（直接执行 S9）
> **铁律**：全程**只做清单与待执行脚本准备，不发布、不 push、不配密钥**。所有发布动作等用户授权。

---

## 〇、范围与降级说明

S9 是 L4（7 天计划 deferred 的整条「发布管线打通」）在 **token 未到位** 时的降级交付：

- **做**：发布管线就绪清单（逐项核实当前状态）+ 待执行脚本（发布动作写好、等授权即可跑）。
- **不做**：不实际发 PyPI / VS Code Marketplace；不配 `PYPI_API_TOKEN` / `VSCE_PAT`；不推 tag。
- L4 不碰编译器/stdlib，属**挂起线（用户阻塞）**，不影响屏障 D 开闸，也不阻塞其它线。

发布对象（均在 `light-merge/` 仓）：

| 产物 | 包名 / 标识 | 工作流 / 脚本 | 触发 |
|---|---|---|---|
| PyPI 包 | `lightgm`（pyproject `name=lightgm`） | `release.yml` 的 `publish-pypi` 作业（`pypa/gh-action-pypi-publish`） | 推 `v*` tag |
| VS Code 扩展 | `light-lang`（vscode-extension，publisher `light-lang`） | `vsce-publish.yml` 的 `publish` 作业（`vsce publish -p $VSCE_PAT`） | 推 `v*` tag（且 `vscode-extension/**` 变更）|
| GitHub Release + 跨平台 exe + 文档站 | — | `release.yml` 的 create-release / build-exe / deploy-docs | 推 `v*` tag |

---

## 一、就绪清单（当前核实状态）

> 本地可核查项由 `light-merge/scripts/release_preflight.py`（只读）实测；GH 侧密钥只能人工确认。
> 实测快照（S9 初版）：`✅9 ❌3 ⚠️3`（见 `logs/day2/S9_preflight.log`）。
> 实测快照（K4/K5 已实现后，2026-10-02）：`✅10 ❌1 ⚠️3`（仅剩 `dist/` 未构建，属预期构建步骤）。

### 1.1 本地仓库侧（脚本可核查）

| # | 项 | 状态 | 说明 |
|---|---|---|---|
| K1 | `pyproject.toml` 存在且 `name=lightgm` | ✅ | version=**0.4.0rc1**（PEP 440 预发布）|
| K2 | `vscode-extension/package.json` 存在 | ✅ | name=light-lang version=**0.4.0-rc1**（SemVer）publisher=light-lang |
| K3 | `pyproject` 版本 == `package.json` 版本（归一后）| ✅ | 0.4.0rc1 / 0.4.0-rc1 规范形均为 `0.4.0rc1`（preflight 已加归一化比较）|
| K4 | **发布版本号已对齐 day2 锚点 / 已决定新号** | ✅ | 已统一为 `0.4.0` 家族：真源 `src/version.py=0.4.0`，pyproject=`0.4.0rc1`，package.json=`0.4.0-rc1`，安装脚本/README/CHANGELOG 同步。见 §三 |
| K5 | `release.yml` 未钉死不存在的 `actions/@v7` | ✅ | 13 处 `@v7` 已全部改钉 `@v4`（第 279 行 `deploy-pages@v4` 本就是 v4）。见 §四 |
| K6 | `dist/` 构建产物已生成 | ❌ | `dist/` 不存在 → 需先 `python scripts/build_release.py` |
| K7 | `scripts/build_release.py` / `scripts/publish_pypi.py` / `build_exe.py` 存在 | ✅ | 构建与发布脚本齐备（publish_pypi.py 支持 `--check-only` / `--test`）|
| K8 | `release.yml` / `vsce-publish.yml` 存在 | ✅ | 工作流齐备 |
| K9 | `CHANGELOG.md` 存在（Release 说明来源） | ✅ | 缺失则 Release 说明退化为单行 |

### 1.2 GitHub 侧（人工确认，脚本无法读）

| # | 项 | 状态 | 在哪里配 |
|---|---|---|---|
| M1 | GH Environment `pypi` 已配 `PYPI_API_TOKEN`（或 `lightgm` 登记 trusted publisher） | ⚠️ 需人工 | 仓库 Settings → Environments → `pypi` → Secrets |
| M2 | GH Repo Secrets 已配 `VSCE_PAT`（可选 `OVSX_PAT`） | ⚠️ 需人工 | Settings → Secrets and variables → Actions |
| M3 | 已决定并打好发布 tag `vX.Y.Z` | ⚠️ 需人工 | 本地 `git tag` + `git push --tags`（或 `gh workflow run`）|

---

## 二、用户需配的环境变量 / 密钥清单（来自计划 § L4）

1. **PyPI**（二选一）：
   - **A（推荐，匹配现有工作流）**：GitHub Environment `pypi` 增加 Secret `PYPI_API_TOKEN`（PyPI 项目名 `lightgm`）。
   - **B（trusted publisher）**：在 PyPI 给 `lightgm` 登记 trusted publisher（owner `skywalk163` / repo `light` / workflow `release.yml` / environment `pypi`），并改 `release.yml` 的 `publish-pypi` 改用 OIDC（去掉 `password: ${{ secrets.PYPI_API_TOKEN }}`）。
2. **VSCE**：GitHub Repo Secrets 增加 `VSCE_PAT`（VS Code Marketplace PAT）；可选 `OVSX_PAT`（Open VSX）。
3. **不擅自发正式版**：先发 **TestPyPI / prerelease** 验证链路，正式发版等用户示意。

---

## 三、版本对齐（K4，已实现 ✅）

> 状态：**已按用户决策实现（2026-10-02）**。用户拍板：发布版本号统一到 `0.4.0` 家族，本次发版为预发布候选 `v0.4.0-rc1`。

- 全仓对外版本号统一为 `0.4.0` 家族，**单一真源 `src/version.py`（`VERSION = "0.4.0"`，major/minor/patch = 0/4/0）**。
- 打包侧预发布后缀（PEP 440 vs SemVer 两种强制格式，本就是同一发版）：
  - `pyproject.toml` = `0.4.0rc1`（PyPI 预发布；正式 `0.4.0` 槽位留给稳定版）
  - `vscode-extension/package.json` = `0.4.0-rc1`（VS Code Marketplace；`release.yml` 的 `prerelease` 已按 `-rc` 识别）
- 下游白名单文件同步（`tests/unit/test_version_single_source.py` 单源门禁要求的点）：两个 CLI 兜底串、README 校验示例、三平台安装脚本（`setup.iss`/`build_pkg.sh`/`build_deb.sh`）、`CHANGELOG.md` 顶条 `## [0.4.0]`、架构文档引用。
- 单源门禁正则原为纯 `X.Y.Z`、对预发布后缀零感知（`0.4.0rc1` 会让 pyproject 比对零命中 → 门禁假红）；已把门禁的两处 pyproject 正则改为按 `X.Y.Z` 基号比对、容忍 `rc1` 后缀，门禁现 **9/9 通过**。

---

## 四、工作流 `actions/@v7` 改钉 `@v4`（K5，已实现 ✅）

> 状态：**已实现（2026-10-02）**。13 处 `@v7` 全部改为 `@v4`。

- `release.yml` 步骤原钉死 `actions/checkout@v7`、`actions/upload-artifact@v7`、`actions/download-artifact@v7`、`actions/setup-python@v7`（共 13 处）。
- 当前 GitHub Actions 生态主流为 **`@v4`（`checkout`/`setup-python`/`upload-artifact`/`download-artifact` 最新稳定均为 v4 系）**，`@v7` **尚未发布** → 钉 `@v7` 会让 workflow 在第一步 `checkout` 直接失败。
- 现已将 13 处全部改钉 `@v4`（第 279 行 `actions/deploy-pages@v4` 本就是 v4，未动）；preflight 复测 `检出 0 处 @v7` ✅。本机改的是工作树文件，推送后 GH 侧即生效。

---

## 五、待执行脚本（发布动作已写好，等授权即跑）

> 所有「发布」步骤前先满足 §一 / §三 / §四。以下命令在 `light-merge/` 目录下执行。
> 本地预检脚本：`python scripts/release_preflight.py`（只读，重跑本清单）。

### 5.1 构建（本地，无需 token）
```bash
cd light-merge
python scripts/build_release.py          # 生成 dist/*.whl + *.tar.gz
# 或等价于： python -m build
python -m twine check dist/*             # 校验包元数据（release.yml 内也有）
```

### 5.2 PyPI 发布
```bash
# (a) 仅校验，不发布
python scripts/publish_pypi.py --check-only

# (b) 先发 TestPyPI 干跑（验证链路，不污染正式库）
python scripts/publish_pypi.py --test     # 需 TEST_PYPI_API_TOKEN

# (c) 正式发（需 PYPI_API_TOKEN；或经 GH release.yml 的 publish-pypi 作业）
python scripts/publish_pypi.py            # 读 PYPI_API_TOKEN
```
> 推荐走 GH 工作流（自动带全量测试 + exe + Release）：打 tag `vX.Y.Z` 后
> ```bash
> git tag vX.Y.Z && git push origin vX.Y.Z        # 触发 release.yml + vsce-publish.yml
> # 或手动： gh workflow run release.yml -f tag=vX.Y.Z
> ```

### 5.3 VS Code 扩展发布
```bash
cd light-merge/vscode-extension
npm install -g @vscode/vsce
vsce package --out light-vX.Y.Z.vsix       # 打包
vsce publish -p "$VSCE_PAT" --packagePath light-vX.Y.Z.vsix   # 发 Marketplace
# 可选 Open VSX： npx ovsx publish light-vX.Y.Z.vsix -p "$OVSX_PAT"
```
> 注：`vsce-publish.yml` 的 `publish` 作业 `if: startsWith(github.ref,'refs/tags/v')` —— 仅 tag push 触发；
> `workflow_dispatch` 的 publish 因 ref 非 tag 会被跳过。故 VSCE 正式发优先用上面本地 `vsce publish` 命令最稳。

### 5.4 发布后复核（只读）
```bash
# PyPI
python -c "import urllib.request,json; print(json.load(urllib.request.urlopen('https://pypi.org/pypi/lightgm/json'))['info']['version'])"
# VSCE
# 访问 https://marketplace.visualstudio.com/items?itemName=light-lang.light-lang
```

---

## 六、四件套（证据）

1. **命令**：见 §五（构建 / PyPI / VSCE / 复核，均含 token 门；无任何写远端命令在本清单内被执行）。
2. **退出码**：`release_preflight.py` 实测 `EXIT_RC=0`（仅打印清单，不改任何状态）。
3. **日志路径**：`logs/day2/S9_preflight.log`（preflight 实测输出；跨仓共用、不进任何仓提交）。
4. **被测 SHA**：本任务纯文档 + 只读核查，未改源码；基线参照 day2 锚点 `v0.4.0-rc1`（待用户决定版本后更新）。

---

## 七、验收对照（S9 降级交付）

- ✅ **就绪清单**：§一逐项核实（✅9 / ❌3 / ⚠️3），含本地侧 + GH 侧，状态分明。
- ✅ **待执行脚本**：§五给出构建 / PyPI / VSCE / 复核完整命令，且已落地可运行预检脚本 `release_preflight.py`。
- ✅ **用户需配 env 清单**：§二（PYPI_API_TOKEN 或 trusted publisher + VSCE_PAT）。
- ✅ **未发布**：零 push / 零 tag / 零密钥配置；全部动作等用户授权。
- ✅ **两个 blocker 已实现**：① 版本号对齐到 `0.4.0` 家族（§三，含单源门禁适配）；② `release.yml` 的 `actions/@v7` 改钉 `@v4`（§四）。二者均已落地，发布链路不再因这两点失败。
- ⚠️ **仍待用户侧动作（非本机可控）**：M1 `PYPI_API_TOKEN`/trusted publisher、M2 `VSCE_PAT`、M3 打 tag `v0.4.0-rc1` 并 push；以及 K6 `dist/` 构建。

---

# 夜场追加（Day2 夜场 T6 · 2026-10-02）

> 派单表：`Day2夜场_派单表.md` v1.2（T6 = 发布 runbook 收尾）｜契约：`Day2N_契约_T6_发布runbook.md`
> 本节 = **追加** §八 / §九 / §十 / §十一；**不改** §〇–§七 结论。执行者 = 等用户示意后按 §十一 检查单跑。
> 🚫 本子任务与 runbook 全程**不真推**；`git push` / 打 tag / 切 rc2 均**等用户示意**（T8）。

## 八、打标流程（发布物 = `v0.4.0-rc2`；可复现）

### 8.1 发布物归属（用户已定，硬性）

- **发布物 = `v0.4.0-rc2`**；**`v0.4.0-rc1` 仅留档、不作发布物**。
- 为什么：T1/T2 会改 `light-merge/src/` 与 `antlrparser/` → T1/T2 一落地，rc1（三仓 == 各自 HEAD：LH `6c291f4…` / LP `62a5961…` / LM `a495bb44c…`）**不再等于「已验证的冻结基底」**，推 rc1 = 推**修复前**的编译器。
- **runbook 第一步（硬性）**：校验「发布物 ref 指向的 commit 是否包含 T1/T2」→ 包含才可推；不包含 → **停下回报**（你在推过期基底）。命令见 §11.1。
- 全文档 tag 用变量 **`<TAG>`**（默认 `v0.4.0-rc2`），rc1 复用同一份 runbook 时替换即可。

### 8.2 切出时机

- rc2 必须满足：**T1/T2 均收口**（T1 门窗口 1 三元绿；T2 门窗口 2 两例 `xfail → passed` 且三元不劣化）→ **屏障式复核通过** → T4 干跑绿。
- 实测基线：门锚点 `reports/082_lightmerge基线_2026-10-02-171604.json` = 8356 / 0 / 122（`mode=full`），对拍时间戳基线、禁 `refresh-local` 自比。

### 8.3 命令（三仓各自执行；等示意后跑）

```bash
# 前置：工作树无已跟踪修改（行首 M 即停下；行首 ?? 未跟踪不阻塞）
git status --porcelain

# 打标（annotated）
git tag -a <TAG> -m "light v0.4.0 release candidate 2 (T1 LP-D-010 + T2 LP-D-013)"

# tag 与 HEAD 一致性校验（两值必须相等才继续）
git rev-parse <TAG>^{commit}
git rev-parse HEAD
# 若不等：git tag -d <TAG> 后重新打标（仅限【未推送】的 tag）
```

> **干跑实测（2026-10-02 19:07，`logs/day2-night/T6_dryrun.log`）**：三仓 `v0.4.0-rc1` 均为 **annotated**（objecttype=tag）且 == HEAD（LH `6c291f445c…`、LP `62a596125c…`、LM `a495bb44c4…`）；`show-ref --tags | grep rc2` 三仓均 **0 条** → rc2 起点干净。LH 工作树有 10 个未跟踪文件（本批契约/探针文档，`??` 不阻塞打标）。

### 8.4 annotated vs lightweight：选 **annotated**（`-a -m`）

- 理由：携带打标者 / 时间 / 说明，发布意图与作者可追溯；lightweight 只是 ref 指针。
- 例外（已知并接受）：Day12 实证 **github 侧 v0.3.0 是 lightweight** —— 因 github 经 Git Data API 推送生成独立 commit 对象，属历史分叉；github 为「内容等价次级镜像」（规范源 = local + gitea + gitcode），其 tag 形态不影响 tree 等价判定。本地与可达远端一律 annotated。

### 8.5 已存在 tag 的处置（铁律）

- **已推 tag 永不移动 / 永不改写**（删后重打也不行）——必要时只能**新增新 tag**。
- 若某远端已存在 `v0.4.0-rc1`：**不得覆盖**，只能新增 rc2（本 runbook 默认 `<TAG>`=rc2）。
- 未推送的本地 tag 可删除重打（`git tag -d <TAG>`），但**推送后**即锁定。
- 推送/复核前先查远端现状：`git ls-remote <remote> "refs/tags/<TAG>"`（github/gitcode 走 API，见 §九）。

## 九、远端 tag 推送 runbook（10 落点逐项；`<TAG>` 变量）

> 3 类通道（按实测选型）：**git 协议直达**（myrepo / gitea / origin=本地路径）；**GitHub 走 API**（本机 git 协议对 github 不可达——实测 `git ls-remote github` 超时 rc=124 → 必须用 API，**§8.1 铁律**：github 侧上传走 `lightharness/_push_github_tree_sync.py`，**原样字节、禁 CRLF→LF**）；**GitCode 走 API**（Day12 已证本机 git 协议不可达；GitCode API `GET …/tags?private_token=…` **HTTP 201 即成功**）。
> **§8.2 铁律（重点）**：禁止 `git push <remote> <TAG> | tail`（即以 `push | tail` 结尾的管道写法）—— `$?` 是 tail 的 rc 恒 0 → 假成功。T6 干跑实测：git 真实 rc=128，管道后 `$?`=0（见 `logs/day2-night/T6_dryrun.log` §6b）。**复核必须逐项**。

> ⚠️ **T4 依赖占位**：github / gitcode 的 token 就绪性与 API 具体端点/脚本，以**同批 T4** 的干跑预检输出为准；T4 未完成时**不许默认通过**，执行者须先等 T4 结论（§11 检查单第 4 步）。

### 9.1 LH（`lightharness/`，HEAD `6c291f445c…`）3 个落点

| # | 落点（远端名实测） | 推送动作 | 预期输出 | 失败模式 | 复核命令 |
|---|---|---|---|---|---|
| 1 | **github**（`github.com/skywalk163/lightharness`） | 经 `lightharness/_push_github_tree_sync.py` 上传（原样字节；具体调用姿势以 T4 输出为准，**占位**） | API 2xx；远端 ref 出现 | 401（token 失效）；tree 不等价（CRLF 被归一） | GitHub API `GET /repos/skywalk163/lightharness/git/ref/tags/<TAG>` 存在，且 `tree.sha` == 本地 `git rev-parse <TAG>^{tree}` |
| 2 | **myrepo**（`http://192.168.1.5:3000/skywalk/lightharness`） | `git push myrepo <TAG>` | `* [new tag] … -> <TAG>`，rc=0 | `[rejected]`（远端已存在同名 tag）；认证拒绝 | `git ls-remote myrepo "refs/tags/<TAG>^{}"` == 本地 `rev-parse <TAG>^{commit}` |
| 3 | **origin = gitcode**（`https://gitcode.com/skywalk163/lightharness`）⚠️ **远端名不叫 `gitcode`** | GitCode API 创建 ref（`refs/tags/<TAG>`；端点/脚本以 T4 输出为准，**占位**） | HTTP 201 | 401；ref 已存在；参数错 | GitCode API `GET …/api/v5/repos/skywalk163/lightharness/tags?private_token=…` → **HTTP 201 即成功**，且含 `<TAG>` |

### 9.2 LP（`lightplugin/`，HEAD `62a596125c…`）3 个落点

| # | 落点（远端名实测） | 推送动作 | 预期输出 | 失败模式 | 复核命令 |
|---|---|---|---|---|---|
| 4 | **github**（`github.com/skywalk163/lightplugin`） | 经 tree_sync 上传（原样字节；**占位** T4） | API 2xx；远端 ref 出现 | 401；tree 不等价 | GitHub API ref 存在 + `tree.sha` == 本地 `^{tree}` |
| 5 | **gitcode**（`https://gitcode.com/skywalk163/lightplugin.git`） | GitCode API 创建 ref（**占位** T4） | HTTP 201 | 401；ref 已存在 | GitCode API tags → **HTTP 201 即成功**，含 `<TAG>` |
| 6 | **gitea**（`http://skywalk@192.168.1.5:3000/skywalk/lightplugin.git`） | `git push gitea <TAG>` | `* [new tag]`，rc=0 | `[rejected]`；认证拒绝 | `git ls-remote gitea "refs/tags/<TAG>^{}"` == 本地 commit |

### 9.3 LM（`light-merge/`，HEAD `a495bb44c4…`，发布仓）4 个落点

| # | 落点（远端名实测） | 推送动作 | 预期输出 | 失败模式 | 复核命令 |
|---|---|---|---|---|---|
| 7 | **github**（`github.com/skywalk163/light`） | 经 tree_sync 上传（原样字节；**占位** T4） | API 2xx；远端 ref 出现 | 401；tree 不等价（此仓为发布母仓，CRLF 回归影响最大） | GitHub API ref 存在 + `tree.sha` == 本地 `^{tree}` |
| 8 | **gitcode**（`https://gitcode.com/skywalk163/light`） | GitCode API 创建 ref（**占位** T4） | HTTP 201 | 401；ref 已存在 | GitCode API tags → **HTTP 201 即成功**，含 `<TAG>` |
| 9 | **origin = 本地**（`g:\github\light`）⚠️ **不是任何托管平台** | `git push origin <TAG>` | `* [new tag]`，rc=0 | 本地裸仓不存在 / 路径错 | `git ls-remote origin "refs/tags/<TAG>^{}"` == 本地 commit |
| 10 | **gitea**（`http://skywalk@192.168.1.5:3000/skywalk/light.git`） | `git push gitea <TAG>` | `* [new tag]`，rc=0 | `[rejected]`；认证拒绝 | `git ls-remote gitea "refs/tags/<TAG>^{}"` == 本地 commit |

> **统一铁律（每条推送后必做）**：① 复核**逐项**执行，10 项全绿才进入下一步；② git 协议落点用 ls-remote、github/gitcode 用 API，**互不替代**；③ 任何一项复核失败 → 停 → 读 §十 回滚预案，不继续推剩余落点。

## 十、回滚预案（按失败类）

| 失败类 | 可回滚？ | 动作 | 验证回滚完成 |
|---|---|---|---|
| **① tag 推错远端**（ref 出现在错误的仓/平台） | ✅ 可（该 ref 在本轮前不存在时） | 删除误推 ref 即可：git 落点 `git push <remote> :refs/tags/<TAG>`；API 落点 DELETE ref。**先确认远端本轮前无此 ref**（ls-remote/API 查证），**绝不删除早已存在的同名 tag** | `git ls-remote <remote> "refs/tags/<TAG>"`（API 落点 GET）→ ref 已不存在 |
| **② 推了错误的 commit**（tag 指向错 commit） | ⚠️ 分情况 | **远端已推** → **不可改写**，只能发新 tag（如 `<TAG>-errata` 或下一号 rc）并更新引用；**未推/刚误推且无他人拉取** → 删 ref + 本地 `git tag -d` 重打重推 | 删后 `ls-remote` ref 消失；重推后 `rev-parse <TAG>^{commit}` 全链一致 |
| **③ github tree 与本地不等价（CRLF 回归）** | ✅ 可 | **不改 tag**（铁律）；用 tree_sync 按**原样字节**重推修复后的 tree（脚本已入库 `lightharness/_push_github_tree_sync.py`，Day12 §8.1 反跑已证：归一必不等价、原样必等价） | API `tree.sha` == 本地 `git rev-parse <TAG>^{tree}` |
| **④ PyPI 版本已占用** | ❌ 通常**不可回滚** | PyPI 已发布版本**不可撤回**：只能 **yank**（标记为不推荐）或发**补丁号**（如 rc2 被占 → rc3 / 0.4.0 正式版）。VSCE 同理（Marketplace 版本不可覆盖，只能递增） | `python -c "…pypi.org/pypi/lightgm/json…['info']['version']"` 确认线上版本；yank 后在 PyPI 网页确认状态 |

> 铁律重申：**不移动已推 tag**（任何回滚都不得改写已推送的 tag ref 内容）；PyPI 无撤回语义，发布前用 `--test`（TestPyPI）干跑（Day11 §5.2）。

## 十一、发布前检查单（一页，等示意时照着跑）

> 顺序执行，每步「通过判据 + 不通过怎么办」；**任一步不通过即停**，修复/回报后再从该步续跑。

| # | 步骤 | 通过判据 | 不通过怎么办 |
|---|---|---|---|
| 1 | **校验发布物 ref 是否包含 T1/T2（硬性第一步）**：`git -C lightharness log --oneline -1 <TAG>^{commit}`（或先确认 `<TAG>` 指向 T1/T2 合流后的 commit） | `<TAG>` 指向的 commit 是 **T1（LP-D-010）与 T2（LP-D-013）收口之后**的 commit（git log 能看到两处修复/重生成提交） | **停下并回报**：你要推的是修复前基底。等 T1/T2 收口后重打 `<TAG>` |
| 2 | 三仓工作树干净 | `git status --porcelain` 三仓均无行首 `M`（`??` 允许） | 先 commit/stash 已跟踪改动，再继续 |
| 3 | `<TAG>` 已打且 == HEAD | 三仓 `rev-parse <TAG>^{commit}` == `rev-parse HEAD` | 按 §8.3 重打（未推送时可 `git tag -d` 重打） |
| 4 | **T4 预检结论到位**（引用同批 T4 报告）：token 三件套就绪 / github+gitcode 逐项 API 可达 / 本地一致性 | T4 报告含「<TAG> 机制干跑绿」且无未决 blocker | **不许默认通过**：等 T4 收口；T4 未完成则停在此步 |
| 5 | 发布前置就绪（Day11 §一）：`dist/` 已构建（K6）、`release_preflight.py` 全 ✅、密钥清单（§二）用户侧已配 | preflight 无 ❌ 阻断项；M1/M2 已配 | 按 §五 5.1 先构建；密钥缺口回报用户 |
| 6 | 10 落点逐项推送（§九） | 10/10 均到「预期输出」 | 失败项按 §十 回滚预案处置后重试该落点 |
| 7 | 10 落点逐项复核（§九复核命令） | 10/10 复核全绿（API 落点 HTTP 201 / ref 存在 + tree 等价；git 落点 ls-remote SHA 一致） | 复核不过 → 按 §十：①/②/③ 处置；④ 只影响 PyPI 步（本单第 8 步） |
| 8 | 触发发布动作（引用，**不重写** Day11 §5.2–5.4）：PyPI（`publish_pypi.py --test` 先干跑 → 正式）、VSCE（`vsce publish`）、GitHub Release/exe/文档站 | 各端发布流程触发成功、无 401/版本冲突 | 按 §十 ④；TestPyPI 干跑失败先修链路，不直接碰正式库 |
| 9 | 发布后复核（Day11 §5.4） | PyPI JSON version == `<TAG>`；Marketplace 页面可访问；Release 已生成 | 差异逐项排查：版本占用走 §十 ④，其余回到对应步骤修复后重发（补丁号） |

> 完成 9 步后：向用户回报「发布完成 + 10 落点复核表 + 四件套」；**未得示意不自动执行本单任何 push/打标动作**（T8 由用户授权触发）。
