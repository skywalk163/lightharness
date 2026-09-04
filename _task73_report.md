# 复刻增量 #73 交付报告：interaction 纯逻辑

> 对标原版：`packages/interaction/{commands,user-questions,permission-presets}/src`
> 光明模块：`src/交互命令.light`（17 个导出段落）
> 测试：`examples/test_交互命令.light`（23 个用例段落 + 5 组反跑，全绿 rc=0）
> 反跑脚本：`_task73_antirun.py`（5/5 全红 + 还原复绿，SCRIPT_RC=0）
> 门禁：`python 运行.py examples/test_交互命令.light` 退出码=0 且断言全过。

## 一、源文件 → 段落对照表

| 原版位置 | 原版函数 | 光明段落 | 备注 |
|---|---|---|---|
| commands/brand.ts | 命令品牌（编译期消歧） | `命令标识` | 名义品牌，运行期恒等投射 |
| commands/index.ts | `parseCommand(line)` | `解析命令` | 逐字符手写正则等价 `/^[a-z][a-z0-9_-]*$/u`；名字后须空白（`chr(9/10/13)`/空格）否则返回 空 |
| commands/index.ts | `commandNameChar` / `COMMAND_NAME` | `命令名字符` / `命令名合规` | 首字符 `[a-z]`、续字符 `[a-z0-9_-]` |
| commands/index.ts | `renderThrown` | `安全渲染抛出` | `尝试 转字符串` 捕获异常给占位串 |
| user-questions/index.ts | `isRecord` | `是记录` | 非 空/非列表/是字典 |
| user-questions/index.ts | `restoreUserQuestionError` | `还原用户问题错误` | 命中 `{name,message,code}=UserQuestionError` 重 hydrate，否则透传 |
| user-questions/index.ts | `validateAskUserQuestionRequest` | `校验提问请求` | 缺 questions 键/空表 → `EMPTY_QUESTIONS`；`intent.approve` 须命中某 `option.label` 且带 intent 须带 `detail` → `BAD_INTENT` |
| permission-presets/index.ts | `effectivePermissionPreset` | `有效权限预设` | 逆序扫描首个 `permission/preset` 取 `preset` |
| permission-presets/index.ts | `applyKnobEvent` | `应用旋钮事件` | preset/sandbox/approval 三旋钮纯状态转移 |
| permission-presets/index.ts | `foldKnobs` | `折叠旋钮` | 从空旋钮态冷折叠整段事件日志 |
| permission-presets/index.ts | `derivePreset(ctx, sandboxDefault, approvalDefault)` | `推导预设(状态, 沙箱默认, 审批默认, 预设表)` | 有效旋钮+表匹配；保留先前选择，否则首个命中，否则 custom（宿主 `this.presets/this.ctx` 投影为入参） |
| permission-presets/index.ts | `optionOf` | `预设选项` | 表内项 → PresetOption；custom → 保留选项含说明文案 |
| permission-presets/index.ts | `selectFor` | `选择权限` | 所有表项选项 + 当前推导值；仅当 current==custom 追加 custom 选项 |
| permission-presets/index.ts | `resolve` | `解析预设` | 名称 → 规格，未知抛 `unknown preset` |
| commands/invariant.ts | `validateEvent(command)` | `校验命令生命周期` | run↔done 配对 + `sourceEventSeq` 不变式（重复 run / 无前置 run / 指向 command 事件 / 越界 均回调 失败） |
| permission-presets/invariant.ts | `validateEvent(permission/preset)` | `校验权限预设事件` | permission/preset 事件须命名已知预设，否则回调 失败；非相关类型忽略返回 空 |

**复刻边界（宿主绑定全部投影剥离）**：Cordis ctx / octokit / session.append / 运行时 setter / tool-ask-user / user-approval 一律未复刻或投影剥离；权限预设表 `Record<string,PresetSpec>` 与两个回退默认（沙箱默认 / 审批默认）改为**入参**传入，使 `derivePreset`/`optionOf`/`selectFor`/`resolve` 成为纯函数（对齐原版 `this.presets`/`this.ctx` 的等价物）。

## 二、本轮根因修正（两个真问题，均实测定位）

### 根因 A（致命，误报为语法错误）：`字符串长度` 从错误模块导入
`src/交互命令.light` 原第 13 行写 `从 内置核心字符串 导入 截取, 截取到末尾, 字符串长度`，但 **`字符串长度` 并不由 `内置核心字符串` 导出**（其导出清单仅有 `字符串获取/截取/去除空白/字符串包含/开头/结尾/查找子串/最后索引/截取到末尾/字符串计数` 等）。真身在 **`字符串工具轻量.light`**（第 17 行 `导出 ... 字符串长度 ...`）。

后果：整个 `交互命令` 模块导入失败 → 测试文件里所有 `校验提问请求(...)` / `推导预设(...)` 等调用因名字未绑定，被解析器**误报为行 91 起的「语法错误」**（实际是上游 import 失败的连锁）。孤立探针曾一度把矛头引向「嵌套字面量作实参」，反复横跳。

**修复**：拆成两行导入——
```
从 内置核心字符串 导入 截取, 截取到末尾
从 字符串工具轻量 导入 字符串长度
```
修复后模块正常导入，行 91 同类调用即能正常解析运行（实测 `校验提问请求({...})` 解析通过）。

### 根因 B（解析器上下文相关 bug，新语言缺陷 L-066）：实参为「含嵌套集合的字面量 / 另一函数调用」时，非函数体首条语句即解析崩坏
即便模块导入已修好，测试仍报行 91/115/124/143/170/195 等多处「语法错误」。二分隔离定位确认：**当函数调用 X 的实参是「含嵌套集合的字面量」或「X 本身就是另一函数调用的实参（嵌套调用）」，且该调用不在函数体首条语句位置时，解析器会误判括号闭合（报「期望 } 但得到 )」并级联后续报错）**。

