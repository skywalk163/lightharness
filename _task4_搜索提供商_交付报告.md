# 任务4 交付报告 —— 搜索提供商域（web-search 族，纯逻辑面）

> 轮次：复刻 第14轮 ｜ 日期：2026-09-13 ｜ 对标卡：**#95（新增）**
> 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 本路可写文件（4 个，全部新增，零越界）：
> `lightharness/src/搜索提供商.light`（478 行 / 40 段）
> `lightharness/examples/test_搜索提供商.light`（286 行 / 152 断言）
> `lightharness/_antirun_search.py`
> `lightharness/_task4_搜索提供商_交付报告.md`（本文件）

---

## 一、上游对应表（文件 / 行号 / 核心语义）

| 上游文件 | 行 | 核心语义 | 本模块落点 |
|---|---|---|---|
| `packages/web/web/src/types.ts` | 1–130 | `WebSearchRequest` / `WebSearchResult` / `WebSearchSource` 统一词表 | §1 统一参数模式、§4 归一结果形状 |
| `web-search-deepseek/src/provider.ts` | 27 / 35 / 38 / 41 / 44 / 47 | `DEEPSEEK_PROVIDER_ID='deepseek-official'`、`DEFAULT_BASE_URL='https://api.deepseek.com/anthropic/v1'`、`DEFAULT_MODEL='deepseek-v4-flash'`、`DEFAULT_API_VERSION='2023-06-01'`、`DEFAULT_MAX_TOKENS=4096`、`DEFAULT_MAX_USES=5` | §0 常量、§2 `深寻默认参数` |
| 同上 | 56 / 88 | `DeepSeekSearchLlmRequest`、`DeepSeekSearchProviderOptions` | §3 请求形状 |
| 同上 | 121 `citationSnippets` | 从 content blocks 抽 `{url → snippet}` 映射 | §4 `引用摘录` |
| 同上 | 145 `mapAnthropicResponse` | Anthropic 风格响应 → `WebSearchResult` | §4 `归一深寻响应` |
| 同上 | 180 `class DeepSeekSearchProvider`（313–370 为宿主面） | provider 实例：可用性/请求/解析 | §2 `可服务` + §5 错误族 |
| `web-search-exa/src/provider.ts` | 19 / 22 / 25 / 28 | `EXA_PROVIDER_ID='exa'`、`DEFAULT_BASE_URL='https://api.exa.ai'`、`DEFAULT_SEARCH_TYPE='auto'`、`DEFAULT_HIGHLIGHTS_PER_RESULT=1` | §0 常量、§2 `艾克萨默认参数` |
| 同上 | 56 `mapExaResult` / 74 `mapExaResponse` | `results[] → {title,url,snippet,score,publishedDate}`；`text` 缺省回退 `highlights[0]` | §4 `归一艾克萨响应`、`首个非空高亮` |
| `web-search-perplexity/src/provider.ts` | 19 / 22 / 25 / 28 / 31 | `PERPLEXITY_PROVIDER_ID='perplexity'`、`DEFAULT_BASE_URL='https://api.perplexity.ai'`、`DEFAULT_MODEL='sonar'`、`DEFAULT_MAX_TOKENS=1024`、`PerplexityRecency='day'|'week'|'month'|'year'` | §0 常量、§2 `彭普默认参数`、`时间范围枚举` |
| 同上 | 56 `mapPerplexityResult` / 73 `mapPerplexityResponse` | `search_results[] → source`；缺失时回退 `citations`（纯 URL 串，snippet 空） | §4 `归一彭普响应` |
| 三家 `provider.ts` | 368 / 158 / 164 `isPositiveInteger` | 正整数判定（默认值边界） | §0b `是正整数` |

**上游合并说明**：任务书要求三提供商合并一路（对标卡 #95），本模块以「统一参数模型 + 三家适配器 + 注册表」结构承载，避免三份复制。

---

## 二、实现要点

1. **§1 统一参数模式**（`统一参数模式` / `校验搜索参数` / `有搜索参数错误` / `归一参数`）
   复用 `src/工具.light` 的 `校验参数`（JSON Schema 子集校验器），把三家的公共参数收敛为一张模式表：
   `query`（必填、minLength 1）、`limit`（integer、minimum 1、maximum 100）、
   `time_range`（enum `day|week|month|year`）、`language`（minLength 2）、`safesearch`（enum `off|moderate|strict`）；
   各提供商特有参数（deepseek `model`、exa `type`、perplexity `model`）走 `选项` 覆盖。
   校验错误结构 = `{路径, 原因, 期望}`，原因词汇沿用校验器：`missing` / `minLength` / `minimum` / `maximum` / `enum`。

