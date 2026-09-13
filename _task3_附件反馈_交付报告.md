# 任务3 交付报告 —— 附件与反馈域（attachment + feedback 纯逻辑面）

> 轮次：复刻 第15轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#100（新增）** ｜ 差异编号 **R15-D3** ｜ 缺陷编号预分配 **L-125~L-126**
> 上游只读：`G:\github\deepseek-harness`（本地 HEAD `9d9035b7c1`；任务书标注 `a305303422`，差异见 §六）
> 本路可写文件（4 个，全部新增，零越界）：
> - `lightharness/src/附件反馈.light`（689 行 / 64 段）
> - `lightharness/examples/test_附件反馈.light`（249 行 / **148 断言**）
> - `lightharness/_antirun_t3_附件反馈.py`
> - `lightharness/_task3_附件反馈_交付报告.md`（本文件）
> 另：最小复现 `lightharness/examples/_repro_L125.light`（铁律 2 要求，缺陷 L-125）

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `attachment/src/brand.ts` | 6·13 `AttachmentId` / 18·25 `ImageVariantId` | 品牌同一性函数（不校验） | §1 `造附件标识` / `造变体标识`（+ 项目级 `是附件标识形状`） |
| `attachment/src/types.ts` | 8 `ImageMediaType` | v1 栅格图片媒体类型四值 | §2 `图片媒体类型表` / `是合法图片媒体类型` |
| `attachment/src/types.ts` | 11 `ImageAttachmentRef` / 39 `FileAttachmentRef` | 持久附件引用形状 | §2 `是图片附件引用` / `造图片附件引用` / `是文件附件引用` / `造文件附件引用` |
| `attachment/src/types.ts` | 49 `EncodedFileAttachment` / 85 `EncodedImageAttachment` | wire 上传形状 | §2 `是编码图片附件` / `是编码文件附件` |
| `attachment/src/types.ts` | 74 `ImageAttachmentLimits` | 部署解析限额 | §2 `是图片附件限制` / `造图片附件限制` |
| `attachment/src/types.ts` | 100 `PromptContentPart` / 110 `AttachmentAdmissionPart` / 115 `AdmittedPromptContentPart` | 提示部件三态 | §2 `是提示部件` / `是已准入部件` |
| `attachment/src/types.ts` | 136 `ImageRequestPolicy` / 144 `RequestImageAttachment` | 请求图片策略 | §4 `投影策略尺寸`（策略驱动） |
| `attachment/src/admission.ts` | 15 `decodeCanonicalBase64` / 26 `decodeBase64` | 规范 base64 判定 + 解码字节长度 | §3 **只读复用** `附件准入.light`（#48）的 `是规范base64` / `解码字节长度` |
| `attachment/src/admission.ts` | 31 `saveInput` / 49 `admitEncodedImages` / 66 `admitEncodedFile` | 图片空串 reject、文件空串 accept、批量准入 | §3 `准入单张图片` / `准入单个文件` / `准入图片批次` |
| `attachment/src/request-projection.ts` | 13 `requestImageDimensions` | 保比整数尺寸 + 硬像素预算（`Math.min/floor/round/sqrt`） | §4 `投影图片尺寸` / `取整半数上`（L-125 绕法） |
| `attachment/src/error.ts` | 3 `IMAGE_ADMISSION_ERROR_CODES`(9) / 18 `ATTACHMENT_ERROR_CODES`(17) | 封闭错误码集 | §5 `图片准入错误码表` / `附件错误码表` |
| `attachment/src/error.ts` | 46 `AttachmentError` / 67 `isAttachmentError` / 79 `isImageAdmissionError` | 错误类与判定 | §5 `造附件错误` / `是附件错误` / `是图片准入错误` |
| `feedback/command-feedback/src/index.ts` | 29 `FEEDBACK_CATEGORIES` / 42 `USAGE` | 七类反馈词表与用法文案 | §6 `反馈类别表` / `反馈用法文案` / `反馈必填文案` |
| `feedback/command-feedback/src/index.ts` | 57 `recordFeedback` | 首尾空白丢弃、空白记缺省、两项皆无仍记录 | §6 `规范化反馈记录` |
| `feedback/command-feedback/src/index.ts` | 72 `executeFeedbackCommand` / 101 `record` | 命令结果与 Remote 结果 | §6 `反馈命令结果` / `造反馈记录确认` / `造反馈会话缺失` |
| `feedback/message-feedback/src/index.ts` | 62 `timestamp` / 63 `itemSchema` | 反馈项模式（updatedAt ≥ createdAt） | §7 `是合法反馈项` |
| `feedback/message-feedback/src/index.ts` | 284 `resolveNote` | 备注：缺省/纯空白/超字节上限 | §7 `校验备注` / `字节数` |
| `feedback/message-feedback/src/index.ts` | 166 `put`（170–198） | 版本比对、材料无变化跳过、createdAt 继承、updatedAt 单调 | §7 `是版本冲突` / `应跳过写入` / `造反馈项` |
| `feedback/message-feedback/src/index.ts` | 97 `currentItems` | 事件流折叠（put 覆盖 / delete 移除 / 过滤 sessionId） | §7 `当前反馈项` |
| `feedback/message-feedback/src/types.ts` | 139 `MessageFeedbackFailure` 五码 | 业务失败码集 | §7 `消息反馈失败码表` / `是消息反馈失败码` |

