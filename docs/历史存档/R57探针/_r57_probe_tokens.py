# -*- coding: utf-8 -*-
"""R57 任务1 探针：对目标片段直接 tokenize，观察切分。"""
import sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
LM = os.path.join(ROOT, 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)
from lexer import Lexer  # noqa: E402

CASES = [
    '设 为了 为 "为了值"',
    '设 作为 为 "作为值"',
    '设 认为 为 "认为值"',
    '设 成为 为 "成为值"',
    '段落 测试返回语句:',
    '段落 测试真的与返回:',
    '段落 测试_返回真:',
    '返回 真',
    '设 甲为三',
    '设 甲 为 三',
]

for det in (True, False):
    print(f"===== deterministic={det} =====")
    for s in CASES:
        try:
            toks = Lexer(deterministic=det).tokenize(s)
            out = [(t.type.name, t.value) for t in toks]
        except Exception as e:  # noqa: BLE001
            out = f'<EXC {type(e).__name__}: {e}>'
        print(f"{s!r:40} => {out}")
    print()
