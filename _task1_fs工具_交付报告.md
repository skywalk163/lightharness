# 任务1 交付报告：fs 工具域（tool-fs 纯逻辑面 → src/文件系统工具.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第14轮_任务prompt分发 (1).md` 任务1
> 日期：2026-09-13 ｜ 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 目标模块：`lightharness/src/文件系统工具.light`（对标 #92 tool-fs；与第13轮 #86 字符串替换编辑器 同域互补）

---

## 一、上游对应表（packages/fs/tool-fs/src/，11 文件 1555 行）

| 上游位置 | 光明段落/常量 | 核心语义 |
|---|---|---|
| error.ts（34 行） | 提示读错误 / 守卫编辑前提 | FS_NOT_OBSERVED 文案逐字 `cannot modify "X": file has not been read — read the file, then retry`；FS_STALE_VERSION 追加 ` — re-read the file, then retry`；其余码透传 |
| read.ts（210 行） | 解析读参数 | READ_LIMIT=2000；offset 默认 1、limit 默认/上限 maxLimit；`X must be a positive integer` / `limit must be less than or equal to N` 逐字 |
| read-target.ts（34 行） | 判读目标 | `cannot read "X": not found`（FS_NOT_FOUND）/ `cannot read "X": not a regular file`（FS_NOT_REGULAR_FILE）逐字；目录与符号链接均在此拒 |
| read-render.ts（272 行） | 造读窗口 / 渲染读输出 / 语言自路径 | READ_MAX_LINE_LENGTH=2000（单行截断尾注 `... (line truncated to N chars)` 逐字）、READ_MAX_BYTES=51200 行字节预算；envelope `<path>/<type>file</type>/<content>` 模板逐字；footer 三态逐字（Output capped / Showing lines X-Y of N / End of file）；langFromPath 扩展名→高亮语言映射 |
| read-image.ts（351 行） | 图媒体类型 / 造图元数据 / 渲染图输出 | PNG/JPEG/WebP/GIF：扩展名声明优先、无扩展名字节签名嗅探（PNG 8 字节/JPEG FFD8FF/GIF87a·GIF89a/RIFF+WEBP）逐字判据；ImageAttachmentRef 形状 {attachmentId, mediaType, bytes, width, height, name?, originalDimensions?}；图片 envelope `<type>image</type>` + `${mediaType} image, WxH px, B bytes`（+降采样后缀）；宿主解码/降采样剔除 |
| write.ts（152 行） | 判写参数 / 写操作判定 / 写后信封 | 仅 `file_path must be a non-empty string` 一条校验；无追加/创建标志参数（任务书差异，登记）；create-or-overwrite 语义；信封 `<path>/<type>file</type>/<content>Created\|Updated file</content>` 逐字 |
| edit.ts（168 行） | 校验编辑参数 / 施加编辑 / 编辑后文案 | file_path/old_string/new_string 必填三文案逐字 + `old_string and new_string must differ`；replace_all=假 要求唯一命中（多命中策略在本层判定，见 §五）、真=全替换；确认文案两条逐字 |
| diff.ts（79 行） | 行差分表 / 差异到文件差异 | jsdiff structuredPatch（LCS 行级）等价实现；DIFF_CONTEXT=3；hunk 行 `-`/`+`/上下文；FileDiff {path, oldText(纯插入时 null), newText}；`\` 开头 no-newline 行跳过语义由构造保证 |
| index.ts（79 行） | 呈现读调用 / 呈现写调用 / 呈现编辑调用 / 执行读命令 / 执行写命令 / 执行编辑命令 | read→generic/read 卡（标题带窗口 `(start - end)`）、write/edit→diff 卡（title `Write/Edit ${file_path}`）；四命令参数 schema 汇总 |
| sandbox.ts / session-cwd.ts | 宿主面剔除 | 沙箱策略/会话 cwd 注入剔除（登记 §五） |

## 二、实现要点

1. **宿主面入参化**：宿主字典键 `"查信息"/"读文本"/"写文本"/"读头字节"`（+可选 `"读上限"/"行上限"/"字节上限"/"已观察"`）；文件内容、存在性、版本、图片头字节全部注入。
2. **观察守卫语义**：edit 前置链=未观察（FS_NOT_OBSERVED，先于存在性）→ 存在性（not found）→ 版本比较（FS_STALE_VERSION）；read 成功后登记已观察快照（对齐上游 emit fs/observed）。
3. **LCS 行级 diff**：DP 字典键 `"甲,乙"` 最长公共子序列 + 回溯（三态单循环防越界）+ 变更点 ±3 上下文分 hunk（相邻合并对齐 jsdiff 间隔 ≤2×context）；另提供 渲染统一差异文本（`---/+++/@@ -a,b +c,d @@`，jsdiff 形态长度 1 省略 `,1`）——任务书要求的统一格式输出，上游本层不产出文件头（补充实现）。
4. **edit 多命中**：上游唯一性判定在后端 ctx.fs.editText（契约不可见）；本层实现多命中抛错，文案按语义拟定 `old_string matched N times in file; provide a more specific old_string or set replace_all=true`（登记 R14-D1）。
5. **空文本行表语义**：diff 对空串取空行表（对齐 jsdiff），纯插入→oldText null。
6. **行为差异**：行字节预算以码点计数近似 UTF-8 字节；降采样比率浮点文本形态与 toFixed(2) 不逐一对应（登记 R14-D1）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_文件系统工具.light
test_文件系统工具 PASS   （rc=0）
```

