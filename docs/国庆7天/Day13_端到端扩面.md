# Day13 · 轨道B e2e 扩面（多轮 + SSE + 真实 LLM smoke）

> 派单：Day2 S7（P2，编译器冻结）｜执行：C 路｜日期：2026-10-02
> 被测 SHA：light-merge `d6b84a716` / lightharness `f21c0191` / lightplugin `11c78735`
> 前置：Day5 `端到端demo.light`（单轮工具调用闭环）+ `e2e_demo.ps1`（Web SSE）

---

## 〇、一句话

- **多轮对话**：3 轮用户问题跑通，消息数 首轮 2 → 次轮 4 → 三轮 6，历史跨轮累积 ✓
- **SSE**：现有 `e2e_demo.ps1` 段 2 重跑落盘日志（HTTP 200 + `text/event-stream` + `data:` 帧 + `[DONE]`）✓
- **真实 LLM smoke**：**未跑通（退 mock）**——`.env` 只有 `AIStudio_Access_Token`，试千帆 OpenAI 兼容端点 401、试 aistudio 端点 404。按派单表 §六 纪律退回 mock，不阻塞。

---

## 一、多轮对话扩面（≥3 轮）

### 新增文件
`lightharness/examples/端到端demo_多轮.light`（~95 行）

在 Day5 单轮 demo 基础上扩：
- 同一会话连续跑 3 个用户问题（`跑一轮` × 3）
- mock 客户端每轮直接流式回文本（不调工具），聚焦验证消息历史累积
- 自检：第 N 轮发给 LLM 的消息数 > 第 N-1 轮

### 跑法
```
cd lightharness
PYTHONUTF8=1 CODEBUDDY_SAFE_DELETE_ENABLED=0 \
  ../light-merge/.venv/Scripts/python.exe 运行.py examples/端到端demo_多轮.light
```

### 实测输出（rc=0）
```
[1/4] stdlib 自检：转字符串(真) = True
[2/4] 组装注册表...
      工具数: 148
[3/4] 第 1 轮用户问题: 第一轮：你好，请用一句话打招呼。
      轮次结算: completed | 最终回复: 多轮第1次回复：我已收到你的问题。
[3/4] 第 2 轮用户问题: 第二轮：我刚才说了什么？请复述。
      轮次结算: completed | 最终回复: 多轮第1次回复：... 多轮第2次回复：...
[3/4] 第 3 轮用户问题: 第三轮：我们一共聊了几轮？请数一下。
      轮次结算: completed | 最终回复: 多轮第1次回复：... 多轮第2次回复：... 多轮第3次回复：...
[4/4] 多轮自检：
      LLM 总请求次数: 3（预期 3：每轮 1 次，不调工具）
      消息数：首轮 2 → 次轮 4 → 三轮 6
      OK 多轮历史累积：消息数逐轮增长（system + 历史 user/assistant 在回灌）
      OK 反跑判据#2：首轮首条 role=system
```

- 日志：`logs/day2/S7_multiturn_demo.log`
- rc = **0**

### 关键判据
- 消息数 2→4→6：每轮 +2（user + assistant），证明会话跨轮持久化正常
- 最终回复逐轮追加：第 2 轮回复含第 1 轮文本，第 3 轮含前两轮——证明 `取最终文本(会话对象)` 聚合了全历史
- 首轮首条 role=system：造系统消息未破坏

---

## 二、SSE 工具流（重跑 Day5 e2e_demo.ps1 落盘日志）

Day5 的「CLI rc=0 + SSE 200」在仓库里**零日志**（v0.3.0 教训）。本次重跑落盘。

### 跑法
```
cd lightharness
powershell -ExecutionPolicy Bypass -File e2e_demo.ps1
```

### 实测输出（rc=0）
```
[段 1/2] CLI 闭环：python 运行.py examples/端到端demo.light
  → 已注册工具数: 148
  → 请求#1 调 bash（echo e2e-ok）
  → 请求#2 流式最终文本
  → 消息数：首轮 2 → 次轮 4（工具结果回灌）
[段 1/2] OK rc=0

[段 2/2] Web UI 闭环：起 mock Web 服务 + curl SSE
  GET /api/config -> {"configured":1,"mock":1,"model":"deepseek-flash",
                      "endpoint":"https://api.deepseek.com/chat/completions","has_key":1}
  POST /v1/chat/completions?stream=true -> HTTP 200  CT=text/event-stream; charset=utf-8
  SSE 帧序列 OK（含 data: 帧与 [DONE]）
```

