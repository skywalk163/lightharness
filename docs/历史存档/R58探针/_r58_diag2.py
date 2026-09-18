# -*- coding: utf-8 -*-
import subprocess, re
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')

# 1. test_http_client.py git 状态与内容
p = LM / 'tests' / 'test_http_client.py'
print('=== test_http_client.py 存在:', p.exists(), '| mtime:', p.stat().st_mtime if p.exists() else '-')
r = subprocess.run(['git', '-C', str(LM), 'status', '--short', '--', 'tests/test_http_client.py'],
                   capture_output=True, text=True, encoding='utf-8')
print('git status:', r.stdout.strip() or '(clean/tracked)')
r = subprocess.run(['git', '-C', str(LM), 'ls-files', '--', 'tests/test_http_client.py'],
                   capture_output=True, text=True, encoding='utf-8')
print('ls-files:', repr(r.stdout.strip()))
if p.exists():
    txt = p.read_text(encoding='utf-8', errors='replace')
    print('--- 头部 20 行 ---')
    print('\n'.join(txt.splitlines()[:20]))
    print('--- 含 aiohttp/skip 的行 ---')
    for i, line in enumerate(txt.splitlines(), 1):
        if 'aiohttp' in line or 'skip' in line.lower() or 'importorskip' in line:
            print(' ', i, line.strip()[:100])

# 2. phase9 生成机制
p9 = LM / 'tests' / 'test_stdlib_phase9.py'
txt = p9.read_text(encoding='utf-8', errors='replace')
print()
print('=== test_stdlib_phase9.py 行数:', len(txt.splitlines()))
for kw in ['生成', 'write', 'Path(', 'hook', 'install', 'importlib', '断言工具', 'shutil', 'tmp']:
    hits = [(i, l.strip()[:120]) for i, l in enumerate(txt.splitlines(), 1) if kw in l]
    if hits:
        print('--- 关键词', kw, ':', len(hits), '处 ---')
        for i, l in hits[:6]:
            print(' ', i, l)
