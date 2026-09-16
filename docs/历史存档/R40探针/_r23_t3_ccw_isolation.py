# -*- coding: utf-8 -*-
"""R23 任务3 补充探针：对全部 184 条 CCW 做「隔离中立」自证 + 语料命中形态统计。

隔离中立：单独 tokenize 该词，「含该条」与「去该条」token 序列逐字节一致。
另统计该词在 .light 语料中作为**独立汉字段**出现的次数（决定语料是否真受影响）。
输出 _r23_t3_ccw_isolation.json。只读。
"""
import sys, glob, hashlib, json, re

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa

CUR = frozenset(L.COMMON_COMPOUND_WORDS)
CORPUS = []
for g in (HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
          LIGHTP + '/examples/**/*.light', LIGHTP + '/stdlib/**/*.light',
          LIGHTP + '/tests/**/*.light'):
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))
TEXTS = {f: open(f, encoding='utf-8', errors='replace').read() for f in CORPUS}
ALLTEXT = '\n'.join(TEXTS.values())

sweep = json.load(open(HARNESS + '/_r23_t3_ccw_sweep.json', encoding='utf-8'))
probe = json.load(open(HARNESS + '/_r23_t3_probe.json', encoding='utf-8'))
C1 = set(probe['cat1_builtin'])
C2 = set(probe['cat2_other'])
ALLMAP = set(probe['all_map_keys'])


def h(src):
    try:
        return hashlib.sha256(
            repr([(t.type.name, t.value) for t in L.Lexer(src).tokenize()]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def standalone_count(w):
    """该词在语料中作为「连续汉字字段整体」出现的次数（前后非汉字）。"""
    pat = re.compile(r'(?<![^\W\d_])' + re.escape(w) + r'(?![^\W\d_])')
    return len(pat.findall(ALLTEXT))


res = {}
for w in sorted(CUR):
    with_t = h(w)
    L.COMMON_COMPOUND_WORDS = CUR - {w}
    try:
        without_t = h(w)
    finally:
        L.COMMON_COMPOUND_WORDS = CUR
    iso = (with_t == without_t)
    res[w] = {
        'iso_neutral': iso,
        'standalone': standalone_count(w),
        'corpus_neutral': w in set(sweep['neutral']),
        'cat': '①builtin_map' if w in C1 else ('②其它映射' if w in C2 else ('③无映射' if w not in ALLMAP else '?')),
    }

both = [w for w in res if res[w]['iso_neutral'] and res[w]['corpus_neutral']]
only_corpus = [w for w in res if res[w]['corpus_neutral'] and not res[w]['iso_neutral']]
only_iso = [w for w in res if res[w]['iso_neutral'] and not res[w]['corpus_neutral']]
neither = [w for w in res if not res[w]['iso_neutral'] and not res[w]['corpus_neutral']]
print(f'CCW 总 {len(CUR)}')
print(f'双中立（语料中立 ∧ 隔离中立）：{len(both)}')
print(f'仅语料中立（隔离**非**中立）：{len(only_corpus)} -> {sorted(only_corpus)}')
print(f'仅隔离中立（语料非中立）：{len(only_iso)} -> {sorted(only_iso)}')
print(f'两者皆非中立（真护栏）：{len(neither)} -> {sorted(neither)}')
print('\n仅语料中立者的「独立字段出现次数」：')
for w in sorted(only_corpus):
    print(f"   {w}: standalone={res[w]['standalone']}  {res[w]['cat']}")

json.dump(res, open(HARNESS + '/_r23_t3_ccw_isolation.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已写 _r23_t3_ccw_isolation.json')
