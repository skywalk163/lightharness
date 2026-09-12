# 任务1（消息/附件域）交付报告 —— #4 System 词表 + #48 通用文件附件

> 日期：2026-09-12 ｜ 轮次：第11轮 任务1 ｜ 仓库：`G:\dswork\duan-light-merge\lightharness`
> 上游（只读）：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）

## 一、上游依据（文件:函数）

### #4 System 词表
- `packages/llm/llm/src/message.ts:238` —— `createSystemMessage(text, plugin): SystemMessage`
  - `role: 'system'`；`content: text.length === 0 ? [] : [{ type:'text', text }]`；`source: { kind:'plugin', plugin }`。
  - 语义：空文本 → content 空数组（「无系统提示」，不投影任何 wire 消息）；非空 → 单个 text 块；来源恒为 plugin。
- 类型：`message.ts:158` —— `SystemMessage extends Message { role:'system'; source: MessageSourceMap['plugin'] }`。
- 上游测试：`packages/llm/llm/tests/message.spec.ts` 仅覆盖 createUser/freeze/createAssistant/createToolResult，**无独立 System 用例**；本路按 createSystemMessage 语义补断言。

### #48 通用文件附件
- `packages/attachment/attachment/src/admission.ts:15` —— `decodeCanonicalBase64(data, empty, code)`：
  - 空串策略参数化：图片 `empty='reject'`（空串即拒）、文件 `empty='accept'`（空串=零字节合法）。
  - 往返相等判定（decode→re-encode 比对）；非规范抛 `AttachmentError`，文案 Image/File 分流。
- `admission.ts:66` —— `admitEncodedFile(attachments, file)`：`saveFile({data, ...name})`，逐字提交。
- `packages/attachment/attachment/src/types.ts:49` —— `EncodedFileAttachment { data, name? }`；`:39` `FileAttachmentRef { attachmentId, name, bytes }`。
- `packages/attachment/attachment/src/index.ts:187` —— `saveFile` 注释原文：**「Files carry no admission limits: any byte content and length is accepted」**——文件无大小/类型限额。
- 上游测试：`packages/attachment/attachment/tests/admission.spec.ts:75` `admitEncodedFile` 三段（合法/空串零字节/非规范拒绝）。

## 二、实现要点（复核结论）

**勘察发现：两个 src 在先前轮次（第10轮 L-083 拷贝原语落地时）已按上游 0.1.5 形态实现并提交，本轮逐字段复核后与上游语义一致，无需改逻辑。** 本轮工作 = 对齐复核 + 补独立测试 + 反跑判据 + 报告。

### src/消息.light（已对齐，未改动）
- `造系统消息(文本, 插件)`（第92–96行）：
  - 空文本 → `content=[]`；非空 → `[造文本块(文本)]`；`role="system"`；`source={kind:"plugin", plugin:插件}`；`id=造标识()`；`content` 经 `深拷贝` 脱钩（对齐上游 `freezeMessage` 的 structuredClone+deepFreeze）。
  - 与上游 `createSystemMessage` 字段逐一吻合。

