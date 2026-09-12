# 任务5 交付报告：负零数值域区分（T2-D4 ⚪）

> 任务来源：`G:\dswork\duan-light-merge\光明语言改进_并行任务书.md` 任务5
> 日期：2026-09-12
> 铁律：语言修复落在 light-merge（编译器 + stdlib 地板）；lightharness 仅作验证（简化绕法 + 全量 CI）。
> 决策：**方案A（语言层提供 `是负零` 判定原语）** —— 上游真实拒绝负零，非文档性声明。

---

## 一、上游核实结论（任务书验收 #1）

读 `G:\github\deepseek-harness` 源码与测试，**上游确实拒绝负零序号**：

- 实现：`packages/session/session-format/src/json.ts:24`
  ```ts
  if (!Number.isSafeInteger(value) || (value as number) < 0 || Object.is(value, -0)) {
    throw new SessionFormatError(`${label} must be a non-negative safe integer`)
  }
  ```
  恢复边界的 `非负安全整数` 校验显式用 `Object.is(value, -0)` 拒绝负零。
- 测试断言（4 处）：
  - `session-format/tests/json.spec.ts:12` — 参数化用例 `['negative zero', -0]` 期望抛错
  - `session-log-deepseek/tests/invariant.spec.ts:66` — `rejects negative-zero format versions restored across the owned invariant boundary`
  - `session-persistence-jsonl/tests/generation.spec.ts:847` — `rejects a negative-zero physical version`
  - `session-persistence-jsonl/tests/jsonl.spec.ts:2108 / 2129` — 负零 `createdAt` / `delegationDepth` 拒绝

**结论：T2-D4 是真实行为差异（非文档声明），采用方案A。**

## 二、根因（Root Cause）

- 上游 JS 数字无 int/float 之分，`-0` 保留 IEEE 754 符号位；光明/Python 中 `-0 == 0` 为 `True`、`hash(-0) == hash(0)`，语言层不可区分。
- 此前 `lightharness/src/会话格式.light` 的 `段落 安全整数` 仅判 `值 < 0`，负零（-0.0）被放行，与上游 `must be a non-negative safe integer` 语义不符。

## 三、做了什么（Fix Points）

### 1. 语言本体（light-merge）
- `stdlib/内置核心判型.light:79-84`：新增 `段落 是负零` —— **纯光明实现（零 Python 导入）**：`isinstance(值, float)` 且 `值 == 0.0` 且 `转字符串(值)` 以 `-` 开头。-0.0 是唯一以 `-` 开头的零值浮点。
- `stdlib/builtins.py:946-953`：`是负零` 一行转发到 `内置核心判型.是负零`。
- `src/code_generator.py`：`builtin_map` 注册 `'是负零'` + 无 stdlib 兜底 lambda（`math.copysign(1.0, v) < 0.0`）。
- `src/code_generator_unified.py` / `src/keywords.py` / `src/type_inferencer.py`：统一 builtin_map / 关键词表 / 返回类型（`TYPE_BOOLEAN`）。
- `任务书/自举地板清单.json`：登记 `是负零`（has_light_impl，证据行 `内置核心判型.light:79`）。

### 2. 差分测试（light-merge）
- `tests/unit/test_地板搬迁_判型_S2.py`：新增 oracle `_oracle_是负零`（math.copysign）与逐条对拍参数化用例（负零矩阵 11 条），另有「真身 vs oracle 不得分叉」「只认浮点负零」两防腐用例。

