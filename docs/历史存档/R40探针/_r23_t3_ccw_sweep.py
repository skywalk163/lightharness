# -*- coding: utf-8 -*-
"""R23 任务3：COMMON_COMPOUND_WORDS 逐条隔离中立验证（全语料 token 零变化）。

判据：对每一条 CCW 条目 w，单独把它从表中移除，重跑「含 w 的全部语料文件」token 序列；
      零变化 ⇒ 该条冗余（已由第21轮上下文敏感切词 / 预扫描 / codegen 内建登记覆盖）；
      有变化 ⇒ 真护栏，保留并记录依赖文件。

只读（模块属性内存态替换，finally 恢复），不改任何文件。
输出 JSON：lightharness/_r23_t3_ccw_sweep.json
"""
import sys, glob, hashlib, json

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

try:
    CAT = json.load(open(HARNESS + '/_r23_t3_probe.json', encoding='utf-8'))
except Exception:  # noqa
    CAT = {}
C1 = set(CAT.get('cat1_builtin', []))
C2 = set(CAT.get('cat2_other', []))
ALLMAP = set(CAT.get('all_map_keys', []))
BUILTIN = set(CAT.get('builtin_map', []))


def h(src):
    try:
        return hashlib.sha256(
            repr([(t.type.name, t.value) for t in L.Lexer(src).tokenize()]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


print(f'语料 {len(CORPUS)} 文件；CCW {len(CUR)} 条', flush=True)
BASE = {f: h(TEXTS[f]) for f in CORPUS}
print('基线 dump 完成', flush=True)

neutral, guard = [], {}
for idx, w in enumerate(sorted(CUR), 1):
    sub = [f for f in CORPUS if w in TEXTS[f]]
    if not sub:
        # 语料未命中：用单片段隔离自证
        sub = []
    L.COMMON_COMPOUND_WORDS = CUR - {w}
    try:
        if sub:
            mod = {f: h(TEXTS[f]) for f in sub}
        else:
            mod = {}
    finally:
        L.COMMON_COMPOUND_WORDS = CUR
    ch = [f for f in sub if BASE[f] != mod.get(f)]
    if not sub:
        # 语料未命中 → 用「单独 tokenize 该词」隔离自证
        with_t = h(w)
        L.COMMON_COMPOUND_WORDS = CUR - {w}
        try:
            without_t = h(w)
        finally:
            L.COMMON_COMPOUND_WORDS = CUR
        if with_t == without_t:
            neutral.append(w)
            print(f'[{idx}/{len(CUR)}] {w}: 语料0命中 + 隔离中立 ⇒ 冗余', flush=True)
        else:
            guard[w] = {'files': 0, 'isolated': True}
            print(f'[{idx}/{len(CUR)}] {w}: 语料0命中 但隔离**非**中立 ⇒ 护栏', flush=True)
        continue
    if ch:
        guard[w] = {'files': len(ch), 'sample': sorted(ch)[:5]}
        print(f'[{idx}/{len(CUR)}] {w}: 护栏 —— 变化 {len(ch)}/{len(sub)} 文件 '
              f'{[f.split("/")[-1] for f in sorted(ch)[:3]]}', flush=True)
    else:
        neutral.append(w)
        cat = '①builtin_map' if w in C1 else ('②其它映射' if w in C2 else ('③无映射' if w not in ALLMAP else '?'))
        print(f'[{idx}/{len(CUR)}] {w}: 冗余（{len(sub)} 文件零变化，{cat}）', flush=True)

out = {
    'corpus_files': len(CORPUS),
    'ccw_total': len(CUR),
    'neutral': sorted(neutral),
    'guard': guard,
    'neutral_count': len(neutral),
    'guard_count': len(guard),
}
json.dump(out, open(HARNESS + '/_r23_t3_ccw_sweep.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n冗余 {len(neutral)} 条 / 护栏 {len(guard)} 条', flush=True)
print('冗余:', ' '.join(sorted(neutral)), flush=True)
print('护栏:', ' '.join(sorted(guard)), flush=True)