- 日志：`logs/day2/S7_e2e_demo_ps.log`
- rc = **0**

### SSE 帧形状（Day5 已验证，本次复跑未破坏）
```
data: {"choices":[{"delta":{"role":"assistant","content":""},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":"Web UI mock 流式回复：E2E 联调成功。"},"finish_reason":null}]}
data: {"choices":[{"delta":{},"finish_reason":"stop"}]}
data: {"种类":"统计",...}
data: {"种类":"会话","session_id":"e2e-curl-1"}
data: [DONE]
```

---

## 三、真实 LLM smoke（退 mock，如实记录）

### 尝试
`.env` 里与模型相关的 key 只有：
```
AIStudio_Access_Token="6cac673...d4dc0c"
```
按派单表 §六 预警：计划假设「DeepSeek 推理 key」，实际没有。试两个百度端点：

| 端点 | 结果 |
|---|---|
| `https://qianfan.baidubce.com/v2/chat/completions`（千帆 OpenAI 兼容） | **401 未经授权** |
| `https://aistudio.baidu.com/llm/chat`（AI Studio 直连） | **404 未找到** |

- 日志：`logs/day2/S7_real_llm_smoke.log`
- 两个端点均未返回有效 chat completion

### 判定
**真实 LLM smoke 未跑通**。原因：
1. `.env` 无 DeepSeek key（计划 §四 轨道B 的假设不成立）
2. `AIStudio_Access_Token` 对千帆 OpenAI 兼容端点 401（该 token 是 AI Studio AppBuilder 产物 token，不是千帆平台 API Key）
3. 本环境无网络代理/其他 key 可切换

### 处置（按派单表 §六 纪律）
- **退回 mock**：本轨所有 e2e 验证走 mock 客户端，不消耗真实 token
- **不阻塞相位**：mock 路径已覆盖「多轮消息累积 + SSE 帧形状 + 工具调用回灌」三条主链路
- **后续**：真 LLM 路径留给轨道 C（FreeBSD 1.5 上配 DeepSeek key 实测），或等用户提供有效 key 后补跑

---

## 四、反跑判据

1. **破坏 `--stdlib-dir` 透传** → `转字符串(真)` 应出中文「真」。本次实测基线 **True**（英文），透传正常。
2. **破坏 `造系统消息`** → 首轮首条 role != system。本次实测两轮 demo（单轮 Day5 + 多轮 S7）首轮首条均为 `system`。
3. **破坏会话跨轮持久化** → 多轮 demo 消息数不增长。本次实测 2→4→6 线性增长。

---

## 五、四件套

| 项 | 值 |
|---|---|
| light-merge SHA | `d6b84a7169b645231d89e1f27ba20321a148d603` |
| lightharness SHA | `f21c0191e663fa9a3b397bbc8f377cdaf19caf2b` |
| lightplugin SHA | `11c78735a81d32673d880e44a264d6ffada179b4` |
| 新增文件 | `examples/端到端demo_多轮.light`（~95 行） |
| 修改文件 | 无（`e2e_demo.ps1` 未改，直接重跑） |
| 代码改动 | **0**（未动 src/、light-merge/src/、antlrparser/） |
| 日志 | `logs/day2/S7_multiturn_demo.log`、`S7_e2e_demo_ps.log`、`S7_real_llm_smoke.log` |

## 六、砍线与遗留

- **真 LLM smoke 退 mock**：见 §三，不阻塞。
- **未跑 0.82 权威门**：本轨不改编译器，按 v2.3 纪律门由 team lead 在 12:30/18:00 窗口统一批跑。
- **未 push**：本地新增文件不提交，等用户示意。
- **`examples/端到端demo_多轮.light` 是纯新增**：未改 Day5 的 `端到端demo.light` 与 `e2e_demo.ps1`，老路径回归不受影响。
