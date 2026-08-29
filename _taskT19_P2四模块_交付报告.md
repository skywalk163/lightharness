# 第19轮 lightharness · P2 生态层四模块并行 + #9 溢出恢复 —— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`
> 承接：第 18 轮 interaction + subagent 完成。本轮按用户指示并行完成：遥测、code-runtime、e2b 云沙箱，以及 #9 溢出恢复。
> 日期：2026-08-29

---

## 1. 本轮成果总览

4 个任务全部完成，pytest 门禁 **75 passed 全绿**（71→75，新增 4 个测试）。

| # | 模块 | 状态 | 测试 |
|---|---|---|---|
| 19 | 遥测 telemetry | done | test_遥测.light |
| 20 | code-runtime 代码执行运行时 | done | test_代码运行时.light |
| 9v3 | 上下文压缩溢出恢复 | done(v3) | test_溢出恢复.light |
| 21 | e2b 云沙箱客户端 | done(接口层+本地模拟) | test_e2b.light |

---

## 2. 模块一：遥测（#19 done）

### 实现（`src/遥测.light`）
- **`遥测收集器` 类**：
  - `记录轮次开始(轮次)` / `记录轮次结束(轮次, 结果)`
  - `记录步骤(轮次, 步骤, 延迟秒, 用量)` —— 适配光明用量字段 `输入`/`输出`（兼容 promptTokens/completionTokens）
  - `记录工具调用(工具名, 延迟秒)` / `记录错误(错误描述)`
  - `汇总()` → `{轮次数, 总步骤, 总工具调用, 总错误, 总延迟秒, 总promptToken, 总completionToken, 工具调用明细}`
  - `输出()` —— 打印可读汇总

### 代理循环接入（`src/代理.light`）
- 构造时从 `选项["遥测"]` 传入实例
- `驱动`：轮次开始/结束记录
- `执行步骤`：步骤延迟 + 用量记录
- `执行组` 单例分支：工具调用延迟记录

### 验证（`test_遥测.light`，PASS）
- 直接测试：2 步骤 + 1 工具调用 + 1 错误 → 汇总正确（总promptToken=180, 总completionToken=80）
- 代理集成：驱动后验证 轮次数=1、总步骤>=2、总工具调用=1、总错误=0、工具调用明细含 add
- 反跑判据：总步骤断言改反即红 ✓

---

## 3. 模块二：code-runtime（#20 done）

### 实现（`src/代码运行时.light`）
- **`代码运行时` 类**：
  - `执行(代码)` → subprocess.run(["python", "-c", 代码])，捕获 stdout/stderr/返回码，超时控制
  - `执行取文本(代码)` —— 成功返回 stdout，失败返回错误描述
  - `状态()` → `{执行次数, 超时秒}`
- **`造代码执行工具(运行时, 工具名, 描述)`** —— 包装为工具定义，参数 `{代码}`，可注册到注册表

### 验证（`test_代码运行时.light`，PASS）
- 直接执行：正常代码（print/计算）、错误代码（1/0、语法错误）、执行取文本（成功/失败）
- 工具注册：注册 `执行Python` 工具，通过注册表调用返回 42
- 反跑判据：输出断言改反即红 ✓

---

## 4. 模块三：#9 溢出恢复（v3 done）

### 实现（`src/代理.light` 执行步骤增强）
- **溢出检测**：`是溢出错误(描述)` 方法，检测关键词：context/Context/overflow/maximum context/too long/400
- **请求异常恢复**：LLM 请求包在 `尝试...捕获` 里，捕获异常后检测溢出，是则压缩后 `继续`（重试当前步骤），最多 2 次
- **完成原因 error 恢复**：组装器返回 error 时同样检测溢出，是则压缩后重试
- 与 v2 压力触发协同：step 前检查 + 溢出后恢复，双重保障

### 验证（`test_溢出恢复.light`，PASS）
- mock 客户端第一次抛 "context length exceeded (400)"，第二次返回正常回答
- 压缩管理器用极低阈值（上下文窗口=1，任何消息都超过），确保压缩触发
- 验证：轮次 completed、客户端调用 2 次、代理内部压缩管理器压缩次数>=1
- 反跑判据：客户端调用次数 2 改反即红 ✓

---

## 5. 模块四：e2b 云沙箱（#21 done(接口层+本地模拟)）

### 实现（`src/e2b客户端.light`）
- **`E2BClient` 类**：
  - 构造：`(API密钥, 模板)` —— 无 API key → 本地模拟模式；有 API key → 远程模式（接口层）
  - `启动()` —— 本地模拟标记 started；远程模式标记 started（实际 SDK 调用留待后续）
  - `执行代码(代码)` —— 本地模拟用 subprocess 执行；远程模式返回接口层提示
  - `执行取文本(代码)` / `关闭()` / `状态()`
- **`造e2b工具(客户端, 工具名, 描述)`** —— 包装为工具定义

### 设计决策
- e2b SDK（`e2b` Python 包）未在环境中安装，且需要 API key。本轮实现**接口层 + 本地模拟降级**，确保可测试、可扩展。远程模式的实际 SDK 调用留待后续（需 `pip install e2b` + API key）。

### 验证（`test_e2b.light`，PASS）
- 本地模拟模式：启动/正常代码/计算/错误代码/执行取文本/关闭
- 工具注册：注册 `e2b执行` 工具，调用返回 101
- 反跑判据：输出断言改反即红 ✓

---

## 6. 光明语言新坑记录

- **L-019**（第 18 轮）：变量名与类名相同导致 UnboundLocalError（`设 X 为 新建 X(...)`）
- **L-020**（本轮）：函数名包含 `接收` 子串导致词法分析误判（`测直接收集` 含"接收"→ 改为 `测直接遥测`）
- **`或` 运算符注意**：在 `捕获` 块内或特定上下文可能解析异常，本轮通过拆开条件规避（根因待查，src/会话.light 等文件的 `或` 正常工作）

---

## 7. 文档与回归

- `对标清单.json`：#9 → done(v3 自动触发+溢出恢复)；新增 #19 遥测、#20 code-runtime、#21 e2b（总 21 条）
- `README.md`：P2 生态层更新（6 模块已落地），#9 v3 注明
- pytest 全量门禁 → **75 passed 全绿**

---

## 8. 已知遗留 / 边界

1. **e2b 远程模式**：仅接口层，实际 e2b SDK 调用需安装 `e2b` 包 + API key，留待后续。
2. **遥测输出目标**：当前仅控制台输出，未对接 OpenTelemetry/Prometheus 等后端。
3. **code-runtime 语言**：v1 仅支持 Python，多语言（JS/Shell）留待后续。
4. **溢出恢复上限**：最多 2 次重试，超过后返回错误。可配置化留待后续。

---

## 9. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_遥测.light        # 遥测
python 运行.py examples/test_代码运行时.light   # code-runtime
python 运行.py examples/test_溢出恢复.light     # #9 溢出恢复
python 运行.py examples/test_e2b.light          # e2b 云沙箱
python -m pytest tests/ -q                      # 回归门禁（75 passed）
```
