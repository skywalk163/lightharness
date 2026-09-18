# -*- coding: utf-8 -*-
"""R61 修中文分词.light:124 截取 (start,len)→(start,end)。"""
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\中文分词.light')
t = p.read_text(encoding='utf-8')
old = "      设 词 为 截取(文本, i, j)"
new = "      设 词 为 截取(文本, i, i 加 j)"
assert old in t, '旧调用未找到'
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('PATCHED 中文分词.light:124 截取(文本, i, i 加 j)')
