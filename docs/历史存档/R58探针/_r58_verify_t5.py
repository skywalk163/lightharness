# -*- coding: utf-8 -*-
import json
from pathlib import Path

F = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
raw = F.read_bytes().decode('utf-8')
print('BOM:', raw.startswith('\ufeff'))
print('尾换行:', raw.endswith('\n'))
print('CRLF:', '\r\n' in raw)
data = json.loads(raw)
items = data['条目']
print('条目数:', len(items))
print('编号范围:', items[0]['编号'], '->', items[-1]['编号'])
i197 = [x for x in items if x['编号'] == 197]
print('#197 存在:', bool(i197))
if i197:
    print('#197 备注长度:', len(i197[0]['备注']))
    print('#197 备注开头 300 字:')
    print(i197[0]['备注'][:300])
# 无损往返
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
print('无损往返一致:', canonical == raw)
# #196 是否被改
i196 = [x for x in items if x['编号'] == 196][0]
print('#196 备注含「确认为真并已修复」:', '确认为真并已修复' in i196['备注'])
