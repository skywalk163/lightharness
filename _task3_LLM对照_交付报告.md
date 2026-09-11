# 第 8 轮 任务3 交付报告 —— LLM 消息/请求行为对照

> 上游锚点：`a305303422`（0.1.5-rc.2，`packages/llm/llm` 13 spec + `packages/llm/llm-deepseek` 12 spec，共 25）
> 对照域：光明 lightharness 的 LLM 消息构造 / 请求体映射 / 流式翻译 / 模型目录 / 单价 / token 分桶
> 源约束：**src 全程只读**，本路只新增测试 + 反跑脚本 + 本报告

---

## 1. 上游 spec ↔ 光明覆盖状态总表

| 上游 spec | 语义 | 光明覆盖 | 落点 |
|---|---|---|---|
| `llm/message.spec.ts` | 消息构造（系统/用户/助手/工具结果、content 块） | ✅ | `test_消息` + 本次节A |
| `llm/content.spec.ts` | content 块（text/tool-result/file/resource） | ✅ | `test_消息` 节C + 路2 `造文件块` |
| `llm/call-config.spec.ts` | 请求体字段级相等 | ✅ | 本次节C（`组装请求` 字段透传/省略） |
| `llm/assembler.spec.ts` | finish kinds / 块装配 | ✅ | 本次节B6/B7（`翻译完成原因` 映射） |
| `llm-deepseek/translate.spec.ts` | SSE → 块 流式翻译 | ✅ | 本次节B（B1–B5/B7） |
| `llm-deepseek/adapter.spec.ts` | `DEFAULT_MODELS` 模型目录 | ✅ | 本次节D（路5 已落地） |
| `llm-deepseek/request-pricing.spec.ts` | 模型单价映射 | ✅ | 本次节E（`取单价`） |
| `llm-deepseek/serialize.spec.ts` | 请求体序列化 | ✅ | 本次节C（字段映射一致） |
| `llm/properties.spec.ts` | 模型属性/defaults | △ | 节D 部分覆盖（contextWindow/modalities） |
| `llm/invariant.spec.ts` | API 不变量 | △ | `翻译流` 不相交桶语义 |
| `llm-deepseek/topology.spec.ts` | 拓扑/adapter 组合 | △ | 模型目录拓扑 |
| `llm-deepseek/image-tokens.spec.ts` | 图片令牌估算 | ❌ 未移植 | 光明无字节级图片 token（见 §5-D3） |
| `token-meter/*` 4 spec | 上下文分解/路由定价/turn-usage/用量投影 | △ | 路5 已落 `估算上下文分解`/`聚合单次用量`；`route-pricing`/`surface-*` 未移植 |
| `llm/registry`、`dynamic-config`、`egress`、`file-store`、`files-api`、`upload-index`、`sse`、`loader-composition` | 非 LLM 消息/请求域（harness 基础设施） | — | 超出本路对照范围 |

> ✅ 完全覆盖　△ 部分覆盖　❌ 未移植　— 非 LLM 域，不在复刻对照范围

---

## 2. 光明既有测试覆盖标记

任务书要求对照光明已有 11 个 LLM 域测试（标记覆盖状态）。核对结果：

| 光明测试 | 覆盖的上游 spec |
|---|---|
| `test_消息` | message / content |
| `test_客户端` | translate / serialize / assembler |
| `test_客户端深化` / `test_客户端超时` | transport / retry |
| `test_流` / `test_流深化` | translate / sse |
| `test_令牌估算` / `test_令牌估算1.5` | token-meter breakdown |
| `test_模型目录`（路5） | adapter / DEFAULT_MODELS |
| `test_附件准入` / `test_附件准入1.5`（第5轮任务2） | file-store / upload-index（准入侧） |

本次新增 `test_行为对照_LLM.light` 作为**跨域聚合对照**，将上述分散断言按上游 spec 节头归并，便于"翻 spec 即知哪条断言没覆盖"。

---

## 3. 本次新增 `examples/test_行为对照_LLM.light`（六节对标）

