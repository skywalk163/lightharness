# -*- coding: utf-8 -*-
"""规范化对标清单：统一为 dumps(indent=1, ensure_ascii=False) + CRLF + 无尾换行。"""
import json
from pathlib import Path

F = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
raw = F.read_bytes().decode('utf-8')
data = json.loads(raw)
print('[解析] 条目数:', len(data['条目']))
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
print('[差异] 规范长度 %d vs 当前 %d' % (len(canonical), len(raw)))
if canonical != raw:
    # 逐字符找差异
    for i, (a, b) in enumerate(zip(canonical, raw)):
        if a != b:
            print('首处差异 @%d:' % i)
            print('  规范:', repr(canonical[max(0, i - 40):i + 40]))
            print('  当前:', repr(raw[max(0, i - 40):i + 40]))
            break
assert not canonical.endswith('\n')
F.write_bytes(canonical.encode('utf-8'))
print('[写回] 规范化完成，大小 %d 字节' % F.stat().st_size)
data2 = json.loads(F.read_bytes().decode('utf-8'))
print('[回读] 条目数:', len(data2['条目']))
canon2 = json.dumps(data2, ensure_ascii=False, indent=1).replace('\n', '\r\n')
print('[终验] 规范往返一致:', canon2 == canonical)
i196 = [x for x in data2['条目'] if x['编号'] == 196][0]
print('[196] 备注长度:', len(i196['备注']), '｜ 备注头部:', i196['备注'][:60])
