# 第9轮 任务2 交付报告 —— LLM 域修复（T3-D1 / T3-D2）

> 日期：2026-09-12 ｜ 仓库：`G:\dswork\duan-light-merge\lightharness`
> 编译器：`G:\dswork\duan-light-merge\light-merge`（LIGHT_MERGE）
> 依据：`docs/功能对标/行为差异清单.md`（T3-D1 / T3-D2）
> 上游（只读）：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 上游关键参考：`packages/llm/llm-deepseek/src/translate.ts:55-72`（`mapUsage`）、`packages/llm/llm/tests/message.spec.ts`、`assembler.spec.ts`

---

## 一、上游依据与差异根因

| 差异 ID | 模块 | 上游期望 | 光明实际 | 根因 |
|---|---|---|---|---|
| T3-D1 | `src/客户端.light` `翻译用量` | `mapUsage` 在 `inputTokens`/`outputTokens` 之外补 `totalTokens = prompt_tokens + completion_tokens`（原始合计，含缓存命中部分） | 仅 `输入`/`输出`（+可选 `缓存读`/`推理`），无 `totalTokens` 桶 | 复刻缺口，未实现该桶 |
| T3-D2 | `src/消息.light` `造Xxx消息` | `createXxxMessage` 经 `deep-freeze` 与传入 `content` **脱钩**，调用方改入参不影响已构造消息 | 按引用组装 `content`，调用方改入参会污染已构造消息 | 光明无深拷贝/冻结内置 |

**关键语义澄清（T3-D1）**：上游 `totalTokens` = `prompt_tokens + completion_tokens`（**原始合计**），并非任务书字面上的「输入+输出」。当存在缓存命中时二者不等：如 `prompt_tokens=100, completion_tokens=20, prompt_cache_hit_tokens=40` → 上游 `totalTokens=120`（含缓存命中），而「未缓存输入+输出」=60+20=80。本次严格对齐上游，采用 `prompt_tokens + completion_tokens`。

---

## 二、修复点（文件:行）

### T3-D1 —— 补 `totalTokens` 桶
- `src/客户端.light:35` 段落 `翻译用量`：新增 `设 总计 为 用量["prompt_tokens"] + 用量["completion_tokens"]`（:46），并在构造结果后补 `结果["totalTokens"] 为 总计`（:50）。
- 仅改动 wire→usage 映射路径（`翻译用量` = 上游 `mapUsage` 等价层）；`造用量`（`src/流.light`，通用 TokenUsage 构造器，测试直接调用）与 `聚合单次用量`（`src/令牌估算.light:142` 已有 `totalTokens`）保持不变，避免影响既有测试语义。

### T3-D2 —— 消息构造深拷贝脱钩
- `src/消息.light:65` 新增段落 `拷贝内容块表`：每块字典逐键拷贝（`遍历 键 之 块` + `新块[键] 为 块[键]`），返回新列表。
- 以下构造函数在组装时统一用 `拷贝内容块表(内容)` 代替原引用：
  - `造用户消息`（:78）、`造用户消息带来源`（:82）、`造助手消息`（:86）、`造助手消息带回放`（:93）、`造工具结果消息`（内层 `造工具结果块(... 拷贝内容块表(内容) ...)` 于 :97）、`造系统消息`（content 本地构造，亦统一包裹 :107，行为不变、风格一致）。
- 绕法登记为语言缺陷 **L-083**（见 §六），未引入任何 Python 依赖。

---

## 三、测试与 CI

- 新建 `examples/test_修复_LLM.light`：覆盖 T3-D1（含缓存命中/无缓存/推理桶三组数据，断言 `totalTokens` 存在且 = `prompt+completion`）+ T3-D2（用户/用户带来源/助手/助手带回放/工具结果/系统消息 及 `拷贝内容块表` 独立验证，断言调用方改入参不影响已构造消息）。**运行通过（rc=0）**。
- 既有回归（本次改动相关，已逐一复跑全绿）：
  - `examples/test_客户端.light`（含 `翻译用量` 断言）✅
  - `examples/test_消息.light` ✅
  - `examples/test_行为对照_LLM.light`（含 §B1 usage，本次同步更新断言，见 §五）✅
  - `examples/test_流.light` / `test_令牌计量.light` / `test_令牌估算.light` / `test_会话.light` / `test_代理深化.light` / `test_子智能体.light` / `test_压缩自动.light` / `test_钩子.light` / `test_交付.light` / `test_附件准入1.5.light` 全部 ✅（确认 `消息.light` 拷贝改造未引入回归）。
