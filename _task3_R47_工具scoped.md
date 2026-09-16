# 第47轮任务3交付：scoped tools 可见性 + 指导过滤 + PTC 决策面（#8）

> 日期：2026-09-17 ｜ 状态：**完成**

## 一、上游对照（只读）

- `packages/core/tools/src/index.ts`：
  - `restrict({allow?, deny?})`（1061-1088）：空过滤器报错（no-op 视为配置 bug）；
    不得点名保留 PTC 运输工具 `run_code`；未知全局名报错。
  - `ToolLayer.admits`（731-737）：allow 定义 → 名字须在白名单；deny 定义 → 名字不得在黑名单。
  - `view()`（1142-1182）：继承面逐名过**全链限制求交**（`layers.every(layer.admits(name))`）；
    作用域自有注册遮蔽继承名且**不受限制约束**；呈现非 native → 注入 `run_code`
    （限制不得波及保留运输工具）。
  - `modeFor`（892-898）：作用域链**就近胜出**；全链未声明 → 部署默认 `native`。
  - `collapses`（1314-1316）：`ptc && name !== 'run_code' && !nested` → 直接派发折叠
    （名字仍可见，调用只能走 run_code SDK 子派发；嵌套调用不折叠）。
  - `PreToolDecision = allow | deny{reason} | ask{reason?}`；`resolveAsk`（1669-1716）：
    ask 无审批服务 → deny（not yet supported）；`allowed-once` → allow；denied/cancelled → deny。
  - 守卫单调否决：任一 guard 返回理由即 deny，且不可被放行翻案（700-704）。
- 指导过滤：既有 R46 交付 `过滤可见指导`/`裁交叉推荐` 已对齐渲染语义，本轮接上
  **限制链驱动的可见性判定**（判定可见 传 限制链放行 的闭包包装）。

## 二、修改（互斥区内，纯逻辑追加）

### src/工具.light（追加到 §作用域工具判定 之后）
- `代码运输名 = "run_code"`；
- `造限制(允许表=空, 禁止表=空)`：空过滤器抛 `[EMPTY_RESTRICTION]`；
  点名 run_code 抛 `[RESERVED_TRANSPORT_NAME]`；编译为 {允许?, 禁止?}；
- `限制放行单(限制, 名字)`：单层 admits 语义；
- `限制链放行(限制链, 名字)`：沿链求交，任一层否决即不可见；
- `作用域可见视图(继承名单, 限制链, 自有名单, 呈现)`：继承面过滤 + 自有注册追加
  （遮蔽继承、不受限）+ 非 native 注入 run_code（去重）；
- `呈现模式判定(链声明表)`：就近胜出，全链空 → native；
- `折叠判定(名字, 呈现, 嵌套)`：ptc + 非嵌套 + 非 run_code → 折叠。

### src/工具执行.light（追加 §7，全部 具 前缀/具名常量）
- `决放行/决拒绝/决询问`、`预决表`；`批准放行("allowed-once")/批准拒绝/批准取消`、`审批结果表`；
- `具造预决(种类, 理由=空)`：种类校验 `[UNKNOWN_PRE_TOOL_DECISION]`；allow 不得带理由；
- `具询问收敛(预决, 审批结果=空, 有通道=真)`：allow/deny 原样收敛；
  ask 无通道 → deny；allowed-once → allow；denied/cancelled/未知 → deny（对齐 resolveAsk）；
- `具守卫裁决(否决理由, 预决)`：守卫单调否决，理由非空即 deny 不可翻案。

## 三、新增测试

`examples/test_R47_工具scoped.light`（rc=0），9 组断言覆盖：
- 限制掩码四例（allow/deny/空过滤抛错/保留名抛错）；
- 链求交（自身层否决、祖先层 allow 未含）；
- 作用域视图五例（native 全继承/限制过滤/自有不受限/ptc 注入 run_code/both 注入）；
- 呈现就近胜出三例；折叠判定五例；
- 指导过滤（限制链闭包包装 → 过滤可见指导保序过滤 + 裁交叉推荐裁剪/保留）；
- PTC 收敛七例 + allow 带理由抛错 + 未知种类抛错 + 守卫单调性三例。

## 四、回归

- 既有 `test_agent工具调用.light`、`test_R38_工具展示.light`、`test_R40_端到端互举.light`、
  `test_工具系统.light` 全 rc=0；
- 本机全量 pytest 基线外零新增红（见收口记录）。

## 五、铁律核对

- 只补纯逻辑，未接宿主权限总线；`工具注册表`/`执行`流水线既有行为未动；
- 既有工具执行测试不破。
