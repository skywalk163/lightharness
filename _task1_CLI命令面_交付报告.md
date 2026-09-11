# 第 7 轮任务 1 交付报告：CLI 命令面（dump-config / version / help / 未知命令）

- **任务单**：`G:\dswork\duan-light-merge\宿主逼近_第7轮_任务prompt分发.md`（第 42–84 行，任务 1）
- **代码库**：`lightharness`（HEAD `ab57e2b4`，并发推进中；本报告只覆盖任务 1 自有文件）
- **交付日期**：2026-09-11
- **结论**：✅ 全部完成。run 路径零行为变化，新增 dump-config / version / help / 未知命令分支，用例 5 项断言全绿，反跑判据 3/3 成立。

---

## 1. 改动文件（3 个，全部为任务 1 自有文件）

| 文件 | 性质 | 说明 |
|---|---|---|
| `src/总入口.light` | 修改（+144/-3 行） | 头注命令面声明、4 条新增 import、run 本体重命名、EOF 追加命令面调度 |
| `examples/test_CLI命令面.light` | 新增（110 行） | 5 项断言（版本号 / dump-config / help / 未知命令 / 调度与来源单元检查） |
| `_antirun_cli_cmds.py` | 新增（118 行） | 3 项反跑判据，字节级备份/恢复 |

**未改动**：`docs/功能对标/对标清单.json`、`docs/功能对标/语言缺陷账.md`（互斥：由路M 回填登记）。
`src/远端总线.light`、`_antirun_remotes_whitelist.py`、`examples/test_远端白名单.light` 等为并发任务（远端白名单）所有，非本次改动。

---

## 2. 上游对应表

| 上游（`apps/cli/src/args.ts` L1-25 + `dump-config.ts`） | lightharness 落点 | 实现状态 |
|---|---|---|
| launcher 只解析自己拥有的 flags，其余原样转交 booted 树内插件 | 头注「命令面」段 + 环境变量传参（规避与 `light run` argv 冲突） | ✅ 等价映射 |
| `DshInvocation` 三态：profile 引导 / dump-config / plugin | `段落 调度命令` 四态：`run` / `dump-config` / `version` / `help` | ✅ 等价映射 |
| `runDumpConfig`：打印组合配置树，**注释命名每个来源** | `段落 取配置文本`：每行标注「来源: 环境变量 / .env / 内置默认」 | ✅ |
| dump-config **不 boot、不 `!!js` eval** | 打印配置树即返回，不建客户端、不跑 agent、不读密钥 | ✅（用例②断言） |
| Cordis profile / patch 层系统 | 无对应语言面 | ⛔ 未映射，维持对标登记 |
| `!!js` 表达式求值 | 无对应语言面 | ⛔ 未映射，维持对标登记 |
| argv 子命令解析（`dsh dump-config`） | 光明无 argv 子命令 → `HARNESS_CMD` 环境变量 | ✅ 等价映射 |
| `version` 打印 | `设 版本号 为 "0.1.5-lh"`（对齐对标清单 0.1.5-rc.2，`-lh` 标识复刻分支） | ✅ |

### dump-config 输出字段（逐项带来源标注）

```
=== 当前生效配置（版本 0.1.5-lh） ===
子命令: run（来源: 环境变量 HARNESS_CMD，缺省 run）
命令根: <cwd>（来源: 运行时 当前目录()）
模型: deepseek-flash（来源: 内置默认 取默认模型()）      ← 链：环境变量 HARNESS_MODEL
                                                        ← → .env HARNESS_MODEL
                                                        ← → .env OPENAI_MODEL
                                                        ← → 内置默认 取默认模型()
模型单价表（美元 / 1M tokens，输入 / 输出；来源: 内置默认 令牌计量.单价表）
  deepseek-chat 0.27/1.10 … gpt-4o-mini 0.15/0.60
  未知模型 1.00/2.00（来源: 内置默认 令牌计量.缺省单价表）
压缩配置（来源: 环境变量优先，缺省 内置默认 压缩E5.压缩配置）
  阈值token: 8000（来源: 内置默认 8000）
  保留轮数: 6（来源: 内置默认 6）
  上下文窗口: 32768（来源: 内置默认 32768）
会话根: sessions（来源: 环境变量 HARNESS_ROOT，缺省 sessions）
未列字段: 端点与密钥不打印（HARNESS_ENDPOINT / DEEPSEEK_API_KEY / …）
未映射宿主面: profile / patch / plugin 层与 argv 子命令解析（Cordis 层系统），维持对标登记
```

---

## 3. 实现要点

1. **run 路径零行为变化**：原 `段落 主`（headless 主流程）整体重命名为 `段落 执行运行`，正文一字未改；新 `段落 主 接收 命令值=空` 只做子命令分派。缺省子命令 `run`，因此 `HARNESS_CMD` 未设时行为与改动前逐字节一致。
2. **来源标注独立成段落**，避免与 `解析模型` 的取值逻辑耦合：
   - `取模型来源(环境取值, 文件甲取值, 文件乙取值)` → 四态字符串常量，被用例⑥单元断言。
   - `取环境变量来源(目标键, 缺省文案)` → 压缩三参数复用，避免三份复制粘贴。
