# -*- coding: utf-8 -*-
"""R21 任务1 探针：验证 L-152 预扫描根因（不修改任何文件）。"""
import os, sys
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
os.environ.setdefault('LIGHT_MERGE', r'G:/dswork/duan-light-merge/light-merge')

from lexer import Lexer  # noqa

CASES = {
    'L152嵌套': "段落 小于判断 接收 甲:\n  返回 甲 + 1\n段落 主:\n  段落 内层返回 接收 函数值:\n      返回 函数值(9)\n  断言相等(内层返回(小于判断), 10, \"x\")\n主()\n",
    '模块级同形': "段落 测试段 接收 函数值:\n  返回 函数值(9)\n",
    '普通': "段落 去重占位 接收 名单:\n  返回 名单\n",
}

for tag, src in CASES.items():
    lx = Lexer()
    defs = lx._scan_user_definitions(src)
    print('=' * 60)
    print(f'[{tag}] definitions({len(defs)}) =', sorted(defs))
    # 只看与 函数值/内层返回 相关
    for probe in ('函数值', '内层返回', '内层', '值', '函数', '测试段', '去重占位'):
        if probe in defs:
            print(f'   in-defs: {probe!r}')
    try:
        toks = lx.tokenize(src)
        seq = [(t.type.name, t.value) for t in toks if isinstance(t.value, str)]
        # 打印与 函数值 相关的 token
        print('   token 序列(前40):', seq[:40])
    except Exception as e:
        print('   tokenize 异常:', type(e).__name__, e)
