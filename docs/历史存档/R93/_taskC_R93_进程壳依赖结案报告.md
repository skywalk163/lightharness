# R93-C · `进程.light` 壳 vs `进程.py` 真身依赖结案报告

> 轮次：R93-C ｜ 2026-09-24 ｜ 承接 R92 `_taskM_R92_收口报告.md` §7 遗留中的 R91-C 观察项
> 前置：A 路（杀树两用例结构解耦重写）已完成（`_r93/a_summary.txt`、`a_rerun_summary.txt`）
> 结论一句话：**R91-C 的机理判定是错的。真正原因是 `tests/conftest.py` 把 `contrib/` 插到 `sys.path` 最前，裸 `import 进程` 命中 `contrib/进程.py`（另一套真实现，有 `进程队列`/`进程锁` 但**没有** `当前进程PID`/`进程启动`）；`.light` 壳从未被加载。修法：conftest 换序为 stdlib 在 contrib 前，一行级最小改动，语法核心零改动。**
> 执行方式：纯本机（win32，light-merge/.venv），未 commit/push，未动远端。

---

## 1. 判据达成表

| 判据 | 状态 | 证据 |
|---|---|---|
| 壳真身依赖关系讲清楚（有代码证据） | ✅ | §3 一手取证链（探针 A~C + pytest 内 sys.path 打印 + 钩子源码引用） |
| 让 import 在最小子集下不再解析到空壳 | ✅ | `tests/_r93c_probe2_tmp.py`（已删临时文件）孤立跑 **5/5 绿**：进程/线程/配置/随机 裸 import 无预热即命中 stdlib 真身 |
| 有书面"切子集不支持"结论**或**已完成最小修复 | ✅（选了修复） | conftest 换序，见 §5 |
| 全量口径不劣化 | ✅ | stdlib 全套件 572 绿；HTTP服务端+分布式 16 绿；unit 原生腿 43 绿；`-n auto` 宽子集 588 绿（§6） |
| 语法核心零改动 | ✅ | 仅改 `tests/conftest.py`（10 行注释 + 2 行调序）；lexer/parser/codegen/import-hook **均未动** |

**结论：选「让 import 在最小子集下正确解析」路径，未走"切子集不支持"书面结案，也未引入模块加载器副作用。**

---

## 2. 背景（R91-C 原判定）

- 文件 `stdlib/进程.light` 只有 16 行 `导出 …` 声明（无实现），真身 `stdlib/进程.py`（447 行，`当前进程PID` 在 L172 且在 `__all__`）。
- R91-C 在 0.82 FreeBSD 上把 b2 批切出来跑，出现两条红：
  - `tests/test_stdlib_comprehensive.py::test_import`：`AssertionError: False is not true`
  - `tests/test_stdlib_comprehensive.py::test_process_pid`：`AttributeError: module '进程' has no attribute '当前进程PID'`
- R91-C 判定：`import 进程` 解析到的是**声明壳 stub**（无 `当前进程PID`），触发条件是"收集期预热把真进程模块预热进 sys.modules，缺预热文件的子集才命中壳"。
- 当时结论：这是测试切子集的组织问题、非产品缺陷，但一直没结案，挂在 R92 §7 观察项。

---

## 3. 一手取证链（推翻 R91-C 判定）

### 3.1 先看钩子源码：壳根本不会被加载

`stdlib/_light_import_hook.py` 的 `LightFinder.find_spec`（约 L200-238）逻辑：

```python
if _exists_exact(base, realname + '.py'):
    if not _is_pure_light(light_file):
        return None          # ← 同名 .py 存在且 .light 非纯光明 → 让位给 CPython
```

- `进程.light` 首两行是 `# 光明标准库 - 进程管理模块` / `#`，**不含「纯光明实现」魔数**（`_is_pure_light` 判 False）。
- 因此钩子对 `import 进程` 一律返回 `None`，CPython 的标准 `PathFinder` 直接加载 `stdlib/进程.py`。
- **结论：壳 `进程.light` 从未被加载过，"拿到壳"这个前提本身不成立。**