2. **§2 默认值填充与可用性**（`深寻默认参数` / `艾克萨默认参数` / `彭普默认参数` / `填默认参数` / `可服务`）
   上游 `*_DEFAULT_*` 常量逐一对齐（`baseURL/model/apiVersion/maxTokens/maxUses/searchType/highlightsPerResult`）；
   `填默认参数` = 默认表 ← 宿主 `选项` 覆盖（逐键覆写）；
   `可服务`（上游 `available()`）= 密钥为**非空字符串** 且 该提供商关键上限为**正整数**
   （DeepSeek：`maxTokens` + `maxUses`；Exa：`highlightsPerResult`；Perplexity：`maxTokens`）；URL 可解析性留在宿主面。

3. **§3 请求形状构造**（`公共请求头` / `构造深寻请求` / `构造艾克萨请求` / `构造彭普请求` / `构造请求`）
   **只造字典不发送**：返回 `{url, method:"POST", headers, body}`。
   公共头 = `content-type`/`accept`（`application/json`）+ `user-agent: deepseek-harness/0.0.1`（上游 `USER_AGENT`）
   + `authorization: Bearer <key>`；DeepSeek 额外补 `x-api-key` 与 `anthropic-version`。
   三家 body 结构（与上游 fetch 入参逐字段对齐）：
   - DeepSeek `POST {base}/messages` → `{model, max_tokens, messages:[{role:"user",content:[{type:"text",text}]}], tools:[{type:"web_search_20250305", name:"web_search", max_uses}]}`；
   - Exa `POST {base}/search` → `{query, type, contents:{highlights:{highlightsPerUrl}}, numResults?}`（`numResults` 仅在归一结果含 `maxResults` 时出现）；
   - Perplexity `POST {base}/chat/completions` → `{model, max_tokens, messages:[{role:"user",content}] , search_recency_filter?}`（仅当归一结果含 `timeRange` 时出现）。
   未知提供商统一抛 `unknown web search provider: <名>`（与上游英文文案一致）。

4. **§4 响应归一**（`归一深寻响应` / `归一艾克萨响应` / `归一彭普响应` / `归一搜索响应` / `归一空响应` / `归一异常响应`）
   统一输出 `[{title, url, snippet, score?, publishedDate?}]`。
   异常/空响应一律归一为**空列表 + 错误信息**（不抛异常），保证宿主侧可降级。

5. **§5 错误族**（`码缺密钥` / `码限流` / `码参数非法` / `码提供商错误` / `码空响应` / `码解析失败` / `码已中止` + `状态码转错误码`）
   词汇：`API_KEY_MISSING` / `RATE_LIMITED` / `INVALID_PARAM` / `PROVIDER_ERROR` / `EMPTY_RESPONSE` / `PARSE_ERROR` / `ABORTED`；
   映射：`401→API_KEY_MISSING`、`429→RATE_LIMITED`、`400→INVALID_PARAM`、`5xx→PROVIDER_ERROR`，另有 `上游码转本卡码` 做上游错误码收敛。

6. **§6 提供商注册表**（`提供商列表` / `是已知提供商` / `提供商描述` / `取提供商` / `提供商注册表`）
   三家以 `名称/描述/默认端点/默认模型/认证头` 入册；未知提供商抛 `unknown web search provider: <名>`。

**语言绕法**（沿用既有缺陷，无新增）：
- L-084：裸标识符避 `为` 字；
- L-004/L-090：避保留字与内建前缀（`字典/包含/输出/空/返回/设/是/并/之/映射`）；
- L-045：`写` 只接受字面量串或变量 —— 全部诊断改走 `抛出 新建 错误("…" + 转字符串(x))`；
- 无可直接调用的 `trim` 类字符串方法（`str` 无中文方法名）→ 统一用 `字符串工具.去除首尾空白` 与手写 `去空白长`。

---

## 三、测试验证

命令：`cd lightharness && python 运行.py examples/test_搜索提供商.light`

```
===== 第 14 轮任务 4：搜索提供商域（纯逻辑面）=====
test_搜索提供商 PASS
```

