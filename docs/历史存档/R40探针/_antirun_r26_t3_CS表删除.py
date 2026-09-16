# -*- coding: utf-8 -*-
"""R26 任务3 反跑：CS 表 30 字逐条三重判据（G1 语料 / G2 词首编译门 / G3 边界形态）。

在任务1+2 的「词首并入正面规则」实现之上执行：对每个原 CS 字 c，把 c 从 CS 撤出
（内存态 monkeypatch，不改磁盘），检验：
  G1 含 c 的语料文件 token 序列是否零变化；
  G2 语句起始裸名 `{词首复合名} 为 7` 是否与基线一致（整词成 IDENTIFIER）；
  G3 六类边界形态 token 流是否不变。
可删条件 = G1 ∧ G2 ∧ G3。

输出：_task3_R26_CS表逐条验证_证据.json
"""
import os
import sys
import json
import glob
import time

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

# 词首复合名（每字一个语料真实构词场景；含被正面类别覆盖的 12 字）
HEAD_NAME = {
    '乘': '乘法', '余': '余数', '例': '例表', '减': '减法', '出': '出错',
    '列': '列数', '则': '则例', '到': '到位', '加': '加法', '对': '对立',
    '常': '常规', '引': '引导', '接': '接续', '断': '断裂', '是': '是否',
    '末': '末项', '模': '模组', '段': '段数', '的': '的确', '真': '真空',
    '空': '空格', '类': '类别', '自': '自然', '试': '试探', '跳': '跳表',
    '过': '过载', '配': '配置', '长': '长度', '除': '除法', '首': '首项',
}
# G3 六类边界形态
BOUNDARY = [
    '返回 真', '返回 空', '返回 假',
    '配[0]', '段[1]',
    '甲 加 乙', '甲 减 乙', '甲 乘 乙', '甲 除 乙',
    '从 1 到 10', '如果甲则乙', '当 真:', '的 后随空白',
    '己 名称 为 名称', '父 进程ID', '设 X 为 5', '类 动物:',
]
# 30 字原始 CS（第22-25轮状态）
CS30 = sorted('乘余例减出列则到加对常引接断是末模段的真空类自试跳过配长除首')


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def toks(mod, text):
    try:
        return repr([(t.type.name, t.value)
                     for t in mod.Lexer(text, deterministic=True).tokenize()
                     if t.type.name not in ('EOF', 'NEWLINE')])
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def main():
    t0 = time.time()
    import lexer as L
    CS_new = L._COMPOUND_SAFE_SINGLE_KEYWORDS
    HEAD = L._P0A_HEAD_MERGE_SINGLE
    print('CS(新版)=%d  HEAD=%d  语料=%d' % (len(CS_new), len(HEAD), len(CORPUS)))

    SRC = {f: read(f) for f in CORPUS}
    base = {f: toks(L, SRC[f]) for f in CORPUS}
    base_g2 = {c: toks(L, HEAD_NAME[c] + ' 为 7') for c in CS30}
    base_g3 = {s: toks(L, s) for s in BOUNDARY}

    result = {}
    for c in CS30:
        trial = frozenset(set(CS_new) - {c})
        L._COMPOUND_SAFE_SINGLE_KEYWORDS = trial
        L.Lexer.compound_safe_single_keywords = trial
        # G1
        g1_files = []
        for f in CORPUS:
            if c not in SRC[f]:
                continue
            if toks(L, SRC[f]) != base[f]:
                g1_files.append(os.path.relpath(f, ROOT).replace('\\', '/'))
        # G2
        g2_line = HEAD_NAME[c] + ' 为 7'
        g2_new = toks(L, g2_line)
        g2_ok = (g2_new == base_g2[c])
        # G3
        g3_bad = [s for s in BOUNDARY if toks(L, s) != base_g3[s]]
        # restore
        L._COMPOUND_SAFE_SINGLE_KEYWORDS = CS_new
        L.Lexer.compound_safe_single_keywords = CS_new
        deletable = (len(g1_files) == 0) and g2_ok and (len(g3_bad) == 0)
        result[c] = {
            'g1_changed': len(g1_files), 'g1_files': g1_files[:6],
            'g2_line': g2_line, 'g2_ok': g2_ok,
            'g2_base': base_g2[c][:150], 'g2_new': g2_new[:150],
            'g3_bad': g3_bad,
            'deletable': deletable,
            'in_new_cs': c in CS_new,
        }
        print('  %s  G1=%d  G2=%-5s G3=%-2d  %s'
              % (c, len(g1_files), g2_ok, len(g3_bad), '可删' if deletable else '保留'))

    json.dump({'cs_new': ''.join(sorted(CS_new)), 'cs30': ''.join(CS30),
               'head': ''.join(sorted(HEAD)), 'corpus': len(CORPUS),
               'result': result, 'seconds': round(time.time() - t0, 1)},
              open(HARNESS + '/_task3_R26_CS表逐条验证_证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    dl = [c for c in CS30 if result[c]['deletable']]
    keep = [c for c in CS30 if not result[c]['deletable']]
    print('\n可删 %d 字: %s' % (len(dl), ''.join(sorted(dl))))
    print('保留 %d 字: %s' % (len(keep), ''.join(sorted(keep))))
    print('耗时 %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