### 3.2 定位真正的解析目标：`contrib/进程.py`

用 `find` 全仓搜 `进程.light` / `进程.py`：

```
./stdlib/进程.light   (401 B, 16 行导出壳)
./stdlib/进程.py      (11858 B, 真身)
./contrib/进程.light  (2182 B, 纯光明实现：class 进程 / class 进程池 / class 进程队列 …)
./contrib/进程.py     (12264 B, 并发实现)
```

**关键**：`contrib/进程.py` 是一套**不同的真实现**，`__all__` 是：

```python
['当前进程标识', '父进程标识', '进程名称', 'CPU核心数',
 '执行系统命令', '执行命令列表',
 '进程', '进程池', '进程队列', '管道',
 '共享值', '共享数组', '进程锁', '并行处理']
```

它有 `进程队列`/`进程锁`（所以 R91-C 判定它"是壳 stub"不成立），但**没有** `当前进程PID`/`进程启动`/`进程运行`/`进程停止` 等 stdlib 管理 API——comp 的两个断言因此必红。

### 3.3 探针矩阵（决定性实验）

用 light-merge venv 跑 5 组探针（`_r93/c_reproduce.py`，已落盘）：

| 实验 | sys.path 顺序 | `import 进程` 落点 | `当前进程PID` |
|---|---|---|---|
| M1 | **复刻 conftest**（contrib 在 stdlib 前） | `contrib\进程.py` | **False** ❌ |
| M2 | 复刻 conftest + 先 `import 进程` 预热 + 再插 stdlib 到 sys.path[0] | 仍是 `contrib\进程.py`（**命中缓存**，插 stdlib 无效） | **False** ❌ |
| M3 | 复刻 conftest + **先**插 stdlib 到 sys.path[0] 再 import | `stdlib\进程.py` | True ✅ |
| M4 | 仅 stdlib 在 path（无 contrib） | `stdlib\进程.py` | True ✅ |
| M5 | stdlib 在 contrib 前 | `stdlib\进程.py` | True ✅ |

- M1：**conftest 顺序（contrib 在前）下裸 `import 进程` 必命中 contrib 实现 → comp 必红**。
- M2：一旦某个文件先 `import 进程`（contrib 版入 `sys.modules`），之后 comp 即使把 stdlib 插到 `sys.path[0]` 也**无效**（Python `import` 命中缓存）——这正是 R91-C 说的"预热"，但预热的是 **contrib 版**而不是"真身"。
- M3：只有**首次** `import 进程` 前 stdlib 已在路径最前，才能解析到 stdlib 真身。

### 3.4 pytest 内实抓 sys.path 顺序

在 pytest 进程内（`conftest.py` 生效后）打印：

```
旧序：['...\tests', '...\src', '...\contrib', '...\stdlib', '...\tools', ...]
        ↑ __file__ = ...\contrib\进程.py  has 当前进程PID=False
新序：['...\tests', '...\src', '...\stdlib', '...\contrib', '...\tools', ...]
        ↑ __file__ = ...\stdlib\进程.py  has 当前进程PID=True
```

铁证：`conftest.py` 的 `sys.path.insert(0, _contrib_dir)` 是**最后一条** insert，于是 `contrib` 成了 `sys.path[0]`，覆盖 `stdlib`。

### 3.5 全量为什么绿？——预热掩盖

`test_stdlib_comprehensive.py` 自己（L17-18）会 `sys.path.insert(0, stdlib_path)`，且全量 `tests/` 里多个文件（如 `test_stdlib_phase3.py`、`test_stdlib_third_party.py`）在 conftest 加载后就 `from 进程 import …`。**首次** import 若发生在这些文件里且此时 stdlib 已在路径最前，则 stdlib 版进 `sys.modules`，comp 后续 import 命中缓存 → 绿。R91-C 切 b2 子集时恰好缺少这些"先 import 且路径已修正"的文件，contrib 版先入缓存 → 红。

---

## 4. 修复方案选择

任务书给了两选一：
1. 若能让壳在 import 时就正确 re-export 真身，做最小改动；
2. 若动它要碰 light 模块加载机制（风险大），书面结案"切子集不支持"。

