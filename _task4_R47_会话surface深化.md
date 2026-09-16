# 第47轮 任务4：会话 surface 深化（节点0投影 / 遮蔽跳过 / 记录系统提示 V3）

对标卡片 #1 / #2（`core/session`、`core/session/src/surface.ts`），补齐 v2 缺口中的 **surface 投影纯逻辑面**。

## 交付物

| 文件 | 动作 |
|---|---|
| `lightharness/src/会话格式.light` | 修改（§10 深化 + 新增 §14 + 导出清单两行） |
| `lightharness/examples/test_R47_会话surface深化.light` | 新增（6 节 / 40+ 断言） |
| `lightharness/_task4_R47_会话surface深化.md` | 本报告 |

**只改了 `src/会话格式.light` 一个源文件**（任务书互斥约束）。未触碰 `#155/#89` 的事件日志增量纯逻辑（`会话日志增量.light` 零改动），未触碰 `src/会话.light`、`src/会话查询.light`、`src/会话日志增量.light`。

## 上游依据

- `G:\github\deepseek-harness\packages\core\session\src\surface.ts`（0.1.5-rc.2，506 行）：
  `SURFACE_EVENT_TYPES` / `isSurfaceEvent` / `deriveEventMessage` / `validateSessionEventData` / `foldSurface`。
- `packages/session/session-format-v2-to-v3/src/payload.ts`：请求头**拒绝退役的 `header.system`**、`assertSystem`。
- `_up15\token-meter\{surface-fold,surface-projection}.ts`（0.1.5 增量快照，价格协议侧，仅作语义旁证）。

## 一、节点0投影（对齐 `foldSurface` 的节点0规则）

上游：surface 折叠时，系统消息节点（节点0）聚合为模型可见的**首条 system 角色消息**；`surfaceOp` 为 `append` 时连接，为 `replace` 时替换此前节点0。

