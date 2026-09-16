# 任务2（R41·P0）交付报告 —— 真实网络IO

> 日期：2026-09-16 ｜ 负责人：WorkBuddy ｜ 状态：**完成（本机 Windows rc=0）**
> 目标：把 `web服务器.light` / `HTTP服务端.light` 从「硬编码 127.0.0.1、无网络级认证、入参/内存模拟」接到**真实网络**，并新增真实 HTTP 客户端（GET/POST）打通端到端链路，支撑后续 0.82 双平台验证。

---

## 一、根因 / 本轮回溯（最重要的修正点）

### 1.1 宿主层此前为何接不上真实网络
- `stdlib/HTTP服务端.light` 的 `构造` 里 `bind(("127.0.0.1", 0))` 硬编码本机回环，`web服务器.light` 也无「绑定地址 / 网络令牌」的概念（S1 设计即「仅本机、无认证」）。
- `web-fetch` 等需要真实出网请求的能力此前只能靠「入参注入 / 内存模拟」绕开，无法在 0.82 局域网验证场景下暴露真实服务、也打不了真实端点。
- 本轮把宿主层从「入参化 / 内存模拟」接到**真实IO**：服务端可配 `绑定地址`、按 `HARNESS_TOKEN` 做网络级门禁；客户端用光明 socket 原语实现真实 `GET/POST`。

### 1.2 调试中踩的三处 light 语言/接线坑（已修，均非服务端逻辑缺陷）
**坑① 客户端误从 HTTP服务端 导入 `单调时钟`**（`cannot import name '单调时钟'`）
`真实HTTP客户端.light` 初版写了 `从 HTTP服务端 导入 ... 单调时钟`。`单调时钟` 是 **light 内建（全局可用）**，不是 `HTTP服务端` 的导出符号 → 导入失败。
修复：删掉该导入，直接当内建用（与 `HTTP服务端.light` 自身体一致）。

**坑② POST 时 `str` 与 `bytes` 拼接**（`can only concatenate str (not bytes) to str`）
`真实请求` 把 `请求文本(字符串)` 与 `体文本` 直接 `+`。当 `体文本` 是 bytes 字面量时类型不匹配；且 `Content-Length` 若按 `长(体文本)` 算会把 bytes 长度算成字符数（误）。
修复：请求体一律字符串，`Content-Length` 改用 `长(体文本.encode("utf-8"))`；验收脚本的 `聊天体()` 返回**字符串字面量**（`'{"model":"x",...}'`，非 `b'...'`）。这恰好反向印证了语言缺陷账待登记的「**light 无字节串字面量**」——要 bytes 必须 `.encode()`。

**坑③ 清理 `WinError 145 目录非空`**
验收脚本末尾 `删除目录(会话根)` 失败：会话持久化写入了嵌套子目录，`删除目录` 不递归。
修复：改用 `删目录树(会话根)`（递归删）。

> 结论：三处均为接线/验收脚本层面的坑，**服务端非阻塞模型与路由门禁逻辑本身无缺陷**；均已在代码与验收脚本中固化，不回流。

### 1.3 非阻塞模型对齐（S2 H1/H4 教训，必须守住）
- `HTTP服务端.light` 在 FreeBSD 上曾因「POSIX 不继承 `O_NONBLOCK`、发送无 monotonic 截止」挂死 12 分钟（H1/H4）。本轮客户端**复用同一套选择器原语**（`新建选择器/探测就绪/是否愿等读/是否愿等写/关闭选择器`）+ 显式 `setblocking(假)` + 每请求一个 `单调时钟()` 截止超时。
- **死锁防护**：真实客户端跑在**测试主协程（事件循环）**里，若阻塞会冻住服务端 `处理循环` 任务 → 整个测试死锁。故所有调用必须 `等待 真实GET/真实POST` 让出事件循环，绝不能同步 `recv` 到底。

---

## 二、做了什么（交付物 + 设计）

