# -*- coding: utf-8 -*-
"""R21 任务3 反跑（修剪后语义）：验证 COMMON_COMPOUND_WORDS 精简的正确性。

三层判据：
  A（基线自检）：两次 dump 语料 token 一致。
  B（删除中立·语料级）：把 190 条已删条目**补回** → 语料 token 序列逐文件一致。
     等价于「删除这 190 条对全语料零影响」。
  B2（删除中立·隔离级）：对每条已删条目，单独 tokenize：
     补回前后 token 序列一致（逐条真冗余自证）。
  C（正向控制）：本工具能检出差异 —— 清空整表后 `弹性模量` token 变化。
  D（TierB 确为护栏）：对每条 TierB 保留条目，删除它 → 单独 tokenize 该词变化。

证据写入 _task3_r21_thin_evidence.json。
"""
import os, sys, glob, hashlib, json

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa

final = json.load(open(HARNESS + '/_r21_ccw_trim_final.json', encoding='utf-8'))
DELETED = sorted(final['delete'])
TIERB = sorted(final['keep_tierB'])
CUR = frozenset(L.COMMON_COMPOUND_WORDS)

CORPUS = []
for g in (HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
          LIGHTP + '/examples/**/*.light', LIGHTP + '/stdlib/**/*.light',
          LIGHTP + '/tests/**/*.light'):
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))


def tok_key(src):
    try:
        toks = L.Lexer(src).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def dump(tab):
    L.COMMON_COMPOUND_WORDS = tab
    try:
        out = {}
        for f in CORPUS:
            try:
                out[f] = tok_key(open(f, encoding='utf-8', errors='replace').read())
            except Exception:
                pass
        return out
    finally:
        L.COMMON_COMPOUND_WORDS = CUR


def one(entry, tab):
    L.COMMON_COMPOUND_WORDS = tab
    try:
        return tok_key(entry)
    finally:
        L.COMMON_COMPOUND_WORDS = CUR


def main():
    print(f'语料 .light 文件：{len(CORPUS)}')
    print(f'当前表条目：{len(CUR)}  已删：{len(DELETED)}  TierB 保留：{len(TIERB)}')
    ok = True
    ev = {'corpus_files': len(CORPUS), 'table_now': len(CUR),
          'deleted': len(DELETED), 'tierB': len(TIERB)}

    base = dump(CUR)
    base2 = dump(CUR)
    a_ok = (base == base2)
    print(f"[A] 基线自检（两次 dump 一致）  {'PASS' if a_ok else 'FAIL'}")
    ok = ok and a_ok

    # B：补回已删条目 → 语料 token 中立
    FULL_BACK = CUR | frozenset(DELETED)
    back = dump(FULL_BACK)
    ch = [f for f in base if base[f] != back.get(f)]
    b_ok = (len(ch) == 0)
    print(f"[B] 补回 {len(DELETED)} 条已删条目 → 语料 token 变化 {len(ch)} 文件  "
          f"{'PASS（删除对全语料零影响）' if b_ok else 'FAIL'}")
    for f in ch[:3]:
        print('      变化:', f)
    ev['corpus_changed_on_restore'] = len(ch)
    ok = ok and b_ok

    # B2：逐条隔离中立
    bad = []
    for e in DELETED:
        if one(e, CUR) != one(e, FULL_BACK):
            bad.append(e)
    b2_ok = (len(bad) == 0)
    print(f"[B2] 逐条隔离中立（{len(DELETED)} 条）  违规 {len(bad)} 条  "
          f"{'PASS' if b2_ok else 'FAIL'}")
    for e in bad[:8]:
        print('      [B2-FAIL]', e)
    ev['isolated_nonneutral'] = bad
    ok = ok and b2_ok

    # C：正向控制（能检出差异）
    h_full = one('设 结果 为 弹性模量', CUR)
    h_empty = one('设 结果 为 弹性模量', frozenset())
    c_ok = (h_full != h_empty)
    print(f"[C] 正向控制：清空整表后 `弹性模量` token 变化  {'PASS' if c_ok else 'FAIL'}")
    ok = ok and c_ok

    # D：TierB 确为护栏（删掉它 → 该词 token 变化）
    minus = CUR - frozenset(TIERB)
    not_guard = []
    for e in TIERB:
        if one(e, CUR) == one(e, minus):
            not_guard.append(e)
    d_ok = (len(not_guard) == 0)
    print(f"[D] TierB（{len(TIERB)} 条）逐条均为护栏  非护栏 {len(not_guard)} 条  "
          f"{'PASS' if d_ok else 'FAIL'}")
    for e in not_guard[:8]:
        print('      [D-非护栏]', e)
    ev['tierB_not_guard'] = not_guard
    ok = ok and d_ok

    json.dump(ev, open(HARNESS + '/_task3_r21_thin_evidence.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