| 节 | 对标 spec | 断言要点 |
|---|---|---|
| **A 消息构造** | message / content | `造系统消息` 空文本→`content:[]`、非空→单 text 块、`source={kind:'plugin',plugin}`；`造文本块`/`造助手消息`/`造工具结果消息` 形状逐字段 |
| **B 流式翻译** | translate / sse | B1 文本拼接 + usage 延迟到 DONE；B2 reasoning 先于 text（独立块）；B3 工具调用按 index 重组（`{"city": "Paris"}`）；B4 并行工具调用；B5 空响应→`EMPTY_RESPONSE`；B7 length→`max-tokens` |
| **C 请求体映射** | call-config / serialize | `组装请求`：`model`/`messages`/`stream`/`tools`/`temperature`/`max_tokens` 透传；无工具/无选项时省略对应键 |
| **D 模型目录** | adapter / DEFAULT_MODELS | 默认 `deepseek-flash`、目录 4 条、V41 Flash `in-history`+image 模态、V4-Flash 无 `systemPromptUpdate`、未命中返回空 |
| **E 单价查找** | request-pricing | `deepseek-flash`=0.27/1.10、`gpt-4o`=2.50/10.00、未知/空串回落 1.00/2.00 |
| **F token 分桶** | token-meter breakdown/turn-usage | `估算上下文分解` 三桶==独立估算；`聚合单次用量` 多 attempt 汇总（uncachedInput/output/total/cacheRead/cacheWrite/reasoning，仅全含某桶才输出） |

测试运行：`python 运行.py examples/test_行为对照_LLM.light` → 六节全 `通过`。

---

## 4. 反跑判据（`_antirun_llm_contrast.py`）

判据设计：**改反源码关键字段 → 断言应红 → 还原 → 复绿**，证明对照断言真实捕获回归。

| 判据 | 操作 | 期望 | 结果 |
|---|---|---|---|
| 基线（未改） | — | 绿 | ✅ 绿 |
| **A 请求体字段** | 删 `组装请求` 的 `model` 键 | 红（节C「C 请求体 model 字段」失败） | ✅ 红 |
| A 还原 | 还原 `客户端.light` | 绿 | ✅ 绿 |
| **B token 分桶** | `聚合单次用量` 未缓存输入每桶 +1 | 红（节F「F 未缓存输入=160」失败，得 162） | ✅ 红 |
| B 还原 | 还原 `令牌估算.light` | 绿 | ✅ 绿 |

执行结果：**5/5 成立**。脚本用内存备份做 patch/restore，规避 `运行.py` 退出后异步残留进程短暂清空源文件的竞态，**无 `.bak` 残留**，退出码 0。

运行：`python _antirun_llm_contrast.py`

---

## 5. 行为差异清单（对照中发现的真实不一致）

对照不只是"断言过了"，更记录"上游有、光明缺/不同"之处，供语言/复刻升级参考：

- **D1 — usage 无 `totalTokens` 桶**：上游 `mapUsage` 在 `prompt_tokens`+`completion_tokens` 之外补 `totalTokens`；光明 `造用量` 仅输出 `输入/输出`（及可选的 `缓存读/推理`）。已在节B1 显式断言 `包含("totalTokens")==假`。属**复刻缺口**，非语言缺陷（纯语义未实现）。
- **D2 — 消息构造按引用组装、非深拷贝**：上游 `createXxxMessage` 经 `deep-freeze` 保证消息与传入 content **脱钩（detached）**；光明 `消息.light` 直接 `设 消息 为 [...]`/字典组装，**按引用**组装，调用方改入参会污染已构造消息。属**行为差异**，当前无断言覆盖（建议后续补回归）。
- **D3 — 无图片令牌计数**：`image-tokens.spec.ts` 的字节级图片 token 估算（`estimateImageTokens`）光明未移植（无字节级模型），故节E 仅对标模型单价表，未对标图片单价。属**未移植域**。

未新增语言缺陷（`语言缺陷账.md` 本路只读，未登记）。

---

## 6. 未移植项与理由

| 未移植项 | 理由 |
|---|---|
| `image-tokens`（图片令牌估算） | 光明无字节级图片 token 模型，等价能力缺失 |
| `token-meter/route-pricing`、`surface-fold`、`surface-projection`、`token-usage-projection` | 缺单价路由表 / surface 模型，且属路5 已按互斥表移交的未移植项 |
| `registry`/`file-store`/`files-api`/`upload-index`/`egress` 等 | 非 LLM 消息/请求域，超出本路"消息/请求行为对照"范围 |

---

## 7. 验证结果 / 运行方式

| 项 | 命令 | 结果 |
|---|---|---|
| 新增对照测试 | `python 运行.py examples/test_行为对照_LLM.light` | ✅ 六节全通过 |
| 反跑判据 | `python _antirun_llm_contrast.py` | ✅ 5/5 成立 |
| 源码污染检查 | `git diff src/客户端.light src/令牌估算.light` | ✅ 无差异（src 全程只读） |

交付物：
- `examples/test_行为对照_LLM.light` — 六节 LLM 行为对照（节头对标上游 spec）
- `_antirun_llm_contrast.py` — 反跑判据（A 请求体字段 / B token 分桶）
- `docs/功能对标/_task3_LLM对照_交付报告.md` — 本报告
