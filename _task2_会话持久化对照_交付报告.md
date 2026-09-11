# _task2_会话持久化对照_交付报告.md —— 第 8 轮任务 2（会话/持久化行为对照）

> 日期：2026-09-11 ｜ 仓库：`lightharness` ｜ 编译器：`light-merge`（LIGHT_MERGE env）
> 上游：`G:\github\deepseek-harness` @ `9d9035b7c1`（0.1.5-rc.2，任务书标注 a305303422 为同窗口早期提交）
> 交付物：`examples/test_行为对照_会话持久化.light`（31 断言，全绿）+ `_antirun_session_contrast.py`（3 判据，全过）
> 铁律遵守：**src 零改动**；新文件仅 `.light` 测试 + 反跑 `.py` 判据；忠实上游断言语义。

---

## 1. 场景对照表（上游 spec → 光明用例 → 覆盖状态）

### core/session（目录实际 15 spec）

| 上游 spec | 场景要点 | 光明用例 | 状态 |
|---|---|---|---|
| surface.spec.ts | 空 surface 产生空节点 | 本轮 §1a/§1b | ✅ |
| surface.spec.ts | user 消息上浮 / 首事件序号 0 | 本轮 §1c/§1d | ✅ |
| surface.spec.ts | 节点0 system 投影 / append 连接 / replace 替换 / 遮蔽跳过 | 本轮 §2a–§2e（既有 test_会话格式 #4 部分覆盖） | ✅ |
| surface.spec.ts | replace 起点/终点不存在、start>end 抛错 | 本轮 §3a–§3c | ⚠️**差异 D1**（光明静默） |
| surface.spec.ts | sourceEventSeqs 快照隔离 | 本轮 §4a | ⚠️**差异 D2**（引用共享） |
| surface.spec.ts | 节点0 头部保护（非 system 头不保护/来源校验） | — | ⚠️未映射（光明无该守卫，见 §5 备注） |
| canonical-envelopes.spec.ts | 可选字段缺省省略 + 嵌套头保留 | 本轮 §5a–§5e、§5g | ✅ |
| canonical-envelopes.spec.ts | 编码→解码版本还原 | 本轮 §5f | ⚠️**差异 D3**（版本键名不一致） |
| json.spec.ts | JSON 标量词汇/容器准入 | 既有 test_会话格式 #1（往返幂等） | ✅ |
| sequence-types.spec.ts | 非负安全整数准入 | 本轮 §6a–§6c | ✅ |
| sequence-types.spec.ts | 恢复边界拒绝负零序号 | — | ⚠️**差异 D4**（数值域不可区分） |
| session.spec.ts | 事件记录形状/追加/查询/投影统计/压缩替换 | 既有 test_会话 #1–#6、test_会话深化 #1–#2 | ✅ |
| request-header.spec.ts | 请求头快照/PTC 重命名 | 既有 test_会话V3迁移 #3 | ✅ |
| seq-ranges.spec.ts | 紧凑 run 准入 | 既有 test_会话格式 #3 | ✅ |
| repair.spec.ts | 未闭合 tool/call 合成 tool/result | — | ❌**未映射**（光明无 repair 段落，登记缺口 G1） |
| invariant / properties | 序号连续性/往返幂等不变量 | 由各既有测试断言承担 | ✅（property-runner 宿主面剔除） |
| fork / scoped / derived-cache / gen-persistence-catalog / typert | 分叉血缘/作用域/派生缓存/catalog 生成/类型层 | — | ⚠️宿主面剔除（Cordis 装配/租约/代码生成） |

### session-persistence-jsonl（目录实际 16 项，含 2 个 e2e 与 fixtures；任务书按 13 spec 计）

| 上游 spec | 场景要点 | 光明用例 | 状态 |
|---|---|---|---|
| jsonl.spec.ts | 首行非 session 头 / 缺日志 / strict 抛错 / recoverable 跳过续读 | 本轮 §7a–§7e | ✅ |
| jsonl.spec.ts | 读写往返 / 增量追加 | 既有 test_持久化、test_持久化增量 | ✅ |
| v3-event-admission.spec.ts | V3 envelope 必选/多余键/未知类型直通 | 既有 test_会话格式 #2a–#2d | ✅ |
| v2-system-migration / v2-ptc-migration.spec.ts | v0→v3 全链迁移 / PTC 词汇 / 系统提示提升 | 既有 test_会话V3迁移 #1–#4；本轮补 §8a 链外版本抛错、§8c 链内推进 | ✅ |
| content-admission.spec.ts | 载荷准入 | 既有 test_会话格式 #2b/§2c | ✅ |
| win32.spec.ts | 路径段编码（encodeSegment/projectKey） | 既有 test_持久化（路径编码） | ✅ |
| generation / migration-verifier / migration-refusal / multi-edge-publication | 迁移产物发布与校验 | — | ⚠️宿主面剔除 |
| lease / lease.two-process.e2e / built-migration-worker.e2e | 文件锁/写租约/进程边界 | — | ⚠️宿主面剔除（持久化.light 头注明示「文件锁/写租约属宿主层，不移植」） |
| zstd / zstd.compat | 压缩算法 | — | ⚠️剔除（持久化.light 为 P0 纯文本版） |
| fixtures | 测试夹具 | — | ⚠️非 spec |

---

## 2. 翻译要点