最小复现：
```
段落 触发:
  设 占位 为 1                       # 前导语句（关键触发条件）
  断言相等(某函数({"a":[{"b":1}]}), 空, "x")   # 嵌套字面量作实参 → 期望 } 但得到 )
```
- 去掉前导语句（即该调用成为函数体首条）→ 解析通过；
- 把嵌套字面量 / 嵌套调用**先 `设` 成变量**再当实参 → 解析通过（已验证）。

**绕法（全量落地于测试文件）**：所有「调用结果」与「含嵌套集合的字面量」一律先 `设` 成变量再当实参。简单字面量（无嵌套集合的字典/列表、字符串、`空`、变量、索引变量 `X["k"]`、调用结果+索引 `f(x)["k"]`）作实参是安全的，保持原样。

### 附带修正（原测试逻辑 bug，非语言缺陷）
- 用例_校验提问请求 的「合法请求」原用了 `approve:"X"` + `options:[{label:"Y"}]`（故意不匹配），却期望 `校验提问请求` 返回 空——而该请求实际会抛 `BAD_INTENT`。已改为合法请求（`approve` 命中 `option.label` 且带 `detail`），与「抛_意图无选项」用例（同请求、期望抛）各司其职。
- 用例_校验命令生命周期 的「合法序列」原 `sourceEventSeq:1` 指向索引 1 的 done 事件本身（属 command 事件），触发 `失败记` 抛 `sourceEventSeq points to command event`——原把非法序列当合法。已插入中间非 command 事件（`sandbox/mode`，置于索引 1），使 `sourceEventSeq:1` 指向它，满足源模块不变量。

## 三、反跑验证表（5/5 全红 + 还原复绿）

脚本 `_task73_antirun.py`：绿色原文驻留内存，每次从原文重做单点破坏写入 `src/交互命令.light`、运行测试、确认 rc≠0、立即还原；末尾复绿确认 rc=0。**全程零 /tmp**。

| # | 破坏点 | 源改动 | 变红表现 | 结果 |
|---|---|---|---|---|
| ① | 解析命令 末尾返回改 空 | `返回 {"name":名,"rawInput":余}` → `返回 空` | 解析命令("/help") 得 空，反跑_解析命令 抛「应解析出 name=help」 | RED (rc=1) |
| ② | 推导预设 首命中改返回 custom | 循环内 `返回 名` → `返回 自定义预设` | 匹配态误判 custom，反跑_推导预设 断言失败 | RED (rc=1) |
| ③ | 有效权限预设 逆序改从 0 | `设 i 为 长 - 1` → `设 i 为 0` | 返回首个而非末个，反跑_有效_末个 期望 "b" 得 "a" | RED (rc=1) |
| ④ | 校验提问请求 空问题闸删 | 两道 EMPTY_QUESTIONS 闸改 `如果 (假): 抛出` | 空请求 `{}` 不抛，反跑_校验提问请求 判「期望抛错但未抛」 | RED (rc=1) |
| ⑤ | 校验命令生命周期 重复 run 闸删 | `如果 (列表包含(已见运行,id)==真): 失败(...)` → `如果 (假): 失败(...)` | 重复 run 误判合法，反跑_校验命令生命周期 判「期望抛错但未抛」 | RED (rc=1) |

**复绿确认**：还原后 `python 运行.py examples/test_交互命令.light` 打印 `--- 测试交互命令 通过 ---`，rc=0。SCRIPT_RC=0。

## 四、语言缺陷登记

| 编号 | 现象 | 本模块处置 |
|---|---|---|
| L-036 | 缺失键 `[]` 直接访问抛 `键错误` | 源模块全部可选字段访问走 `字典包含键` 守卫（`校验提问请求`/`校验权限预设事件`） |
| L-037 | `断言(条件,标签)` 静默 no-op | 测试一律用 `断言相等(实际,期望,标签)` |
| L-046 | 单字 `出` 不可作变量名 | 源模块变量用 `状态/事件/名/表` 等，绝不用 `出` |
| L-051 | 多行字面量破坏缩进 | 所有字典/列表字面量单行 |
| L-054 | 嵌套字面量内 `\n` 破坏后续块 | 嵌套字面量内不写 `\n`（用 `chr(10)`） |
| L-063 | 字典裸键被当变量 | 字典键一律带引号 |
| **L-066（新）** | **实参为含嵌套集合的字面量 / 另一函数调用时，非函数体首条语句即解析崩坏（期望 } 但得到 )）** | **所有调用结果、含嵌套集合的字面量先 `设` 变量再当实参** |

> L-066 已写入 `docs/功能对标/语言缺陷账.md`（同文件 §L-066）。另：`字符串长度` 由 `字符串工具轻量` 导出（非 `内置核心字符串`）属 stdlib 导出清单不一致，已在源模块修正导入，建议 A9 在文档中收敛。

## 五、遗留 / 后续

- **未复刻部分（任务书白名单外）**：`tool-ask-user` / `user-approval` 两个子模块，以及 `index.ts` 装配层、`invariant.ts` 的 Cordis 宿主绑定，按任务书不在本批范围，未复刻。
- **L-066 建议语言侧修复**：解析器对「函数调用实参」的括号闭合判定应与语句位置无关；当前绕法（提取变量）完全可用，但可读性有损，建议在 A9 泳道排期修解析器。
- **复用 `_task73_antirun.py` 范式**：绿色原文驻留内存 + 零 /tmp 的单点破坏-还原模式，可作为后续增量复刻反跑的标准脚手架。
