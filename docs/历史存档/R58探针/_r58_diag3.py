# -*- coding: utf-8 -*-
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')

# 1. stdlib 里 断言工具.* 文件
sd = LM / 'stdlib'
hits = [f.name for f in sd.iterdir() if '断言' in f.name]
print('=== stdlib 含「断言」文件:', hits)

# 2. _light_import_hook.py 回退逻辑
hk = LM / 'stdlib' / '_light_import_hook.py'
txt = hk.read_text(encoding='utf-8', errors='replace')
print('=== _light_import_hook.py 行数:', len(txt.splitlines()))
for kw in ['回退', 'fallback', '.py', '同名', 'suffix', 'exists', 'find_spec', '忽略', 'ignore']:
    hits2 = [(i, l.strip()[:110]) for i, l in enumerate(txt.splitlines(), 1) if kw in l]
    if hits2:
        print('---', kw, len(hits2), '处 ---')
        for i, l in hits2[:8]:
            print(' ', i, l)

# 3. tests/test_stdlib_phase9/ 目录内容
d9 = LM / 'tests' / 'test_stdlib_phase9'
if d9.exists():
    print('=== tests/test_stdlib_phase9/ 内容 ===')
    for f in d9.iterdir():
        print(' ', f.name, f.stat().st_size)
    # 生成物 测试断言工具.py 的 import 行
    gen = d9 / '测试断言工具.py'
    if gen.exists():
        g = gen.read_text(encoding='utf-8', errors='replace')
        print('--- 生成物 import 行 ---')
        for i, l in enumerate(g.splitlines(), 1):
            if 'import' in l and '断言工具' in l:
                print(' ', i, l.strip()[:100])