**本路选 1，且改动比预期更小**——因为真因不在 `.light` 壳本身，而在 conftest 的路径顺序。修 conftest 让裸 import 落回 stdlib，**完全不触碰** `_light_import_hook.py` 或 `进程.light`，语法核心零改动、零导入副作用风险。

### 修法：`tests/conftest.py` sys.path 换序

原：

```python
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _tools_dir)
sys.path.insert(0, _stdlib_dir)
sys.path.insert(0, _contrib_dir)   # ← 最后 insert → 成为 sys.path[0]
```

新（`R93-C-PATH-ORDER` 哨兵）：

```python
sys.path.insert(0, _project_root)
sys.path.insert(0, _src_dir)
sys.path.insert(0, _tools_dir)
# [R93-C-PATH-ORDER] 顺序调整：stdlib 必须先于 contrib 入 sys.path。
# （注释说明真根因与影响面，见 §3）
sys.path.insert(0, _contrib_dir)
sys.path.insert(0, _stdlib_dir)    # ← 最后 insert → stdlib 成为 sys.path[0]
```

要点：
- **`from contrib.X import …` 不受影响**：`contrib` 在 `sys.path` 里仍是包目录，显式 `from contrib.HTTP服务端 import …`（如 `test_stdlib_phase8.py`）走包路径，与裸 import 不同。
- **`stdlib` 内部模块**不受影响（stdlib 的 `.py` 之间没有裸 import 同名模块，已 `grep` 验证）。
- **`contrib` 内部模块**不受影响（同样验证无裸 import 同名模块）。
- **纯光明 stdlib 模块**（`HTTP服务端` 等）由 `_light_import_hook` 编译加载，钩子对 stdlib 目录优先，不受路径顺序影响。

---

## 5. 换序安全性核查（换序前静态分析）

stdlib 与 contrib 有 9 个同名模块：`HTTP服务端`、`数据验证`、`线程`、`网络请求`、`进程`、`配置`、`随机`（另 `__init__`/`__pycache__`）。逐模块 AST 解析 API 差集，结论：

- **测试通过裸 import 使用「contrib 独有 API」的处数 = 0**（用 AST 遍历 tests/ + unit/ + src/ 全部 `from X import A` 与 `import X as m; m.A` 两种形态）。
- 关键同名模块 stdlib 版已覆盖测试所需全部属性：`进程`/`线程`/`网络请求`/`随机`/`数据验证` → stdlib 缺失 = 空。
- **唯一例外**：`HTTP服务端` 的 `HTTP服务端`/`处理循环`/`发送字节`/`连接中断`/`新建选择器` 在 stdlib 侧只有纯光明 `.light`（486 行，无 `.py`），AST 无法解析其属性。但 `test_http_server_light.py` 与 `test_distributed_eval_light.py` 都在 import 前 `sys.path.insert(0, _STDLIB)` 且 `install([_STDLIB, _分布式])` 挂钩子，**不受 conftest 顺序影响**——实测这两文件换序后全绿。

---

## 6. 验证记录（一手）

全部用 light-merge venv，`-o addopts=` + `--basetemp=<仓内新目录>` + `CODEBUDDY_SAFE_DELETE_ENABLED=0`（坑 1 姿势）：

| # | 命令 | 结果 | 日志 |
|---|---|---|---|
| 1 | 裸 import 探针（`tests/_r93c_probe2_tmp.py`，进程/线程/配置/随机 无预热断言）孤立跑 | **5 passed**（终端直出，未落盘） | 临时探针已按红线清理 |
| 2 | stdlib 全套件（phase2~13 + comprehensive + complete + third_party）单进程 | **572 passed, 8 xfailed, 2 xpassed** | `_r93/c_verify_stdlib.log` |
| 3 | `test_http_server_light.py` + `test_distributed_eval_light.py` 单进程 | **16 passed** | `_r93/c_verify_http.log` |
| 4 | `tests/unit/test_原生腿_R11C_数据高级.py` + `test_原生腿_R13B_能力扩展.py` | **43 passed, 1 skipped** | `_r93/c_verify_unit.log` |
| 5 | stdlib 全套件 + HTTP + 分布式 `-n auto`（并发压力） | **588 passed, 8 xfailed, 2 xpassed** | `_r93/c_verify_nauto_wide.log` |
| 6 | 关键裸 import 8 文件 `-n auto`（comp/phase2~5/third_party/http_server/distributed_eval） | **170 passed, 6 xfailed, 2 xpassed** | `_r93/c_bareimport_nauto.log` |

