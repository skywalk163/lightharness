# -*- coding: utf-8 -*-
"""R21 任务2 探针：上下文敏感切词 A/B/C 判据现状（不修改文件）。"""
import os, sys
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
os.environ.setdefault('LIGHT_MERGE', r'G:/dswork/duan-light-merge/light-merge')
from lexer import Lexer  # noqa


def show(tag, src):
    lx = Lexer()
    defs = lx._scan_user_definitions(src)
    try:
        toks = lx.tokenize(src)
    except Exception as e:
        print(f'[{tag}] tokenize 异常: {type(e).__name__}: {e}')
        return
    seq = [(t.type.name, t.value) for t in toks if isinstance(t.value, str) and t.value.strip()]
    print(f'[{tag}]')
    print('   defs =', sorted(defs))
    print('   toks =', seq)


# A判据：表达式上下文关键字前缀标识符（定义+调用同源码，模拟真实文件）
show('A-注册', "段落 去重占位 接收 名单:\n  返回 名单\n段落 主:\n  设 结果 为 去重占位([1,1,2])\n  返回 结果\n主()\n")
# A判据-未注册：仅调用，无定义（孤立片段）
show('A-未注册', "设 结果 为 去重占位([1,1,2])\n")
# B判据：语句起始位置关键字不变
show('B', "如果 条件 为 真:\n  设 甲 为 1\n")
# B判据2：接收参数（段落头部关键字+名）
show('B2', "段落 测试段 接收 参数值:\n  返回 参数值\n")
# C判据：运算符关键字在表达式中
show('C', "设 结果 为 甲 与 乙\n")
show('C2', "设 结果 为 甲 或 乙\n")
show('C3', "设 结果 为 非 甲\n")
# 补充：函数调用语境关键字尾名（第20轮已修）
show('D-调用', "断言为真(甲)\n")
show('D2-调用', "设 结果 为 判定为空(甲)\n")
