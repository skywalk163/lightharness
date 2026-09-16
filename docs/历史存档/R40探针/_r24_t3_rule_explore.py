# -*- coding: utf-8 -*-
"""R24 任务3 规则探索：CR1（成员访问段首并入规则）能否安全替代被删单字。

基准 = committed HEAD（只读 git show）。全部内存态；不写 src/lexer.py。

配置：
  B0     = HEAD
  G1     = HEAD + 任务1 闸门（R21 分支：整串含 _P0A_OP 则不并）
  CR1    = HEAD + 成员访问段首并入规则（separator 之后的新段视为名字续段）
  G1CR1  = HEAD + G1 + CR1
  G1CR1D = G1CR1 + 删任务2分类①的 13 字
"""
import os
import sys
import glob
import json
import time
import hashlib
import tempfile
import importlib.util
import subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'

PATTERNS = [
    HARNESS + '/examples/**/*.light',
    HARNESS + '/src/**/*.light',
    HARNESS + '/tests/**/*.light',
    LIGHTP + '/examples/**/*.light',
    LIGHTP + '/stdlib/**/*.light',
    LIGHTP + '/bootstrap/**/*.light',
    LIGHTP + '/src/**/*.light',
    LIGHTP + '/tests/**/*.light',
]
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
GENERATED = [os.path.join(LIGHTP, 'bootstrap')]

D13 = set('例出则常引接是末试跳过长首')

A_GATE_OLD = ("                    if (_lead_kw and 0 < _lead_len < len(full_identifier)\n"
              "                            and _lead_kw not in _OPERATOR_KEYWORDS):")
A_GATE_NEW = ("                    if (_lead_kw and 0 < _lead_len < len(full_identifier)\n"
              "                            and _lead_kw not in _OPERATOR_KEYWORDS\n"
              "                            and not self._p0a_contains_op(source, pos, len(full_identifier))):")

B_INIT_OLD = ("                if embedded_found:\n"
              "                    # 有内嵌关键字，分段输出\n"
              "                    scan_pos = 0\n")
B_INIT_NEW = ("                if embedded_found:\n"
              "                    # 有内嵌关键字，分段输出\n"
              "                    scan_pos = 0\n"
              "                    _seg_after_sep = False\n")

C_EMIT_OLD = ("                            # 输出关键字\n"
              "                            tokens.append(Token(TokenType.KEYWORD, sub_kw, line, current_col))\n"
              "                            consumed += sub_len\n"
              "                            current_col += sub_len\n"
              "                            full_identifier = full_identifier[sub_len:]\n"
              "                            scan_pos = 0\n")
C_EMIT_NEW = (C_EMIT_OLD +
              "                            # R24任务3 CR1：记录刚输出的是否为成员/关系分隔符，\n"
              "                            # 供其后「段首单字并入规则」判定这是成员名续段而非语句词首。\n"
              "                            _seg_after_sep = sub_kw in self._P0A_SEP\n")

D_COND_OLD = ("                                if scan_pos > 0 and scan_pos + sub_len < len(full_identifier):\n"
              "                                    scan_pos += sub_len\n"
              "                                    continue\n"
              "                                if (scan_pos > 0\n"
              "                                        and scan_pos + sub_len == len(full_identifier)\n"
              "                                        and sub_kw in _trailing_alias):\n")
D_COND_NEW = ("                                if ((scan_pos > 0 and scan_pos + sub_len < len(full_identifier))\n"
              "                                        or _seg_after_sep):\n"
              "                                    scan_pos += sub_len\n"
              "                                    continue\n"
              "                                if (scan_pos > 0\n"
              "                                        and scan_pos + sub_len == len(full_identifier)\n"
              "                                        and sub_kw in _trailing_alias):\n")

PROBE = [
    '甲之长度', '甲之首项', '甲之末项', '甲之例子', '甲之常规', '甲之引用', '甲之跳过',
    '甲之则是', '甲之输出', '甲之断点', '甲之列表', '甲之类', '长度(数列)', '首项(数列)',
    '自之姓名', '印 自之姓名', '返回 自之姓名', '打印 对象之方法', '对象之属性',
    '自加乙', '甲加乙', '甲并乙丙', '对于', '10的幂', '去除空格', '索引', '种类', '阶乘',
    '我的书', '函数的参数', '红色的花', '大的小的', '甲的', '的', '甲 的 书',
]

PER_CHAR_BASE = '甲之'
PER_CHAR_TAIL = '顶'
D13_LIST = '例出则常引接是末试跳过长首'


