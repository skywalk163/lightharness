# Day3 凌晨 T3 · 版本号 rc1→rc2 归位 + preflight 锚点去硬编码

> 派单：`Day3凌晨_派单表.md` v1.0 · T3（B 线，发布）
> 执行时间：2026-10-03 06:4x–06:5x（CST，+08:00）
> 出口 tag：`subtask-T3-done`

---

## 〇、结论速览

| 验收项 | 结果 |
|---|---|
| 四处版本串 rc1 → rc2 | ✅ `src/version.py` / `pyproject.toml` / `vscode-extension/package.json` / `CHANGELOG.md` |
| preflight 锚点去硬编码 | ✅ 由写死的 `0.4.0rc1` 改为**读本地最新 `v*` tag** |
| version 单源门禁 | ✅ `tests/unit/test_version_single_source.py` **9/9 passed** |
| preflight | ✅ **12 ✅ / 0 ❌ / ⚠️3（GH 侧人工项）**，且「版本号与最新 tag 对齐」现为**显式绿条目** |
| 产物名 | ✅ `lightgm-0.4.0rc2-py3-none-any.whl` + `lightgm-0.4.0rc2.tar.gz`，`twine check` 双 PASSED |

---

## 一、改了什么

| 文件 | 改动 |
|---|---|
| `src/version.py:16` | `VERSION_NAME` = `v0.4 国庆发布候选版（rc1）` → **（rc2）** |
| `pyproject.toml:7` | `version = "0.4.0rc1"` → **`0.4.0rc2`** |
| `vscode-extension/package.json:5` | `"0.4.0-rc1"` → **`0.4.0-rc2`** |
| `CHANGELOG.md` 顶条 | 标题与打包后缀说明改为 rc2，并记下本次归位的原因 |
| `scripts/release_preflight.py` | 新增 `_latest_release_tag()`；第 7 项检查由「对比写死的 rc1 锚点」改为「对比本地最新 `v*` tag」，并在对齐时**显式输出一条绿条目**（原来只在不对齐时才出条目，对齐时静默） |

`git status --porcelain`：6 个 `M`（含 workflow），无新增跟踪外文件（除 `?? logs/`）。

---

## 二、⚠️ 一个必须记下的坑：本仓有两条 tag 血脉

第一版 `_latest_release_tag()` 我用的是 `git tag -l 'v*' --sort=-v:refname`（按版本号倒序），
结果取到的是 **`v7.0.0`** —— 那是合并前遗留的旧号段，实际比 0.4.0 家族更老：

```
--sort=-v:refname      → v7.0.0 / v6.3.0 / v6.2.0-rc1 / v6.1.0 / v6.0.0
--sort=-creatordate    → v0.4.0-rc2 / v0.4.0-rc1 / v0.3.0 / v7.0.0 / v6.3.0
```

按版本号倒序会把一条**早已停用的旧线**当成「最新发布」，
于是「版本是否与最新 tag 对齐」这条检查会永远红、且红得莫名其妙。
已改为 **`--sort=-creatordate`**（按创建时间倒序），并把这段理由写进函数 docstring，
免得后人再"优化"回 `-v:refname`。

---

## 三、验证三件套

| 验证 | 命令 | 结果 |
|---|---|---|
| 版本号单一真源门禁 | `pytest tests/unit/test_version_single_source.py -v -o "addopts=" --timeout=120` | **9 passed in 0.84s**（含 `test_pyproject_与真源一致`、`test_CHANGELOG_最新条目等于真源`、`test_所有对外可见版本串等于真源`） |
| preflight | `python scripts/release_preflight.py` | **本地可核查 12 ✅ / 0 ❌**；关键区现含 `✅ 发布版本号与最新 tag v0.4.0-rc2 对齐` |
| 重新构建 | `python scripts/build_release.py` | `lightgm-0.4.0rc2-py3-none-any.whl`（2055449 B）+ `lightgm-0.4.0rc2.tar.gz`（2389991 B），`twine check` **双 PASSED** |

**产物名确认**：上一批是 `lightgm-0.4.0rc1-*`（rc2 的 tag 编出 rc1 的包号），
**本批已经是 `lightgm-0.4.0rc2-*`** —— 上一批 T3 记的那笔账销掉了。

---

## 四、为什么不动 `VERSION` 本身

`src/version.py` 的 `VERSION = "0.4.0"`（major/minor/patch = 0/4/0）**没动** ——
它是"要发的正式版号"，`rc` 只是预发布后缀，归位只动后缀与展示名。
正式 `0.4.0` 槽位仍然空着，等发正式版时用。

---

## 五、出口判据回看

| 判据 | 达成 |
|---|---|
| 四处版本号改完 | ✅ §一 |
| version 单源门禁绿 | ✅ 9/9 |
| preflight 仍无 ❌ | ✅ 12✅/0❌（比上一批还多一条显式绿） |
| 产物名为 rc2 | ✅ `lightgm-0.4.0rc2-*` |
