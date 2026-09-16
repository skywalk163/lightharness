# -*- coding: utf-8 -*-
"""R26 G2 探针：在 class=CS-12 下 tokenize 语句起始裸名，判断是否被切碎。
只读。"""
import os
import sys
import json
import tempfile
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))
ANCHOR = "del _assert_F, _assert_DUAL, _assert_TAM, _assert_TAM_new\n"
DROP12 = {'余', '例', '出', '则', '常', '引', '接', '末', '试', '跳', '长', '首'}


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def load_src(tag, src):
    d = os.path.join(tempfile.gettempdir(), 'r26g2_' + tag)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'lxr_%s.py' % tag)
    open(p, 'w', encoding='utf-8', newline='').write(src)
    spec = importlib.util.spec_from_file_location('lxr_%s' % tag, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['lxr_%s' % tag] = mod
    spec.loader.exec_module(mod)
    return mod


def build(variant):
    src = read(LEXER)
    src = src.replace('sub_kw in self.compound_safe_single_keywords',
                      'sub_kw in _P0A_HEAD_MERGE_SINGLE')
    src = src.replace('candidate in _COMPOUND_SAFE_SINGLE_KEYWORDS and pos + 1 < text_len:',
                      'candidate in _P0A_HEAD_MERGE_SINGLE and pos + 1 < text_len:')
    src = src.replace('candidate in _compound_safe and pos + 1 < text_len:',
                      'candidate in _P0A_HEAD_MERGE_SINGLE and pos + 1 < text_len:')
    src = src.replace('_compound_safe = _COMPOUND_SAFE_SINGLE_KEYWORDS',
                      '_compound_safe = _P0A_HEAD_MERGE_SINGLE')
    if variant == 'cs12':
        expr = ("frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS - "
                "{'余','例','出','则','常','引','接','末','试','跳','长','首'})")
    elif variant == 'cs':
        expr = "frozenset(_COMPOUND_SAFE_SINGLE_KEYWORDS)"
    else:
        raise SystemExit('variant?')
    return src.replace(ANCHOR, ANCHOR + "\n_P0A_HEAD_MERGE_SINGLE = " + expr + "\n", 1)


def toks(mod, s):
    try:
        return [(t.type.name, t.value)
                for t in mod.Lexer(s, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:  # noqa
        return [('ERR', type(e).__name__ + ':' + str(e)[:60])]


def main():
    sys.path.insert(0, os.path.join(LIGHTP, 'src'))
    import lexer as base
    mods = {'base(CS30)': base}
    for v in ('cs', 'cs12'):
        mods['variant:' + v] = load_src(v, build(v))

    # 语句起始裸名 G2 用例（每字一个词首复合名）
    NAMES = ['长度', '出错', '列数', '规则', '则例', '常规', '引导', '接口',
             '断裂', '是非', '月末', '试探', '跳过', '首项', '余数', '举例']
    print('=== G2：语句起始裸名 `{名} 为 7` ===')
    for nm in NAMES:
        line = '%s 为 7' % nm
        outs = {k: toks(m, line) for k, m in mods.items()}
        head_ok = {}
        for k, tk in outs.items():
            # 首个 token 是否覆盖整个名字（IDENTIFIER/CHINESE_NUM 且值==名字）
            head_ok[k] = bool(tk) and tk[0][1] == nm
        flag = 'OK ' if all(head_ok.values()) else '★G2失败'
        print('%-4s %s' % (flag, nm), {k: v[:4] for k, v in outs.items()})

    # 独立单字在词首
    print('\n=== 单字词首 `{字}度数 为 7` ===')
    for c in ['长', '出', '列', '则', '常', '引', '接', '末', '试', '跳', '首', '余', '例']:
        line = '%s度数 为 7' % c
        outs = {k: toks(m, line) for k, m in mods.items()}
        print('  %s ->' % c, {k: v[:3] for k, v in outs.items()})


if __name__ == '__main__':
    main()
