# 第16轮 lightharness · #9 压缩自动触发收口（P1 v2）—— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`
> 承接：第 14 轮 P0/P1 深化时 #9 压缩自动触发押后（需 token 计量+压力触发+溢出恢复，规模超轮）。本轮按用户指示收口。
> 日期：2026-08-28

---

## 1. 背景与目标

原版 `compaction/compaction-basic` 的自动触发机制：
- **token 计量**：tokenMeter 服务估算会话 token 数
- **压力触发**：agent/pre-step 检查 token > thresholdRatio × contextWindow，超过则自动压缩（保留 retainTokens 尾部）
- **溢出恢复**：LLM 返回 CONTEXT_WINDOW_EXCEEDED 时压缩并重试

lightharness v1（第 8 轮）只有**手动确定性策略** `压缩到最近(保留N条)`，调用方主动调。本轮补 v2 自动触发。

---

## 2. 实现

### 2.1 `src/压缩.light` 新增（v2 自动触发）
- **`估算token(消息表)`**：轻量 token 估算（文本块字符数 / 3，中英文混合简化）
- **`压缩管理器` 类**：
  - 配置：`上下文窗口`(默认 128000)、`阈值比例`(默认 0.75)、`保留条数`(默认 10)
  - `阈值token()` = 上下文窗口 × 阈值比例
  - `检查并压缩()`：估算 token > 阈值 → 调 `压缩到最近`，返回是否触发，累计 `压缩次数`
  - `状态()`：返回 {估算token, 阈值token, 压缩次数, 消息数}

### 2.2 `src/代理.light` 接入（step 前检查）
- 顶部 `从 压缩 导入 压缩管理器`
- `代理循环` 新增属性 `压缩管理器`（默认空）
- 构造时从 `选项["压缩配置"]` 创建管理器（可选，不破坏现有调用）
- `执行步骤` 开头：`如果 己.压缩管理器 != 空: 己.压缩管理器.检查并压缩()`

### 2.3 配置入口
```
代理循环(会话, 客户端, 注册表, ["压缩配置": ["上下文窗口": N, "阈值比例": R, "保留条数": K]])
```

---

## 3. 验证

### 3.1 `examples/test_压缩自动.light`（3 部分，PASS）
1. **直接压缩**：12 条 300 字符长会话 + 阈值 100 token → 触发压缩，消息数 12→≤4，压缩次数=1
2. **不压缩**：阈值极高（999999×0.9）→ 不触发，压缩次数=0，消息数不变
3. **代理集成**：10 条 250 字符 + 选项压缩配置 → `代理.驱动()` step 前自动压缩，轮次 completed，`代理.压缩管理器.压缩次数>=1`

### 3.2 反跑判据
- 把 `压缩次数` 断言 1 改 2 → EXIT=1（红）✓

### 3.3 回归
- `test_代理.light`（无压缩配置）不回归 ✓
- pytest 全量门禁 → **68 passed 全绿**（test_压缩自动 纳入，无副作用）

---

## 4. 文档
- `对标清单.json` #9：`done` → `done(v2 自动触发)`，证据补 test_压缩自动/代理接入，目标/反跑判据更新
- `README.md`：上下文压缩行更新为「已实现(v2 自动触发)」，目录结构补描述

---

## 5. 已知遗留 / 边界

1. **溢出恢复**（context-overflow）：LLM 返回上下文溢出错误时自动压缩重试。本轮未实现——需要客户端层错误码识别（HTTP 400 + error.message 匹配）+ 代理循环重试循环，留待后续专项。
2. **token 估算精度**：轻量字符/3 估算，非真实 tokenizer。原版用 tokenMeter（可接 tiktoken）。v2 估算足以驱动压力触发，精度不足时可调阈值比例。
3. **retainTokens 语义**：原版按 token 数保留尾部，光明版按消息条数保留（`保留条数`）。等价但粒度不同。
4. **异步代理**：`异步代理.light` 未接入压缩管理器（本轮只接同步 `代理.light`）。异步版留待后续。

---

## 6. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_压缩自动.light    # 压缩自动触发（3 部分）
python 运行.py examples/test_压缩.light         # v1 手动压缩（不回归）
python 运行.py examples/test_代理.light         # 代理循环（无压缩配置，不回归）
python -m pytest tests/ -q                      # 回归门禁（68 passed）
```
