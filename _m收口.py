# -*- coding: utf-8 -*-
import re, io

base = '/home/skywalk/dswork/lightharness'

# --- 1. 任务书：补 B-f2/B-f4/C 完成标记 ---
tp = base + '/docs/功能对标/R221_并行任务书_0.2.2-rc.3对齐.md'
t = open(tp, encoding='utf-8').read()
t = t.replace(
  '| **T-0367** |\n',
  '| **T-0367** ✅ 已完成（217b208） |\n'
)
t = t.replace(
  '| **T-0369** |\n',
  '| **T-0369** ✅ 已完成（d26e47e） |\n'
)
t = t.replace(
  '| **T-0365**（依赖 A1/A2） |\n',
  '| **T-0365** ✅ 已完成（f099c72，依赖 A1/A2） |\n'
)
t = t.replace(
  '| M | 收口：对标清单补条目、CHANGELOG、版本 bump、三远端 | 主控 | 待 B/C 完成 |\n',
  '| M | 收口：对标清单补条目、CHANGELOG、版本 bump、三远端 | 主控 | 进行中（对标清单 #358~#365 已补） |\n'
)
open(tp, 'w', encoding='utf-8').write(t)
print('任务书已更新')

# --- 2. CHANGELOG：插入 v0.6.1-rc1 段（patch 位递增） ---
cp = base + '/CHANGELOG.md'
c = open(cp, encoding='utf-8').read()

seg = """## [v0.6.1-rc1] — 2026-11-17

> **R221 收口（0.2.2-rc.3 对齐）**：上游锚点 `dsh-v0.2.2-rc.1`（`66491b05e3`）→ **`dsh-v0.2.2-rc.3`（`38a6a5c965`，2026-11-13）**。
> 版本自 `v0.6.0-rc1` 走 patch 位升 **`v0.6.1-rc1`**（同 rc.2 特性面收尾 + 插件面板缺陷修复）。

### 新增

- **HarnessError 基类**（B-f2 T-0367）：稳定机器码 `code` 与人类消息分离、`cause` 链、`name` 取子类名；rc.2 起 20+ 包新错误类统一继承（`src/错误增强.light`）。
- **forge 变更请求三条**（B-f1 T-0366）：#9 快照概览 / #10 diff 定 head / #11 评审读取码（`src/变更请求.light`）。
- **插件更新方式**（B-f3 T-0368）：#12 registry/git 双通道 + 安装结果核对（`src/插件注册表.light`）。
- **搜索按计费三态选凭据**（B-f3 T-0368）：#18 credential 来源 + 延迟失败语义（`src/网页搜索.light`）。
- **会话批量追加 + 运行时上下文提醒**（B-f4 T-0369）：#14 批量追加去重、#13 提醒完整模型（`src/会话.light` / `src/会话日志深化.light`）。
- **子代理中断默认关**（B-f4 T-0369）：#15 中断两层次语义（`src/子代理预设选择.light` / `src/代理团队.light`）。

### 修复

- **插件面板异常**（T-0385）：`造卡片` 透传 `工具表`、MCP 桥接补只读原因；修复启动后全部插件显示「异常 / 不包含任何组件」（`src/插件面板.light` / `src/web服务器.light`）。

### 变更

- **llm-deepseek 凭据与模型增补**（B7 T-0364）：新增 `credential.ts` + 模型/凭据增补，补 R220 漏项（`src/模型目录.light` / `src/模型列表缓存.light`）。
- **工作树清理判定**（B-f2 T-0367）：retainOnArchive / 未归档引用 / 只读（`src/工作区变更.light`）。
- **终端 CLEANUP_FAILED + 17 附件码**（B-f2 T-0367）：错误码归类（`src/终端.light` / `src/附件准入.light`）。
- **宿主面登记**（C T-0365）：§11 append，登记 126 → 148。

### 判据

- `examples/test_R221_B7模型增补.light`（119 断言）
- `examples/test_R221_Bf1变更请求快照.light`（76 断言）
- `examples/test_R221_Bf2错误与清理.light`（69 断言）
- `examples/test_R221_Bf3更新与计费.light`（67 断言）
- `examples/test_R221_Bf4会话与子代理.light`（117 断言）
- `examples/test_r221插件面板e2e.light`（10 断言）

"""

# 插到 v0.6.0-rc1 段之前
anchor = '## [v0.6.0-rc1] — 2026-11-16'
if anchor in c:
    c = c.replace(anchor, seg + anchor, 1)
    open(cp, 'w', encoding='utf-8').write(c)
    print('CHANGELOG 已插入 v0.6.1-rc1')
else:
    print('!! 未找到 v0.6.0-rc1 锚点')
