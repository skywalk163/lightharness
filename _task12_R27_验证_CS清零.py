# -*- coding: utf-8 -*-
"""R27 任务1+2 验证：CS 16字规则化（A类 DUAL + B类 F∩CS 全位置吸收）后，
把 CS 清空（模拟任务3删除），校验：
  - 全语料 843+ 文件 token 序列零变化（vs 基线 CS=16）
  - G2 词首编译门：16 字词首复合名 `{名} 为 7` 整词成 IDENTIFIER
  - G3 边界形态：运算符切分/值字面量切分/范围切分/下标访问 不变
若全过 → 任务1+2 规则正确，CS 可清零（任务3）。
"""
import os
import sys
import glob
import time
import importlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

HEAD_NAME = {
    '乘': '乘法', '减': '减法', '加': '加法', '除': '除法', '模': '模组',
    '真': '真空', '空': '空格', '到': '到位',
    '列': '列数', '对': '对立', '是': '是否', '段': '段数', '的': '的确',
    '类': '类别', '自': '自然', '配': '配置',
}
BOUNDARY = [
    '返回 真', '返回 空', '返回 假',
    '配[0]', '段[1]',
    '甲 加 乙', '甲 减 乙', '甲 乘 乙', '甲 除 乙', '甲 模 乙',
    '从 1 到 10', '如果甲则乙', '当 真:', '的 后随空白',
    '己 名称 为 名称', '父 进程ID', '设 X 为 5', '类 动物:',
    '加法', '减法', '乘法', '除法', '模组', '真空', '空格', '到位',
    '列数', '对立', '是否', '段数', '的确', '类别', '自然', '配置',
]


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def toks(mod, text):
    try:
        return [(t.type.name, t.value)
                for t in mod.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def main():
    t0 = time.time()
    L = importlib.import_module('lexer')
    importlib.reload(L)
    CS0 = L._COMPOUND_SAFE_SINGLE_KEYWORDS
    print('基线 CS=%d  语料=%d' % (len(CS0), len(CORPUS)))

    SRC = {f: read(f) for f in CORPUS}
    base = {f: toks(L, SRC[f]) for f in CORPUS}
    base_g2 = {c: toks(L, HEAD_NAME[c] + ' 为 7') for c in HEAD_NAME}
    base_g3 = {s: toks(L, s) for s in BOUNDARY}

    # 模拟任务3：CS 清零
    L._COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset()
    L.Lexer.compound_safe_single_keywords = frozenset()

    # G1 全语料
    changed = []
    for f in CORPUS:
        if toks(L, SRC[f]) != base[f]:
            changed.append(os.path.relpath(f, ROOT).replace('\\', '/'))
    # G2
    g2 = {c: (toks(L, HEAD_NAME[c] + ' 为 7') == base_g2[c]) for c in HEAD_NAME}
    # G3
    g3 = {s: (toks(L, s) == base_g3[s]) for s in BOUNDARY}

    # 还原
    L._COMPOUND_SAFE_SINGLE_KEYWORDS = CS0
    L.Lexer.compound_safe_single_keywords = CS0

    print('\n=== G1 全语料（CS清零 vs 基线）===')
    print('  变化文件数: %d' % len(changed))
    for f in changed[:30]:
        print('    %s' % f)
    print('\n=== G2 词首编译门（16字）===')
    for c in HEAD_NAME:
        print('  %s %s  %s' % (c, HEAD_NAME[c], 'OK' if g2[c] else 'FAIL'))
    print('\n=== G3 边界形态 ===')
    for s in BOUNDARY:
        if not g3[s]:
            print('  FAIL: %s' % s)
    print('  G3 失败数: %d / %d' % (sum(1 for v in g3.values() if not v), len(BOUNDARY)))

    ok = (len(changed) == 0) and all(g2.values()) and all(g3.values())
    print('\n总判定: %s' % ('ALL OK ✅ CS可清零' if ok else '有失败 ❌'))
    print('耗时 %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