对照：**换序前**，`tests/_r93c_probe_tmp.py`（裸 `import 进程`）+ `test_stdlib_comprehensive.py` 组合里，探针 `进程.__file__ = contrib\进程.py`、`has 当前进程PID = False`（§3.4 旧序行）。

> 说明：换序前该组合仍绿（27 passed），因为 comp 文件自身把 stdlib 插到 sys.path[0]（§3.5）。真正会红的是"某文件先裸 import 进程 之后 comp 才 import"的 b2 子集——探针 5/5 绿已直接证明换序后无预热也不再依赖预热，机理上彻底消除。

---

## 7. 产物与台账登记

### 7.1 代码改动

| 文件 | 改动 |
|---|---|
| `light-merge/tests/conftest.py` | sys.path 换序（stdlib 在 contrib 前）+ `R93-C-PATH-ORDER` 哨兵注释，`+10/-1` 行 |

**未动**：`stdlib/进程.light`、`stdlib/进程.py`、`stdlib/_light_import_hook.py`、`src/`、`contrib/`。
**未 commit/push**（按任务书红线，合流由 M 路统一）。

### 7.2 台账登记

`light-merge/tests/ci_environment_reds.txt` 新增「R93 销账登记」注释段（`#` 开头，判据脚本不解析）：

- **R91-C 观察项 → 销账**：真根因是 conftest 路径顺序导致裸 import 命中 contrib 实现，非壳 stub；已由 R93-C-PATH-ORDER 修掉，不再是 flaky。
- **W-12 / W-14**：记录 R93-A 已重写用例结构解耦（15 轮 0 假红），但最终销账判据交给 B 路（选定 worker 数后连续全量 judge 新增红=0），本路不越权。

### 7.3 落盘产物

| 文件 | 说明 |
|---|---|
| `_taskC_R93_进程壳依赖结案报告.md` | 本报告 |
| `_r93/c_reproduce.py` | 机理矩阵探针（M1~M5） |
| `_r93/c_verify_*.log` | §6 各轮验证日志 |
| `_r93/c_stdlib_suite.log` / `c_http_suite.log` / `c_b2_nauto.log` / `c_bareimport_nauto.log` | 换序中间过程日志 |
| `_r93/c_conftest.old.bak.py` | conftest 原序备份（便于对拍） |

---

## 8. 红线自查

| 红线 | 状态 |
|---|---|
| 不碰 light 模块加载器/编译器核心 | ✅ 仅改 conftest 路径顺序 |
| 不 commit/push | ✅ 全部留在工作区，交 M |
| 不能一行修就别为"修"而引入导入副作用风险 | ✅ 换序经静态 API 差集核查（contrib 独有 API 裸用 = 0）+ 多套件实测无回归 |
| 语法核心零改动 | ✅ |

## 9. 遗留与交接

- **M 路注意**：`tests/conftest.py` 是本机与 0.82 共用的 pytest 配置。换序修复在 0.82 同样生效（机理与平台无关，是 Python import 行为）。若 M 在 0.82 补跑全量，建议一并确认 `test_stdlib_comprehensive.py` 在 b2 子集场景已绿；本路未连 0.82（夜间降级判据：C 若没动 stdlib 可判不劣化——本路确实没动 stdlib，仅动 conftest）。
- **B 路前置**：A 已完成（`_r93/a_summary.txt` 类级 15 轮两杀树用例 0 假红；`a_rerun_summary.txt` 复跑 10 轮 0 假红），C 已完成，B 可开跑。