- **全量 CI 由路M 统一跑**（`python scripts/ci_test.py`，目标 222 passed / 0 failed 保持全绿）。

---

## 四、反跑判据（≥2 项，内存级备份/恢复 src）

脚本：`_antirun_llm_fix.py`（内存备份 `客户端.light`/`消息.light` 原式，patch→立跑→从内存还原，规避 `运行.py` 异步残留清空源文件的竞态，对齐第8轮教训）。

| 项 | 操作 | 期望 | 结果 |
|---|---|---|---|
| 基线 | 原始 src | 绿 | ✅ 成立 |
| A | `客户端.light` 删 `设 总计`+`结果["totalTokens"] 为 总计` | totalTokens 断言红 | ✅ 成立 |
| B | `消息.light` 把 `拷贝内容块表(内容)` 全改回 `内容`（直接引用） | 脱钩断言红 | ✅ 成立 |
| 恢复 | 还原两文件原式 | 绿 | ✅ 成立 |

**反跑结论：4/4 成立**。

---

## 五、既有断言更新

| 文件 | 位置 | 原断言（差异态） | 新断言（修复态） | 说明 |
|---|---|---|---|---|
| `examples/test_行为对照_LLM.light` | §B1 末尾（原 :111-112） | `块B1[用量idx]["usage"].包含("totalTokens") == 假`（「光明无 totalTokens 桶」） | `== 真`，且 `块B1[用量idx]["usage"]["totalTokens"] == 7`（=5+2） | T3-D1 已修复，该条差异断言转为对齐断言（行为对齐，非测试迁就 bug，符合铁律 #2）。**注意**：该文件不在任务2 互斥表「可追加测试」清单内，但铁律 #2 要求修复致红必须同步更新，故更新并特此说明，供路M 复核。 |

> 说明：`test_行为对照_LLM.light` 为第8轮对照产物，本次仅调整其「差异记录」性质的断言以反映修复；其余 §A–§F 不受影响。

---

## 六、差异清单回填状态

- 本次修复 `T3-D1`、`T3-D2` 两项，应在 `docs/功能对标/行为差异清单.md` 标记 **✅ 第9轮已修复**。
- **按文件互斥表，`行为差异清单.md` 为「路M 统一回填」只读项，本任务未直接改动该文件**，回填状态移交路M 在收口时统一执行（见 §八）。

---

## 七、语言缺陷新登记

- **L-083**（光明无深拷贝/浅拷贝/冻结内置，消息构造需逐块拷贝脱钩）—— 已登记至 `docs/功能对标/语言缺陷账.md`（附于 L-081 之后）。
- 最小复现：`examples/_repro_L083.light`（修复形态，运行 rc=0）。
- 绕法：`src/消息.light` `拷贝内容块表` + 全构造器统一调用，已落地。

> 注：互斥表将 `语言缺陷账.md` 标注为「路M 统一登记」只读项；但任务2 prompt 与铁律 #4 均明确要求「登记 L-083（缺陷账 + _repro_L083.light）」，且本任务为单任务独立执行（非四路并行冲突场景），故按要求登记。路M 收口时**请勿重复登记 L-083**。

---

## 八、移交清单（给路M）

1. **已改 src（互斥表任务2 内）**：`src/客户端.light`（T3-D1，:46/:50）、`src/消息.light`（T3-D2，:65 新增 + :78/:82/:86/:93/:97/:107 调用）。
2. **新增测试/脚本**：`examples/test_修复_LLM.light`、`_antirun_llm_fix.py`、`examples/_repro_L083.light`。
3. **既有断言更新**：`examples/test_行为对照_LLM.light` §B1（见 §五）。
4. **缺陷账**：L-083 已登记（路M 勿重复）。
5. **差异清单回填**：T3-D1、T3-D2 → 标记「✅ 第9轮已修复」（由路M 执行）。
6. **全量 CI**：请路M 跑 `scripts/ci_test.py` 复核 222 passed / 0 failed（本任务单测与受影响回归均已本地复绿）。

---

## 九、小结

- T3-D1：严格对齐上游 `mapUsage`（`totalTokens = prompt_tokens + completion_tokens`，含缓存命中），仅作用于 wire→usage 映射层，零改动既有 `造用量`/`聚合单次用量` 语义。
- T3-D2：以「逐块拷贝」绕法实现消息构造脱钩，行为对齐上游 `deep-freeze`，登记 L-083。
- 反跑 4/4、新增 + 既有回归全绿，无越界改 src。
