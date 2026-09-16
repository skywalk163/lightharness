# -*- coding: utf-8 -*-
"""R23 任务1 探针3：枚举单字关键字并测量「通用词尾并入」规则的影响。

目标：把 _TRAILING_ALIAS_MERGE = {己} 换成**通用规则**
      （词尾位置 + 单字关键字 + 非 _P0A_OP + 非值字面量 + 非 compound_safe → 并入标识符）
后，全语料 token 是否零变化。

只读，不改文件。
"""
import sys, glob, hashlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa
from keywords import ALL_KEYWORDS, VERB_ARITY  # noqa

ALL_SINGLES = sorted({k for k in (set(ALL_KEYWORDS) | set(VERB_ARITY)) if len(k) == 1})
CUR = frozenset(L._TRAILING_ALIAS_MERGE)
VALUE_LITERALS = frozenset({'真', '假', '空'})
P0A_OP = L.Lexer._P0A_OP
CS = L._COMPOUND_SAFE_SINGLE_KEYWORDS

print(f'单字关键字总数 {len(ALL_SINGLES)}')
print('全部:', ''.join(ALL_SINGLES))
print('  in _P0A_OP      :', ''.join(sorted(k for k in ALL_SINGLES if k in P0A_OP)))
print('  in compound_safe:', ''.join(sorted(k for k in ALL_SINGLES if k in CS)))
print('  in 值字面量      :', ''.join(sorted(k for k in ALL_SINGLES if k in VALUE_LITERALS)))
REMAIN = [k for k in ALL_SINGLES
          if k not in P0A_OP and k not in CS and k not in VALUE_LITERALS]
print(f'  余下（通用规则候选，{len(REMAIN)}）:', ''.join(REMAIN))

CORPUS = []
for g in (HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
          LIGHTP + '/examples/**/*.light', LIGHTP + '/stdlib/**/*.light',
          LIGHTP + '/tests/**/*.light'):
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))
TEXTS = {f: open(f, encoding='utf-8', errors='replace').read() for f in CORPUS}
print(f'\n语料 .light 文件：{len(CORPUS)}')


def dump(files=None):
    out = {}
    for f in (files if files is not None else TEXTS):
        t = TEXTS[f]
        try:
            toks = L.Lexer(t).tokenize()
            out[f] = hashlib.sha256(
                repr([(x.type.name, x.value) for x in toks]).encode()).hexdigest()
        except Exception as e:  # noqa
            out[f] = 'ERR:' + type(e).__name__
    return out


base = dump()
print(f'基线（TAM={sorted(CUR)}）完成', flush=True)

# ① 逐条：把单个候选加进 TAM，看语料是否变化（只挑含该字的文件）
print('\n== 逐条「加入 TAM」的语料影响 ==', flush=True)
nonneutral = []
for k in REMAIN:
    if k in CUR:
        print(f'  {k}: 已在表内，跳过', flush=True)
        continue
    sub = [f for f in TEXTS if k in TEXTS[f]]
    L._TRAILING_ALIAS_MERGE = CUR | {k}
    try:
        mod = dump(sub)
    finally:
        L._TRAILING_ALIAS_MERGE = CUR
    ch = [f for f in sub if base[f] != mod.get(f)]
    if ch:
        nonneutral.append((k, ch))
        print(f'  {k}: 变化 {len(ch)}/{len(sub)} 文件  e.g. {[f.split("/")[-1] for f in ch[:3]]}', flush=True)
    else:
        print(f'  {k}: 零变化（{len(sub)} 文件含该字）', flush=True)
print(f'  → 非中立候选 {len(nonneutral)} 条：{"".join(k for k, _ in nonneutral)}', flush=True)

# ② 整体：通用规则 = REMAIN 全部并入
L._TRAILING_ALIAS_MERGE = frozenset(REMAIN)
try:
    gen = dump()
finally:
    L._TRAILING_ALIAS_MERGE = CUR
ch_all = [f for f in base if base[f] != gen.get(f)]
print(f'\n== 整体通用规则（{len(REMAIN)} 条）vs 现状 ==')
print(f'  语料 token 变化文件数：{len(ch_all)}')
for f in ch_all[:20]:
    print('   ', f.replace(ROOT + '/', ''))
