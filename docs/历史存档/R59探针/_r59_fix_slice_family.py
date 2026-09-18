# -*- coding: utf-8 -*-
"""R59 路M 预修：截取 (start,len) 误用族修复 #2/#3。

- 编码解码.light L373（URL查询串解码）：截取(对, 等号+1, 长(对)-等号-1) → end=长(对)
- 参数解析.light L136（--输出=7 解析）：截取(词, 等号+1, 长(词)-等号-1) → end=长(词)
证据：T6C 两测试（本机还原实验确认由 .light 依赖链编译路径暴露；133701 时走 .py 回退所以绿）。
"""
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib')

def patch(fname, old, new, tag):
    p = LM / fname
    t = p.read_text(encoding='utf-8')
    if old not in t:
        print(f'[{tag}] 未找到，跳过（可能已修）')
        return False
    t = t.replace(old, new, 1)
    assert '纯光明实现' in '\n'.join(t.splitlines()[:2]), f'[{tag}] 首两行魔数丢失'
    p.write_text(t, encoding='utf-8')
    print(f'[{tag}] PATCHED')
    return True

patch('编码解码.light',
      '设 值 为 编码URL查询解码(截取(对, 等号 + 1, 长(对) - 等号 - 1))',
      '设 值 为 编码URL查询解码(截取(对, 等号 + 1, 长(对)))',
      '编码解码L373')
patch('参数解析.light',
      '设 值给 为 截取(词, 等号 + 1, 长(词) - 等号 - 1)',
      '设 值给 为 截取(词, 等号 + 1, 长(词))',
      '参数解析L136')