### 2.1 交付物（五项，全部到位）
| 文件 | 类型 | 说明 |
|---|---|---|
| `lightharness/stdlib/HTTP服务端.light` | 最小改动 | 构造加 `绑定地址` 参数（默认 `127.0.0.1`） |
| `lightharness/src/web服务器.light` | 改造 | 绑定+token 配置化 + 安全铁律 + 非 loopback 401 门禁 |
| `lightharness/src/真实HTTP客户端.light` | 新增 | 异步非阻塞 GET/POST + 超时 |
| `lightharness/examples/test_R41_真实网络IO.light` | 新增 | 全链验收，rc=0 |
| `lightharness/_task2_R41_真实网络IO.md` | 新增 | 本报告 |

**铁律遵守**：socket 显式 `setblocking(假)`；真实客户端必须有超时（禁止无限挂起）；安全铁律（非 loopback + 无 token = 拒绝启动硬报错）；零修改纯逻辑层（`文件系统工具.light`/`宿主IO.light` 本轮不涉及）。

### 2.2 服务端：绑定地址可配置（最小改动）
`HTTP服务端.light`：
- 加属性 `绑定地址 = "127.0.0.1"`；
- `构造 接收 处理器, 超时值, 绑定地址="127.0.0.1"`：`bind((绑定地址, 0))` 取代硬编码 `("127.0.0.1", 0)`；端口仍由内核分配、`getsockname()` 取回。
- 默认 `127.0.0.1` 不变 ⇒ **向后兼容 S1（仍只绑本机）**。

### 2.3 web服务器：绑定 + 网络令牌 + 安全铁律 + 401 门禁
- `配置(...)` 新增 `绑定地址="", 令牌=""` 两参：留空则读 `环境变量("HARNESS_BIND", "127.0.0.1")` / `环境变量("HARNESS_TOKEN", 环境变量("HARNESS_WEB_TOKEN", ""))`（兼容既有 `HARNESS_WEB_TOKEN`）；显式传入覆盖环境变量。
- **安全铁律（硬报错，不警告）**：`非(是回环地址(绑定地址)) 且 令牌空` → `抛出 新建 错误("安全铁律：绑定非 loopback ... 但未设置 HARNESS_TOKEN，拒绝启动")`。
- 模块级助手 `是回环地址(地址)`：命中 `127.0.0.1` / `::1` / `localhost` / `127.` 开头。
- **非 loopback 401 门禁（与既有 S2 会话令牌并存不悖）**：仅当 `非回环绑定 且 期望令牌非空` 时强制——校验请求头 `X-Auth-Token` 或查询 `?token=`，任一相符即过，否则返回 `401`（`未认证：非 loopback 绑定要求携带 X-Auth-Token`）。该门禁独立于 `认证` 模块的 `HARNESS_WEB_TOKEN` 会话级校验。
- 末行 `新建 HTTP服务端(路由处理器, 超时值, 绑定地址)` 把绑定地址透传。

### 2.4 真实HTTP客户端：异步非阻塞 GET/POST
`真实HTTP客户端.light`：
- `真实GET` / `真实POST` / `真实请求`（统一核心）。构造请求文本（`Connection: close` → 服务端响应后主动关闭、`recv==0` 即结束）；POST 带 `Content-Type` + `Content-Length`（按 `.encode("utf-8")` 长度）。
- `套接字.setblocking(假)`；`socket.socket(AF_INET, SOCK_STREAM)`。
- **connect**：非阻塞可能 `EINPROGRESS` → 等「写就绪」+ monotonic 截止，超时抛 `连接中断("连接超时")`。
- **send**：非阻塞 `send` 循环，`send` 不保证一次发完；`是否愿等写(e)` 时探测就绪 + `异步睡眠` 让步，超时抛 `连接中断("发送超时")`。
- **recv**：非阻塞 `recv(4096)`，`是否愿等读(e)` 时探测就绪 + 让步，超时抛 `读取错误("读取超时")`；`recv==0` → 对端关闭、跳出。
- 复用 `HTTP服务端` 暴露的 `新建选择器/探测就绪/是否愿等读/是否愿等写/关闭选择器/连接中断/读取错误`；异常文本统一走 `e.args`（光明仅暴露英文 args）。
- 返回 `["状态": int, "头": str, "体": str]`；`Connection: close` 下无需解析 chunked/keep-alive。

