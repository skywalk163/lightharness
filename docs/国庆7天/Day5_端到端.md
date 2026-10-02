# Day5（轨道 B）· 端到端联调 · 交付报告（三段式）

> 日期：2026-10-02｜仓库：lightharness｜分支：`track-b-e2e`（出口 tag `track-B-done`）
> 反跑判据：① 破坏 `--stdlib-dir` 透传 → `转字符串(真)` 变中文「真」；② 破坏 demo 的 `造系统消息` → 首轮无 system
> 门结果：**本轨不自带门**（v2.3 支线纪律：0.82 门收归 12:30/18:00 全局窗口统一批跑，避免多轨同时调门污染基线链）。本轨未跑 0.82 权威门。

---

## 一、根因

- **现象**：单入口 `lightharness/运行.py` 与 `light-merge/cli/light.py` 的 `--stdlib-dir` 透传**早已打通**（`运行.py:129` 硬编码 `['light','run','--stdlib-dir',STDLIB,entry]`），`examples/运行Web服务器.light` 也已支持 mock/端口文件/限时停机；但计划书 §四 轨道 B 标注的交付物 `examples/端到端demo.light` **在磁盘上不存在**（已实测确认）。即：引擎就绪，缺一条把「单入口 → 系统提示 → 完整 agent 循环（含工具调用）→ 流式输出 → Web UI SSE」串起来的**可复现演示路径**。
- **定位路径（只跑不改的探查）**：
  1. 读 `运行.py`（120 行）→ 确认单入口与 `--stdlib-dir` 透传已就绪，无需改编译器。
  2. 读 `examples/运行Web服务器.light`（201 行）→ 确认 mock 模式开关（`HARNESS_WEB_MOCK=1`）、固定令牌（`HARNESS_WEB_TOKEN`）、端口文件（`HARNESS_PORT_FILE`）、限时停机（`HARNESS_WEB_LIFETIME`）均已支持。
  3. 读 `src/总入口.light` → agent 循环入口 = `组装注册表()` + `跑一轮(客户端, 注册表, 会话, 问题)`（`总入口.light:259`），其内部 `代理循环.驱动` 自动处理「系统提示 → 请求 → tool-call → 工具执行 → 结果回灌 → 再请求 → 结束」。
  4. 读 `src/代理.light:629/699-705` 与 `examples/test_代理.light:30-33` → 拿到 mock 客户端触发一次真实工具调用所需的流块形状（`造块开始(0,"tool-call")` + `造工具调用增量` + `造块结束` + `造结束(造工具调用原因())`）。
- **结论**：缺口在**演示层**，不在引擎层。按 v2.2「先探针再动手」的教训，本轨先跑 `test_联调CLI.light` 确认 `组装注册表/跑一轮` 在主树可用，再据此拼 demo——**未改动任何 src/ 编译器或运行时文件**。

## 二、做了什么

**总策略：纯新增，零修改既有文件** —— 本轨只 `新增` 两个交付物 + 本报告，`src/`、`examples/运行Web服务器.light`、`light-merge/src/`、`antlrparser/` 一行未动（守住「编译器工作树冻结」开闸条件）。

| 文件 | 变更 | 说明 |
|---|---|---|
| `examples/端到端demo.light` | **新增 ~95 行** | mock 客户端两阶段脚本：第 1 次请求返回 `tool-call` 块（真调 `bash echo e2e-ok`），第 2 次请求流式返回最终文本；记录每次发给 LLM 的网络消息，用于自检「首轮首条 role=system」与「工具结果回灌使消息数 2→4」。`python 运行.py examples/端到端demo.light` 一键跑通。 |
| `e2e_demo.ps1` | **新增 ~110 行（UTF-8 with BOM）** | copy-paste 一键脚本：段 1 跑 CLI demo；段 2 后台起 mock Web 服务（`HARNESS_WEB_MOCK=1` + 固定令牌 `e2e-token-123` + 限时 60s），轮询端口文件后 `curl /api/config` 与 `POST /v1/chat/completions?stream=true` 断言 SSE，最后自清临时件。任一段失败即非零退出。 |
| `docs/国庆7天/Day5_端到端.md` | 新增（本文件） | 三段式交付报告。 |
| `docs/国庆7天/README.md` | +1 行台账 | 进度表登记轨道 B。 |

> **编码坑（血泪，记入报告）**：首版 `e2e_demo.ps1` 写成 UTF-8 **无 BOM**，Windows PowerShell 5.1（`powershell.exe`）按 GBK 解码，中文 `运行.py`/`运行Web服务器.light` 变乱码、字符串引号配对错乱，整脚本解析失败（`The string is missing the terminator`）。已用 `[IO.File]::WriteAllText(..., UTF8Encoding($true))` 转成 **UTF-8 with BOM** 后一次跑通。今后本仓 PowerShell 脚本一律带 BOM。

## 三、现在能跑什么

### 3.1 CLI 端到端 demo（单入口闭环）

