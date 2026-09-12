# 路M 收口说明 —— 第12轮（6 域并行复刻：查询/投影/代理环境/回放/协议/审批）

> 日期：2026-09-12 ｜ 路：路M（收口执行者）｜ 仓库：`G:\dswork\duan-light-merge\lightharness`
> 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 任务书：`G:\dswork\duan-light-merge\复刻_第12轮_任务prompt分发.md`（6 并行 + 路M）
> 收口 commit 链：dbd6eac（任务1）→ 66a33e3（任务2）→ 8efa90e（任务3）→ 791bd01（任务4）→ 1b0ac67（任务5）→ 69c4430（任务6）→ 本收口 commit

---

## 一、六路修复统计

| 路 | 范围 | 新增模块 | 新增测试 | 反跑结果 |
|---|---|---|---|---|
| 任务1 | 会话查询域：cold-read + tool-session-query 纯逻辑 | `src/会话冷读.light` + `src/查询工具.light` | `test_会话冷读.light`（≥8 断言）+ `test_查询工具.light`（≥8 断言） | `_antirun_coldread.py` 2/2 PASS |
| 任务2 | 会话投影域：turn-outline + checkpoint-policy | `src/会话轮次大纲.light` + `src/检查点策略.light` | `test_会话轮次大纲.light`（13 组）+ `test_检查点策略.light`（6 组） | `_antirun_outline_ckpt.py` 3/3 PASS |
| 任务3 | 代理启动环境域：http-proxy policy + launch-environment | `src/代理策略.light` + `src/启动环境.light` | `test_代理策略.light`（≥10 断言）+ `test_启动环境.light`（≥6 断言） | `_antirun_proxy_env.py` 3/3 PASS |
| 任务4 | 测试支撑域：llm-replay 纯逻辑面 | `src/大模型回放.light` | `test_大模型回放.light`（65 断言） | `_antirun_replay.py` 3/3 PASS |
| 任务5 | 运行时协议域：code-runtime-python 协议层 | `src/代码运行时协议.light` | `test_代码运行时协议.light`（≥12 断言） | `_antirun_protocol.py` 3/3 PASS |
| 任务6 | 审批域：user-approval + tool-ask-user 对照收口 | 修改 `src/审批.light`（+172 行） | `test_审批对照.light`（D1~D10 断言） | `_antirun_approval.py` 3/3 PASS（CRLF 变异串字节级处理） |

**合计**：新增 src 模块 9 个，修改 src 模块 1 个（审批.light），新增测试 9 个，反跑脚本 6 个全部 PASS（共 17 项判据）。任务2 测试由路M 接手补齐（主() 调用 + PASS 打印 + 反跑脚本 + 交付报告），随 66a33e3 合入。

---

## 二、CI 终值

