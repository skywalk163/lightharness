# -*- coding: utf-8 -*-
import json
p = r'G:\dswork\duan-light-merge\lightharness\reports\_task4_R57_存量红明细_072454.json'
data = json.load(open(p, encoding='utf-8'))
reds = data['baseline_reds']
out = []
for r in reds:
    if r['category'].startswith('词法层'):
        out.append((r['category'], r['id'], r['message'][:100]))
print('词法层共 %d 条:' % len(out))
for c, i, m in out:
    print('[%s] %s' % (c, i))
    print('      %s' % m)
print()
# 语义债-代码生成断言 21 条 id
out2 = [r['id'] for r in reds if r['category'] == '语义债-代码生成断言']
print('语义债-代码生成断言 %d 条:' % len(out2))
for i in out2:
    print(' ', i)
print()
# 类/成员访问 14
out3 = [r['id'] for r in reds if r['category'] == '语义债-类/成员访问']
print('语义债-类/成员访问 %d 条:' % len(out3))
for i in out3:
    print(' ', i)
print()
# 解析层 7
out4 = [r['id'] for r in reds if r['category'] == '解析层-语法错误']
print('解析层-语法错误 %d 条:' % len(out4))
for i in out4:
    print(' ', i)
