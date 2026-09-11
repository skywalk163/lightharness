# 第7轮·任务3｜URL/IP 加固纯逻辑 + webhook 初始模型选择 —— 交付报告

- 分支：`task-7-ip-webhook`（worktree `wt-R7T3`，基 `e1d7e95`＝第6轮收口点）
- 对照基准：上游 `a305303422`（0.1.5-rc.2），仓库 `G:\github\deepseek-harness`（只读参考）
- 任务书：`宿主逼近_第7轮_任务prompt分发.md` §任务3（URL/IP+webhook；卡 #47 web-fetch-http、#71 webhook）
- 改动文件：`src/抓取策略.light`（+11 段纯逻辑）、`src/webhook会话.light`（`初始模型监听` 同步简化 5 行内）、`examples/test_IP安全校验.light`（新建）、`_antirun_ip_policy.py`（反跑判据）、`_task3_IP加固webhook_交付报告.md`（本报告）

## 1. 上游对应表

| 上游增量（a305303422） | 上游语义 | 本路实现位置 |
|---|---|---|
| `packages/web/web-fetch-http/src/network.ts` `isNonPublicIpLiteral(hostname)` | `isIP(剥括号) != 0 且 !isPublicIpAddress()`——IP 字面量无需 DNS 解析，代理/直连会精确命中回环或私网服务；公网校验只放行公网地址 | `抓取策略.light`：`主机是否非公网字面量`（等价组合）+ `是IP字面量`/`IP是否公网`/`剥IPv6括号` 判定族（共 11 段） |
| `network.ts` `stripIpv6Brackets` | 以 `[` 开头且以 `]` 结尾 → slice(1,-1)；否则原样 | `剥IPv6括号` |
| `network.ts` `isPublicIpAddress`（ipaddr.js range） | IPv4 非 unicast 范围拒绝（0/8、10/8、100.64/10、127/8、169.254/16、172.16/12、192.0.0.0/24、192.168/16、198.18/15、224/4、240/4）；IPv6 拒绝 ::/128、::1/128、::ffff:0:0/96、fc00::/7、fe80::/10、ff00::/8；IPv4 映射按其内嵌 IPv4 | `IPv4是否公网`（按段判定，含 0.0.0.0）、`IPv6是否公网`（前导字符近似） |
| `packages/webhook/webhook/src/session.ts`（a66e470204..a305303422 的 5 行 diff） | installInitialModelSelection 简化：agent 取事件载荷 `{ agent }` 解构（不再查 `agentCtx.agent`），删 undefined 检查 | `webhook会话.light` `初始模型监听`：agent 改为**载荷优先**（对齐解构），保留 装配槽 回退与空守卫（光明直调契约见 §2） |

## 2. 实现要点

### 2.1 抓取策略.light（卡 #47 纯逻辑面）
新增 11 段（追加于文件尾部，既有 6 段零改动）：
- **剥IPv6括号**：`[`/`]` 包围才剥（对齐 stripIpv6Brackets）。
- **判定原语**：`是数字字符`/`是十六进制字符`（光明无正则字符类，显式比较）、`是0到255`（1~3 位数字 + `整数()` 区间比较，对齐任务书「0-255 区间比较用 整数 转换」）。
- **是IP字面量**：`是IPv4字面量`（恰好三点分隔、每段 0-255）或 `是IPv6字面量`（含冒号、其余字符为十六进制或点——IPv4 嵌入段；无正则捕获组，不校验段数与压缩形态，注释已说明近似）。
- **IP是否公网**：`IPv4是否公网` 按四段数值判定，覆盖任务书全部 11 个拒绝前缀（含 0.0.0.0、198.18/15 双段、192.0.0.0/24 三段精确）；`IPv6是否公网` 前导字符近似（`::`/`::1` 全等、`::ffff:` 映射、`fc`/`fd`→fc00::/7、`fe8`-`feb`→fe80::/10、`ff`→ff00::/8）；**非 IP 字面量（域名）→ 真**（只判字面量，域名交 DNS 校验，与任务书一致）。
- **主机是否非公网字面量**：`是IP字面量 且 非公网 → 真`（等价 isNonPublicIpLiteral）。
- 头注释补对标点（network.ts isNonPublicIpLiteral）；宿主网络动作（dns.lookup/pinning/NAT64 探测）维持「已剔除（宿主网络层）」登记不变。

### 2.2 webhook会话.light（卡 #71，任务3-2）
- 光明侧存在对应逻辑（`初始模型监听`，即 installInitialModelSelection 投影）→ **同步简化对齐**：agent 从 `装配槽["代理上下文"]["agent"]` 改为**载荷优先**（`载荷["agent"]`，对齐上游 `{ agent }` 解构）。
- **兼容回退**：上游删除的 `agentCtx.agent` 查表与 undefined 检查，在光明投影中保留为——载荷为空（既有 `test_webhook会话` 以 `监听(空, 下一步)` 直调）或载荷无 agent 时回退 `装配槽["代理上下文"]["agent"]`；仍空 → 抛 `webhook Session setup has no scoped Agent [WEBHOOK_NO_AGENT]`（原错误保留）。上游简化本质（不再依赖 ctx 查表、agent 来自事件载荷）已对齐，回退仅保既有直调契约。
- 其余段落零改动（仅 `初始模型监听` 内 5 行内替换）。

