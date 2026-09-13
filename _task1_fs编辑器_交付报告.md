# 任务1 交付报告：fs 编辑器域（tool-str-replace-editor → src/字符串替换编辑器.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第13轮_任务prompt分发.md` 任务1
> 日期：2026-09-13 ｜ 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2，HEAD `9d9035b7c1` 的 +2 commit 仅涉 flock/rc.d，与本域无关）
> 目标模块：`lightharness/src/字符串替换编辑器.light`（对标 #86 str-replace-editor；#60 点名未实现本轮收口）

---

## 一、上游对应表（packages/fs/tool-str-replace-editor/src/index.ts，531 行）

| 上游位置 | 光明段落/常量 | 核心语义 |
|---|---|---|
| L17 `TRUNCATED_MESSAGE` | 设 截断尾注 | `<response clipped><NOTE>...` 尾注；反引号略去（文案差异，见 §六） |
| L33-37 `maybeTruncate` | 截断内容 | ≤上限原样；超限 截取(0,上限)+尾注 |
| L43-52 `matchOffsets` | 收集命中偏移 | indexOf 循环推进；光明 `查找子串` 无起点参，以 截取到末尾+相对偏移 等价实现；空搜索返回空表防死循环（上游由 old_str 非空门禁保证） |
| L54-64 `lineNumbersAt` | 偏移行号 | 单游标递增扫描计数换行 |
| L89-99 `resolveTarget` | 解析目标 | trim 空串抛「路径必须为非空字符串」；非 `/` 开头抛「路径 X 不是绝对路径，应以 / 开头。是不是想写 /X？」 |
| L101-122 `statExisting` | 查看路径/替换于文件/插入于文件 内联 | 不存在抛「路径 X 不存在，请提供有效路径」；目录仅 view（「路径 X 是目录，只有 view 命令可用于目录」）；非普通文件（无法查看/编辑/插入 "X"） |
| L124-135 `requiredForCommand` | 必填参数 | 缺省抛「参数 X 是 Y 命令必填」；allowEmpty=假 且空串抛「参数 X 是 Y 命令为空」 |
| L137-184 `formatFileView` | 格式化文件视图 | 头部总行数提示（含「这里有 X 行」）；view_range 校验族（非两整数/起∈[1,总行数]/止≤总行数/止=-1 到文尾/止≥起，文案带 `[a, b]` 与元素值）；止=-1 或缺省渲染到文尾 |
| L181 `padStart(6,' ')` | 渲染视图行 | 行号 6 位右对齐 + 两空格 + 行文本 |
| L186-215 `listDirectory` | 造目录视图 + 收集目录行 + 目录行较前 | 根行 `d\t根`；递归 2 层（深度<2 才下钻）；过滤 `.` 开头/node_modules/`__pycache__`；行格式 `d\|f\|?\t显示路径`；按键（\t 后路径）码点升序（选择排序，不原地改入参）；头部 `Here're the files...` 保留英文 |
| L217-238 `viewPath` | 查看路径 | 目录 + view_range≠空 抛「path 指向目录时不允许使用 view_range 参数」 |
| L240-273 `createFile` | 创建文件 | file_text 必填（allowEmpty=真，空文件合法，对齐上游默认）→ 路径校验 → 已存在抛「文件已存在: X。create 不能覆盖」→ 写 → 「新文件创建成功: X」 |
| L275-327 `replaceInFile` | 替换于文件 | new_str 为 无 抛「参数 new_str 必须省略或为字符串」→ 路径校验 → old_str 必填且非空 → 0 命中抛「未执行替换，old_str 未在 X 中原样出现」→ 多命中抛「未执行替换，old_str 在行 [n1, n2] 出现多次，请确保唯一」（行号=偏移行号）→ 单命中 前段+新+后段 写回 →「文件 X 已编辑成功」 |
| L329-369 `insertInFile` | 插入于文件 | insert_line/new_str 必填 → 行范围 [0, 总行数]（非整数/负/超上界同文案「insert_line 参数无效: X。应在文件行范围内: [0, N]」）→ split('\n') 前中后三段拼接写回 |
| L376-423 `presentEditorCall` | 呈现编辑调用 | view=generic/read；create/str_replace=diff（diffs 旧/新文本）；insert=generic/edit + 位置行 max(1, insert_line+1) |
| L471-496 `execute` | 执行编辑命令 | 四命令分发；schema 枚举与 path 必填门禁手写化（宿主面剔除，见 §五） |
| L505-529 `Config` | 宿主字典键 "上限"（默认 16000） | maxOutputChars 正安全整数校验由宿主承担 |

## 二、实现要点

