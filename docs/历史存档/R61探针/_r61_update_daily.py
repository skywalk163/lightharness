# -*- coding: utf-8 -*-
"""每日记忆 2026-09-18 追加 R61 收口段。"""
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\.workbuddy\memory\2026-09-18.md')
t = p.read_text(encoding='utf-8')
add = """
### 第61轮 收口（路M）：拆分后首轮全量门 + 4 新增红处置（已提交不 push）
- **任务2-4 交付核实**：本机定向 114 passed/1 skipped/1 xfailed rc=0。任务2 `_test_null_safety.py::test_paragraph_call` 旧式→现代语法（`段落 相加 接收 甲，乙：`，不改编译器），DeprecationWarning `段落 名 接收 参数` 已废弃；任务3 `code_generator.py:625` builtin_map 补 `'去除空格'→'_light_builtin.去除空白'` 连带修复 颜色/格式化/参数解析 同款裸名（**登记未修**：code_generator_unified.py ANTLR/unified 后端同款缺口）；任务4 截取族三后端 +5 用例 22 passed 双端一致。
- **全量门（唯一一次 0.82 fast py3.12 xdist，7884 用例，509.8s）**：对拍 201545（跨树对比）→ 已修复 4 = 预期全达成（test_paragraph_call + 钉桩 R22×2 + 身份证_O0对拍），**新增红 4**：
  1. **test_中文分词_O0对拍（真回归，已修）**：中文分词.light:124 `截取(文本,i,j)` 仍是 (start,len) 语义——R60 LLVM 截取对齐 [start:end] 的漏网，start>0 时 FMM 窗口失效（3 vs 4 词）；修 `截取(文本,i,i加j)`，本机 1 passed。
  2. **test_内置函数证据行号可定位（元数据漂移，已修）**：R60（a1b4e7a0）改 codegen_typed.py 净 +9 行未同步 docs/原生腿能力清单.json evidence 行号，226 条错位 → 自动重定位（_gen_typed_builtin 区间内按 name 取最近行，0 MISS），本机 1 passed。
  3. **test_ffi_full_workflow（环境性，已验）**：0.82 红本机绿 → 0.82 定向复跑 1 passed（FakeLib 抖动）。
  4. **test_获取JSON（外网瞬时，已验）**：httpbin 502 → 0.82 定向复跑 1 passed。
- **影响面**：中文工具族 + native_leg_capability + R61 hook腿 + null_safety 整文件 **40 passed** 无连带回归。
- **拆分提速结论（如实上行）**：拆分后全量**未变快**——509.8s vs R60 408s；sync 文件数 41197→5312（-87%）但包体积 30.71→120.24MB（+291%，266MB 中间产物：_taskR11B_test_* 143.73MB + LH docs 历史探针 92.90MB + 媒体 29.34MB）；积木库本就不参与 pytest 收集，拆分省的是 sync 文件数不是 pytest 执行时间。下轮建议中间产物进 EXCLUDE_DIRS。
- **两仓 commit（未 push）**：light-merge `e26ac68b`（14 改 + 3 报告 + 1 新测试，显式 git add）；lightharness `b84a5df`（对标 #200 + 233330 基线三件套 + _task1/_taskM_R61 报告 + R61探针/ 19 文件）。lighting 仓 `c3161d6e` 已提交未 push。
- **对标清单 #200 追加**（含拆分提速结论 + 遗留登记），diff 仅 +9 行（json.dumps ensure_ascii=False indent=1 与源格式吻合）。
- **遗留**：code_generator_unified.py 去除空格缺口；`段落 名 接收 参数` 废弃待现代化；lighting 未 push；266MB 中间产物治理待裁决。
"""
t = t.rstrip('\n') + '\n' + add.lstrip('\n')
p.write_text(t, encoding='utf-8')
print('2026-09-18.md appended')
