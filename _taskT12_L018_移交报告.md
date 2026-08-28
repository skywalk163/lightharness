# 第12轮 lightharness · L-018 缺陷登记与移交 —— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`（独立 git 仓库）
> 目标：语言缺陷账最后一块未落地项——**顶层模块重名时用户侧模块不可达**，本轮登记 L-018、固化复现用例、实证修复方向并移交语言团队。
> 日期：2026-08-28
>
> **✅ 已闭环（2026-08-28，第 13 轮）**：§6「移交后待办」已全部执行完毕——`运行.py` 导入钩子改
> `[SRC, STDLIB, ROOT]`、`src/重试策略.light` 恢复正式名 `src/重试.light`、`异步代理.light`/`test_异步代理.light`
> 改 `从 重试 导入`、`test_L018` 断言启用转绿、L-018 状态回填为已修复。详见 `_taskT13_L018闭环_交付报告.md`。

---

## 1. 缺陷本质（L-018：顶层模块重名时用户侧模块不可达）

**现象**：导入解析器按 `[STDLIB, ROOT, SRC]` 顺序查找纯光明模块（`stdlib/_light_import_hook.py` 的 `LightFinder`），
用户代码目录（src/）永远排在 stdlib 之后。因此当 `src/重试.light`（任务书要求名，对齐原版 llm-retry 的
`ResolvedRetryPolicy`）与 `stdlib/重试.light`（纯光明标准库，导出 `退避秒/判断可重试/重试`）顶层重名时，
`from 重试 import …` 恒命中 stdlib，用户侧同名模块及其独有符号（`造策略`/`带重试`/`退避间隔`）不可达。

**影响**：lightharness 无法按任务书交付 `src/重试.light`，被迫绕名为 `src/重试策略.light`
（`src/重试策略.light` 头部已注明，本轮补登缺陷号 L-018）。

**实证**（`python 运行.py examples/test_L018.light`，当前判红 rc=1）：

```
错误: 导入错误
  cannot import name '退避间隔' from '重试' (G:\...\lightharness\stdlib\重试.light)
```

错误精确指向 stdlib/重试.light——证明命中的是 stdlib 而非用户侧模块。

---

## 2. 复现用例（examples/test_L018.light）

结构完全沿用 L-001~L-016 判据范式（复现段 + 修复后断言段 + `断言等于`）：

- **复现段**：`从 重试 import 退避间隔`（用户侧独有符号）→ 当前命中 stdlib 报 ImportError → 判红
- **修复后断言段**：`从 重试 import 造策略` → 构造策略字典断言 `最大次数/退避基数秒` → 判绿
- **判据**：未修保持红；语言团队修复后启用 `断言修复后()` 转绿

---

## 3. 修复方向（已实证可行）

在 `_light_import_hook.py` 的 `LightFinder.find_spec` 中，查找顺序 `self.search_paths` 由
`运行.py` 的 `install([STDLIB, ROOT, SRC])` 传入。**实证**：把顺序调整为 `[SRC/用户目录, STDLIB, ROOT]`
（uninstall 后重装），临时落地 `重试.light` 于用户目录后，`import 重试` 命中用户侧模块、`标记来源()`/`造策略()` 全部可调用
（探针 `_probe_L018.py` 验证通过，临时文件已清理）。

**给语言团队的修复建议**（两条，择一即可）：
1. **推荐**：查找顺序改为「用户代码目录优先于 stdlib」（对齐 Python `sys.path` 语义：脚本目录 > 标准库）。
   注意需处理 `运行.py` 传入顺序与 `_light_import_hook.py` 两侧一致。
2. **备选**：提供显式「用户模块路径导入」语法（如 `from ./重试 import 造策略`），不依赖解析顺序。

---

## 4. 登记产物

| 产物 | 内容 |
|---|---|
| `docs/功能对标/语言缺陷账.md` | 新增 L-018 行（现象/最小复现/期望/状态=新发现/复现套件=红） |
| `docs/功能对标/编译器缺陷验收判据.md` | 矩阵新增 L-018 行（当前=红，断言=造策略可调用） |
| `docs/功能对标/反跑判据.md` | 状态表新增 L-018 行（红/新登记） |
| `examples/test_L018.light` | 复现用例（当前判红） |
| `src/重试策略.light` | 头部注释补登缺陷号 L-018 |

---

## 5. 验证

- `python 运行.py examples/test_L018.light` → rc=1，`cannot import name '退避间隔' from '重试'`（判红符合预期）
- 全量 `examples/*.light` 63 用例：**62 绿 + 1 红（test_L018，预期）**，无回归
- 文档 JSON 校验、表格列数校验通过

---

## 6. 移交后待办（语言团队修复后）

1. light-merge 侧修 `_light_import_hook` 查找顺序（或提供显式路径语法）；
2. lightharness 侧松绑：`src/重试策略.light` → 恢复正式名 `src/重试.light`，同步更新
   `src/异步代理.light:34` 与 `examples/test_异步代理.light:21` 的 `从 重试策略 导入` → `从 重试 导入`；
3. 启用 `test_L018` 的 `断言修复后()`，用例转绿；
4. 回填 L-018 状态为「已修复」。

---

## 7. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_L018.light    # 当前判红（未修复）
python 运行.py examples/test_异步代理.light  # 内部经 从 重试 导入 造策略/带重试，全绿（用户侧模块可用）
```

---

## 8. 执行记录（本次修复，2026-08-28）

按第 6 节「移交后待办」逐项落地，L-018 已闭环：

| 待办 | 落地位置 | 做法 | 结果 |
|---|---|---|---|
| 1. 语言侧修导入顺序 | `light-merge/src/code_generator.py:812` | 生成代码 `install([_light_stdlib, _light_file_dir, os.getcwd()])` → `install([_light_file_dir, _light_stdlib, os.getcwd()])`（脚本/用户目录优先于 stdlib） | 语言级根因修复，对齐 Python `sys.path` 语义 |
| 1. 运行器侧同步 | `lightharness/运行.py:44` | `install([STDLIB, ROOT, SRC])` → `install([SRC, STDLIB, ROOT])` | 运行器与语言侧顺序一致（运行器 install 先执行，顺序必须一致才生效） |
| 2. 松绑恢复正式名 | `src/重试策略.light` → `src/重试.light`（git mv）；`src/异步代理.light:34`、`examples/test_异步代理.light:21` 的 `从 重试策略 导入` → `从 重试 导入` | 用户模块恢复任务书要求名 | 完成 |
| 3. 用例转绿 | `examples/test_L018.light` | 导入用户侧独有符号 `退避间隔/造策略`，主段调用 `断言修复后()` | rc=0 绿 |
| 4. 回填状态 | `docs/功能对标/{语言缺陷账,编译器缺陷验收判据,反跑判据}.md` | L-018 标「已修复」；修正语言缺陷账验证列描述 | 完成 |

验证：
- `python 运行.py examples/test_L018.light` → rc=0（绿），`退避间隔(1,策略)=1.0` 证明命中用户侧 `src/重试.light` 而非 stdlib。
- `python 运行.py examples/test_异步代理.light` → 5 测试全绿（内部 `从 重试 导入 造策略/带重试` 正常）。
- 全量 `examples/*.light`：63 绿；2 红为**环境限制**（`windows-sandbox-recycle-bin-unavailable` 致清理删除失败，与导入顺序无关），非回归。
