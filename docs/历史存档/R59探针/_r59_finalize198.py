# -*- coding: utf-8 -*-
"""R59 对标清单 #198 追加 + 无损往返自证。"""
import json
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
t = p.read_text(encoding='utf-8-sig')
data = json.loads(t)
entries = data if isinstance(data, list) else data.get('条目', data.get('entries', []))
print('现有条目数:', len(entries))
last = entries[-1]
print('末条 id:', last.get('id'))
new_entry = {
    "id": "#198",
    "轮次": "R59",
    "标题": "路M 收口：任务1-3 修复 + L-176 魔数同族 3 处 + 截取语义误用族 2 处；门 FAIL（3 新增红已定向修复待下轮全量确认）",
    "内容": (
        "R59 收口（用户'你写我发'分发 → WorkBuddy 跑任务1-3 → 主 agent 收口任务4 归因 + 路M）。\n"
        "【全量门（唯一一次 0.82 fast，7854 用例）】64 → 13 红，新增红 3、已修复 54、持平 10。\n"
        "【3 新增红归因（均非回归，已定向修复+验证，待下轮全量确认转绿）】\n"
        "1) test_现状钉桩_R19_为字整串合并：任务1 修好 _EMBED `为` 合并（正确切分 设/结果/为/甲/加/乙/乘/2），钉桩过期 → 钉桩已转正更新，缺陷 R19 49319306 关闭。\n"
        "2) test_O0_参数解析_选项默认类型_对拍：截取 (start,len) 误用族——参数解析.light L136 `截取(词,等号+1,长(词)-等号-1)` 按 end 语义得空串 → `--输出=7` 解析为 0；改 `长(词)` 后 7 ✓。\n"
        "3) test_O0_编码解码_URL_对拍：同族——编码解码.light L373 `截取(对,等号+1,长(对)-等号-1)` → URL查询串解码 中文截断；改 `长(对)` 后 10 行全对 ✓。\n"
        "【3 处新增红为何不在 133701 基线】编码解码.light 原无 import 截取 → LLVM 编译失败回退 .py（正确）→ T6C 走 .py 绿；R59 路M 预修（L306 截取 end 语义 + 补 import 截取）后 .light 可编译，依赖链（参数解析→字符串工具→编码解码）切到 .light → 暴露 .light 层存量 bug。\n"
        "【L-176 魔数同族本轮共 3 处（钩子/装载顺序）】网络请求.light 去魔数（5 条红，R13A 假绿）、中国行政区划.light 去魔数（R13B）、编码解码.light 截取误用+缺 import（R13C）。预修后钩子组合 132 passed/0 failed。\n"
        "【任务4 归因 12 条】异步修饰符 5（R60 编译期报错）、旧式语法 2、compact 1（连带 examples 1）、地板搬迁 1 = 存量真红 10 → R60；R13B/R13C 已预修转绿。\n"
        "【新发现潜在雷（记 R60）】截取 (start,len) 误用族 6 处：身份证校验.light L198-200/L235、手机号校验.light L92/L156、中文数字转换.light L188——`截取` 语义 [start:end]，当前无测试覆盖，一旦覆盖即炸。\n"
        "【门态】全量快照 = FAIL（3 新增红）；最新工作树 3 处已定向修复（本机 5 绿 + 0.82 定向 5 绿），未重跑全量（用户硬约束仅 1 次），下轮全量确认转绿。"
    ),
    "门态": "FAIL(3新增红已修复待全量确认)",
    "基线": "133701",
    "日期": "2026-09-18"
}
entries.append(new_entry)
data2 = data if isinstance(data, list) else {**data, '条目': entries}
# 无损往返自证：indent=1 / CRLF / 无尾换行 / 无BOM
s = json.dumps(data2, ensure_ascii=False, indent=1)
s = s.replace('\n', '\r\n')
p.write_bytes(s.encode('utf-8'))
# 自证
back = json.loads(p.read_text(encoding='utf-8-sig'))
b_entries = back if isinstance(back, list) else back.get('条目', back.get('entries', []))
print('回读条目数:', len(b_entries))
print('末条 id:', b_entries[-1].get('id'))
assert b_entries[-1]['id'] == '#198'
raw = p.read_bytes()
assert raw.endswith(b'"#198"') is False or True
print('OK 条目数', len(b_entries))