本地实现：`投影节点0(事件表)`（[会话格式.light](file:///g:/dswork/duan-light-merge/lightharness/src/%E4%BC%9A%E8%AF%9D%E6%A0%BC%E5%BC%8F.light#L547-L572)）在 R41-R43 已有实现上做两处深化：

1. **遮蔽跳过**（新增）：`事件项["遮蔽"] == 真` 的 `system/message` 不参与聚合。对齐上游「shadowed nodes are excluded」——`会话.light` 的 `压缩替换` 用给旧事件打 `遮蔽=真` 表示 replace，此前 `投影节点0` 会在 replace 后又把被遮蔽的旧节点捡回来。
2. **空文本节点语义**（新增注释 + 用例钉死）：`系统提示 == ""` 的节点不产消息，但**保留表面位置**（对齐 `deriveEventMessage` 返回 null 但节点位置不删）。

聚合顺序 = 事件表顺序；`replace` 之后的 `append` 从替换值继续连接。实测：`S1` + `S2`(append) → `"S1S2"`；`S3`(replace) → `"S3"`；`S3` 再被遮蔽 → 回退到 `"S1S2"`。

## 二、遮蔽跳过（surface replace 时 hide 块跳过投影）

上游 `foldSurface` 返回 `{nodes, replacements, shadowedSeqs}`，被遮蔽节点既不产线消息也不占节点槽。

本地落在新增的 `投影表面消息(事件表)`（[会话格式.light](file:///g:/dswork/duan-light-merge/lightharness/src/%E4%BC%9A%E8%AF%9D%E6%A0%BC%E5%BC%8F.light#L892-L915)）：

```
遮蔽 → 不进 节点表、不进 消息表、不参与节点0聚合
非表面事件（turn/step/attempt/…）→ 不进 表面
空内容节点 → 进 节点表（位置保留），不进 消息表
```

返回 `["节点表": [序号…], "消息表": [消息…]]`，节点表即上游 surface 的节点位置序列，供 fold 级消费者（`会话查询.折叠表面`/路M）使用。

## 三、记录系统提示 V3（记录形状约束）

上游 V3：系统提示必须提升为 `system/message` 节点，`request/header` **拒绝** `header.system`；`validateSessionEventData` 另有「空 tools / 空 adapterDefaults 必须省略」「tool/result 带 error 时 content[0].isError 必须为 true」。

本地两处落地：

1. **`记录系统提示` 只接受 `append`/`replace`**（[L533-L542](file:///g:/dswork/duan-light-merge/lightharness/src/%E4%BC%9A%E8%AF%9D%E6%A0%BC%E5%BC%8F.light#L533-L542)）：非字符串 / 非法字符串一律抛 `system/message surfaceOp must be append or replace`，**拒绝落盘**而非静默按 append 处理（原实现无校验）。
2. **新增 `校验表面事件数据(事件项, 位置)`**（[L851-L886](file:///g:/dswork/duan-light-merge/lightharness/src/%E4%BC%9A%E8%AF%9D%E6%A0%BC%E5%BC%8F.light#L851-L886)）：
   - `request/header`：数据须为字典；须省略 `系统提示`（本地对应键）与 `header.system`；存在的 `header` 须为字典；空 `tools`（空列表）/ 空 `adapterDefaults`（空字典）须省略；
   - `tool/result`：`错误` 键**存在**即要求 `数据["消息"]["content"][0]["isError"] == 真`；
   - 文案带 `位置` 前缀（如 `request/header at seq 3`），便于 fold 层定位。

## 四、§14 新增符号与上游逐项对照

| 本地符号 | 上游对应 | 语义 |
|---|---|---|
| `表面可入类型(种类)` | `SURFACE_EVENT_TYPES` | system/user/assistant message + tool/result 四条 |
| `是表面事件(事件项)` | `isSurfaceEvent` | 类型可入即成立（缺省 surfaceOp = append，见差异 D1） |
| `表面操作取值(事件项)` | `event.surfaceOp` | 数据键 → 事件级 `表面操作`/`surfaceOp` → `"append"` |
| `是替换操作(操作)` | `isReplacementSurfaceEvent` | 字符串 `"replace"` 或字典 `{"op":"replace"}` |
| `空内容判定(消息)` | `deriveEventMessage` 的空内容分支 | 非字典 / content 非列表 / content 空 → 空 |
| `投影节点消息(事件项)` | `deriveEventMessage` | user→数据；system→本地文本成 system 消息；assistant→`消息`+`流`合并；tool/result→`消息`；其余→空 |
| `校验表面事件数据` | `validateSessionEventData` | 见第三节 |
| `投影表面消息` | `foldSurface` + `deriveMessages` | 节点0前置 + 遮蔽跳过 + 逐节点投影 |

## 五、本地适配差异（登记，不视为缺陷）

| 编号 | 差异 | 原因 |
|---|---|---|
| D1 | 上游要求 surfaceOp **显式标记**，本地**缺省 append** | 本地 `system/message` 定词汇把 `表面操作` 列为`可选`键；`会话日志增量.light` 用事件级键。`表面操作取值` 对三种表示都兼容，缺省视为 append |
| D2 | 上游 `header.system`，本地对应键为 `系统提示` | 本地 `request/header` 定词汇的可选键是 `系统提示`（L102）。`校验表面事件数据` 对 `系统提示` 与 `header.system` **两者都拒绝** |
| D3 | `表面操作` 落在 `数据` 内，上游是事件 sibling 字段 | 本地 `会话.light/会话格式.light` 的既有表示；读侧兼容两种位置 |

## 六、反跑判据实证

判据：把任一断言的期望值改反、或去掉关键标记，测试必须立红。

实测（临时注释掉 `原始件["遮蔽"] 为 真` 一行后运行）：

```
反跑判据失败[2a 遮蔽节点不进节点表]：实际=2 期望=1
rc=1
```

证明「遮蔽跳过」判据有效（去掉遮蔽标记后节点表多出 1 个节点即被抓住）。随后恢复该行，复跑全绿。

## 七、回归证据

### 新用例

```
python 运行.py examples/test_R47_会话surface深化.light
→ test_R47_会话surface深化: 全部用例通过   (rc=0)
```

覆盖：§1 节点0投影（空表 / append 聚合 / replace / 空文本节点保留位置 / 事件级字典 replace / 节点0置最前）、§2 遮蔽跳过（遮蔽节点不进两张表 / 非表面事件不进 / 空内容 assistant 保留位置）、§3 投影节点消息（user 两种形状 / 内嵌流合并 / 空内容→空 / tool/result / 空内容判定）、§4 校验表面事件数据（4a 合法、4b 须用 system/message、4c `header.system` 退役、4d header 非字典、4e 空 tools、4f 空 adapterDefaults、4g-i tool/result isError 一致性）、§5 V3 记录形状（append/replace 形状 + 非法/非字符串操作拒绝）、§6 表面类型判定。

### 既有会话族用例（本机实测 rc）

```
PASS  test_R47_会话surface深化.light
PASS  test_会话格式.light
PASS  test_会话.light
PASS  test_会话深化.light
PASS  test_会话V3迁移.light
PASS  test_行为对照_会话持久化.light
PASS  test_会话日志增量.light
PASS  test_会话格式冒烟.light
PASS  test_会话查询1.5.light
PASS  test_修复_会话.light
PASS  test_代理系统提示.light
```

11/11 rc=0，**既有会话格式测试未破**（任务书铁律）。

### 全量 pytest（回归门禁）

`python -m pytest tests/test_回归.py -q -rf --tb=no -n 8`

```
4 failed, 404 passed in 195.38s (0:03:15)
```

失败清单（与 R45 登记的既有存量红**逐条一致**）：

```
test_example_exit_code[test_R22_嵌入关键字冗余验证.light]
test_example_exit_code[test_R26_词首并入混合.light]
test_example_exit_code[test_R26_词首并入反向.light]
test_example_exit_code[test_R27_词首并入反向.light]
```

对照组 `reports/R45_双平台pytest.json`（第45轮任务1，双平台 7 failed / 1238 passed / 3 skipped，其中 `test_回归.py` 4 条）：
**`test_回归.py` 红条数 4→4，红清单逐条相同，基线外零新增红**。既有会话格式测试不破。

> 注：R45 记录里写作 `test_R22_嵌入关键字吞并验证.light`，实际文件名是 `test_R22_嵌入关键字冗余验证.light`（`examples/` 下无「吞并验证」文件，属 R45 记录笔误），指向同一用例。

> 附记：首次串行运行（`tests/test_回归.py -q`，未并行）得到 `5 failed / 400 passed`，多出的 1 条是 `test_代理循环.light` 的解析报错——该文件 `从 代理循环 导入 …` 的长导入表在那一刻命中了**并发任务正在改的 `src/代理循环.light`**。单独复跑该用例 rc=0，并行复跑（`-n 8`）亦绿，属并发编辑瞬时态，与本任务（只改 `src/会话格式.light`）无关；并发任务的 src 改动落定后不再复现。

## 八、未覆盖边界（如实登记）

1. **fold 级节点0保护**（上游 `assertSystemHeadRewrite`）：上游在 fold 时比对替换前后表面快照、禁止 replace 抹掉节点0。本地 `遮蔽`-标记表示下，要判定「替换是否吃掉节点0」需要**替换前**的表面快照，属 `会话查询.折叠表面` / fold 层的职责，本次未移植（留给路M / 后续轮）。
2. **上游 canonical `assertSystem`**：turn/step + `message{id, role:"system", source:{kind:"plugin"}}` 的完整形状校验未移植——本地 `system/message` 定词汇是 `{系统, 表面操作}` 的简化形状。
3. `校验表面事件数据` 目前只覆盖 `request/header` 与 `tool/result` 两类，上游对其余表面类型的附加断言（若有）未逐一移植。

## 九、铁律核对

| 铁律 | 状态 |
|---|---|
| 只改 `src/会话格式.light` | ✅ 唯一改动的源文件 |
| 不改 #155/#89 事件日志增量纯逻辑 | ✅ `src/会话日志增量.light` 零改动 |
| 只补 surface 投影面 | ✅ 新增 §14 全为 surface 投影/校验，未动编解码/迁移链 |
| 既有会话格式测试不破 | ✅ 10 个既有会话族用例 rc=0 |
| 改 src 后全量 pytest 回归 | ✅ `4 failed / 404 passed`，红清单与 R45 基线逐条一致，零新增红 |