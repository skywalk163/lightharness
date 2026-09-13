# 第14轮路M收口说明

> 日期：2026-09-13 ｜ 上游：`G:\github\deepseek-harness` @ a305303422（0.1.5-rc.2）
> 编译器：`G:\dswork\duan-light-merge\light-merge` ｜ 工作区：`G:\dswork\duan-light-merge\lightharness`（branch main）
> 前置：第13轮收口 `80c9bc0` + 4 决策落地 `ebbcdb3`（CI 267 全绿）

---

## 一、6 路交付总览

| 任务 | 域 | 上游包 | 光明模块 | 测试断言数 | 反跑 | 新缺陷 |
|---|---|---|---|---|---|---|
| 1 | fs 工具 | fs/tool-fs（11文件，剔除sandbox/session-cwd） | `src/文件系统工具.light` | ≥12 | 3/3 | 无（L-104空缺） |
| 2 | 代理团队 | experimental/agent-team（14文件纯逻辑，剔除client/persisted） | `src/代理团队.light` | ≥15 | 3/3 | 无（L-107~110空缺） |
| 3 | JSONL持久化 | session/session-persistence-jsonl（3文件纯逻辑，剔除storage/lease/worker/win32/zstd） | `src/会话持久化JSONL.light` | ≥45（8组） | 3/3 | 无（L-111~112空缺） |
| 4 | 搜索提供商 | web/web-search-{deepseek,exa,perplexity}（9文件，剔除fetch/AbortSignal） | `src/搜索提供商.light` | 152 | 3/3 | 无（L-113~115空缺） |
| 5 | 类型系统 | typert/generator+protocol（8文件纯逻辑，剔除cordis-catalog/tsdown-plugin/workspace） | `src/类型系统.light` | 167 | 3/3 | **L-116** |
| 6 | 会话标题族 | session/session-title族（8文件，剔除client/LLM调用） | `src/会话标题族.light` | 159 | 3/3 | **L-119, L-120** |

**文件互斥零越界**：6 路均只新增文件，未修改任何既有 `src/` 模块。

---

## 二、分路提交链

```
bcdae77  任务1(fs工具域): tool-fs纯逻辑面(read/write/edit/diff/错误族+呈现形状; 反跑3/3)
f1cf19f  任务2(代理团队域): agent-team纯逻辑(任务看板/任务图/名册/邮箱/日志/活动/生命周期/不变量; 反跑3/3)
15196a6  任务3(JSONL持久化域): session-persistence-jsonl纯逻辑面(行格式/生成/迁移校验; 反跑3/3)
de1db99  任务4(搜索提供商域): web-search三提供商纯逻辑面(参数schema/请求构造/响应归一/错误映射; 反跑3/3)
a205c99  任务5(类型系统域): typert generator+protocol纯逻辑面(协议消息/类型IR/分析器/渲染器/发射器; L-116; 反跑3/3)
405c039  任务6(会话标题族域): session-title族纯逻辑面(类型/规范化/不变量/提示构造/事件形状; 命名冲突改族名; L-119/L-120; 反跑3/3)
```

---

## 三、路M 过程中发现并修复的问题

### 3.1 任务1/2/3 反跑脚本路径问题（已修复）

