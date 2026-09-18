# -*- coding: utf-8 -*-
"""R60 路M：对标清单追加 #199（ensure_ascii=False + indent=1 + CRLF + 无尾换行 + 无BOM，round-trip 自证）。"""
import json
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
data = json.loads(p.read_text(encoding='utf-8'))
items = data['条目']
assert items[-1]['id'] == '#198', f"末尾 id 异常: {items[-1]['id']}"

new_entry = {
    "id": "#199",
    "轮次": "R60",
    "标题": "路M 收口：compact 词法 + 异步拦截收窄 + 截取族修复；门 FAIL（3 新增红已处置待下轮全量确认）",
    "内容": (
        "R60 收口（用户'你写我发'分发 → WorkBuddy 跑任务1-4 → 主 agent 收口路M）。\n"
        "【全量门（唯一一次 0.82 fast，7871 用例）】13 → 4 红，新增红 3、已修复 12、持平 1。\n"
        "【已修复 12】R59 已修 3（钉桩 R19、T6C 参数解析、T6C URL）+ 任务2 异步修饰符编译期报错 5 + 任务1 compact 1 + examples 连带 1 + 任务3 地板搬迁 1 + 4A-2 func_non_nullable 连带 1。\n"
        "【持平 1 = 存量剩红】test_paragraph_call（旧式语法，归因 R61）。\n"
        "【3 新增红处置（均非回归，双端定向验证，未重跑全量）】\n"
        "1) test_身份证校验_O0对拍：任务3 按官方 [start:end] 语义改身份证校验.light 截取 → 暴露 LLVM 后端 `截取` 语义缺陷——codegen_typed.py:2467 调 dv_substr(str,start,len) 把第三参 end 直传 len（dv_substr 内 en=st+len），与 .light 官方定义（内置核心字符串.light L13-15 [start:end]）不一致；修复：LLVM 后端 `截取` 改传 end-start 并 clamp 负值（对齐字符串切片 4223-4235）。连带暴露颜色.light RGB解析 2 处 (start,len) 误用：L201 `截取(干净,1,长(干净)-1)`→`长(干净)`、L222 `截取(干净,左括+1,右括-左括-1)`→`右括`（原 len 语义下碰巧对）。修复后本机 + 0.82 定向（身份证/手机号/T6C 颜色/编码解码/参数解析）全绿。\n"
        "2) 钉桩 R22_接收字合并 × 2（test_现状钉桩_R22_接收字合并、test_现状钉桩_全角逗号）：任务1 修复 B 修好 `接收甲` 合并（现在 段落/加法/接收/甲）→ 钉桩过期 → 转正更新（断言反转 + 缺陷关闭），本机 + 0.82 定向 4 钉桩全绿。\n"
        "【路M 收窄（关键，防门 FAIL 于未然）】任务2 异步拦截（IDENTIFIER 形态 异步* 当值一律报错）误伤 3 条合法已定义名：stdlib/并发.light:81（异步信号量）、stdlib/HTTP服务端.light:451（异步接受）、examples/test_R21_L152家族嵌套形参.light:66（异步作用域）——合并树互举反跑 677 曾新增 3 条解析失败；路M 在拦截条件补放行 lexer.user_definitions 已定义名（`异步` 开头且已定义 = 合法值）→ 互举反跑复跑 0 新增（+已修复 2），5 条目标红仍编译期拦截（本机+0.82 定向 6 passed）。\n"
        "【门态】全量快照 = FAIL（3 新增红）；最新工作树 3 处已处置（LLVM 截取修复 + 颜色 2 处 + 钉桩转正）+ 收窄，本机 9 passed / 0.82 全定向 165 passed / 0 failed，未重跑全量（用户硬约束仅 1 次），下轮全量确认 0 新增、剩 1 存量红 test_paragraph_call（R61）。"
    ),
    "门态": "FAIL(3新增红已处置待全量确认)",
    "基线": "172617",
    "日期": "2026-09-18"
}
items.append(new_entry)

# 写改规则：indent=1 + ensure_ascii=False + CRLF + 无尾换行 + 无BOM
s = json.dumps(data, ensure_ascii=False, indent=1)
s = s.replace('\n', '\r\n')
p.write_bytes(s.encode('utf-8'))  # 无 BOM

# round-trip 自证
d2 = json.loads(p.read_text(encoding='utf-8'))
assert d2 == data, 'round-trip 不一致'
assert d2['条目'][-1]['id'] == '#199'
assert not p.read_bytes().startswith(b'\xef\xbb\xbf'), '出现 BOM'
print(f"OK: 共 {len(d2['条目'])} 条（{d2['条目'][-2]['id']} → {d2['条目'][-1]['id']}），BOM 无，CRLF 无尾换行")