## 3. 测试与 CI

### 3.1 定向测试（新建）
`examples/test_IP安全校验.light` 全绿（输出 `test_IP安全校验 PASS`），3 组判据：
1. **是IP字面量**：`1.2.3.4` 真 / `256.1.1.1` 假（越界）/ `::1` 真 / `[::1]` 真（剥括号）/ `example.com` 假 / 空串 假；`剥IPv6括号` 三种形态。
2. **IP是否公网**：`8.8.8.8` 真；`127.0.0.1`/`192.168.1.1`/`10.0.0.1`/`172.16.0.1`/`169.254.1.1`/`0.0.0.0`/`100.64.0.1`/`192.0.0.1`/`198.18.0.1`/`224.0.0.1`/`240.0.0.1` 假（IPv4 11 前缀全覆盖）；`::1`/`fc00::1`/`fe80::1`/`ff02::1`/`::ffff:8.8.8.8` 假、`2001:4860:4860::8888` 真（IPv6）；域名 → 真（交 DNS）。
3. **主机是否非公网字面量**：`127.0.0.1`/`192.168.0.1`/`[::1]` 真（拒绝）；`8.8.8.8`/`example.com` 假（放行）。

### 3.2 反跑判据（机器验证）
`python _antirun_ip_policy.py` → **2/2 双向全红**：
- A：`127/8` 判定 `返回 假`→`返回 真`（回环放行）→ test_IP安全校验 红（rc=1）；恢复 → 绿
- B：IPv4 公网兜底 `返回 真`→`返回 假`（8.8.8.8 拒绝）→ 红；恢复 → 绿

### 3.3 既有回归（任务书指定，全绿）
- `test_抓取策略`：`--- 抓取策略纯逻辑核心（模块47）测试通过 ---`（既有 6 段零影响）
- `test_webhook会话`：`--- 测试webhook会话 通过 ---`（`用例_模型监听` 以 `监听(空, 下一步)` 直调，验证回退契约；其余用例不受影响）

### 3.4 全量 CI（本 worktree 自验）
`python scripts/ci_test.py` → **pytest 通过 + smoke 通过（全部通过）**；pytest 收集 215 例（= 213 基线 + test_IP安全校验；任务1/2 新测试在各自 worktree，路M 收口合计期望 **216 passed / 0 failed**）。

## 4. 反跑判据

`_antirun_ip_policy.py`（字节级备份/恢复，CRLF 归一化处理）：
- A：`127.0.0.1` 私网判定改错（放行）→ 红；恢复 → 绿 ✓
- B：`8.8.8.8` 公网判定改错（拒绝）→ 红；恢复 → 绿 ✓

## 5. 未移植项（宿主面维持登记）

- **network.ts 宿主面**：`resolvePublicAddresses`（node:dns lookup + AbortSignal 竞速）、地址固定连接（pinning/undici dispatcher）、RFC 6052 NAT64 前缀探测（RFC6052_PREFIX_LENGTHS/IPV4ONLY_SENTINELS）——依赖 node:dns/undici 宿主设施，维持「已剔除（宿主网络层）」登记。
- **isPublicIpAddress 精确度差异**：光明侧 `IPv6是否公网`/`是IPv6字面量` 为字符扫描近似（无 ipaddr.js 段解析/压缩形态校验、无 IPv4 映射内嵌 IPv4 精确重判——`::ffff:8.8.8.8` 按前缀整体拒绝，行为与上游一致但判定面更宽）；IPv4 侧按段精确。
- **webhook session.ts 宿主胶水**：事件总线（agentCtx.on）、scoped Agent 装配、`next()` 瀑布——由 `装配槽`/`下一步` 入参投影，光明侧不实现总线本体（既有登记不变）。

## 6. 移交清单

- `src/抓取策略.light`（+11 段：剥IPv6括号/是数字字符/是十六进制字符/是0到255/是IPv4字面量/是IPv6字面量/是IP字面量/分解IPv4/IPv4是否公网/IPv6是否公网/IP是否公网/主机是否非公网字面量）
- `src/webhook会话.light`（`初始模型监听` 载荷优先 + 回退，5 行内）
- `examples/test_IP安全校验.light`（新建，3 组判据 PASS）
- `_antirun_ip_policy.py`（反跑 2/2 双向通过）
- `_task3_IP加固webhook_交付报告.md`（本报告）
- 临时补丁脚本（_task3_append_ip/_task3_fix_webhook/_task3_fix_webhook2）已清理