1. **`{...}` 是插值语法**：光明字符串里的 `{x}` 会被词法当插值求值（`"{这是坏行}"` 报 `name '这是坏行' is not defined`）。坏行样本改用无花括号非法 JSON 文本（`这不是合法JSON的坏行`），strict/recoverable 语义不变。
2. **builtin_map 静默遮蔽**：`断言`→`_light_assert`、`文本`→`str`、`类型`→`type`、`当前目录`→`内置当前目录()` 等 277 个键会覆盖同名导入。断言助手命名 `核验/核验真/核验含`，参数避用 `文本`。
3. **「捕获不能用在模块顶层」**：全部断言与 尝试/捕获 置于 `段落 主` 内；helper 段落定义在 `主` 之前（光明段落不支持前向引用）。
4. **`标准链` 未导出**：改用导出符号 `定义迁移 + 创建链 + 迁移头V0V1…迁移事件V2V3` 自拼对照链（§8），语义与会话格式.标准链等价。
5. **临时目录自清理**：`取对照根` = cwd + `\_contrast_r8t2_tmp`，结尾 `目录存在` 守卫 + `删目录树`；反跑判红运行残留由脚本 `cleanup_tmp` 兜底。
6. **错误文案按上游逐字对齐**：`must be non-negative` / `must be an integer` / `会话日志首行不是 session 头` / `unsupported session format migration 2.1` / `empty session log` 均以子串包含断言（对齐 jest `toThrow(/…/)` 形态）。

## 3. 测试与 CI

```
cd lightharness
python 运行.py examples/test_行为对照_会话持久化.light   # 31 断言，RC=0
python _antirun_session_contrast.py                      # 3 判据 + 字节级恢复，RC=0
```
回归抽查（只读未改）：`test_会话格式` / `test_会话V3迁移` / `test_持久化` 均 RC=0。全量 CI 由路M 统一跑。

## 4. 反跑判据（_antirun_session_contrast.py，3 项 ≥ 2）

| 项 | 变异 | 判红方式 | 实测 |
|---|---|---|---|
| A | 5d 编解码断言期望 `"hdr1"→"hdrX"` | rc≠0 | ✓ 红 |
| B | 8c 迁移断言期望 `"3.0"→"2.0"` | rc≠0 | ✓ 红 |
| C | 删除 §2 整节（节点0 五条断言） | 输出缺 `✓ 2b` | ✓ 红 |
| — | 恢复后 sha256 与原文件一致 | 哈希比对 | ✓ |

备份/恢复仅针对**测试文件自身**，不碰 src。

## 5. 差异清单（供路M 汇总决策；未改 src）

| # | 上游场景 | 光明行为 | 上游期望 | 疑似根因 | 建议 |
|---|---|---|---|---|---|
| D1 | surface.spec：replace 起点/终点不存在、start>end **抛错** | `会话.压缩替换`（src/会话.light:175-201）静默无操作，区间外事件原样保留 | 无效区间抛错 | 该段仅按序号过滤区间，无存在性与顺序校验 | 补区间校验抛错；或登记为已知简化 |
| D2 | surface.spec：sourceEventSeqs 是**快照**，调用方改动不影响已记录事件 | `事件带来源`（src/会话格式.light:174-177）直接引用同一列表，调用方 `列表追加` 会透传 | 快照拷贝 | 光明无浅拷贝内置，段落直赋引用 | 引入 `列表快照` 内置或逐元素拷贝 |
| D3 | canonical-envelopes/session：V0 编码→解码**还原版本 3.0** | `编码V0头`(会话格式.light:208) 写中文键 `主/次`，`解码V0头`(:188-189) 读英文键 `major/minor`，往返退化 2.0 | 往返版本一致 | 编解码键名约定不一致；持久化主路径 `行对象`(持久化.light:98-100) 走英文键故不受影响 | 统一版本键为英文 `major/minor`（对齐上游 JSON 形状） |
| D4 | sequence-types：恢复边界**拒绝负零序号** | 光明/Python 数值域 `-0` 与 `0` 不可区分，`安全整数`(:27-32) 仅判 `值 < 0` 后放行 | 负零拒绝 | 数值域差异，非逻辑遗漏 | 登记为语言层限制；如需对齐须在解析层识别 `"-0"` 文本 |
| D5（观察） | surface.spec：节点0 仅头部 system 受保护 | `会话格式.投影节点0`(:537) append 连接分支读 `数据["system"]`（英文键），与 `记录系统提示` 写入的 `["系统"]` 键不一致——**第二条 append 必抛 KeyError**；类方法 `会话.投影节点0`(:89) 用 `["系统"]` 正确 | append 连接生效 | 模块级投影段落键名笔误 | 修 :537 为 `["系统"]`；测试走类方法未触发，故未入断言 |
| G1（缺口） | repair.spec：为仍未闭合的 tool/call 合成 tool/result（含 surfaceOp/来源序号） | 光明无对应段落 | repair 语义 | 未翻译该域 | 登记 SessionFormat 缺口账，是否补真身由路M 裁决 |

## 6. 移交清单

- 新增 `examples/test_行为对照_会话持久化.light`（31 断言 / 8 节，节头标注对标 spec）
- 新增 `_antirun_session_contrast.py`（A/B/C 三判据 + 字节级恢复校验）
- **src/*.light 零改动**（D1–D5/G1 仅登记，未擅改）
- 上一会话遗留的 25 个 `_w3_probe/probe_r8t2*` 临时探针已全部删除，空目录已移除
- `docs/`（对标清单/缺陷账/差异清单）按铁律只读，待路M 统一回填 D1–D5 与 G1
