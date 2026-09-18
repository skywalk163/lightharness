# -*- coding: utf-8 -*-
"""查 133701 基线 JSON 中网络请求 5 条 + 其他红的 message 原文。"""
import json, re
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
base = json.loads((LH / 'reports' / '082_lightmerge基线_2026-09-18-133701.json').read_text(encoding='utf-8'))
fails = base['failed']
print('failed 元素结构示例:')
print(json.dumps(fails[0], ensure_ascii=False, indent=1)[:500])
print('\n=== 网络请求相关红 message ===')
for f in fails:
    if isinstance(f, dict) and '网络' in str(f.get('name', '')) or (isinstance(f, str) and 'stdlib_phase3' in f):
        print(json.dumps(f, ensure_ascii=False, indent=1)[:900])
        print('---')
# 找 地板搬迁 与 examples 的 message
print('\n=== 地板搬迁 / examples / R13 / compact 红 message ===')
for f in fails:
    s = str(f)
    if any(k in s for k in ['地板搬迁', 'examples_run', '原生腿_R13', 'compact_binary']):
        if isinstance(f, dict):
            print(json.dumps(f, ensure_ascii=False, indent=1)[:700])
        else:
            print(s)
        print('---')
