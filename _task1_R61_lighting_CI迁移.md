# 任务1 续 · R61 —— 积木库 CI 由 light-merge 迁入 lighting 仓

> 触发：用户指示「删掉 2 个纯积木库 CI 流水线，但是要在 lighting 项目里加上相应 CI 流水线」
> 前置：`_task1_R61_拆分提速量化.md`（light-merge 侧已删 `.github/workflows/eval.yml`、
> `.gitcode/workflows/eval.yml` 并移除 gitea 的积木库门禁 step）
> 本轮：**在 lighting 仓补齐三平台流水线**，并修掉迁移时暴露的 4 个拆分遗留缺陷
> 状态：**已提交 `c3161d6e`（19 files, +386/−56）**；**未 push**（lighting `main` 无上游配置，无 `-u` 不会误推）
> 已提交态复验：工作树 == HEAD 时复跑门禁 **24/24 全绿，rc=0**

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| lighting 新增流水线 | **3 条**（gitea `ci.yml` / github `eval.yml` / gitcode `eval.yml`） |
| 迁移暴露的拆分遗留缺陷 | **4 类**（编译器路径、三个「根」、体检 E8、索引样例路径）—— 全部已修 |
| 端到端验证 | **完整门禁 24/24 闸门全绿，rc=0，耗时 86.5s** ✅ |
| 修复前实测 | 首次跑：**门禁未通过（2 项）** —— 冒烟可运行率 0.9777 / 问题块数 4（随后归因修复） |

---

## 1. 为什么「直接搬过去」搬不动

lighting 仓根即原 `light-merge/积木库/`，于是**原流水线里所有 `积木库/xxx` 路径都要去掉一层**——
这是机械的。真正卡住的是三件不机械的事：

| # | 拦路点 | 证据 | 后果（若不修） |
|---|---|---|---|
| 1 | **编译器不在本仓** | `评估/冒烟.py` 硬编码 `os.path.join(_ROOT,'cli','light.py')`；而拆后 `_ROOT` = 工作区上级（`…/duan-light-merge`），`cli/` 在它下面没有 | 冒烟 151 块全报「无法运行」 |
| 2 | **「根」从 1 个变成 3 个** | 拆分前 `_ROOT` 一个变量同时充当「编译器根 / 运行 cwd / 工位落点」 | 修好 #1 后仍有块失败（见 §3.2） |
| 3 | **体检 E8 判据把空集当通过** | `评估/体检.py` `git ls-files -- 积木库/` 在拆后仓里恒为空集 → `git_rel not in 已跟踪` 对所有块成立 | E8 全量误报，体检恒红 |

第 3 条与 light-merge 侧的 `test_pure_light_hook.py` 是**同一类**（裸路径 → 空集 → 判据失真），
只不过一个表现为「假绿空转」、一个表现为「假红误报」。

---

## 2. 新增的三平台流水线（lighting）

| 文件 | runner | 编译器怎么来 | 关键差异 |
|---|---|---|---|
| `.gitea/workflows/ci.yml` | `freebsd`（act_runner host） | `git clone --depth 1 http://192.168.1.5:3000/skywalk/light.git` → `$HOME/.cache/light-compiler`（已有则 `fetch` 复用）；可用 `GITEA_LIGHT_URL` 覆盖 | checkout 走**本地镜像全 URL** `http://192.168.1.5:3000/actions/checkout@v4`（项目约定：裸写 `actions/checkout@v4` 会偶发回落 github.com）；pip 走本地 devpi，取不到时回退 pypi.org |
| `.github/workflows/eval.yml` | `ubuntu-latest` | `actions/checkout@v4` 跨仓 + `repository: skywalk163/light`、`path: _light` | 保留原 cron `0 1 * * *`；`paths` 过滤排除 `*.md`/`docs_site`/`archive`；artifact 上传 `评估/报告/` |
| `.gitcode/workflows/eval.yml` | `euleros-2.10.1` | 无跨仓 checkout → `git clone --depth 1 https://gitcode.com/skywalk163/light.git` | 沿用 `checkout-action@0.0.1` + `cd repo_workspace` 约定；保留「报告摘要」步 |

