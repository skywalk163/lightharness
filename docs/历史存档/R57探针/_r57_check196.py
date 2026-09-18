# -*- coding: utf-8 -*-
import json
p = r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json'
d = json.load(open(p, encoding='utf-8'))
items = d['条目']
nums = [x['编号'] for x in items]
print('条目数:', len(items))
print('编号连续 1..%d: %s' % (max(nums), nums == list(range(1, max(nums) + 1))))
i196 = [x for x in items if x['编号'] == 196][0]
print('196 备注长度:', len(i196['备注']))
print('196 备注开头:', i196['备注'][:80])
print('196 证据条数:', len(i196['证据']))
# 无损：除 196 外历史条目与追加前一致（用原始 195 核对）
i195 = [x for x in items if x['编号'] == 195][0]
print('195 备注开头:', i195['备注'][:60])
