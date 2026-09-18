# -*- coding: utf-8 -*-
"""从 133700 xml 提取 stdlib_phase3 5 条 + 异步 5 条 message。"""
import re
from pathlib import Path

LH = Path(r'G:\dswork\duan-light-merge\lightharness')
xml = (LH / 'reports' / '_082_lm_results_2026-09-18-133700.xml').read_text(encoding='utf-8', errors='replace')
# 按 testcase 块切
blocks = re.findall(r'<testcase[^>]*classname="([^"]+)"[^>]*name="([^"]+)"[^>]*>(.*?)</testcase>', xml, re.S)
print('testcase 总数:', len(blocks))
for cn, nm, body in blocks:
    if ('stdlib_phase3' in cn) or ('异步修饰符' in nm):
        m = re.search(r'<(failure|error)[^>]*message="([^"]*)"', body)
        msg = m.group(2)[:220] if m else '(none)'
        print(f'{cn}::{nm}\n   [{msg}]')
