# -*- coding: utf-8 -*-
"""查 100010 junitxml：test_http_client 与 phase9 的状态；查钩子回退逻辑。"""
import re
from pathlib import Path

xml = Path(r'G:\dswork\duan-light-merge\lightharness\reports\_082_lm_results_2026-09-18-100010.xml').read_text(encoding='utf-8')
print('=== 100010 中 test_http_client 相关 testcase ===')
for m in re.finditer(r'<testcase[^>]*classname="([^"]*test_http_client[^"]*)"[^>]*name="([^"]*)"[^>]*>\s*<(?:failure|error|skipped)[^>]*message="([^"]{0,80})', xml):
    print(' ', m.group(1), '::', m.group(2), '=>', m.group(3)[:60])
print()
print('=== 100010 中 测试断言工具 相关 testcase ===')
n_pass = 0
for m in re.finditer(r'<testcase[^>]*classname="([^"]*测试断言工具[^"]*)"[^>]*name="([^"]*)"(?:[^>]*)/>', xml):
    n_pass += 1
print('  通过(自闭合)数:', n_pass)
for m in re.finditer(r'<testcase[^>]*classname="([^"]*测试断言工具[^"]*)"[^>]*name="([^"]*)"[^>]*>\s*<(?:failure|error)[^>]*message="([^"]{0,60})', xml):
    print('  红:', m.group(2), '=>', m.group(3)[:50])
