# -*- coding: utf-8 -*-
"""R59 路M 预修：编码解码.light 补 import 截取（LLVM 编译期绑定，修复 URL编码 错位输出）。

证据：_r59_slice_o0（显式 import 截取 → %E5%85%89 正确）vs _r59_url_dump（未 import →
%E5%8589%89 错位）。编码解码.light 原无任何 import（调用截取依赖隐式全局，Python 后端运行时
可见，LLVM 编译期不可见）。内置核心字符串.light 零依赖（无循环风险）。
"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\编码解码.light')
t = p.read_text(encoding='utf-8')
old = '导出 二进制转字符串 字符串转二进制。\n'
new = '导出 二进制转字符串 字符串转二进制。\n从 内置核心字符串 导入 截取。\n'
assert old in t, '未找到导出区尾'
t = t.replace(old, new, 1)
assert '纯光明实现' in '\n'.join(t.splitlines()[:2]), '首两行魔数丢失'
p.write_text(t, encoding='utf-8')
print('PATCHED')
for i, l in enumerate(t.splitlines(), 1):
    if '内置核心字符串' in l:
        print(f'L{i}: {l.strip()[:90]}')