`rc=0`，152 条断言全绿，覆盖：参数校验各原因（`missing`/`minLength`/`minimum`/`maximum`/`enum`）、
枚举表、默认值填充、可用性判定、三家请求形状（URL/headers/body）、三家响应归一（含 Exa highlights 回退、
Perplexity citations 回退）、空/异常响应归一、错误族各码文案、HTTP 状态码映射、注册表与未知提供商抛错。

---

## 四、反跑结果（3/3 ALL OK）

命令：`python _antirun_search.py`

```
=== 第 14 轮任务 4 反跑判据（搜索提供商域）===
✓ A 响应归一不再提取 url (判红运行 rc=1)
✓ B 参数校验 limit 上界放开 (判红运行 rc=1)
✓ C 401 不再映射为 API_KEY_MISSING (判红运行 rc=1)
✓ 字节级恢复校验 (sha256 31b87bb1e99f)
✓ 恢复后回归绿 (rc=0，PASS 已打印)
ALL OK
```

判据细节（变异点均落在 `src/搜索提供商.light`，逐条以「变异未命中即判失败」守护）：
- A：DeepSeek 归一里 `设 来源 为 {"url": 地址}` → `设 来源 为 {}`（不再提取 url）→ 取 url 断言红；
- B：参数模式 `属性["limit"] 为 {"type":"integer","minimum":1,"maximum":100}` → 去掉 `"maximum": 100` → `limit=101` 应报 `maximum` 的断言红；
- C：`状态码转错误码` 的 `如果 状态 == 401: 返回 码缺密钥` → `返回 码提供商错误` → 401 映射断言红。
恢复走 `finally`，逐字节 sha256 校验通过（`31b87bb1e99f`）。

---

## 五、未移植项（宿主面登记）

| 上游位置 | 内容 | 处置 |
|---|---|---|
| 三家 `provider.ts` fetch 段 | `fetch`/`undici` 网络 IO、`redirect:'error'`、重定向策略 | 剔除，宿主注入响应 |
| deepseek `provider.ts:331–366` | `abortable` / `throwIfSearchAborted` / `searchAborted` / `isAbortError`、`AbortSignal` 竞速 | 剔除（宿主超时层） |
| 三家密钥解析 | `resolveApiKey` 异步凭证解析、`CredentialRef` 诊断 | 剔除，密钥入参化 |
| `WebError` / `HarnessError` | 类体系与堆栈语义 | 以 `{ok, code, message, provider}` 纯字典承载 |
| deepseek `recordRequest` | 会话事件 `web/deepseek-search-llm-request` 落盘 | 剔除（会话层职责） |
| 重试/退避 | provider 内重试与超时 × 重试联动 | 剔除（宿主层） |

任务书扩展（上游无对应，按 §复刻范围 实现）：
`limit/time_range/language/safesearch` 统一参数与 `[1,100]` 上限；六码错误族与 HTTP 状态码映射
（上游一律 `WEB_PROVIDER_ERROR`，状态码只进消息文本）；Perplexity `time_range → search_recency_filter`。

---

## 六、语言差异（新缺陷）

**本路无新增缺陷**。全程只沿用既有登记项（L-004 / L-045 / L-084 / L-090），未出现需要新登记的
词法/语法/语义障碍。任务书预分配的 **L-113 / L-114 / L-115 本路未占用**，请路M 收口时保持空缺或顺延。

（本轮新增的两项缺陷 L-119 / L-120 由任务6 登记，见 `_task6_会话标题族_交付报告.md` §六；
其触发面为「v4.0 L0 单字别名」与「标识符被关键字全切分」，与本域无关。）

---

## 七、移交清单（→ 路M）

| # | 事项 | 说明 |
|---|---|---|
| 1 | 对标卡 #95 | web-search 族（deepseek+exa+perplexity 合并一路）→ `src/搜索提供商.light`，建议状态 `done` |
| 2 | 缺陷编号 | L-113~L-115 本路**未占用**，请勿分配 |
| 3 | 行为差异 | 见本文 §一「上游合并说明」/§二 1.4.5.6 / §五 任务书扩展 —— 请汇总为 R14-D4 |
| 4 | 只读引用 | `src/工具.light`（`校验参数` 复用）、`src/抓取策略.light`、`src/网页搜索.light`（对标卡 #51，同域参考）均**只读未改** |
| 5 | 提交文件 | `src/搜索提供商.light`、`examples/test_搜索提供商.light`、`_antirun_search.py`、本报告（4 个新文件） |
| 6 | 本路测试命令 | `python 运行.py examples/test_搜索提供商.light`（勿与其它路并发跑，避免 `_run_src` 内联路径互扰） |