---

## 二、实现要点

### §1 附件标识品牌
上游 `AttachmentId(value)` / `ImageVariantId(value)` 是**同一性函数**（`value as Branded<...>`，不校验）。本模块保留同一性语义，另加**项目级**形状判据 `是附件标识形状`：非空字符串且不含 `/`、`:` 与任何空白（含 NBSP / 全角空格，码点 9/10/11/12/13/32/160/12288）——依据上游注释「绝不是文件系统路径或带凭证 URL」这一不变量给出可测判据。**上游无此校验，属本研究加强项**，已登记 §五。

### §2 类型与形状
- 形状判据一律「先 `是字典` → 再 `字段齐备` → 再逐字段类型/域」，`note` / `name` / `condition` 等可选项用 `字典包含键` 守卫（L-103 同族纪律）。
- `是图片附件引用` 覆盖 `originalDimensions` 嵌套形状；`bytes ≥ 0`、`width/height ≥ 1`（对齐上游「正宽度/正高度」语义）。
- `是编码图片附件` 的 `data` 直接走 `是规范BASE64图片`（**非空**）；`是编码文件附件` 走 `是规范BASE64文件`（**允许空串**=零字节合法）——与上游 `admission.ts` 的 `empty: 'reject' | 'accept'` 分派一致。

### §3 wire 准入（复用 #48 判据底座）
- **不重复实现**规范 base64 判定：`从 附件准入 导入 是规范base64, 解码字节长度`。该模块（第48号卡）已 1:1 复刻 `decodeCanonicalBase64` 的四条判据（字符集 / 长度 %4 / 填充连续且 ≤2 / 尾比特规范）与 `(组数*3 - 填充数)` 字节长度。
- 本模块在其上补 **wire 层的分派与批次语义**：图片空串 reject、文件空串 accept；批次按「张数 → 单张字节 → 累计总字节」三段限额短路，并回传首个失败下标与错误码。
- 上游 `admitEncodedImages` 委托 `AttachmentStore.saveImages`（宿主持久化，剔除）；本模块回传「已解码输入 + 字节数」形状，由调用方接宿主存储。

### §4 请求投影几何（L-125 命中点）
- `requestImageDimensions` 逐句对照：`scale = min(1, sqrt(maxPixels/(w*h)))`；`scale==1` 原样返回（**小图不放大**）；宽 ≥ 高走宽度台阶、否则走高度台阶，台阶内每步用 `Math.round` 校正另一维并保证 `w*h ≤ maxPixels`，且不破 1。
- 上游 `Math.round` 是 **half-up**（`.5` 一律进位），而光明内建 `四舍五入` 是**银行家舍入**（实测 `四舍五入(2.5)==2`、`四舍五入(0.5)==0`）→ 记为 **L-125**，绕法 `取整半数上(x) = 向下取整(x + 0.5)`。
- 判别例（测试已钉死）：`投影图片尺寸(8, 5, 14)` 应为 `{4, 3}`；若误用银行家舍入则得 `{4, 2}`。反跑 B 判据即用此例。