- **现象**：任务1/2/3 的反跑脚本 `_antirun_t1_文件系统工具.py` / `_antirun_t2_代理团队.py` / `_antirun_t3_会话持久化JSONL.py` 由执行者放在上级目录 `G:\dswork\duan-light-merge\`，脚本内 `BASE = os.path.join(os.path.dirname(__file__), "lightharness")` 假设脚本在上级目录。
- **处置**：路M 将3个脚本移到 `lightharness/` 根目录（与其他反跑脚本统一），并将 BASE 改为 `os.path.dirname(os.path.abspath(__file__))`（脚本所在目录即 lightharness）。修复后6反跑全 ALL OK。
- **教训**：反跑脚本应统一放在 lightharness 根目录，路径用 `os.path.dirname(os.path.abspath(__file__))` 自定位，不假设上级目录结构。

### 3.2 任务6 命名冲突（执行者已正确处理，路M裁定确认）

- **现象**：任务书写作 `src/会话标题.light` / `examples/test_会话标题.light`，但这两个文件已被第49号对标卡（session-title/normalize）占用且已 done（`src/会话标题.light` 238 行）。
- **处置**：任务6执行者正确地改用 `src/会话标题族.light` / `examples/test_会话标题族.light`，并**只读导入** #49 的 `规范化会话标题` 复用规范化能力，避免覆盖既有交付物。路M 裁定确认此处理正确。
- **教训**：任务书撰写前应检查目标模块名是否已被既有对标卡占用（特别是 session/goal/core 等早轮已覆盖的域）。

---

## 四、新缺陷登记（L-116 / L-119 / L-120）

### L-116（任务5 类型系统域）：序列化JSON 键序敏感且与字典==语义不一致

- **现象**：`序列化JSON` 保留字典插入序、不做键排序，与 `字典 ==`（键序无关）语义不一致。同构字典 `甲==乙` 为真，但 `序列化JSON(甲)==序列化JSON(乙)` 为假。
- **触发点**：`src/类型系统.light` 的 `节点相等` 在未知节点种类分支回退为 JSON 串比较。
- **绕法**：直接用 `甲 == 乙`；若必须走 JSON，先做键规范化（键列表→排序→按序重建字典→再序列化）。
- **repro**：`examples/_repro_L116.light`（rc=0）。

### L-119（任务6 会话标题族域）：L0 单字别名是静默保留字，误用报错完全误导

- **现象**：`设 配 为 [10,20]` 合法，但 `打印 配[0]` 词法把 `配` 判为 K_MATCH（`匹配` 的单字别名）→ 解析成 `match [0]:` 空体 → 运行期报「缩进错误」。病根是保留字冲突，报错却指向缩进，且第一句合法第二句才炸，排查代价极高。
- **L0 单字别名全表**：若/则/否/是/段/出/导/遍/对/跳/过/试/捕/抛/终/返/配/己/自/设/为/从/当/空/长/首/末/余/父/常/并/与/且/或/的/在/到/现/例/步/断/接/承/宏/引/掷/跃/非/真
- **绕法**：标识符完全避开上表（改用 `配置结果`/`目标表` 等）。
- **repro**：`examples/_repro_L119.light`（rc=0）。

### L-120（任务6 会话标题族域，L-084 同族）：标识符可被关键字序列完全切分时仍被切碎

- **现象**：`捕获 异常 错误己:` → `错误己` 被切成 `错误`(关键字)+`己`(K_SELF 单字别名) → 解析报错；而 `捕获 异常 错误甲:` 正常（`甲` 不是关键字，整串不可全切分）。判定条件是「整串可被关键字全覆盖切分」，而非「标识符等于某个关键字」。
- **绕法**：标识符避开可被关键字（含单字别名）全覆盖切分的组合（用 `错误甲`/`异常对象`/`捕获到的错误` 等）。
- **repro**：`examples/_repro_L120.light`（rc=0）。

**编号空缺说明**：L-104~L-115（任务1~4 无新缺陷）、L-117~L-118（任务5 仅 L-116）均空缺顺延。本轮共新增 3 项缺陷，缺陷账累计 L-001~L-120（含空缺）。

---

## 五、对标回填

对标清单 `docs/功能对标/对标清单.json` 新增 #92~#97：

| 编号 | 功能 | 光明模块 |
|---|---|---|
| #92 | fs/tool-fs 文件系统工具纯逻辑面 | `src/文件系统工具.light` |
| #93 | experimental/agent-team 代理团队纯逻辑 | `src/代理团队.light` |
| #94 | session/session-persistence-jsonl JSONL持久化纯逻辑面 | `src/会话持久化JSONL.light` |
| #95 | web/web-search 三提供商纯逻辑面 | `src/搜索提供商.light` |
| #96 | typert/generator+protocol 类型系统纯逻辑面 | `src/类型系统.light` |
| #97 | session/session-title 族纯逻辑面 | `src/会话标题族.light` |

对标清单累计 97 条。

---

## 六、行为差异回填（R14-D1~D6）

行为差异清单 `docs/功能对标/行为差异清单.md` 新增 R14 段：

| 编号 | 任务 | 差异要点 | 状态 |
|---|---|---|---|
| R14-D1 | 任务1 | FsError 结构化code→光明消息文本承载；edit唯一性本层补齐；read_image条件注册 | ⚪ |
| R14-D2 | 任务2 | 状态枚举以上游为准(deleted墓碑非cancelled)；roster/mailbox/activity/lifecycle宿主异步行为简化 | ⚪ |
| R14-D3 | 任务3 | magic header为判别键type:"session"(无独立magic字符串/无注释行)；校验报告形态(通过/失败+行号+原因) | ⚪ |
| R14-D4 | 任务4 | WebError/HarnessError类体系→{ok,code,message,provider}纯字典；fetch/AbortSignal/凭证解析/事件落盘剔除 | ⚪ |
| R14-D5 | 任务5 | 方法枚举简化；cordis-catalog/tsdown-plugin/workspace剔除；类型相等未知种类回退JSON串比较(L-116) | ⚪ |
| R14-D6 | 任务6 | 命名冲突改族名+只读导入#49规范化能力；client.ts/LLM调用剔除；session/title事件形状与会话格式衔接 | ✅ 已裁定 |

---

## 七、全量 CI 结果

### 7.1 pytest 全量回归

| 运行方式 | 结果 | 耗时 |
|---|---|---|
| `python -m pytest tests/ -q --tb=long`（直接跑） | **276 passed** | 398.9s（6:39） |
| `python scripts/ci_test.py`（CI脚本首次） | pytest 1 failed（test_审批.light rc=1），smoke 5/5 | ~420s |

### 7.2 test_审批.light 偶发失败诊断

- **现象**：CI 脚本首次全量跑时 `test_审批.light` 断言「应绿实际 rc=1」；但**单独跑全绿**（13 用例通过 rc=0）、`pytest -k u5ba1` 单跑 5 passed、在临时目录 cwd 下复跑也全绿。
- **复跑**：直接跑全量 pytest 276 passed 全绿，确认是**偶发 flaky**，非代码缺陷。
- **疑似根因**：全量 pytest 连续运行 274 个测试（每个创建/删除独立临时目录），期间系统资源竞争（临时目录创建/删除的瞬时竞争、CPU 调度、或杀毒软件扫描）导致某个测试的 subprocess 异常返回 rc=1。`test_回归.py` 的 `_run` 函数每个测试在独立临时目录+独立环境变量副本+subprocess 运行，理论无交叉污染，故判定为环境层偶发。
- **处置**：不修改代码；记录为已知 flaky 项，后续若频繁出现再深入诊断（可考虑给 `_run` 加重试机制或增加临时目录创建的重试）。

### 7.3 冒烟测试

5 个核心模块冒烟全通过：test_会话.light / test_代理.light / test_工具.light / test_消息.light / test_流.light。

### 7.4 测试数变化

- 第13轮基线：267 passed（pytest）+ smoke 5/5
- 第14轮：276 passed（pytest，+9：6 新测试 + 3 repro）+ smoke 5/5
- 期望 273（任务书预估），实际 276（+3 repro 文件也被 pytest 遍历）

---

## 八、遗留与待决策（延续）

1. **工具注册表接入点**（R12-D9/D12，第13轮决策1已落地）：查询工具/ask_user_question 待接入登记，宿主面未就绪——维持已决策状态。
2. **approval/* 事件词汇**（第13轮决策2已落地）：已补登会话格式词汇表——已完成。
3. **#88/#35 驱动区块归并**（R13-D3，第13轮决策3已落地）：保守标注不删代码——维持已决策状态。
4. **L-095 HMAC 标准实现**（第13轮决策4已落地）：裁定为编译器侧缺陷，.light层不可修复，维持自洽链路——维持已决策状态。
5. **L-116 序列化JSON 键序敏感**（本轮新增）：建议编译器增加「稳定/排序键」选项或新增 `稳定序列化JSON`——待编译器侧修复。
6. **L-119 L0 单字别名静默保留字**（本轮新增）：建议单字别名在非语句首位置不做关键字判定，或报错文案提示「疑似保留字冲突」——待编译器侧修复。
7. **L-120 标识符关键字全切分**（本轮新增，L-084同族）：建议词法器对「可被关键字完全切分但整体是合法标识符形态」的串优先判定为标识符——待编译器侧修复。
8. **任务书命名预检查**（本轮教训）：后续轮任务书撰写前应检查目标模块名是否已被既有对标卡占用。
9. **反跑脚本路径自定位**（本轮教训）：反跑脚本应统一放 lightharness 根目录，用 `os.path.dirname(os.path.abspath(__file__))` 自定位。
