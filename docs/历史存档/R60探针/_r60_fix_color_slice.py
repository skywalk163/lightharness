# -*- coding: utf-8 -*-
"""R60 路M：颜色.light RGB解析 截取误用修（LLVM 截取 end 语义后暴露）。

`截取(干净, 左括 + 1, 右括 - 左括 - 1)` 意图取 `(` 与 `)` 之间内容，
按 (start,len) 写的第三参；官方语义是 end → 应为 `右括`。
旧 LLVM（len 语义）下碰巧正确（基线绿），R60 修复 LLVM 为 end 语义后
暴露（0.82 定向 test_O0_颜色_解析格式化操作_对拍 红）。
"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\颜色.light')
t = p.read_text(encoding='utf-8')

old = '设 内部 为 截取(干净, 左括 + 1, 右括 - 左括 - 1)'
new = '设 内部 为 截取(干净, 左括 + 1, 右括)'
assert old in t, '未找到误用行'
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('PATCHED 颜色.light RGB解析 截取 → end 语义')
# 魔数护栏：首两行外无「纯光明实现」
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    if i > 2 and '纯光明实现' in l:
        raise SystemExit(f'魔数违规 L{i}')
print('魔数护栏 OK')