- 命令：`$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python scripts/ci_test.py`
- **终值：259 passed, 0 failed**（pytest 全量回归），smoke 5/5 通过。耗时约 626s（pytest）。
- 数字说明：第11轮 252 → 本轮 259。工作区 `examples/*.light` 第11轮基准 243 → 当前 257（新增 9 测试 + 6 `_repro_L085~L090` 修复形态，删除任务4 探针 `_probeG.light`）；CI 计数 = examples/*.light + tests 附加用例。
- **首次全量跑出现 1 失败（偶发，重跑确认）**：`test_审批.light` 用例12d「至少等0.2s」实测 0.1509s。路M 排查：① `等待结果` 段落未被任务6 改动（diff 仅新增 `轮询间隔` 属性，循环逻辑原样）；② 该测试单独跑/模拟 CI 临时目录跑/pytest 方式连跑/pytest 参数化连跑全部通过；③ 探针 60 次 `等待结果(id, 0.3)` 实测最短 0.21s、异常 0 次。判定为**环境性偶发（Windows 时钟回拨/负载时序）**，非任务6 回归；重跑全量 259 passed 0 failed 确认。

---

## 三、对标清单结论

文件：`docs/功能对标/对标清单.json`（79 → 85 条）

### 新增对标卡（#80 ~ #85）
| 编号 | 原版包 | 光明模块 | 状态 |
|---|---|---|---|
| #80 | session-query cold-read + tool-session-query | `src/会话冷读.light` + `src/查询工具.light` | done（纯逻辑面；宿主胶水 service-boundary/workspace-access 不移植） |
| #81 | session-turn-outline + session-checkpoint-policy | `src/会话轮次大纲.light` + `src/检查点策略.light` | done（纯逻辑面；Cordis 插件壳/flush 副作用剔除） |
| #82 | util/http-proxy + util/launch-environment | `src/代理策略.light` + `src/启动环境.light` | done（纯逻辑面；undici install/Cordis 宿主剔除） |
| #83 | test-support/llm-replay | `src/大模型回放.light` | done（纯逻辑导出 4 函数；与 llm-mock-server 互补） |
| #84 | experimental/code-runtime-python protocol | `src/代码运行时协议.light` | done（纯协议层；运行时执行仍由 `src/代码运行时.light` 负责）——第11轮遗留收口 |
| #85 | interaction/user-approval + tool-ask-user | `src/审批.light`（对照修复） | done（#73 未覆盖子包对照收口 D1~D10） |

---

## 四、缺陷账登记

文件：`docs/功能对标/语言缺陷账.md`（追加 L-085 ~ L-090，共 6 条，均附 `examples/_repro_L0xx.light` 修复形态 rc=0）

| ID | 来源 | 现象 | 绕法 |
|---|---|---|---|
| L-085 | 任务5 | `e` 指数浮点字面量不被支持（`1e400` 解析为标识符 inf，NameError） | `解析JSON("1e400")`（JSON 数字指数路径正常） |
| L-086 | 任务3/4 | 字符串 `{1,4}` 花括号量词被当重复语法（SyntaxWarning: 'int' object is not callable） | 等价无花括号量词 `[0-9a-f][0-9a-f]?[0-9a-f]?[0-9a-f]?` |
| L-087 | 任务3/4 | `当前目录` 内置映射名无条件发射为 `当前目录()`，import 字典常量后用报 'dict' object is not callable | 不 import 该名，`造目录(...)` 自行构造等价目录对象 |
| L-088 | 任务4 | `捕获 错误 as 变量` 不支持（异常无法绑定变量） | `尝试/捕获 错误:` + 布尔标志 |
| L-089 | 任务4 | 字符串内 `{标识符}` 触发插值破坏（手写 JSON 字面量不可靠） | 测试文本一律 `序列化JSON(...)` 构造 |
| L-090 | 任务3 | 字符串原语裸名与 .light 字符串模块导入共存时名称解析错乱 | 字符串原语一律用编译器内置映射裸名，不 import 字符串模块 |

> 注：任务5 报告原建议编号 L-084，但 L-084 已被第11轮任务6（`为` 字词法切碎）占用，路M 复核后从 **L-085** 起登记。

---

## 五、行为差异登记

文件：`docs/功能对标/行为差异清单.md` 新增「六、第12轮路M行为差异登记」段，共 15 项：

- **✅ 已修复 7 项**（R12-D1~D6、D8）：任务6 对照修复——裁决结果四结果闭集 / ask/never 策略 / never 自动拒绝 / fail-closed unavailable / 词汇外归一 / 开轮前置 hasOpenTurn / 策略文案逐字。
- **⚪ 维持登记 8 项**（R12-D7、D9~D15）：
  - D7 审计对 approval/asked+decided：审计包形状对齐，`approval/*` 事件词汇注册移交路M（会话格式.light 事件词汇表只读，本轮不注册）
  - D9 ask_user_question 形状已修复，工具注册表接入点移交路M
  - D10 光明 权限4预设（上游无此面），正交维持
  - D11 冷读存储通道不同（持久化只读面 vs 上游直读），语义对齐
  - D12 查询工具未注册进工具注册表（与 D9 同决策）
  - D13 URL 类缺失，`HTTP解析URL` 宽松解析语义对齐
  - D14 v3 事件中文键（上游英文键），双键兼容
  - D15 投影行解析内置化（上游宿主接线层），任务书纯逻辑边界
- 汇总统计更新：19 ✅ / 0 🟡 / 10 ⚪。

---

## 六、遗留登记（留后续轮 / 待决策）

1. **工具注册表接入点（R12-D9 + R12-D12）**：ask_user_question（任务6）与 查询工具 呈现/过滤构造（任务1）均为"纯逻辑面已复刻、未注册进 `src/工具.light` 注册表"。任务书明确本轮不注册（避免与第11轮在飞任务冲突），收口**维持不注册**；后续轮如需接入，在 `src/工具.light` 注册表补登记（含 schema 导出）。
2. **approval/* 事件词汇注册（R12-D7）**：会话格式.light 事件词汇表只读，`approval/asked`+`approval/decided` 审计事件未注册；当前审计包由调用方落盘。后续轮如需完整审计链，需在事件词汇表补注册。
3. **上游宿主面未移植（既有延续）**：应答者瀑布（ctx.waterfall）/AbortSignal 竞态、invariant.ts 独立插件、cli.ts/bin.ts、session-format-catalog 宿主接线、undici install、service-boundary/workspace-access 胶水——均属宿主面，维持登记。
4. **`_inspect_gaps.py` / `_inspect_ledger.py` / `_verify_config_auto.py` / `_taskM_*` 工具脚本**：收口工具惯例保留（不提交、不清理）。

---

## 七、文件互斥合规确认

- 收口 commit 仅包含：docs 3 文件（对标清单/行为差异/缺陷账）+ 6 个 `examples/_repro_L085~L090.light` + 本收口说明。
- 6 路分路 commit（dbd6eac~69c4430）各仅含本路文件互斥表内文件，无越界。
- **非本轮改动保留不提交**：`README.md`、`examples/运行Web服务器.light`（HARNESS_WEB_MOCK 自动检测功能，他人/此前工作），工作区原状未动。
- 探针清理：`examples/_probeG.light`（任务4 探针）、`examples/_probe_审批耗时.light`（路M 排查偶发失败用）已删除。
- 全量 CI 259 passed 0 failed，覆盖本轮全部新增/修改模块与既有回归。
