# -*- coding: utf-8 -*-
"""R61 收口：原生腿能力清单 evidence 行号重定位。

R60（a1b4e7a0）改 codegen_typed.py（+12-3）后，docs/原生腿能力清单.json 里
builtin_functions 的 evidence 行号整体漂移 → test_内置函数证据行号可定位 红。

方案：对每条 entry，在 _gen_typed_builtin 方法体区间内找「含该 name 的行」，
取与旧行号最接近的命中行作为新行号；未命中记录 MISS 待人工。
文本级精确替换（只改 evidence 值），保留 JSON 原格式，最小 diff。
"""
import json
import re
from pathlib import Path

ROOT = Path(r'G:\dswork\duan-light-merge\light-merge')
JSON = ROOT / 'docs' / '原生腿能力清单.json'
CODE = ROOT / 'src' / 'llvm' / 'codegen_typed.py'

src = CODE.read_text(encoding='utf-8')
lines = src.splitlines()

# _gen_typed_builtin 方法体区间（1-based 闭区间）
i = src.find('def _gen_typed_builtin(')
assert i > 0, '找不到 _gen_typed_builtin'
j = src.find('\n    def ', i + 10)
起 = src[:i].count('\n') + 1
止 = (src[:j].count('\n') + 1) if j > 0 else src.count('\n') + 1
print(f'_gen_typed_builtin 区间 [{起}, {止}]')

text = JSON.read_text(encoding='utf-8')
data = json.loads(text)
entries = data['tables']['builtin_functions']['entries']
print(f'entries={len(entries)}')

changed, miss = [], []
for e in entries:
    name = e['name']
    ev = e['evidence']
    m = re.search(r'codegen_typed\.py:(\d+)', ev)
    if not m:
        miss.append((name, 'evidence 格式异常: ' + ev))
        continue
    旧号 = int(m.group(1))
    # 方法体内含该 name 的所有行
    cand = [ln for ln in range(起, 止 + 1) if name in lines[ln - 1]]
    if not cand:
        miss.append((name, f'方法体内无含名行（旧号 {旧号}）'))
        continue
    新号 = min(cand, key=lambda ln: abs(ln - 旧号))
    if 新号 == 旧号:
        continue  # 无需改
    # 文本级替换：定位该 entry 的 evidence 值
    pat = re.compile(r'"name":\s*"' + re.escape(name) + r'"')
    mm = pat.search(text)
    assert mm, f'JSON 里找不到 name={name}'
    seg = text[mm.end():]
    evm = re.search(r'"evidence":\s*"src/llvm/codegen_typed\.py:(\d+)"', seg)
    assert evm, f'找不到 evidence: {name}'
    old_ev = seg[evm.start():evm.end()]
    new_ev = f'"evidence": "src/llvm/codegen_typed.py:{新号}"'
    text = text[:mm.end()] + seg[:evm.start()] + new_ev + seg[evm.end():]
    changed.append((name, 旧号, 新号))

print(f'已更新 {len(changed)} 条')
for c in changed[:15]:
    print('  ', c)
if len(changed) > 15:
    print(f'  … 共 {len(changed)} 条')
print(f'MISS {len(miss)} 条：')
for name, why in miss[:30]:
    print('  ', name, '—', why)
if len(miss) > 30:
    print(f'  … 共 {len(miss)} 条')

JSON.write_text(text, encoding='utf-8')
print('已写回', JSON)
