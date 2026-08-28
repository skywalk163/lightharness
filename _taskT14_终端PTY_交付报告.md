# 第14轮 lightharness · P0/P1 对齐深化——终端 PTY 收口 —— 交付报告

> 仓库：`g:\dswork\duan-light-merge\lightharness`（独立 git 仓库）
> 承接：第 13 轮 L-018 闭环后，15 项对标卡全部 done；本轮按用户要求「深化 P0/P1 对齐度，检查 partial 项可收口」。
> 日期：2026-08-28

---

## 1. P0/P1 对齐度排查：4 个 partial 候选

15 项对标卡状态虽全为 done，但逐卡核对「本轮目标」范围与**原版 packages 实际实现**后，发现 4 个真实 partial 点：

| # | 候选 | 原版对照 | 处置 |
|---|---|---|---|
| **#15 终端** | 标卡自述「**PTY 未做**(真 tty 交互转 stdlib/伪终端)；POSIX 信号未实测」 | `packages/terminal/terminal` 是 PTY 会话服务（spawn/read/startSend/signal/close） | ✅ **本轮收口** |
| #8 工具 | JSON Schema 是**宽松超集**（接受 pattern/minimum/maximum/…），原版 `assertSupportedJsonSchema` 会拒绝这些关键字 | `packages/core/tools/src/json-schema.ts` | ⏸ 保留超集（见 §3.1） |
| #13 沙箱 | 自述「不做 landlock/seccomp」 | `packages/sandbox/sandbox-local` 等 | ⏸ 平台不可收口（见 §3.2） |
| #9 压缩 | 仅 v1 确定性策略，缺 token 计量/压力自动触发/溢出恢复 | `packages/compaction/compaction-basic`（thresholdRatio/retainRatio/tokenMeter/context-overflow） | ⏸ 押后（见 §3.3） |

---

## 2. 本轮收口：#15 终端 → done(v2 PTY)

### 2.1 实现（`src/终端.light` 追加 `伪终端会话` 类）

复用**语言标准库** `stdlib/伪终端.light` 的 `伪控制台`（纯光明实现：Windows ConPTY / POSIX openpty），提供**真 tty** 交互（行缓冲、ANSI 颜色、交互式程序）。接口与管道式 `终端会话` 完全对齐，可互换：

| 能力 | 管道式 `终端会话`（v1，保留） | `伪终端会话`（v2，新增） |
|---|---|---|
| 底层 | subprocess.Popen 管道 | 伪控制台（ConPTY/openpty） |
| 启动/写入/读取(超时)/关闭 | ✅ | ✅ |
| 发信号 | SIGTERM/SIGINT→terminate、SIGKILL→kill | SIGINT→写入 `\x03`(Ctrl+C)；SIGTERM/SIGKILL→关闭(强杀) |
| 退出码 | ✅ 精确 | PTY 无（进程持续交互，码=空，文档说明） |
| 真 tty / ANSI | ✗ | ✅（ANSI 原样保留不解析，承原版语义） |
| 平台缺失 | — | 明确抛错（<Win10 1809 / 无 pty 模块），绝不降级管道 |

### 2.2 验证

- `python 运行.py examples/test_终端PTY.light` → **PASS**（启动+状态机 / echo 回显+结果 / 交互持续+自然退出+关闭）
- `python 运行.py examples/test_终端.light`（管道式）→ **PASS 不回归**
- pytest 回归门禁 → **66 passed**（原 65 + test_终端PTY）

### 2.3 文档

- `对标清单.json` #15：状态 `done(v1 管道式)` → `done(v2 PTY)`，本轮目标补 PTY 细节
- `README.md`：修复残余 `dsword`→`dswork`（第 13 轮漏改 1 处）；P1 表格/目录结构/回归门禁节补 PTY

---

## 3. 其余 3 个 partial 点的处置结论（本轮未收口）

### 3.1 #8 JSON Schema 严格对齐 —— 保留超集（不动）
原版 `assertSupportedJsonSchema` **拒绝** pattern/minimum/maximum/minLength/maxLength/minItems/maxItems 等关键字；光明版作为**超集宽松接受并校验**（T10-05 §4.3 已记载）。若严格化会同时破坏 `src/工具.light` 的 6×pattern、4×minimum 等工具定义与 `test_工具深.light` 用例——**改动面大且背离"校验有用"的实用价值**。维持超集，文档已注明对齐边界。

### 3.2 #13 沙箱 landlock/seccomp —— 平台不可收口
原版 sandbox 的 landlock/seccomp 是 **Linux 内核安全机制**，本项目运行在 Windows（无 landlock/seccomp），v1 已做路径护栏+进程隔离+超时（Windows 等价边界）。属于平台限制而非实现缺口，保持 v1 并保留文档说明。

### 3.3 #9 压缩多策略 —— 押后（规模超本轮）
原版 compaction-basic 的完整机制 = token 计量（tokenMeter）+ 压力自动触发（thresholdRatio/retainRatio）+ context-overflow 恢复 + LLM 摘要。光明版 v1 已对齐"手动确定性压缩+造摘要+原位替换"；补齐自动触发需在代理循环接线 token 计量与溢出重试，**涉及 P0 agent-loop 改动，验证链路长**，建议作为独立一轮专项（T15+）而非混入本轮收口。

---

## 4. 复跑方式

```powershell
Set-Location G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_终端PTY.light   # 终端 PTY（v2，需 Win10 1809+）
python 运行.py examples/test_终端.light      # 管道式终端（v1，不回归）
python -m pytest tests/ -q                   # 回归门禁（66 passed）
```