三者统一的关键约定：**用 `LIGHT_MERGE` 告诉脚本编译器在哪**，命令统一为
`python 评估/ci_eval.py --并发 8`（仓根执行、写 `评估/报告/ci_eval.json`）。

```
                                        ┌─ lighting/.gitea/workflows/ci.yml   (freebsd)
lighting（积木库仓，仓根=原 积木库/） ──┼─ lighting/.github/workflows/eval.yml (ubuntu)
                                        └─ lighting/.gitcode/workflows/eval.yml (euleros)
                    │
                    └─ LIGHT_MERGE ──▶ light-merge 检出（提供 cli/light.py + stdlib）
```

---

## 3. 为让流水线真能跑，lighting 侧改了什么

### 3.1 编译器定位（新增，向后兼容）

- `评估/冒烟.py` 新增 `_定位编译根()`：`LIGHT_MERGE` → `LIGHT_RUNTIME` → `_ROOT`（旧布局）→
  `_ROOT/light-merge`（同工作区同级检出）→ `_LIB`（拆分前布局）；都找不到返回 `None`，
  由 `跑()` **抛一条可读错误**，而不是 151 个块各报一次失败。
- `组合.py::_定位运行时()` 同样加 `LIGHT_MERGE`/`LIGHT_RUNTIME` + 同级 `../light-merge` 回退。
- 实测（本机）：
  | 场景 | `_编译根` / `_定位运行时()` |
  |---|---|
  | 不设 env（同工作区） | `G:\dswork\duan-light-merge\light-merge`（同级兜底命中） |
  | `LIGHT_MERGE` 显式 | 同上 |
  | `LIGHT_MERGE=G:/nope`（无效值） | 仍回退同级 → 同上（不因错值崩） |
  | 都不存在 | `RuntimeError: 找不到光明运行时…请设 LIGHT_MERGE…` |

### 3.2 ⚠️ 三个「根」必须分开（本轮最容易踩的一个）

拆分前只需一个 `_ROOT`。拆开后必须分成三个，**实测证据**（探针 `.light`：`从《文件系统》导入《文件大小》` + `打印 文件大小("评估/_冒烟样例.csv")`）：

| 工位文件位置 | 运行 cwd | 结果 | 解释 |
|---|---|---|---|
| light-merge 内 | light-merge | `获取文件大小失败 '评估/…': 系统找不到指定的文件` | stdlib ✓ / 数据路径 ✗（旧的相对路径语义） |
| **lighting 内** | lighting | `cannot import name '文件大小' from '文件系统' (unknown location)` | **stdlib ✗** —— 见下 |
| **light-merge 内** | **lighting** | **`38`** ✅ | stdlib ✓ + 数据路径 ✓ |

机制：`cli/light.py:266,343` 把**源文件所在目录**插到 `sys.path[0]`，stdlib 引导据此向上找
`stdlib/`；工位文件（内联块源码的临时 `.light`）写在 lighting 仓里，向上找不到 `light-merge/stdlib`
→ 解析成 namespace package（`unknown location`）。

于是 `评估/冒烟.py` 的常量拆成三个：

```python
_编译根   = _定位编译根()        # 跑哪个 cli/light.py
_工位目录 = _编译根 or _LIB      # 临时 .light 写哪（必须在编译器仓内）
# subprocess: [python, _编译根/cli/light.py, 'run', tmp], cwd=_LIB
#             ↑ 编译器等        ↑ 工位在编译器仓       ↑ 数据相对路径相对积木库根
```

### 3.3 体检 E8 判据

`评估/体检.py`：`git ls-files -- 积木库/` → `git ls-files -- .`
（拆后本仓根即原 `积木库/`）。修复前后实测：

| | 已跟踪集规模 |
|---|---|
| 修复前 | **0**（空集 ⇒ E8 全量误报） |
| 修复后 | **37042** |

### 3.4 `索引.json` 的样例路径（6 处）

4 个块的 `样例` 字段还写着拆前的路径（`读取CSV` / `读取文本文件` / `文件存在` / `文件大小` / `列目录文件` /
`写入文本文件` 共 6 处）：

