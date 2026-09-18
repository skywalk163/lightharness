# -*- coding: utf-8 -*-
"""R59 路M：更新钉桩 R19（任务1 修复 _EMBED 为字合并 → 钉桩转正）。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\tests\test_R40_语言支撑配套.py')
t = p.read_text(encoding='utf-8')

old = """    def test_现状钉桩_R19_为字整串合并(self):
        \"\"\"`设结果为甲加乙乘2` 目前被吞成 `设` + IDENTIFIER('结果为甲加乙乘2')。

        正确切分（父提交 500743bc 实测）应为：
          设 / 结果 / 为 / 甲 / 加 / 乙 / 乘 / 2
        修好 _EMBED 后本断言会失败 —— 请同步更新任务3 报告与缺陷账。
        \"\"\"
        got = _tokens('设结果为甲加乙乘2')
        assert got == [('KEYWORD', '设'), ('IDENTIFIER', '结果为甲加乙乘2')], (
            '现状已变（可能修好了 _EMBED 的 `为` 合并）。'
            '请更新本钉桩 + 关闭对应缺陷条目。实际=%r' % (got,))"""

new = """    def test_现状钉桩_R19_为字整串合并(self):
        \"\"\"`设结果为甲加乙乘2` 曾吞成 `设` + IDENTIFIER('结果为甲加乙乘2')。

        R59 任务1（lexer._at_statement_start/._emb_head_trigger/._assign_tail）已修好
        _EMBED 的 `为` 合并，正确切分（父提交 500743bc 实测）现已成为现状：
          设 / 结果 / 为 / 甲 / 加 / 乙 / 乘 / 2
        钉桩转正：断言期望正确切分。缺陷条目 R19 `49319306` 已关闭（R59 任务1）。
        \"\"\"
        got = _tokens('设结果为甲加乙乘2')
        assert got == [('KEYWORD', '设'), ('IDENTIFIER', '结果'), ('KEYWORD', '为'),
                       ('IDENTIFIER', '甲'), ('KEYWORD', '加'), ('IDENTIFIER', '乙'),
                       ('KEYWORD', '乘'), ('NUMBER', 2)], (
            'R59 任务1 修复后应为正确切分；若此处再变，请复核 lexer._assign_tail 四重判据。实际=%r'
            % (got,))"""

assert old in t, '未找到钉桩 R19 原文'
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('PATCHED')
