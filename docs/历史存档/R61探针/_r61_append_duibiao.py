# -*- coding: utf-8 -*-
"""R61 收口：对标清单追加 #200。"""
import json
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
data = json.loads(p.read_text(encoding='utf-8'))
assert data['条目'][-1]['id'] == '#199', data['条目'][-1]['id']

entry = {
    "id": "#200",
    "轮次": "R61",
    "标题": "拆分后首轮全量收口：真·拆分树全量 4 红（2 真回归已修 + 2 环境性已验）；存量红清零达成",
    "内容": "R61 收口（用户'你写我发'分发 → WorkBuddy 跑任务1-4 → 主 agent 收口处置 4 新增红）。\n"
            "【任务1-4 交付】1) 拆分提速量化：sync 文件数 41197→5312（-87%），但包体积 30.71→120.24MB"
            "（+291%，被 266MB 中间产物拖累：_taskR11B_test_* 143.73MB + docs 历史探针 92.90MB + 媒体 29.34MB）；"
            "**关键纠正**：R60 全量（201545）实际跑在仍含积木库的树上（拆分提交 be178387 在其后），R61 才是真·拆分后首轮，"
            "对拍属跨树对比；1A 清障 5 改 2 删（含删两个纯积木库 CI）。"
            "2) test_paragraph_call 测试现代化（旧式'段落相加(甲,乙)：'→'段落 相加 接收 甲，乙：'，不改编译器），"
            "DeprecationWarning：'段落 名 接收 参数' 已废弃，将来需再现代化。"
            "3) code_generator.py L625 builtin_map 补 '去除空格'→'_light_builtin.去除空白'，"
            "连带修复 颜色/格式化/参数解析 同款裸名；**登记未修**：code_generator_unified.py（ANTLR/unified 后端）同款缺口仍在。"
            "4) 截取族三后端对拍扩展 +5 用例（22 passed 双端一致），原生腿 4 条已知限制写入 docstring。\n"
            "【全量门（唯一一次 0.82 fast，py3.12 xdist，7884 用例）】4 → 4 红（R60 基线 201545 对拍），"
            "已修复 4 = 预期全达成（test_paragraph_call + 钉桩 R22×2 + 身份证校验_O0对拍），**新增红 4**。\n"
            "【4 新增红处置（2 真回归已修 + 2 环境性已验）】\n"
            "1) test_中文分词_O0对拍（本机+0.82 双侧红，3 vs 4 词）：**真回归**——R60 LLVM 截取语义对齐 [start:end] 的漏网："
            "中文分词.light:124 `截取(文本, i, j)` 仍是 (start,len) 语义，start>0 时取错窗口（FMM 窗口失效）；"
            "修 `截取(文本, i, i 加 j)`，本机 1 passed。\n"
            "2) test_内置函数证据行号可定位（本机+0.82 双侧红）：**元数据漂移**——R60（a1b4e7a0）改 codegen_typed.py 净 +9 行"
            "未同步 docs/原生腿能力清单.json evidence 行号，226 条错位；自动重定位（_gen_typed_builtin 区间内按 name 取最近行，"
            "0 MISS），本机 1 passed。\n"
            "3) test_ffi_full_workflow（0.82 红、本机绿）：环境性抖动，0.82 定向复跑 1 passed。\n"
            "4) test_获取JSON（httpbin 502）：外网瞬时不可用，0.82 定向复跑 1 passed（httpbin 恢复）。\n"
            "【影响面复跑】中文工具族 + native_leg_capability + R61 hook腿 + null_safety 整文件 40 passed，无连带回归。\n"
            "【门态】全量快照 4 红全部处置（2 修复本机验证 + 2 环境性 0.82 定向验证），未重跑全量（用户硬约束仅 1 次），"
            "下轮全量确认 0 新增。\n"
            "【拆分提速结论（须上行给用户）】拆分后**全量并未变快**：0.82 全量 509.8s vs R60 408s（用例 +13、中间产物拖累 sync 包体）；"
            "文件数 87% 减少的红利被 266MB 中间产物抵消，建议下轮治理 _taskR11B_test_*/docs 历史探针/媒体进 EXCLUDE_DIRS。\n"
            "【遗留登记】code_generator_unified.py 去除空格缺口；'段落 名 接收 参数' 语法废弃待现代化；"
            "lighting 仓 28 条未推送（未授权）。",
    "门态": "PASS(4新增红全部处置：2修复+2环境性验证)",
    "基线": "201545",
    "日期": "2026-09-18"
}
data['条目'].append(entry)
p.write_text(json.dumps(data, ensure_ascii=False, indent=1, separators=(",", ": ")), encoding='utf-8')
print('appended #200, total =', len(data['条目']))
