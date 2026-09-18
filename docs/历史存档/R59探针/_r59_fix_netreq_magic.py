# -*- coding: utf-8 -*-
"""R59 路M 预修：网络请求.light 首行去魔数（L-176 同款，全文不得出现「纯光明实现」字样）。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\网络请求.light')
t = p.read_text(encoding='utf-8')
old = '# 纯光明实现 —— stdlib/网络请求.py 的原生腿实现'
new = (
    '# 原生腿实现 —— stdlib/网络请求.py 的原生腿实现（R59：Python 后端优先加载同名 .py；\n'
    '# 本 .light 不带纯光明魔数，见 _light_import_hook._is_pure_light 与 L-176 先例）'
)
assert old in t, '未找到首行'
t = t.replace(old, new, 1)
assert '纯光明实现' not in t, '仍有字样: 全文=%d 处' % t.count('纯光明实现')
p.write_text(t, encoding='utf-8')
t2 = p.read_text(encoding='utf-8')
print('[回读] 首行:', t2.splitlines()[0][:70])
print('[回读] 含魔数字样:', '纯光明实现' in t2)