```bash
cd lightharness
# Git Bash / MSYS 语法；PowerShell 等价：设 $env:PYTHONUTF8=1; $env:CODEBUDDY_SAFE_DELETE_ENABLED=0
PYTHONUTF8=1 CODEBUDDY_SAFE_DELETE_ENABLED=0 \
  python 运行.py examples/端到端demo.light
```

关键输出（真实执行）：

```
[1/5] 单入口 stdlib 自检：转字符串(真) = True
[2/5] 组装注册表（核心工具 + lightplugin 挂载 + MCP）...
      已注册工具数: 148
[3/5] 用户问题: 请用 bash 工具执行 echo e2e-ok，并把结果告诉我
  [stream] 请求#1 → 模型决定调用工具 bash（arguments={"命令":"echo e2e-ok"}）
  [stream] 请求#2 → 模型流式输出最终文本（2 个 text-delta）
[4/5] agent 轮次结算: completed
      已完成：我调用了 bash 工具执行 echo，工具结果已在上文回灌。...
[5/5] LLM 总请求次数: 2（预期 2：工具调用轮 + 最终回答轮）
      OK 反跑判据#2：首轮请求首条 role=system（造系统消息正常）
      消息数：首轮 2 → 次轮 4（次轮更多 = 助手消息+工具结果已回灌）
=== 端到端 demo 完成 ===
```

退出码：`rc=0`

### 3.2 Web UI 流式（SSE）闭环

```bash
cd lightharness
powershell -ExecutionPolicy Bypass -File e2e_demo.ps1
```

脚本段 2 真实输出：

```
[段 2/2] Web UI 闭环：起 mock Web 服务 + curl SSE
  mock Web 服务已起，端口=62234
  GET /api/config -> {"configured":1,"mock":1,"model":"deepseek-flash",
                      "endpoint":"https://api.deepseek.com/chat/completions","has_key":1}
  POST /v1/chat/completions -> HTTP 200  CT=text/event-stream; charset=utf-8
  SSE 帧序列 OK（含 data: 帧与 [DONE]）
==================================================
  轨道 B 端到端联调全通（CLI + Web UI）rc=0
```

SSE body 帧序列（真实 `POST /v1/chat/completions?stream=true`）：

```
data: {"choices":[{"delta":{"role":"assistant","content":""},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":"Web UI mock 流式回复：E2E 联调成功。"},"finish_reason":null}]}
data: {"choices":[{"delta":{},"finish_reason":"stop"}]}
data: {"种类":"统计",...}
data: {"种类":"会话","session_id":"e2e-curl-1"}
data: [DONE]
```

退出码：`SCRIPT_EXIT=0`

### 门三元数字

本轨按 v2.3 支线纪律**不自带 0.82 门**（门是全局互斥资源，统一 12:30/18:00 窗口批跑）。最近一次权威门为 Day2+Day3 组合态（2026-10-02 07:53，见 README 台账）：**failed 0 / skipped 121 / passed 8359**，对 Day1 full 基线零劣化。本轨未改编译器，预期门数字不劣化；若需复测，由 team lead 在下一个门窗口排队执行 `082全量回归.py all --mode full`。

## 四、反跑判据验证

1. **破坏 `--stdlib-dir` 透传 → `转字符串(真)` 变中文「真」（R98/D 教训）**：
   demo `[1/5]` 步打印 `转字符串(真)`。实测基线输出 **`True`**（英文）。若透传被破坏，该值回退为中文兜底 lambda 输出的「真」——demo 会一眼可见地变红。**实测：True，rc=0。**
2. **破坏 demo 的 `造系统消息` → agent 首轮无系统提示**：
   mock 客户端记录每次发给 LLM 的 `网络消息`，demo `[5/5]` 检查首轮首条 `role`。实测 **首条 role = "system"**；且消息数首轮 2（system+user）→ 次轮 4（+assistant tool-call +tool 结果），证明系统提示注入与工具结果回灌都在。**实测：OK，rc=0。**

## 五、遗留 / 偏离声明

- **未改编译器**：`light-merge/src/`、`light-merge/antlrparser/`、`lightharness/src/` 零改动，守「开闸条件 ③ 编译器工作树冻结」。
- **未跑 0.82 权威门**：门由 team lead 在 12:30/18:00 窗口统一批跑（互斥资源），本轨不越界。
- **未 push**：按纪律只本地 commit + 打 `track-B-done` tag，远端推送等用户示意。
- **mock 客户端是「同步返回块列表」**：lightharness 的流式抽象是 `对话响应()` 返回 chunk 列表（非真异步 SSE），demo 用两个 `text-delta` 演示流式切片；真 SSE 出口在 Web UI 段 2 已用 curl 验证。
- **`reports/同步0.82_远程目录.txt` 曾显示 modified**：是门运行时指针文件，非本轨产物，已 `git checkout` 还原，不纳入本轨提交。
- **砍线未触发**：15:00 前 demo 一次跑通，无需降级为「单入口 + mock 启动」。
- **临时件**：`.e2e_port.txt` / `.e2e_web.log` / `.e2e_web.err` 由 `e2e_demo.ps1` 末尾自清；残留已手工清理。
