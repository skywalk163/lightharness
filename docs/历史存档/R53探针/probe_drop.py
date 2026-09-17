# -*- coding: utf-8 -*-
"""检测 parser 的**静默丢语句**路径：_parse_statement 返回假值时
parser_core 只 `self.pos += 1` 前进——该语句被静默丢弃，无错误、无告警。

扫描全语料，列出触发点。
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

import parser_core as pc  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402

DROPS = []
_orig = pc.LightParserCore._parse_statement


def patched(self, *a, **kw):
    tok = self._current()
    before = self.pos
    stmt = _orig(self, *a, **kw)
    if not stmt:
        DROPS.append((getattr(self, '_filename', '?'),
                      tok.line if tok else -1,
                      tok.value if tok else None,
                      self.pos - before))
    return stmt


pc.LightParserCore._parse_statement = patched

ROOTS = [r'G:\dswork\duan-light-merge\lightharness\examples',
         r'G:\dswork\duan-light-merge\light-merge\examples']


def main():
    hit = {}
    for root in ROOTS:
        for p in sorted(glob.glob(os.path.join(root, '*.light'))):
            DROPS.clear()
            try:
                src = open(p, encoding='utf-8').read()
                parser = LightParser()
                parser._filename = p
                parser.parse(src)
            except Exception as e:  # noqa: BLE001
                pass
            if DROPS:
                hit[p] = list(DROPS)
    print(f'触发静默丢语句的文件：{len(hit)}')
    for p, ds in list(hit.items())[:25]:
        print('  -', os.path.relpath(p, r'G:\dswork\duan-light-merge'))
        for f, line, val, adv in ds[:6]:
            print(f'      line={line} tok={val!r} 前进={adv}')


if __name__ == '__main__':
    main()
