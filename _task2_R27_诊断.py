# -*- coding: utf-8 -*-
"""R27 任务2 诊断：B类8字(列对是段的自类配)从CS撤出后，逐文件打印token差异位置。
目的：定位正面规则 _P0A_HEAD_MERGE_SINGLE 未覆盖的具体场景。
"""
import os
import sys
import glob

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

BCLASS = '列对是段的自类配'
G1 = {
    '列': [LIGHTP + '/bootstrap/release/stdlib/断言工具.light'],
    '对': [LIGHTP + '/stdlib/HTTP服务端.light', LIGHTP + '/stdlib/SSE.light',
           LIGHTP + '/stdlib/中文文本处理.light', LIGHTP + '/stdlib/分布式/调度核心.light'],
    '是': [LIGHTP + '/bootstrap/release/stdlib/日期时间.light', LIGHTP + '/bootstrap/release/stdlib/时间管理.light'],
    '段': [LIGHTP + '/examples/games/snake.light', LIGHTP + '/examples/snake_game/主.light',
           LIGHTP + '/stdlib/re.light', LIGHTP + '/stdlib/网络请求.light',
           HARNESS + '/examples/test_R25_单字后缀规则_快速.light',
           HARNESS + '/examples/test_R25_词尾并入边界反向.light'],
    '的': [LIGHTP + '/examples/E阶段_L3L4原生语法/E4_L4_沙箱隔离验证.light',
           LIGHTP + '/examples/L1_baihua/05_遍循环.light', LIGHTP + '/examples/L1_baihua/06_列表.light',
           LIGHTP + '/examples/L1_baihua/07_字典.light', LIGHTP + '/examples/L2_wenyan/学生模块.light'],
    '类': [LIGHTP + '/bootstrap/release/stdlib/装饰器.light', HARNESS + '/examples/test_L013.light'],
    '自': [HARNESS + '/src/权限.light'],
    '配': [HARNESS + '/examples/test_L119.light', HARNESS + '/examples/test_R25_单字后缀规则_快速.light',
           HARNESS + '/examples/test_R25_词尾并入边界反向.light', HARNESS + '/examples/test_团队服务.light'],
}


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def toks(mod, text):
    return [(t.type.name, t.value)
            for t in mod.Lexer(text, deterministic=True).tokenize()
            if t.type.name not in ('EOF', 'NEWLINE')]


def diff_print(b, n):
    i = j = 0
    out = []
    while i < len(b) or j < len(n):
        if i < len(b) and j < len(n) and b[i] == n[j]:
            i += 1; j += 1; continue
        out.append('  基: ' + repr(b[i] if i < len(b) else '∅'))
        out.append('  新: ' + repr(n[j] if j < len(n) else '∅'))
        i += 1; j += 1
        if len(out) > 30:
            break
    return out


def main():
    import importlib
    L = importlib.import_module('lexer')
    importlib.reload(L)
    CS0 = L._COMPOUND_SAFE_SINGLE_KEYWORDS
    for c in BCLASS:
        files = G1[c]
        print('\n========== 撤出 %s ==========' % c)
        for f in files:
            if not os.path.exists(f):
                print('  [缺失] %s' % f); continue
            src = read(f)
            if c not in src:
                continue
            base = toks(L, src)
            trial = frozenset(set(CS0) - {c})
            L._COMPOUND_SAFE_SINGLE_KEYWORDS = trial
            L.Lexer.compound_safe_single_keywords = trial
            new = toks(L, src)
            L._COMPOUND_SAFE_SINGLE_KEYWORDS = CS0
            L.Lexer.compound_safe_single_keywords = CS0
            if base != new:
                print('  -- 文件 %s' % os.path.relpath(f, ROOT).replace('\\', '/'))
                for line in diff_print(base, new):
                    print('     ' + line)
            else:
                print('  -- 文件 %s  无差异(?)' % os.path.relpath(f, ROOT).replace('\\', '/'))


if __name__ == '__main__':
    main()
