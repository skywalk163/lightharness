# -*- coding: utf-8 -*-
"""R59 task3 probe: locate real evidence lines for builtin names and strcmp."""
import json, re, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CODE = os.path.join(ROOT, 'src', 'llvm', 'codegen_typed.py')
JSONF = os.path.join(ROOT, 'docs', '原生腿能力清单.json')
RTC = os.path.join(ROOT, 'src', 'llvm', 'runtime_typed.c')

src = open(CODE, encoding='utf-8').read()
lines = src.splitlines()

# method range
i = src.find('def _gen_typed_builtin(')
j = src.find('\n    def ', i + 10)
start = src[:i].count('\n') + 1
end = (src[:j].count('\n') + 1) if j > 0 else src.count('\n') + 1
print(f'_gen_typed_builtin range: {start}..{end}')

data = json.load(open(JSONF, encoding='utf-8'))
entries = data['tables']['builtin_functions']['entries']
print('builtin entries:', len(entries))

unlocated = []
mapping = {}
for e in entries:
    name = e['name']
    # search for quoted 'name' within method body lines
    needle = "'" + name + "'"
    found = None
    for ln in range(start, end + 1):
        if needle in lines[ln - 1]:
            found = ln
            break
    if found is None:
        unlocated.append(name)
    else:
        mapping[name] = found

print('unlocated:', unlocated)
# show a few mappings
for n in ['?.', '??', 'abs', '打印', '列表追加']:
    print(n, '->', mapping.get(n))

# now find the 20 missing names registration lines
missing = ['is_bool','is_dict','is_float','is_int','is_integer','is_list','is_map',
           'is_number','is_str','is_string','是列表','是字典','是字符串','是布尔',
           '是数值','是数字','是数组','是整数','是浮点','是浮点数']
print('--- missing name locations ---')
for m in missing:
    needle = "'" + m + "'"
    found = None
    for ln in range(start, end + 1):
        if needle in lines[ln - 1]:
            found = ln
            break
    print(m, '->', found, '|', lines[found-1].strip()[:90] if found else 'NOT FOUND')

# strcmp
print('--- strcmp ---')
for ln, l in enumerate(lines, 1):
    if 'strcmp' in l and ('declare' in l or '@strcmp' in l):
        print(f'codegen {ln}: {l.strip()[:120]}')
rt = open(RTC, encoding='utf-8').read().splitlines()
for ln, l in enumerate(rt, 1):
    if 'strcmp' in l:
        print(f'runtime_typed.c {ln}: {l.strip()[:120]}')
