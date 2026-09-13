# _task6_控制器类型_交付报告.md

## 任务

第 16 轮 / 任务 6 · API 控制器类型合并（对标 #109）。

上游对标文件（均以本地 HEAD 9d9035b7c1 为准）：

- `packages/api/workspace-files/src/types.ts`      （166 行）—— 工作区文件域
- `packages/api/settings-controller/src/types.ts`  （ 39 行）—— 设置控制器域
- `packages/api/workspace-controller/src/types.ts` （128 行）—— 工作区控制器域

本任务对应光明模块：`src/控制器类型.light`（新增）。

## 交付物（4 个可写文件）

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| `src/控制器类型.light` | 943 | 三域类型判型/构造 + 错误码映射投影，末尾全量导出 |
| `examples/test_控制器类型.light` | 307 | 15 个用例 / 162 条断言论据（断言相等），`主程()` 收尾打印 PASS |
| `_antirun_t6_控制器类型.py` | LF | A/B/C 三判据字节级变异注入，判红→字节恢复→判绿 |
| `_task6_控制器类型_交付报告.md` | 本文 | 交付报告 |

测试运行：`python 运行.py examples/test_控制器类型.light` → `test_控制器类型 PASS`，rc=0。

## 反跑判据（3/3 ALL OK）

| 判据 | 变异点 | 判红 | 恢复 | 判绿 |
| --- | --- | --- | --- | --- |
| A 正常输出：变更构造→判别→取路径 | `造变更存现` 的 `"version"` 写坏为 `"versio"` | True | 字节一致 | True |
| B 边界：空设置对象键枚举不崩溃 | `判目录打开真` 的 `== 真` 改 `!= 真` | True | 字节一致 | True |
| C 变异立红：变更类型枚举改坏 | `判目录项类型` 的 `"directory"` 写坏为 `"dir"` | True | 字节一致 | True |

判据脚本输出：`[...PASS] x3` + `3/3 ALL OK`，退出码 0。

## 设计说明

1. **三域命名隔离**：文件域前缀「文件/变更/监视帧」、设置域「打开/拒绝/凭据」，工作区域「工作区/基线/增量/跟随帧」，互不重名、互不侵扰；隔离专用用例 `用例_隔离` 交叉断言：工作区视图≠文件统计、设置码≠文件码≠工作区码、目录类型≠增量类型。
2. **判别联合（union）投影**：光明无受抨击的判别联合，统一投影为「形态判型 + 类别取出」：
   - 文件变更：`判变更存在` / `判变更缺席` / `判文件变更` / `取变更路径`；
   - 监视帧：`判就绪帧` / `判变更帧` / `判监视帧` / `取监视帧类别` / `取监视帧变更`；
   - 跟随增量：`upsert` / `remove` / `order` / `archived` 四形态各自判型 + `取增量类型`；
   - 跟随帧：`判基线帧` / `判增量` 汇入 `判跟随帧` / `取跟随帧类型`。
3. **错误码映射表投影**：上游 `declare module ... RemoteErrorDetailsMap` 是纯宿主类型映射，光明以「`判{域}错误码`（码表）+ 判错误详情/判拒绝详情等方式（必填键 + 类型校验）」承载，不注册协议。
4. **可选字段**：一律 `字典包含键` 探测，缺省不判、存在必校验；必填键缺失即判假（详见各用例边界断言）。
5. **布尔严格判别**：光明 `0 == 假` 为真（L-129），禁用相等判布尔；模块内置 `是布尔值` 段落（`type(值) == bool`，与 `预设深化.light` 同款绕法）并导出。

## 任务书措辞与上游实际差异（以实际文件为准）

任务书描述的三处「预期内容」与实际上游不相符，均已按实际文件复刻、未硬凹任务书：

- 任务书称 workspace-files 有「过滤条件」→ 上游 `workspace-files/types.ts` 无任何过滤相关类型；该域实际为 文件统计/文本区间/页文本/字节区间/字节窗/目录项/目录清单/文件变更/监视帧 + 6 错误码。
- 任务书称 settings-controller 有「Settings 形状/设置键判别/设置变更事件」→ 上游该文件仅 文档打开值 + 目录打开值（判别联合）+ 3 错误码（settings/rejected、settings/conflict、credential/rejected），全部照实复刻。
- 任务书称 workspace-controller 有「Feed 类型/工作区状态转换/目录选择结果」→ 上游该文件实际为 工作区视图/创建/改名/删除/顺序/会话前置/归档/基线/跟随增量(四型)/跟随帧 + 7 错误码；`DirectoryEntry/DirectoryListing` 属 `dsh-host-directory-picker` 再导出（非本包定义）。「目录选择结果」对应 `directory-picker/*` 五枚错误码（unavailable/unreadable/exists/create-failed 为本包映射）。
- `WorkspaceFileChange`、`WorkspaceArchiveSessionRequest` 等类型名按上游逐字对齐；`absent:true` / `opened:true|false` / `deleted:true` 等判别字段与枚举值字符串全部照抄上游。

## 差异登记

- **R16-D6**（行为差异）：三域类型均为纯 TypeScript 类型与 declare module 映射，无运行期逻辑；协议注册、client 接线、cordis/defineTool 等宿主面全部剔除为宿主面（不在光明模块承载），本模块只保证形状判型与默认构造与上游链路自洽。
- **L-140**（语言缺陷，预分配）：光明无判别联合/闭包接口类型，联合类型只能投影为「形态判型 + 类别取出」多段落；无 `is` 判别函数一等公民，判别收敛需要 `判xx(值)==真` 布尔链。本任务未引入新的编码缺陷，L-140 作为联合类型投影缺口随本任务登记。

## 遵守的铁律

- 未改动任何既有 `src/` 模块（网络钩子GitHub/钩子协议/acp内容/预设深化/协议深化等）、`stdlib/`、`scripts/`、`运行.py`、`tests/`、`docs/功能对标/`、README 及第三方 `examples/*`。
- 所有 src/test/报告 为 CRLF 行尾、UTF-8 无 BOM；反跑脚本 .py 按惯例保持 LF。
- 全部交付中文；零 Python 绕写业务逻辑。
