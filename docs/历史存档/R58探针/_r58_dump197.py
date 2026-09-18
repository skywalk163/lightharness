# -*- coding: utf-8 -*-
import json
from pathlib import Path

F = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
raw = F.read_bytes().decode('utf-8')
data = json.loads(raw)
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
assert canonical == raw, '无损自证失败'
i197 = [x for x in data['条目'] if x['编号'] == 197][0]
open(r'G:\dswork\duan-light-merge\lightharness\_r58_i197_full.txt', 'w', encoding='utf-8').write(i197['备注'])
print('已导出，长度', len(i197['备注']))
