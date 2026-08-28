# 第13轮 lightharness · L-018 闭环 + 收口 + 回归门禁 —— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`（独立 git 仓库）
> 承接：第 12 轮登记 L-018 并移交；语言团队按移交报告 §6 完成 lightharness 侧松绑（工作区未提交）。
> 本轮：接手验证、补全回填、新建回归门禁、收口遗留文档，一次性提交闭环。
> 日期：2026-08-28

---

## 1. L-018 闭环（语言团队松绑 → 验证转绿 → 状态回填）

### 1.1 语言团队已执行（工作区未提交，本轮接手）
| 项 | 改动 |
|---|---|
| `运行.py` | 导入钩子 `install([STDLIB, ROOT, SRC])` → `install([SRC, STDLIB, ROOT])`（**用户代码目录优先**，对齐 Python sys.path 语义，正是 T12 建议方向） |
| `src/重试策略.light` → `src/重试.light` | 恢复任务书正式名（头部注释已写明 L-018 修复） |
| `src/异步代理.light` | `从 重试策略 导入` → `从 重试 导入` |
| `examples/test_异步代理.light` | `从 重试策略 导入` → `从 重试 导入` |
| `examples/test_L018.light` | 重写：`从 重试 导入 退避间隔, 造策略`，断言修复后() 已启用 |

### 1.2 本轮验证（全绿）
- `python 运行.py examples/test_L018.light` → **rc=0，「测试L018 通过」**（用户侧符号 退避间隔/造策略 均命中 src/重试.light，断言通过）
- `python 运行.py examples/test_异步代理.light` → 全部通过（含重试/超时/工具链）
- **全量 examples 63 用例 0 红**（含转绿的 test_L018）
- 重名核查：src∩stdlib 仅 `重试` 一个重名（正是 L-018 场景），SRC 优先后无其它模块被改命中；`stdlib/重试.light` 已无任何代码引用（其符号 退避秒/判断可重试/重试 无使用点），无破坏

### 1.3 状态回填（本轮完成）
| 文档 | L-018 状态 |
|---|---|
| `语言缺陷账.md` | 新发现 → **已修复（2026-08-28；导入解析器改为用户目录优先）** |
| `编译器缺陷验收判据.md` | 红 → **绿（已修复，用户目录优先）** |
| `反跑判据.md` | 红（新登记） → **绿（已修复）** |
| `tests/test_回归.py` | test_L018 从「预期红」清单移除（转绿计入全量） |

---

## 2. 收口遗留

| 项 | 内容 |
|---|---|
| `对标清单.json` 条目7 | 第 11 轮改名（协程代理→异步代理）连带：`光明模块` 与证据路径中 `src/协程代理.light` → `src/异步代理.light`（JSON 校验通过） |
| `README.md` | 修复 `G:\dsword\` → `G:\dswork\` 路径笔误；src 目录结构由过时子目录描述改为实际扁平布局；运行命令 `src/主程序.light` → `src/总入口.light`；新增「回归门禁」章节 |

---

## 3. 新建回归门禁（tests/）

`tests/test_回归.py`（pytest）：
- 扫描 `examples/*.light`（排除 `_helper_*` 载体），逐用例跑 `python 运行.py` 断言退出码
- 「预期红」清单机制：未修复缺陷判据显式登记（当前为空——L-001~L-018 全绿）
- 一致性守卫：预期红清单与豁免清单必须同步，登记文件必须存在
- **实测：`python -m pytest tests/ -q` → 65 passed（82s）**

意义：lightharness 自此有可重复的自动化门禁，语言团队/后续轮次改动后一键回归，契合第十轮「反跑判据」口径。

---

## 4. 已知遗留 / 边界

1. `stdlib/重试.light` 仍是语言标准库纯光明模块（保留），lightharness 侧无引用；若语言团队后续想删，需确认 light-merge 标准库自身无使用者。
2. 对标清单中条目 2/9/10 的「描述性证据」（如 `src/会话.light 的 整理消息/压缩替换`）带功能说明后缀，`os.path.exists` 不直接命中，属原设计风格，未改动。
3. 平台：Windows 本机实测；POSIX 分支未实测（与项目既有惯例一致）。
4. README 目录结构改为扁平实际布局，但原版包对照仍以 `docs/功能对标/对标清单.json` 为准。

---

## 5. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_L018.light      # L-018（已修复，绿）
python 运行.py examples/test_异步代理.light   # 异步代理（从 重试 导入 造策略/带重试，绿）
python -m pytest tests/ -q                    # 回归门禁（65 passed）
```
