# -*- coding: utf-8 -*-
"""更新 MEMORY.md：R61 收口完成。"""
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\.workbuddy\memory\MEMORY.md')
t = p.read_text(encoding='utf-8')
old = "- **R61 其余待办**：任务2 `test_paragraph_call` 旧式语法现代化；任务3 `中文数字转换.light` 裸名 `去除空格` hook 腿 NameError；任务4 截取族三后端覆盖。预期终态 **0 红**（`test_积木库导入…` 转 skip 1 条，属预期非红）。"
assert old in t, '旧待办行未找到'
new = ("- **R61 门**：基线 **233330**（4 红 / 7884 用例 / 509.8s），对拍 201545 = 已修复 4（预期全达成）+ 新增红 4 全处置 → **门 PASS**。\n"
       "  - 真回归 2（已修）：① 中文分词.light:124 `截取(文本,i,j)` (start,len) 误用 → `截取(文本,i,i加j)`（R60 LLVM 截取对齐 [start:end] 的漏网，start>0 时 FMM 窗口失效）；② docs/原生腿能力清单.json evidence 行号漂移 226 条（R60 改 codegen_typed.py 净 +9 行未同步）→ 自动重定位 0 MISS。\n"
       "  - 环境性 2（已验）：ffi FakeLib 抖动（0.82 定向 1 passed）、httpbin 502 外网瞬时（0.82 定向 1 passed）。\n"
       "  - 影响面：中文工具族 + native_leg_capability + R61 hook腿 + null_safety 整文件 40 passed。\n"
       "  - 两仓 commit（未 push）：light-merge `e26ac68b`、lightharness `b84a5df`；对标清单 **#200**；探针移档 `docs/历史存档/R61探针/`。\n"
       "- **拆分提速结论（R61 实测，须如实上行）**：拆分后全量**未变快**——0.82 全量 509.8s vs R60 408s；sync 文件数 41197→5312（-87%）但包体积 30.71→120.24MB（+291%，266MB 中间产物拖累）；积木库本就不参与 pytest 收集，拆分省的是 sync 不是 pytest 执行时间。下轮建议 `_taskR11B_test_*/`、docs 历史探针、媒体进 EXCLUDE_DIRS。\n"
       "- **R62 待办**：lighting 仓 `c3161d6e`（CI 迁移 19 files）**未 push**；sync 中间产物 266MB 治理；code_generator_unified.py `去除空格` 缺口（ANTLR/unified 后端）；`段落 名 接收 参数` 语法废弃待现代化；下轮全量确认 4 红转绿（预期 0 新增）。")
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('MEMORY.md updated')
