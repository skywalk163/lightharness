# -*- coding: utf-8 -*-
"""R58 收口：#197 备注补路M 最终结果。"""
import json
from pathlib import Path

F = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
raw = F.read_bytes().decode('utf-8')
data = json.loads(raw)
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
assert canonical == raw, '无损自证失败'

i197 = [x for x in data['条目'] if x['编号'] == 197][0]
old = '⑥路M：唯一一次 0.82 全量（fast py3.12），详见 _taskM_R58_收口总报告.md。'
new = (
    '⑥路M：门 PASS（修正后）——终跑 133701（64 红）对拍 100010（99 红）：新增红 0 / 已修复 36 / 持平 63；'
    '红数 99→63。破例发现并修复 **L-176**：断言工具.light 的「纯光明实现」魔数与头注释「缺名回退 .py」自相矛盾'
    '（_is_pure_light 优先 .light 无视 .py → phase9 高级断言 ImportError，R57 门 PASS 实为未触发钩子的运气），'
    '去魔数后 .py 优先、phase9 全绿；另 0.82 装 aiohttp 补环境（2 条转绿）、flaky 单条 10/10 确认偶发。'
    '全量实况 2 次（破例 1 次）。详见 _taskM_R58_收口总报告.md。'
)
assert old in i197['备注'], '未找到 ⑥ 段'
i197['备注'] = i197['备注'].replace(old, new)

out = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
assert not out.endswith('\n')
F.write_bytes(out.encode('utf-8'))
data2 = json.loads(F.read_bytes().decode('utf-8'))
canon2 = json.dumps(data2, ensure_ascii=False, indent=1).replace('\n', '\r\n')
print('[回读] 条目数', len(data2['条目']), '| 往返一致', canon2 == out)
i197b = [x for x in data2['条目'] if x['编号'] == 197][0]
print('[197] 含 L-176:', 'L-176' in i197b['备注'], '| 含 门 PASS:', '门 PASS' in i197b['备注'])