### 2.5 light 网络内建探查清单（任务书要求，缺则登记）
本轮实际复用的真实网络内建/原语（均存在，**无缺失、无伪造**）：`socket.socket` / `setblocking` / `connect` / `send` / `recv` / `close` / `encode` / `find` / `切片` / `单调时钟`（内建全局）/ `异步睡眠` / `创建任务` / `等待`。
**唯一暴露的语言短板**：light **无字节串字面量**（`b'...'` 不支持），bytes 必须经 `字符串.encode("utf-8")` 得到 —— 已登记进语言缺陷账（见下文待办 L-159）。

---

## 三、验证结果（本机 Windows）

运行：`cd lightharness && python 运行.py examples/test_R41_真实网络IO.light` → **EXIT_CODE=0**。
（实测复跑确认：`任务2 全部断言通过（...）`，退出码 0。）

| 场景 | 覆盖 | 断言 | 结果 |
|---|---|---|---|
| A · loopback 无 token | 内核分配端口、起 `处理循环` 任务 | `端口A > 0` | ✅ |
| A · GET /health | 真实客户端非阻塞 GET | `状态 == 200` | ✅ |
| A · POST /v1/chat/completions | mock 客户端驱动、零真实 token | `状态 == 200` 且体含 `r41 real net mock reply` | ✅ |
| B · 非 loopback + token | 绑定 `0.0.0.0` + `HARNESS_TOKEN` | `端口B > 0` | ✅ |
| B · 带 token GET/POST | 头带 `X-Auth-Token` | `状态 == 200`（两处） | ✅ |
| B · 不带 token GET | 401 门禁触发 | `状态 == 401` 且体含 `未认证` | ✅ |
| C · 安全铁律 | 非 loopback 无 token 调 `配置()` | 抛错被捕获（`拒绝 == 真`） | ✅ |
| 清理 | `删目录树(会话根)` | 无残留 | ✅ |

**向后兼容回归**：既有 `examples/test_web路由.light` 同跑 rc=0（绑定默认 `127.0.0.1`、S1 全放行行为不变）。

---

## 四、现在 / 待办（任务3-6 衔接）

1. **语言缺陷账（L-159 起登记历史项）**：本轮任务2 暴露 1 项真实短板——**light 无字节串字面量**（POST 体须 `.encode()`）。另据历史轮次待登记项：`主目录()` 非内建（HARNESS_ROOT 经 `取根目录` 覆盖根解析）、`0o644` 八进制字面量不支持（文件权限须用十进制/os 调用绕开）。三项已追加至 `docs/功能对标/语言缺陷账.md`（L-159/L-160/L-161），属「已登记未修」。
2. **0.82 机器复测**：任务书要求双平台验证。本机（Windows）全绿；0.82（POSIX）复测归任务3/4/5，届时同跑 `test_R41_真实网络IO.light` 比对 rc=0。POSIX 行为已按 S2 H1/H4 教训预先对齐（显式 `setblocking(假)` + monotonic 截止 + 选择器 close）。
3. **任务3-6**（CLI 多平台 + 0.82 接入 / 多平台矩阵 / 端到端 / 质量审查）待后续；0.82 机器信息（IP/SSH/认证）未提供，任务书要求分发时由用户提供。

---

## 五、运行方式（copy-paste）
```bash
cd G:/dswork/duan-light-merge/lightharness
G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe 运行.py examples/test_R41_真实网络IO.light
# 期望输出：任务2 全部断言通过（真实网络IO：loopback GET/POST 200；非loopback 令牌门禁 200/401；无token拒启动 rc=0）
# 退出码 0
```

# 向后兼容回归（可选）
```bash
cd G:/dswork/duan-light-merge/lightharness
G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe 运行.py examples/test_web路由.light
# 退出码 0
```