def sha(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def read(f):
    with open(f, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def load(src_text, name):
    d = tempfile.mkdtemp(prefix='lxr_r_')
    p = os.path.join(d, name + '.py')
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src_text)
    sys.path.insert(0, os.path.join(LIGHTP, 'src'))
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def recompute(mod):
    CS = mod._COMPOUND_SAFE_SINGLE_KEYWORDS
    L = mod.Lexer
    ALL = mod._ALL_KEYWORDS_WITH_VERBS
    trail = frozenset(
        k for k in (ALL - L._P0A_OP - mod._OPERATOR_KEYWORDS - L._P0A_NEVER_SPLIT
                    - mod._AWAIT_KEYWORDS - CS - mod._VALUE_LITERAL_KEYWORDS) if len(k) == 1)
    L._TRAILING_ALIAS_CLASS = trail
    L.compound_safe_single_keywords = CS
    L._P0A_COMPOUND_SAFE = CS | {'当'}
    return CS, trail


def apply_cs_del(mod, chars):
    mod._COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset(mod._COMPOUND_SAFE_SINGLE_KEYWORDS - set(chars))
    return recompute(mod)


def toks(mod, src):
    return ' '.join('%s(%s)' % (t.type.name, t.value) for t in
                    mod.Lexer(src, deterministic=True).tokenize()
                    if t.type.name not in ('EOF', 'NEWLINE'))


def tok_key(mod, src):
    try:
        return sha(repr([(t.type.name, t.value) for t in
                         mod.Lexer(src, deterministic=True).tokenize()]))
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__ + ':' + str(e)[:40]


def is_gen(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED)


def main():
    head = subprocess.check_output(['git', '-C', LIGHTP, 'show', 'HEAD:src/lexer.py'],
                                   encoding='utf-8')
    for nm, old in (('A', A_GATE_OLD), ('B', B_INIT_OLD), ('C', C_EMIT_OLD), ('D', D_COND_OLD)):
        n = head.count(old)
        print('锚点 %s 出现 %d 次' % (nm, n))
        assert n == 1, '锚点 %s 不唯一' % nm

    g1 = head.replace(A_GATE_OLD, A_GATE_NEW)
    cr1 = head.replace(B_INIT_OLD, B_INIT_NEW).replace(C_EMIT_OLD, C_EMIT_NEW).replace(
        D_COND_OLD, D_COND_NEW)
    g1cr1 = g1.replace(B_INIT_OLD, B_INIT_NEW).replace(C_EMIT_OLD, C_EMIT_NEW).replace(
        D_COND_OLD, D_COND_NEW)

    V = {}
    V['B0'] = load(head, '_r_b0')
    V['G1'] = load(g1, '_r_g1')
    V['CR1'] = load(cr1, '_r_cr1')
    V['G1CR1'] = load(g1cr1, '_r_g1cr1')
    v = load(g1cr1, '_r_g1cr1d')
    apply_cs_del(v, D13)
    V['G1CR1D13'] = v

    for n, m in V.items():
        print('%-9s CS=%d trailing=%d' % (n, len(m._COMPOUND_SAFE_SINGLE_KEYWORDS),
                                          len(m.Lexer._TRAILING_ALIAS_CLASS)))

    # ---- 逐字反例矩阵（D13 是否破坏成员名）----
    print('\n===== 逐字反例矩阵：`甲之<c>顶` =====')
    for c in D13_LIST:
        s = PER_CHAR_BASE + c + PER_CHAR_TAIL
        row = []
        for n in ('B0', 'G1CR1', 'G1CR1D13'):
            try:
                t = V[n].Lexer(s, deterministic=True).tokenize()
                row.append('%s' % ' '.join(x.type.name[0] + ':' + x.value for x in t
                                           if x.type.name not in ('EOF', 'NEWLINE')))
            except Exception as e:  # noqa
                row.append('EXC')
        ok = (row[0] == row[2])
        print('  %s %r\n      B0     : %s\n      G1CR1  : %s\n      G1CR1D13: %s   %s'
              % (c, s, row[0], row[1], row[2], 'OK' if ok else '★ 与B0不同'))

    print('\n===== 探针差异（vs B0）=====')
    pb = {n: [toks(m, c) for c in PROBE] for n, m in V.items()}
    for i, c in enumerate(PROBE):
        base = pb['B0'][i]
        diffs = [(n, pb[n][i]) for n in V if n != 'B0' and pb[n][i] != base]
        if diffs:
            print('  %r' % c)
            print('      B0 : %s' % base)
            for n, x in diffs:
                print('      %-9s: %s' % (n, x))

    print('\n===== 全语料 token A/B（vs B0）=====')
    TEXTS = {f: read(f) for f in CORPUS}
    d0 = {f: tok_key(V['B0'], TEXTS[f]) for f in CORPUS}
    res = {}
    for n in ('G1', 'CR1', 'G1CR1', 'G1CR1D13'):
        t0 = time.time()
        dn = {f: tok_key(V[n], TEXTS[f]) for f in CORPUS}
        dt = time.time() - t0
        ch = [f for f in CORPUS if d0[f] != dn[f]]
        cr = [f for f in ch if not is_gen(f)]
        cg = [f for f in ch if is_gen(f)]
        print('  %-9s 变化 真实源 %3d ｜ 生成树 %3d ｜ %.1fs' % (n, len(cr), len(cg), dt))
        for f in cr[:15]:
            print('        真实源:', os.path.relpath(f, ROOT))
        res[n] = {'real': [os.path.relpath(f, ROOT) for f in cr],
                  'gen': [os.path.relpath(f, ROOT) for f in cg]}

    print('\n[自检] B0 二次 dump 一致: %s' % (d0 == {f: tok_key(V['B0'], TEXTS[f]) for f in CORPUS}))
    json.dump({'corpus': len(CORPUS), 'diff': res,
               'probe': {n: pb[n] for n in pb}, 'probe_cases': PROBE},
              open(HARNESS + '/_r24_t3_rule_explore.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('证据 → _r24_t3_rule_explore.json')


if __name__ == '__main__':
    main()
