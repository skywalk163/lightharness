# -*- coding: utf-8 -*-
"""R58：断言工具.light 注释里避免出现完整字符串「纯光明实现」（护栏测试
test_pure_light_hook.py 要求该魔数字样只允许出现在首两行）。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\断言工具.light')
raw = p.read_bytes()
text = raw.decode('utf-8')
was_crlf = '\r\n' in text
text_n = text.replace('\r\n', '\n')

old_a = '# ⚠️ R58：本文件**不带「纯光明实现」魔数**（见 _light_import_hook.py `_is_pure_light`）——'
new_a = '# ⚠️ R58：本文件**不带纯光明魔数**（见 _light_import_hook.py `_is_pure_light`）——'
old_b = '#   带魔数会让钩子「优先加载 .light 并无视同名 .py」，与上文"缺名回退 .py"的设计矛盾，'
new_b = '#   带该魔数会让钩子「优先加载 .light 并无视同名 .py」，与上文"缺名回退 .py"的设计矛盾，'

for old, new in [(old_a, new_a), (old_b, new_b)]:
    assert old in text_n, '未找到: ' + old[:40]
    text_n = text_n.replace(old, new, 1)

if was_crlf:
    text_n = text_n.replace('\n', '\r\n')
p.write_bytes(text_n.encode('utf-8'))
t2 = p.read_text(encoding='utf-8')
print('[回读] 含「纯光明实现」子串:', '纯光明实现' in t2)
print('[回读] 首两行无魔数:', '纯光明实现' not in '\n'.join(t2.splitlines()[:2]))
