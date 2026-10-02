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
