# -*- coding: utf-8 -*-
"""R24 任务1/任务3 候选改动探索（内存态，基准 = committed HEAD）。

只读；不写 src/lexer.py。通过 git show HEAD 取基准文本，内存载入多个变体，
按 token 序列对比全语料（真实源 / 生成树分开统计）。

配置：
  B0     = HEAD 原样
  G1     = +R21 分支第4道闸门：整串含 _P0A_OP 关键字则不并（复用已有 _p0a_contains_op）
  G2     = +R21 分支第4道闸门：整串含 _P0A_SEP(之为于在与) 则不并
  D13    = _COMPOUND_SAFE_SINGLE_KEYWORDS 删任务2分类①冗余13字（例出则常引接是末试跳过长首）
  G1D13  = G1 + D13
  G2D13  = G2 + D13
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

GATE_OLD = ("                    if (_lead_kw and 0 < _lead_len < len(full_identifier)\n"
            "                            and _lead_kw not in _OPERATOR_KEYWORDS):")
GATE_NEW_OP = ("                    if (_lead_kw and 0 < _lead_len < len(full_identifier)\n"
               "                            and _lead_kw not in _OPERATOR_KEYWORDS\n"
               "                            and not self._p0a_contains_op(source, pos, len(full_identifier))):")

SEP_HELPER_OLD = (
    "    def _p0a_contains_op(self, source: str, start: int, length: int) -> bool:\n"
    "        \"\"\"扫描 [start, start+length) 是否含任一始终切分运算符关键字。\"\"\"\n"
    "        end = start + length\n"
    "        p = start\n"
    "        while p < end:\n"
    "            kw, _ = self._match_keyword(source, p)\n"
    "            if kw and kw in self._P0A_OP:\n"
    "                return True\n"
    "            p += 1\n"
    "        return False\n")
SEP_HELPER_NEW = SEP_HELPER_OLD + (
    "\n    def _p0a_contains_sep(self, source: str, start: int, length: int) -> bool:\n"
    "        \"\"\"扫描 [start, start+length) 是否含任一成员/关系分隔符（为之于在与）。\"\"\"\n"
    "        end = start + length\n"
    "        p = start\n"
    "        while p < end:\n"
    "            kw, _ = self._match_keyword(source, p)\n"
    "            if kw and kw in self._P0A_SEP:\n"
    "                return True\n"
    "            p += 1\n"
    "        return False\n")
GATE_NEW_SEP = ("                    if (_lead_kw and 0 < _lead_len < len(full_identifier)\n"
                "                            and _lead_kw not in _OPERATOR_KEYWORDS\n"
                "                            and not self._p0a_contains_sep(source, pos, len(full_identifier))):")

PROBE = [
    '自之姓名', '印 自之姓名', '返回 自之姓名', '甲之乙', '对象之属性', '打印 对象之方法',
    '自加乙', '自减乙', '当加乙', '对于', '10的幂', '去除空格', '索引', '种类', '阶乘',
    '我的书', '函数的参数', '红色的花', '大的小的', '甲的', '的', '甲 的 书',
    '真假标志', '真实值', '空白行', '空值计数', '假名', '假值', '真空度',
    '加法', '减法', '乘法表', '余数', '甲 加 乙', '甲加乙',
    '数列之长度', '结果 之 值', '平台信息等', '甲至10', '甲或"x"',
]


def sha(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def read(f):
    with open(f, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def load(src_text, name):
    d = tempfile.mkdtemp(prefix='lxr_x_')
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
    """按 R23 推导式重算 _TRAILING_ALIAS_CLASS 与类别名，并覆写 CS。"""
    CS = mod._COMPOUND_SAFE_SINGLE_KEYWORDS
    L = mod.Lexer
    ALL = mod._ALL_KEYWORDS_WITH_VERBS
    trail = frozenset(
        k for k in (ALL - L._P0A_OP - mod._OPERATOR_KEYWORDS - L._P0A_NEVER_SPLIT
                    - mod._AWAIT_KEYWORDS - CS - mod._VALUE_LITERAL_KEYWORDS)
        if len(k) == 1)
    L._TRAILING_ALIAS_CLASS = trail
    L.compound_safe_single_keywords = CS
    L._P0A_COMPOUND_SAFE = CS | {'当'}
    return CS, trail


def apply_cs_del(mod, chars):
    mod._COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset(
        mod._COMPOUND_SAFE_SINGLE_KEYWORDS - set(chars))
    return recompute(mod)


def tok_key(mod, src):
    try:
        toks = mod.Lexer(src, deterministic=True).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__ + ':' + str(e)[:40]


def is_gen(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED)


def dump_probe(mod):
    out = {}
    for c in PROBE:
        try:
            toks = mod.Lexer(c, deterministic=True).tokenize()
            out[c] = ' '.join('%s(%s)' % (t.type.name, t.value) for t in toks
                              if t.type.name not in ('EOF', 'NEWLINE'))
        except Exception as e:  # noqa
            out[c] = 'EXC ' + type(e).__name__
    return out


def main():
    head_text = subprocess.check_output(['git', '-C', LIGHTP, 'show', 'HEAD:src/lexer.py'],
                                        encoding='utf-8')
    variants = {}

    b0 = load(head_text, '_lxr_b0')
    variants['B0'] = b0

    g1_txt = head_text.replace(GATE_OLD, GATE_NEW_OP)
    assert g1_txt != head_text, 'G1 闸门替换失败'
    variants['G1'] = load(g1_txt, '_lxr_g1')

    g2_txt = head_text.replace(SEP_HELPER_OLD, SEP_HELPER_NEW).replace(GATE_OLD, GATE_NEW_SEP)
    assert g2_txt != head_text and '_p0a_contains_sep' in g2_txt, 'G2 替换失败'
    variants['G2'] = load(g2_txt, '_lxr_g2')

    d13 = load(head_text, '_lxr_d13')
    apply_cs_del(d13, D13)
    variants['D13'] = d13

    g1d13 = load(g1_txt, '_lxr_g1d13')
    apply_cs_del(g1d13, D13)
    variants['G1D13'] = g1d13
    g2d13 = load(g2_txt, '_lxr_g2d13')
    apply_cs_del(g2d13, D13)
    variants['G2D13'] = g2d13

    print('语料 .light：%d 文件' % len(CORPUS))
    for n, m in variants.items():
        print('%-7s CS=%d trailing=%d' % (n, len(m._COMPOUND_SAFE_SINGLE_KEYWORDS),
                                          len(m.Lexer._TRAILING_ALIAS_CLASS)))

    print('\n===== 探针（B0 → 各变体差异）=====')
    pb = {n: dump_probe(m) for n, m in variants.items()}
    for c in PROBE:
        base = pb['B0'][c]
        diffs = [(n, pb[n][c]) for n in variants if n != 'B0' and pb[n][c] != base]
        if diffs:
            print('  %r' % c)
            print('      B0  : %s' % base)
            for n, v in diffs:
                print('      %-5s: %s' % (n, v))
    print('  （未列出的探针：所有变体与 B0 一致）')

    print('\n===== 全语料 token A/B（vs B0）=====')
    TEXTS = {f: read(f) for f in CORPUS}
    d0 = {f: tok_key(b0, TEXTS[f]) for f in CORPUS}
    res = {}
    for n in ('G1', 'G2', 'D13', 'G1D13', 'G2D13'):
        t0 = time.time()
        dn = {f: tok_key(variants[n], TEXTS[f]) for f in CORPUS}
        dt = time.time() - t0
        ch = [f for f in CORPUS if d0[f] != dn[f]]
        cr = [f for f in ch if not is_gen(f)]
        cg = [f for f in ch if is_gen(f)]
        print('  %-7s 变化 真实源 %3d ｜ 生成树 %3d ｜ 耗时 %.1fs' % (n, len(cr), len(cg), dt))
        for f in cr[:12]:
            print('        真实源:', os.path.relpath(f, ROOT))
        res[n] = {'real': [os.path.relpath(f, ROOT) for f in cr],
                  'gen': [os.path.relpath(f, ROOT) for f in cg]}

    t0 = time.time(); d0b = {f: tok_key(b0, TEXTS[f]) for f in CORPUS}
    print('\n[B0 自检] 二次 dump 一致: %s  (%.1fs)' % (d0 == d0b, time.time() - t0))

    json.dump({'corpus': len(CORPUS), 'probe': pb, 'diff': res},
              open(HARNESS + '/_r24_t1t3_explore.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('证据 → _r24_t1t3_explore.json')


if __name__ == '__main__':
    main()