1. **宿主面入参化**：`ctx.fs` 的 stat/readText/writeText/listDir 投影为宿主字典四段落键 `"查信息"/"读文本"/"写文本"/"列目录"`（+可选 `"上限"`）；版本号、目录条目、文件内容全部由测试/宿主注入，模块只做纯字符串/列表变换 + 校验 + 文案 + 呈现形状。
2. **new_str 三态对齐**：上游 `undefined`（省略→空串，删除替换合法）与 `null`（抛错）两态，光明入参字典以「键不存在 → 空串」与「键存在且值为 无 → 抛」区分（`字典包含键` 判定），语义逐一对齐。
3. **呈现形状键中文化对照**：card→卡片、title→标题、kind→种类、diffs→差异、locations→位置、path→路径、oldText→旧文本、newText→新文本、line→行。
4. **排序口径**：上游 `codepointCompare`（\t 后路径），光明字符串 `<` 码点比较等价；用选择排序生成新表，不原地改入参。
5. **绕法**：字符串原语一律内置裸名（L-090）；文案不含花括号（L-089）；无 且/或 行内布尔链，一律拆嵌套 如果（L-043 规避）；标识符避开「为/返回」等关键字字样（L-084/L-092）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_字符串替换编辑器.light
test_字符串替换编辑器 PASS   （rc=0）
```

`examples/test_字符串替换编辑器.light` 覆盖 10 组 ≥70 断言：命中收集与偏移行号纯函数、解析目标门禁（空/空白/相对+建议文案）、视图行号渲染（6 位右对齐 + 总行数提示）、view_range 区间与校验族（6 错误形态）、截断尾注（前缀+尾注精确拼合 / 未超限不截）、目录 2 层树（过滤 3 类 + 按路径码点排序 + 三层不下钻）、create 门禁（成功/已存在/缺 file_text/无值/空文件合法）、str_replace（唯一命中落盘/未找到/多命中行号 [1, 2] 不落盘/new_str 无/old_str 缺/空/目录拒绝/省略 new_str 删除替换/花括号文本经 序列化JSON 构造）、insert（0 头插/等总行数尾插/多行/超上界/负值/双参数必填/目录拒绝）、命令枚举与必填门禁、四命令呈现形状。测试文本按 L-089 绕法以 `序列化JSON` 构造含花括号内容。

## 四、反跑结果（3/3 ALL OK）

`G:\dswork\duan-light-merge\_antirun_t1_字符串替换编辑器.py`（字节级备份→变异→跑本路测试→断红→恢复→断绿+sha256 逐字节一致）：

```
PASS A 视图行号 6 位右对齐改 4 位 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS B str_replace 多命中不再抛歧义 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS C insert_line 上界放开(>总行数通过) -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 83b34571ba66)
PASS 恢复后回归绿 (rc=0)
ALL OK
```

## 五、未移植项（宿主面登记）

- `ctx.fs` 真实 IO（resolve/stat/readText/writeText/listDir 的磁盘实现）与 `FsTarget.displayPath` 解析——宿主注入。
- `FsError` 错误码类（FS_NOT_FOUND/FS_NOT_REGULAR_FILE/FS_EDIT_NOT_FOUND/FS_AMBIGUOUS_EDIT）：光明以错误消息文本承载，码语义并入文案；结构化 code 字段未复刻。
- `sandboxPolicy`/`MutationPolicy`（sandboxDenialMarker 映射 FS_SANDBOX_DENIED）、`ctx.waterfall` 写意图、`ctx.emit('fs/observed')` 事件、`AbortSignal`——全部剔除，登记宿主面。
- `defineTool` 注册（name/description/parameters schema/output.render）：schema 的 enum/required 门禁在 执行编辑命令 手写化（未知命令/path 必填），参数描述文本与 DEFAULT_DESCRIPTION 长文案未搬运。
- undo：上游本就无，未涉及。

## 六、语言差异（本轮新缺陷登记）

- **L-091（建议编号）**：匿名段落不能跨行内联在调用实参位置（`应用(段落 接收 x: ...)` 解析报「无法识别的语法元素：')'」）。绕法：先赋值再传参。最小复现 `examples/_repro_L091.light`（绕法形态 rc=0）。
- 文案差异（非缺陷）：TRUNCATED_MESSAGE 与错误文案中的反引号在光明文案中略去；view 头部总行数提示按任务书中文化（含「这里有 X 行」），目录头部保留上游英文。

## 七、移交清单

- `lightharness/src/字符串替换编辑器.light`（新增，≈430 行）
- `lightharness/examples/test_字符串替换编辑器.light`（新增，PASS rc=0）
- `G:\dswork\duan-light-merge\_antirun_t1_字符串替换编辑器.py`（反跑 3/3 ALL OK）
- `lightharness/examples/_repro_L091.light`（L-091 绕法形态复现，rc=0）
- 本报告。
- 移交路M：对标清单新增 **#86**（str-replace-editor）；语言缺陷账 **L-091** 起登记；CI 增 1 个 test_ 文件（期望 259+6 passed 中占 1）。