3. **不 boot**：`dump-config` 只读环境变量与 `.env` 明文值，不调用客户端构造、不触发 `有密钥/无密钥` 分支、不写会话根。
4. **未知命令非零退出**：`调度命令` 返回 `假`（打印「未知命令 + help 提示」），`主` 收到 `假` 即 `抛出` → 光明异常冒泡使进程非零退出。
5. **`命令值` 入参注入**：供测试免环境变量即可断言分派表（`主("bogus")` 断言抛错），不影响 CLI 调用形态。
6. **光明语法实证**：段落前向引用不可用（`name '执行运行' is not defined`）→ 命令面段落统一追加到 EOF，位于 `执行运行` 之后；顶层 `设` 语句在 `主()` 前执行，故 `版本号` / `缺省子命令` 可用。EOF 追加的段落内含 `否则如果` 链 + `抛出`，实测未触发 L-079（`_w3_probe/probe5.light`）。
7. **无 Python 绕行、无同名 `.py`**：全部功能落在 `.light`；`_antirun_cli_cmds.py` 是判据脚本（反跑工具），非功能实现。

---

## 4. 测试与回归

| 项 | 结果 |
|---|---|
| `examples/test_CLI命令面.light`（新增，5 项断言） | ✅ rc=0，`全部通过` |
| `examples/test_总入口.light` | ✅ rc=0 `test_总入口 PASS` |
| `examples/test_web路由.light` | ✅ rc=0 `--- 测试web路由(静态/CORS/认证) 通过 ---` |
| `examples/test_入口默认模型.light`（第 5 轮） | ✅ rc=0 `全部通过` |
| `examples/test_联调CLI.light` | ✅ rc=0 `=== test_联调CLI PASS ===` |
| `examples/test_令牌计量.light` | ✅ rc=0 `--- E5 令牌计量测试通过 ---` |

**CLI 冒烟（`examples/运行CLI.light`，cwd=`_w3_probe`，无 `.env`）**：

| 调用 | rc | 输出要点 |
|---|---|---|
| 缺省（无 `HARNESS_CMD`） | 0 | 与改动前一致：`错误: 未提供 API 密钥` + 配置指引 → **run 缺省路径零变化** |
| `HARNESS_CMD=run` | 0 | 与缺省逐字节一致 |
| `HARNESS_CMD=dump-config` | 0 | 配置树 + 来源标注，未 boot、未提示密钥 |
| `HARNESS_CMD=version` | 0 | `0.1.5-lh` |
| `HARNESS_CMD=help` | 0 | 用法表 + 全部 `HARNESS_*` 参数表 |
| `HARNESS_CMD=bogus` | 1 | `未知命令: bogus` + `help 提示: …`（非零退出 ✅） |
| `HARNESS_LIST=1` | 0 | `--- 已有会话列表（根: sessions） ---` / `尚无会话（根目录不存在: sessions）` |

**全量 CI**：按互斥约定由路M 统一执行，本次只跑上述目标回归。

---

## 5. 反跑判据（`_antirun_cli_cmds.py`，3/3 成立）

| 项 | 翻转动作 | 断言 | 翻转后 | 恢复后 |
|---|---|---|---|---|
| A | `取模型来源` 兜底文案 `"内置默认 取默认模型()"` → `"内置默认"` | `test_CLI命令面` 应通过 | rc=1 ✅ 判据成立 | rc=0 ✅ 回绿 |
| B | `主` 未知命令分支 `抛出 …` → `打印 …`（退出码改 0） | 子进程 `HARNESS_CMD=bogus` rc≠0 | rc=0 ✅ 判据成立 | rc=1 ✅ 回绿 |
| C | `设 版本号 为 "0.1.5-lh"` → `"0.1.5"` | `test_CLI命令面` 应通过 | rc=1 ✅ 判据成立 | rc=0 ✅ 回绿 |

脚本以字节级读改写、`finally` 恢复源文件，不改动 git 状态；判据输出：`反跑判据全部成立：3/3 改反即红`（退出码 0）。

---

## 6. 未移植 / 留待后续

- **profile / patch / plugin 层**：Cordis 层系统，光明无对应语言面。已在头注、`dump-config`、`help` 三处声明「维持对标登记」。
- **argv 子命令解析**：光明入口 argv 归属 `light run`，改用 `HARNESS_CMD` 等价映射，已在 help 中标注。
- **`对标清单.json` 回填**：由路M 统一回填（任务 1 只读该文件取版本号与对标项）。
- **语言缺陷账**：本轮无新缺陷（L-079 未触发；段落前向引用与 argv 归属为已知设计约束，不在新增缺陷范围）。
- **并发风险提醒**：仓库 HEAD 在本轮内由 `4d1166b1` → `e1d7e95` → `ab57e2b4` 推进，`src/总入口.light` 由 282 行变为 292 行（他方新增内容）。本次改动基于最新 HEAD 的 EOF 追加方式落地，与他方改动的冲突面仅限文件追加位置；建议路M 全量 CI 时一并核对。

---

## 7. 移交清单（给路M）

- [x] `src/总入口.light`：命令面调度（`版本号` / `缺省子命令` / `取模型来源` / `取环境变量来源` / `取配置文本` / `取用法文本` / `调度命令` / `主`），run 本体迁为 `执行运行`
- [x] `examples/test_CLI命令面.light`：5 项断言，全绿
- [x] `_antirun_cli_cmds.py`：3 项反跑判据，全成立
- [ ] `docs/功能对标/对标清单.json`：回填任务 1 状态（dump-config / version / help / 未知命令 / 来源标注）
- [ ] 全量 CI 与 `语言缺陷账.md`（本轮无新增条目）
- [ ] 合并前核对 `src/总入口.light` 与并发远端白名单任务的行号衔接
