# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\.workbuddy\memory\MEMORY.md')
text = p.read_text(encoding='utf-8')
block = '''
## R58 路M 收口（2026-09-18）
- **门 PASS（修正后）**：终跑 133701（64 红）对拍 R57 基线 100010（99 红）：**新增红 0（修正后）/ 已修复 36（词法16+环境18+额外2）/ 持平 63**；红数 99→63。全程 0.82 全量 **2 次**（131415 首跑暴露 R57 遗留 → 修复 → 133701 终跑定门，破例 1 次，本机零全量）。
- **最重要发现：R57 门 PASS 是「运气」——phase9 钩子缺陷未根治，R58 已修（L-176）**。机制：`_light_import_hook._is_pure_light`（首两行含「纯光明实现」魔数 → 优先加载 .light 无视同名 .py）vs `stdlib/断言工具.light` 头注释「缺名回退 .py」自相矛盾；.light 是原生腿安全子集（276 行无高级断言），完整实现在 断言工具.py（617 行）。钩子装载时 .light 优先 → `from 断言工具 import 断言属性存在` 等 ImportError（phase9 6 条）；100010 绿是 worker 没装钩子的运气（R56 各轮红绿抖动同源）。**修复**：断言工具.light 首行去魔数（且全文无魔数字样，守护栏 test_pure_light_hook）→ .py 优先 → phase9 全绿（本机 145 / 0.82 126 passed）。教训：**钩子/装载顺序类缺陷，定向全绿也会漏**（R57 组合跑 16 绿也是假象）；此类缺陷只能靠「钩子装载 vs 未装载」双路径验证 + 全量兜底。
- **其余新增红**：aiohttp 2 条（test_http_client 文件级 importorskip("requests")，装 requests 后不再 skip 暴露缺 aiohttp）→ 0.82 装 aiohttp 3.14.3 转绿（49 passed）；flaky 1 条（重派心跳）单条 10/10 绿确认为高负载偶发。
- 探针移档 `docs/历史存档/R58探针/`（含 _r58_fix_lightmagic*.py/_r58_gate_*.py 等）。
'''
if 'R58 路M 收口' in text:
    print('已存在，跳过')
else:
    text = text.rstrip('\n') + '\n' + block
    p.write_text(text, encoding='utf-8')
    print('已追加，总长', len(text))