### src/附件准入.light（已对齐，未改动）
- `判定规范base64按策略(数据, 空串策略)`：reject/accept 参数化（图片 reject / 文件 accept）。
- `解码校验(数据, 空串策略, 错误码)`：非规范抛错，文案按错误码分流「Image/File」。
- `规整文件名(名字)`：剥离 `/` 与 `\` 路径，只留叶名（对齐 `FileAttachmentRef.name`）。
- `存文件输入` / `造文件引用` / `准入编码文件`：空串=零字节合法；`attachmentId` 确定性内容寻址（FNV 变体 → `file-<hex>`，差异见「未移植项」）。
- **文件不设限额**：与上游 `saveFile`「any byte content and length is accepted」一致；attachment-local 全部 `maxBytes` 常量均属图片归一化/请求像素预算，无文件限额常量。

## 三、测试与 CI

新增（均 rc=0）：
- `examples/test_消息_System.light` —— 10 断言：空文本 role/content/source、非空文本块形状、id 新鲜唯一、与 user 角色区分。
- `examples/test_附件_通用文件.light` —— 18 断言：合法 base64、空串「图片拒/文件放」分流、非规范文案 Image/File 分流、长度非4倍数/非法字符拒绝、name 规整与缺省、引用确定性与内容寻址、端到端准入。

既有回归（直接跑 `python 运行.py`，与 pytest 同一执行路径）：
- test_消息.light / test_消息深化.light / test_消息_System.light —— rc=0
- test_附件准入.light / test_附件准入1.5.light / test_附件_通用文件.light —— rc=0

> **环境备注（不阻塞）**：`python -m pytest tests/ -q -k 消息` 在本机会把 236/238 全部 deselect。根因是 pytest 对非 ASCII 节点 id 做 `\uXXXX` 转义（collect 可见 `test_\u6d88\u606f_System.light`），中文 `-k` 永远匹配不到转义后的 nodeid；ASCII `-k L001` / `-k System` 正常（-k System 实测 1 passed）。属 harness 既有行为，非本路引入；等效回归以上述直接运行 `.light` 完成，路M 全量 CI 不受影响（全量按文件名遍历，无 -k 中文过滤）。

## 四、反跑判据（_antirun_msg_attach.py，2/2 PASS）

字节级备份/恢复 `src/消息.light`、`src/附件准入.light`：
- **A**：`"role": "system"` → `"role": "System"`（造系统消息行，唯一命中）→ test_消息_System 注入后红 rc=1，恢复后绿 rc=0。
- **B**：`解码校验(数据, "accept", ...)` → `"reject"`（造文件引用行，唯一命中；即去掉文件空串 base64 容错、严格解码）→ test_附件_通用文件 注入后红 rc=1，恢复后绿 rc=0。

脚本 `finally` 兜底恢复，跑完 `git status src/消息.light src/附件准入.light` 无残留。

## 五、未移植项 / 已知差异

1. **attachmentId 非加密强度**：上游 `FileAttachmentRef.attachmentId` = 存储字节的 sha256；光明沿用 `src/安全策略.light 计算哈希`（FNV 变体）→ `file-<hex>`。同输入同值、内容寻址语义一致，仅非加密强度。
2. **无真实字节解码**：纯光明无 Uint8Array/Buffer，「解码字节长度」用纯算术（组数*3-填充），不做真实字节落地；准入语义（规范判定/空串策略/分流）等价复刻。
3. **文件无限额**：上游文件本就不设大小/类型限额，故不移植（非遗漏）。
4. **ContextFormed/form**：上游 plugin source 可带 `form`（instructions/catalog/snapshot/...），由各生产方在装配时附加；`createSystemMessage` 本身不产生 form，故本路不补（保持与上游构造函数同形）。
5. 未触及：AttachmentStore 抽象持久化、saveFileStream/readFileStream、image 归一化（sharp 依赖）等宿主层，留后续轮。

## 六、移交清单（绝对路径）

- 修改：`G:\dswork\duan-light-merge\lightharness\src\消息.light`（已对齐，本轮无逻辑改动）
- 修改：`G:\dswork\duan-light-merge\lightharness\src\附件准入.light`（已对齐，本轮无逻辑改动）
- 新增：`G:\dswork\duan-light-merge\lightharness\examples\test_消息_System.light`
- 新增：`G:\dswork\duan-light-merge\lightharness\examples\test_附件_通用文件.light`
- 反跑：`G:\dswork\duan-light-merge\lightharness\_antirun_msg_attach.py`（2/2 PASS）
- 报告：`G:\dswork\duan-light-merge\lightharness\_task1_消息附件_交付报告.md`

给路M：本路仅新增 2 个 examples 用例 + 1 反跑脚本 + 本报告；src 两文件复核无逻辑改动，全量 CI 应自然纳入新用例（文件名遍历收编），预期 +2 passed。