### §5 附件错误族
- 码表：图片准入 9 条 + 存储/其他 8 条 = **17 条**，与上游 `IMAGE_ADMISSION_ERROR_CODES` / `ATTACHMENT_ERROR_CODES` 逐条一致。
- `isAttachmentError` 上游按「`instanceof Error` + code ∈ 码集」双重判定；光明无跨包原型链且上游注释明言「消费方只依据 `code` 路由」，故本模块取 **code ∈ 码集** 判据。
- 文案：只复刻上游**内联的两条 verbatim** 文案（`Image/File upload is not canonical base64.`）；其余码上游无文案，`规范错误消息` 回退返回码本身——**不杜撰**。

### §6 会话级反馈
- `规范化反馈记录`：`text` 先 `修剪空白`，为空则**整个键不出现**；`category` 缺省则不加键；两项皆无时返回空字典（对应上游「仍记录一条表示请求复核」的语义，由调用方决定是否 append）。
- `反馈命令结果`：原文修剪为空 → `{kind:"error", text:必填文案}`；否则 `{kind:"success", text:"Feedback recorded for session <id>\nAnonymous user: <uid>."}`（文案 verbatim，含 `\n` 与结尾句点）。

### §7 消息级反馈
- `字节数` 手写 UTF-8 字节计数（码点 <128/2048/65536/其余 → 1/2/3/4），对齐 `Buffer.byteLength(note,'utf8')`。
- `校验备注`：缺省 → 成功(空)；非串或纯空白 → `note-blank`；超上限 → `note-too-large` 且回传 `maxBytes`/`actualBytes`；否则成功(原文)。
- `造反馈项` **按上游对象字面量键序**构造（messageId, rating, note?, category?, version, createdAt, updatedAt），规避 L-116（`序列化JSON` 保插入序）导致的键序对拍假红。
- `应跳过写入` = 材料等价（rating/note/category 三者皆同）→ 不追加事件、保留原版本；`是版本冲突` = 请求版本 ≠ 已有项版本（缺省视作 `空`，`空 == 空` 不冲突）。
- `当前反馈项` 折叠事件流：`feedback/message-put` 按 `messageId` 覆盖、`feedback/message-delete` 移除，均按 `sessionId` 过滤，他包事件忽略；返回**首建序**（依赖字典插入序）。

---

## 三、验证结果

### 测试（148 断言，高于铁律 7 的「≥10」）
```
cd lightharness && python 运行.py examples/test_附件反馈.light
===== 第 15 轮任务 3：attachment + feedback 域（纯逻辑面）=====
test_附件反馈 PASS
RC=0
```

### 反跑 3/3（`python _antirun_t3_附件反馈.py`）
```
✓ A 规范 base64 判据取消 (判红运行 rc=1)
✓ B 投影取整退回银行家舍入 (判红运行 rc=1)
✓ C 附件错误码表漏 ATTACHMENT_CORRUPT (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 f5bb952ad1f2)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```
- **A**：`是规范BASE64图片` 末句 `返回 是规范base64(数据)` → `返回 真`，非法 base64（`"aGk"` / `"a Gk="`）被放行 → 3d/3e 红。
- **B**：`取整半数上` 实现换成内建 `四舍五入` → `投影图片尺寸(8,5,14)` 得 `{4,2}` → 4i 红（与 4a/4b 的银行家舍入判据共同锁定该语义分歧）。
- **C**：`附件错误码表` 去掉 `ATTACHMENT_CORRUPT` → 长度 17→16、`是附件错误码("ATTACHMENT_CORRUPT")` 转假 → 5b/5e 红。
- 三判据均**真变异立红**，恢复走 `finally` 并做逐字节 sha256 校验（第13轮教训）。