```diff
- "样例": ["\"积木库/评估/_冒烟样例.csv\""]      →  "评估/_冒烟样例.csv"
- "样例": ["\"积木库/评估/_冒烟写.txt\"", "你好"] →  "评估/_冒烟写.txt"
- "样例": ["\"积木库/数据\""]                   →  "数据"
```

改法是**字节级替换**（不重新序列化），并按项目规矩先做无损往返自证：
`索引.json` 风格 = `ensure_ascii=False` + `indent=2` + CRLF + 无尾换行 —— **往返一致 True**，
改后复验仍 True、`积木库/` 残留 0。

### 3.5 其他

- `lighting/.gitignore` 增 `评估/_冒烟写.txt`、`_冒烟工位*.light`
  （拆分前靠 light-merge 的 `*.txt` 兜底，本仓 .gitignore 更窄 → 跑一次冒烟就多一个未跟踪文件）。
- `评估/*.py` 等 **12 个文件**的 docstring/用法示例里的 `积木库/评估/…`、`积木库/生成/…` 等
  过期路径机械清理（共 40 处；`py_compile` 全过，确认改的都是注释/文档串）。

---

## 4. 验证

### 4.1 本机端到端（就是 CI 跑的那条命令）

```bash
cd lighting && export LIGHT_MERGE="…/light-merge" && python 评估/ci_eval.py --并发 8
```

| 轮次 | 结果 |
|---|---|
| ① 修复前（冷） | **未通过 ✗（2 项）** 耗时 266.2s：`冒烟/可运行率 0.9777 < 1.0`、`冒烟/问题块数 4 > 0`（4 个块：读取CSV / 读取文本文件 / 列目录文件 / 文件大小） |
| ② 定点复跑（6 块） | 修复中 → 终态 **6/6 通过，可运行率 1.0000** ✅ |
| ③ **修复后全量（热）** | **全部通过 ✓，24/24 闸门，rc=0，耗时 86.5s** ✅ |

③ 的 24 项闸门（真实语料 4 / 扰动集 4 / 主基准 7 / 接线 3 / 体检 2 / 冒烟 2 / 兜底 2）全 ✓，
其中 `冒烟 可运行率 1.0`、`冒烟 问题块数 0`、`体检 错误数 0`、`体检 警告数 0`。

### 4.2 其他检查

| 检查 | 结果 |
|---|---|
| 3 个新 YAML `yaml.safe_load` | 全部合法（jobs/steps/on 结构读得出来） |
| light-merge 侧 2 个 YAML（改注释后） | 仍合法 |
| `评估/体检.py` 真跑 | `块总数 182　错误 0　警告 0　全部通过 ✓` |
| `py_compile` | 14 个改动/新增 Python 文件全过 |
| 临时产物 | 无残留（工位 `.light`、`评估/_冒烟写.txt` 已清；生成物 `评估/报告/ci_eval.json` 已 `git checkout` 还原） |

---

## 5. 与任务书/红线的偏差声明

| # | 偏差 | 说明 |
|---|---|---|
| 5.1 | **改动落在第三个仓（lighting）** | 任务书本轮口径是「两仓显式列文件提交」，本项由用户明确指示「在 lighting 项目里加 CI」，故 lighting 需要**单独一次 commit**（见 §6）。探针 `.workbuddy` 内存与报告仍按惯例放 light-merge 工作区/lightharness |
| 5.2 | 为跑通 CI，**改了 lighting 的 3 个运行期文件 + 1 个数据文件** | 非「顺手美化」：不改则流水线必红（§1 三条拦路点）。均向后兼容（不设 `LIGHT_MERGE` 时行为与拆前等价，只是路径少一层） |
| 5.3 | 「跨仓检出」可行性**未在真实 runner 上验证** | github 走 `actions/checkout` 跨仓（假定 `skywalk163/light` 公开/同 owner）；gitcode/gitea 走 `git clone`（假定公开）。两处都已写明私有仓的 token 兜底写法 |
| 5.4 | 本机缺 `pypinyin`/`lunardate`/`opencc` | 冒烟按「缺依赖」单列、不计入可运行率分母（v0.27 既定设计），故不影响本机门禁结论；CI 里会装 |
| 5.5 | `评估/报告/ci_eval.json` 被本机跑动过 | 已还原为 HEAD 版本，未纳入改动清单 |
| 5.6 | 未 commit / 未 push / 未跑 light-merge 全量 | 遵守全局护栏 |

