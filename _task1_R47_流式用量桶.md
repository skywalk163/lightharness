# 第47轮任务1交付：流式用量桶（#5/#6）

> 日期：2026-09-17 ｜ 状态：**完成**

## 一、上游对照（只读）

- `packages/llm/llm/src/types.ts`：`TokenUsage = { inputTokens, outputTokens, totalTokens?,
  cacheReadTokens?, cacheWriteTokens?, reasoningTokens? }`——不相交桶；
  计费输入 = 输入 + 缓存读 + 缓存写 三桶之和（types.ts 头注 "billed input = sum of the three"）。
- `packages/llm/llm-deepseek/src/translate.ts:55-68`（mapUsage）：
  缓存读 = `prompt_tokens_details.cached_tokens ?? prompt_cache_hit_tokens`；
  输入 = `prompt_tokens - cacheRead`（DeepSeek 把命中折进 prompt 总数须减出）；
  `totalTokens = prompt_tokens + completion_tokens`（原始合计）。
- R47 新增映射：`prompt_cache_miss_tokens` → 缓存写（DeepSeek 口径：命中 + 未命中 = prompt_tokens）。

## 二、修改（互斥区内）

### src/流.light
1. `造用量` 增加第 5 个可选参 `缓存写 = 空`（**追加在末位**，既有四参位置调用
   `造用量(输入, 输出, 缓存读, 推理)` 完全兼容）。
2. 新增 `用量桶值(用量, 桶名)`：缺桶归 0 的统一读取。
3. 新增 `用量累计(用量表)`：多块用量按桶累加——缓存读/缓存写/推理各自独立累计不混桶；
   桶在所有输入都缺席则不带该键；`totalTokens` 任一输入带即累计。
4. 新增 `计费输入(用量)`：输入 + 缓存读 + 缓存写（上游计费口径）。
5. 补导出表（原文件无导出段，不影响既有导入路径）。

### src/客户端.light（仅 `翻译用量` 段）
1. 缓存读改双路：`prompt_tokens_details.cached_tokens` 优先，回落 `prompt_cache_hit_tokens`。
2. 新增缓存写：`prompt_cache_miss_tokens` → `缓存写` 桶。
3. `造用量` 调用改五参；其余逻辑（输入减出、totalTokens 合计、0→空归一）不动。

## 三、新增测试

`examples/test_R47_流式用量桶.light`（rc=0）：
- 五桶形状（含缓存写）与四参位置兼容；
- 三段增量累计：输入 220/输出 60/缓存读 50/缓存写 8/推理 12——三桶互不相等不混桶；
- 缺桶归零 + 计费输入（278 = 220+50+8）；
- 翻译用量 wire 三形态（hit+miss+reasoning / details.cached_tokens / 无缓存字段）；
- usage 块经块组装器保真（组装器.用量() 回读完整分桶）。

## 四、回归

- 既有 `test_R43_真实LLM往返.light`、`test_mock大模型服务器.light`、`test_SSE.light` 全 rc=0；
- 本机全量 pytest：见 `_task6`/收口记录（基线外零新增红）。

## 五、铁律核对

- 零修改真实 HTTP/SSE 传输层（`HTTPPost`/`SSE解析器`/`真实对话协程` 未动）；
- 只补词汇/累计纯逻辑；既有测试不破。
