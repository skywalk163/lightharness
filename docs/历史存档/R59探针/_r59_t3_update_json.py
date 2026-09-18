# -*- coding: utf-8 -*-
"""R59 task3: 重录 docs/原生腿能力清单.json 的 builtin evidence 行号 + 补 20 判型内置 + 补 strcmp。"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(ROOT, 'src', 'llvm', 'codegen_typed.py')
JSONF = os.path.join(ROOT, 'docs', '原生腿能力清单.json')

src = open(CODE, encoding='utf-8').read()
lines = src.splitlines()
i = src.find('def _gen_typed_builtin(')
j = src.find('\n    def ', i + 10)
start = src[:i].count('\n') + 1
end = (src[:j].count('\n') + 1) if j > 0 else src.count('\n') + 1
assert i > 0

def locate(name):
    needle = "'" + name + "'"
    for ln in range(start, end + 1):
        if needle in lines[ln - 1]:
            return ln
    return None

d = json.load(open(JSONF, encoding='utf-8'))
b = d['tables']['builtin_functions']
rt = d['tables']['runtime_symbols']

# 1) re-evidence all existing builtin entries
fixed = 0
for e in b['entries']:
    ln = locate(e['name'])
    assert ln, f"无法定位 {e['name']}"
    old = e.get('evidence')
    new = f"src/llvm/codegen_typed.py:{ln}"
    if old != new:
        e['evidence'] = new
        fixed += 1
print(f'builtin evidence updated: {fixed}/{len(b["entries"])}')

# 2) append 20 type-predicate builtins (if missing)
existing = {e['name'] for e in b['entries']}
new_preds = [
    ('是列表', 'Type'), ('是数组', 'Type'), ('is_list', 'Type'),
    ('是字典', 'Type'), ('is_dict', 'Type'), ('is_map', 'Type'),
    ('是字符串', 'Type'), ('is_str', 'Type'), ('is_string', 'Type'),
    ('是数值', 'Type'), ('是数字', 'Type'), ('is_number', 'Type'),
    ('是整数', 'Type'), ('is_int', 'Type'), ('is_integer', 'Type'),
    ('是浮点', 'Type'), ('是浮点数', 'Type'), ('is_float', 'Type'),
    ('是布尔', 'Type'), ('is_bool', 'Type'),
]
added = 0
for name, cat in new_preds:
    if name in existing:
        continue
    ln = locate(name)
    assert ln, f"新内置无法定位 {name}"
    b['entries'].append({'name': name, 'evidence': f"src/llvm/codegen_typed.py:{ln}", 'category': cat})
    added += 1
print(f'builtin appended: {added}')
b['count'] = len(b['entries'])

# 3) append strcmp to runtime_symbols (libc, declared at codegen:686)
rtexisting = {e['name'] for e in rt['entries']}
if 'strcmp' not in rtexisting:
    rt['entries'].append({
        'name': 'strcmp',
        'evidence_declare': 'src/llvm/codegen_typed.py:686',
        'evidence_define': 'C library (not in runtime_typed.c)',
        'category': 'String',
    })
    print('runtime_symbols appended: strcmp')
rt['count'] = len(rt['entries'])

json.dump(d, open(JSONF, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('written. builtin count =', b['count'], 'runtime count =', rt['count'])