---

## 四、语言缺陷登记

### L-125（新增）内建 `四舍五入` 为银行家舍入，与 JS `Math.round` 不一致
- **证据**：`四舍五入(2.5)==2`、`四舍五入(0.5)==0`、`四舍五入(1.5)==2`；JS `Math.round` 分别为 3/1/2。`向下取整` 与 `Math.floor` 则一致（实测 `向下取整(2.7)==2`）。
- **触发面**：任何由 JS `Math.round` 移植的取整；本路 `request-projection.ts:22·25·30·33` 四处直接命中（尺寸会差 1 像素）。
- **绕法**：`取整半数上(x) = 向下取整(x + 0.5)`（非负数与 `Math.round` 逐值等价）。
- **复现**：`examples/_repro_L125.light`（绕法形态，rc=0）。

> 预分配 **L-126 未占用**（本路未再发现独立缺陷），按第14轮先例空缺顺延。

---

## 五、上游面剔除与偏差登记

| 上游面 | 处置 | 理由 |
|---|---|---|
| `attachment/index.ts`（264 行） | **剔除** | Cordis `AttachmentStore` Service 装配面（抽象持久化 + validateImage/saveImage），宿主面；其批次限额语义已由 #48 `附件准入.light` 覆盖 |
| `attachment-local/` | **剔除** | 宿主面（Node fs / sharp / 压缩编码 / 图片规范化） |
| `admission.ts` 的 `AttachmentStore.saveImages/saveFile` | **剔除** | 真实持久化 IO；本模块只回传已解码输入形状 |
| `attachment/brand.ts` 的 `Branded<'...'>` | **简化** | 光明无类型品牌机制；保留同一性函数语义 |
| `message-feedback` 的 `MessageFeedbackService`（317 行中的服务体） | **剔除** | Cordis Remote 服务、`sessionPersistence` 事务、`operationTails` 串行化、`randomUUID`；纯逻辑面（resolveNote/currentItems/put 决策）已复刻，`version` 由调用方注入 |
| `command-feedback` 的 `SessionFeedbackService` / `apply()` | **剔除** | Cordis Remote 与命令注册（宿主面） |
| `feedback/committed` 事件与 `drain` 生命周期 | **剔除** | 宿主并发/持久化语义 |
| 附件标识形状校验 | **加强（本研究新增）** | 上游 `AttachmentId` 不校验；按注释不变量补可测判据 |
| 图片媒体分类 / 错误码文案补全 | **加强（任务书驱动）** | 任务书 §测试要求 提到「分类/未知类型默认值」；上游无对应函数，本模块给 `图片媒体分类`（未知→"未知"），文案一律不杜撰 |

---

## 六、待路M裁定 / 移交清单

1. **对标卡 #100**：本路新增，建议登记为「attachment(brand/types/error/request-projection) + feedback(command/message) 纯逻辑面」，并注明 `admission.ts` 主判据**已于 #48 落地**（本路只做 wire 分派复用），避免 #48 与 #100 边界被误读为重复。
2. **行为差异 R15-D3**：建议记录两条 ——（a）附件标识形状判据为本研究加强项（上游不校验）；（b）`isAttachmentError` 由「instanceof + code」简化为「code ∈ 码集」（上游注释已许可）。
3. **文档/上游版本差异**：任务书头部标注上游 `a305303422`，本地工作副本 HEAD 为 `9d9035b7c1`。本路以**目录布局与文件内容**为对齐依据（任务书列出的 5 个 attachment / 4 个 feedback 文件全部存在且语义吻合），未发现内容漂移；如路M有权威 pin，请以 pin 复核。
4. **未移植项**（供 #100 备注）：附件压缩/编码/规范化、图片持久化、Remote 服务与命令注册、`randomUUID` 版本生成、`feedback/committed` 观察者。