---

## 6. 改动清单（lighting 仓，需单独提交）

### 6.1 新增（3 个流水线）

| 文件 | 行数规模 | 说明 |
|---|---|---|
| `.gitea/workflows/ci.yml` | 5 steps | freebsd runner；编译器 clone 到 `$HOME/.cache/light-compiler`；持久 venv `$HOME/.cache/lighting-ci-venv` |
| `.github/workflows/eval.yml` | 6 steps | ubuntu；跨仓 checkout `_light`；cron 每日 |
| `.gitcode/workflows/eval.yml` | 6 steps | euleros；`checkout-action@0.0.1` + `cd repo_workspace` |

### 6.2 修改（16 个路径）

| 文件 | 关键改动 |
|---|---|
| `评估/冒烟.py` | 新增 `_定位编译根()` / `_编译根` / `_工位目录`；subprocess 用 `_编译根/cli/light.py` + `cwd=_LIB`；`跑()` 加编译器缺失守卫；工位路径 `_LIB`→`_工位目录`（2 处）；usage 路径现代化 |
| `组合.py` | `_定位运行时()` 加 `LIGHT_MERGE`/`LIGHT_RUNTIME` + 同级 `../light-merge` 回退 + 报错文案 |
| `评估/体检.py` | E8：`git ls-files -- 积木库/` → `-- .`（+ 注释） |
| `索引.json` | 6 处 `样例` 路径去 `积木库/` 前缀（字节级替换，无损往返自证） |
| `.gitignore` | + `评估/_冒烟写.txt`、`_冒烟工位*.light` |
| `评估/{ci_eval,兜底待审,兜底跑分,兜底首跑,压测,安全审计,接线跑分,真实跑分,跑分}.py`、`demo/server.py`、`兜底生成器.py` | docstring/用法示例里的 `积木库/…` 过期路径（40 处，纯文本） |

### 6.3 提交记录（已完成）

**`c3161d6e`** `ci(R61): 积木库三平台流水线迁入本仓 + 修拆分遗留的编译器/根/体检/索引路径`
—— 19 files changed, 386 insertions(+), 56 deletions(-)

```
 .gitcode/workflows/eval.yml |  68 +++    .gitea/workflows/ci.yml    | 118 +++    .github/workflows/eval.yml |  81 +++
 .gitignore 5 | demo/server.py 2 | 兜底生成器.py 2 | 索引.json 12 | 组合.py 32
 评估/{ci_eval,体检,兜底待审,兜底跑分,兜底首跑,冒烟,压测,安全审计,接线跑分,真实跑分,跑分}.py
```

暂存方式：**显式列 19 个路径**，未用 `git add .`；R60 遗留的 3 个未跟踪探针
（`_r60_gh_view.txt`、`_r60_gitea_public_out.txt`、`_r60_make_public_out.txt`）**未纳入**本次范围。
提交前已确认工作树相对 HEAD 只有这 3 个未跟踪文件；提交后在同样的工作树上复跑门禁 → 24/24 全绿。

```bash
# 实际执行的暂存（留档）
git add .gitignore demo/server.py 兜底生成器.py 索引.json 组合.py \
  评估/冒烟.py 评估/体检.py 评估/ci_eval.py 评估/兜底待审.py 评估/兜底跑分.py 评估/兜底首跑.py \
  评估/压测.py 评估/安全审计.py 评估/接线跑分.py 评估/真实跑分.py 评估/跑分.py \
  .gitea/workflows/ci.yml .github/workflows/eval.yml .gitcode/workflows/eval.yml
# 未做：git push（lighting main 未设上游）
```

> ⚠️ R60 拆分提交 `be178387` 之后，lighting 仓此前**从未有过 CI**；这是它的第一条流水线。
> 建议 push 后先在 gitea 侧手动 `workflow_dispatch` 跑一次，确认 runner 上编译器 clone 与
> devpi 依赖可用（本机无法覆盖 runner 环境）。
> 三个远端都已配好（`gitea` / `github` / `gitcode`），但 `main` 未设上游，推送需显式指定，例如
> `git push gitea main`。
