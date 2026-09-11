# 任务2（消息词汇表 + 通用文件附件）交付报告

- 轮次：第 5 轮（0.1.5-rc.2 遗留收尾）
- 任务书：`0.15遗留_第5轮_任务prompt分发.md` §任务2
- 状态：**✅ 完成** — 定向用例绿、依赖测试 21/21 绿、反跑判据 4/4 成立、零回归
- 日期：2026-09-11

---

## 一、上游对应表

| 本路实现（光明） | 上游依据 | 语义说明 |
|---|---|---|
| `附件准入.light` `判定规范base64按策略(数据, 空串策略)` | `attachment/src/admission.ts` `decodeCanonicalBase64(data, empty, code)` 的 `empty` 参数 | 图片 `reject`（空串拒绝）/ 文件 `accept`（零字节文件合法） |
| `附件准入.light` `解码校验(数据, 空串策略, 错误码)` | 同上，抛错分支 | 非规范/空串拒绝时按 `code` 区分文案：`INVALID_IMAGE_BASE64` → `Image upload is not canonical base64.`；否则 `File upload is not canonical base64.` |
| `附件准入.light` `规整文件名(名字)` | `attachment/src/types.ts` `FileAttachmentRef.name` =「sanitized display filename, never a path」 | 剥离 `/` 与 `\` 目录路径，只留叶名 |
| `附件准入.light` `存文件输入(文件)` | `admitEncodedFile` 内的 `saveFile({ data, name? })` 入参构造 | 空串合法（零字节）；非规范拒绝（文案含 File） |
| `附件准入.light` `造文件引用(文件)` | `types.ts` `FileAttachmentRef { attachmentId, name, bytes }` | **attachmentId 用纯逻辑哈希近似 sha256**（差异见 §四） |
| `附件准入.light` `准入编码文件(文件)` | `admission.ts` `admitEncodedFile` | 端到端：规范校验 → 引用构造 |
| `消息.light` `造系统消息(文本, 插件)` | `llm/src/message.ts` `createSystemMessage(text, plugin)` | 空文本 → `content: []`（无系统提示）；非空 → 单 text 块；`source = {kind:'plugin', plugin}` |
| `消息.light` `造文件块(附件引用)` | `llm/src/types.ts` `FileBlock { type:'file', attachment }` | 只构造结构化块；投影为句柄文本由装配方负责 |
| `消息.light` `取消息文本` file 分支 | `FileBlock` 注释「投影为确定性句柄文本（名字、字节大小）」 | 一致性补齐：file 块原会静默跳过 |
| `代理.light` 收编局部 `造系统消息` | ——（词汇表收编） | 局部实现删除，改走 `消息.造系统消息(文本, "system-prompt")` |

---

## 二、实现要点

1. **`附件准入.light`（新增 6 段，既有 4 段行为零改动）**
   - 既有 `是规范base64` / `存输入` / `校验图片批次` / `准入编码图片` **一律不动**，既有契约完整保留（既有 `test_附件准入` 绿）。
   - 新增 `判定规范base64按策略` 做空串策略参数化（而非给 `是规范base64` 加参），避免破坏既有调用点。
   - `解码校验` 统一承载「策略判定 + 文案区分」，返回解码字节长度。
   - 错误文案用**文本区分**错误码（光明无枚举），与上游 `AttachmentError` 的 message 逐字一致。
2. **`消息.light`（新增 2 段 + 1 分支）**
   - `造系统消息` 插在「消息构造」区（造工具结果消息之后），`造文件块` 插在「内容块构造」区（造资源块之后）——**均插在文件中部，避开文件末尾边界**（规避 L-079 生成器错位 else 缺陷的触发面）。
   - `取消息文本` 补 file 分支，投影为 `[文件 <name>: <bytes> 字节]`。
3. **`代理.light`（收编）**
   - 局部 `造系统消息(文本)` 删除；导入行补 `造系统消息`；两处调用改为 `造系统消息(渲染文本, "system-prompt")`。
   - **消息形状逐字段不变**：`{id, role:"system", content, source:{kind:"plugin",plugin}}`，`plugin` 沿用原硬编码值 `"system-prompt"`。
4. **语言约束遵循**：布尔链拆多行（L-043，`或` 不可用）；缺键 `字典包含键` 守卫（L-036）；反斜杠字面量写 `"\\"`（光明无 raw 字符串）。

---

## 三、测试与 CI

| 项目 | 结果 |
|---|---|
| 新增 `examples/test_附件准入1.5.light` | ✅ rc=0 |
| 涉及模块既有用例 `test_附件准入` / `test_消息` / `test_代理` / `test_代理深化` | ✅ 全绿 |
| 广泛回归（依赖 `消息.light` 17 例 + 依赖 `代理.light` 10 例，去重 21 例） | ✅ **21/21 绿，零红** |
| 反跑判据 `_antirun_attachments15.py` | ✅ **4/4 成立**（基线 + A/B/C 三组） |

**反跑判据明细**（改反 → 断言红，恢复 → 断言绿）：

| 组 | 改反方式 | 结果 |
|---|---|---|
| A 文件空串「放行」改「拒绝」 | `存文件输入` 的 `"accept"` → `"reject"` | 改反 rc=1，恢复 rc=0 ✅ |
| B 文件错误码改回图片文案 | File 文案 → Image 文案 | 改反 rc=1，恢复 rc=0 ✅ |
| C 引用确定性改随机 | 哈希输入串拼接随机数 | 改反 rc=1，恢复 rc=0 ✅ |

> 全量 CI（`python scripts/ci_test.py`）按任务书由**路M 统一跑**。

---

## 四、未移植项与差异说明

1. **`attachmentId` 非 sha256（明确差异）**
   - 上游 `FileAttachmentRef.attachmentId` = 存储字节的 **sha256**（内容寻址）。
   - 光明无字节级 sha256 直接暴露；按任务书指引复用 `src/安全策略.light` 的 `计算哈希` 先例（乘加哈希 FNV 变体 → `转十六进制`），标识格式 `file-<hex>`。
   - 语义等价性：**「同输入同值」的确定性与内容寻址语义一致**（输入 = 规范 base64 串 + 名字）；**非加密强度**，不可替代安全场景的 sha256。已在源码注释与本节登记。
2. **`ImageAttachmentRef` 的 `width`/`height`/`originalDimensions`**：需真实图像解码，光明无字节图像库；既有 `存输入` 只记字节长，本轮未变（既有契约）。
3. **`AttachmentStore.saveFile` 的持久化提交**：宿主/存储层，按「宿主层不移植」原则剔除；光明侧 `存文件输入` 只产出待存结构。
4. **file 块的请求装配投影**（替换为句柄文本交给 provider）：属装配方职责，`消息.light` 只构造结构化块；`取消息文本` 提供等价的 UI/摘要投影。

---

## 五、移交清单

1. **已查证、无需改动**：`会话格式.light`（V3 catalog）。
   - 查证结论：该 catalog 定的是 **V3 事件类型**词汇（`system/message` 等，载荷字段为文本「系统」），而本次新增的 `造文件块`/`造系统消息` 属 **llm 消息内容块层**，两者无交叉 → **不改**。任务书第 4 条「若 V3 catalog 需要登记」的答案是**否**。
2. **给路M / 后续轮次**：
   - 本路未触碰其它任务文件（任务1 的 `总入口`/`web服务器`/`令牌计量`、任务3/4 文件均未改）；跨路契约满足。
   - 未新增语言缺陷，无需登记 `语言缺陷账.md`。
3. **文件清单**：
   - 改动：`src/附件准入.light`、`src/消息.light`、`src/代理.light`
   - 新增：`examples/test_附件准入1.5.light`、`_antirun_attachments15.py`、本报告