`examples/test_文件系统工具.light` 覆盖 10 组 ≥60 断言：错误族文案（4 码 + 守卫）、read 参数校验 5 形态 + 默认值、read 窗口/渲染（envelope、行号、footer 三态、offset 越界、行截断、字节预算）、语言映射（含大小写归一/点文件）、read-image（声明/嗅探四格式/坏扩展/嗅探失败/元数据形状/envelope/降采样）、write（校验/create-update 判定/信封/集成落盘）、edit（校验 4 文案/多命中/replace_all/唯一命中/未找到/未观察/不存在/读后被删 not found/确认文案/集成+差异）、diff（无变化空/单替换上下文行/插入块统一差异全文/删除/分散独立块/纯插入 null/块头省略 ,1）、呈现形状、read 集成。

## 四、反跑结果（3/3 ALL OK）

`G:\dswork\duan-light-merge\_antirun_t1_文件系统工具.py`（字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally 异常安全路径）：

```
PASS A diff 算法失效(不计算 LCS/逐行退化) -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS B edit 多命中不再要求唯一或 replace_all -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS C read 行范围上界放开(>2000 通过) -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 3f826993040e)
PASS 恢复后回归绿 (rc=0)
ALL OK
```

A 变异为 DP 建表与回溯两处匹配条件同时失效（LCS 退化为空，等价不计算公共子序列）。

## 五、未移植项（宿主面登记）

- `ctx.fs` 真实 IO 与流式读取（streamText ≥10MiB 分支）、原子写入实现、目录自动创建——宿主/后端契约。
- `FsError` 结构化 code 字段（错误以消息文本承载）；`sandbox.ts`（FsSandboxController：升级模式/schema 字段/策略解析/`[sandbox: …]` 错误映射）、`session-cwd.ts`（sessionResolveOptions）——剔除。
- `ctx.waterfall` 写意图/编辑意图、`emit fs/observed` 事件总线——以「已观察快照」入参投影。
- read_image 的 attachment 服务（saveImage 全量解码/16-bit 归一化/降采样/维度校验）与模型路由图像能力门——宿主面；AttachmentError 7 类映射文案未搬运。
- edit 唯一性判定在属后端契约——本层补齐（见 §二.4）；`read_image` 条件注册（无 attachments 不存在）为注册面。

## 六、语言差异（本轮新缺陷登记）

- 无新缺陷（L-104 编号空缺，路M 顺延）。
- 文案差异（非缺陷）：TRUNCATED 类尾注与错误文案的反引号略去；统一差异 `---/+++/@@` 头为本层补充输出（上游 computeHunkDiffs 只消费 hunks）。

## 七、移交清单

- `lightharness/src/文件系统工具.light`（新增，≈520 行）
- `lightharness/examples/test_文件系统工具.light`（新增，PASS rc=0）
- `G:\dswork\duan-light-merge\_antirun_t1_文件系统工具.py`（反跑 3/3 ALL OK）
- 本报告。
- 移交路M：对标清单新增 **#92**（tool-fs）；行为差异清单 **R14-D1**（码点近似字节预算/浮点比率形态/edit 多命中文案自拟/统一差异头补充）；CI 增 1 个 test_ 文件（273 passed 占 1）。