### 3. lightharness 验证侧
- `stdlib/内置核心判型.light` / `stdlib/builtins.py`：自包含 stdlib 同步 `是负零`。
- `src/会话格式.light:31-38`：`段落 安全整数` 将 `是负零` 校验置于 `是整数` **之前** —— -0.0 是 float，放后面会被「must be an integer」先截走，负零将得不到上游的「non-negative」语义；负零是数值域非负性违规，不是整数形态违规。
- `examples/test_行为对照_会话持久化.light`：新增 `6d 负零拒绝` —— `转浮点("-0.0")` 走 `是负零` → 期望 `must be non-negative`（对齐上游）。注：JSON 文本 `"-0"` 在 Python/光明中解析为整数 0，符号位在解析层丢失（JS 数字无 int/float 之分），该形态无法在语言层区分，属宿主解析差异；数值域负零（float -0.0）已显式拒绝。
- `_antirun_session_contrast.py`：新增判据 D —— 将 6d 期望文案改反（`must be an integer`）→ 判红；恢复 → 绿。
- `docs/功能对标/行为差异清单.md`：T2-D4 判定 ✅（第11轮已修复），汇总统计回填（已修复 12 项）。

## 四、最小复现（Minimal Repro）

- 修复前：`安全整数(转浮点("-0.0"), "seq")` 通过（负零被 `值<0` 放行），与上游抛错不符。
- 修复后：`是负零(转浮点("-0.0"))` → 真；`安全整数(转浮点("-0.0"), "seq")` 抛 `invalid seq: must be non-negative`。
- 回归载体：`examples/test_行为对照_会话持久化.light` §6d。

## 五、验证（Verification）

| 项 | 结果 |
|---|---|
| light-merge 判型差分测试 `test_地板搬迁_判型_S2.py` | ✅ 361 passed（含 是负零 全部用例） |
| `examples/test_行为对照_会话持久化.light` | ✅ 全部通过（含 6d 负零拒绝） |
| 反跑判据 `_antirun_session_contrast.py` | ✅ A/B/C/D 四判据全红，字节级恢复校验通过 |
| lightharness 全量 CI（`scripts/ci_test.py`） | ✅ 236 passed + 冒烟 5 例全通过 |

### 顺带收尾（并行任务2 遗留）
- 全量 CI 首次跑时唯一红例 `examples/test_修复_LLM.light`：任务2 交付把 `拷贝内容块表` 绕法改为 `深拷贝` 时**遗漏了该第9轮回归测试的同步**（`src/消息.light` 已删 `拷贝内容块表`，测试仍导入）。本次已同步：导入行移除 `拷贝内容块表`、独立验证段落改用 `深拷贝`（全局内置，无需从 `消息` 导入）。属验证仓库测试同步，非语言改动。

## 六、铁律符合性

- ✅ 语言修复主体落在 light-merge（判型模块 + builtins + 三处注册 + 地板清单）。
- ✅ lightharness 仅作验证：恢复边界接入 `是负零` 拒绝逻辑（绕法即真语义，无简化可减）。
- ✅ 附最小复现（§6d）+ 反跑判据（D）+ 全量 CI 全绿。
- ✅ 交付报告含上游核实结论（json.ts:24 + 4 处测试断言）。

## 七、交付物清单

- `light-merge/stdlib/内置核心判型.light`：`段落 是负零`（纯光明实现）。
- `light-merge/stdlib/builtins.py`：`是负零` 转发。
- `light-merge/src/code_generator.py` / `code_generator_unified.py` / `keywords.py` / `type_inferencer.py`：注册。
- `light-merge/任务书/自举地板清单.json`：登记 `是负零`。
- `light-merge/tests/unit/test_地板搬迁_判型_S2.py`：差分测试。
- `lightharness/stdlib/内置核心判型.light` / `builtins.py`：自包含同步。
- `lightharness/src/会话格式.light`：`安全整数` 负零拒绝（置前校验）。
- `lightharness/examples/test_行为对照_会话持久化.light`：§6d 负零拒绝断言。
- `lightharness/_antirun_session_contrast.py`：判据 D。
- `lightharness/examples/test_修复_LLM.light`：任务2 遗留同步（`拷贝内容块表` → `深拷贝`）。
- `lightharness/docs/功能对标/行为差异清单.md`：T2-D4 → ✅ 已修复。
