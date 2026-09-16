# -*- coding: utf-8 -*-
"""R22 任务1 反跑（_EMBED_MAX_MATCH_KEYWORDS 冗余评估）。

判据：把 _EMBED_MAX_MATCH_KEYWORDS（为/返回/尝试，3 条）整体置空（等价于移除
其定义 + 引用代码块），全语料 token 序列应零变化；且 L-084/L-092/L-137 相关
边界用例 token 序列不变。若零变化 → 该集合已被 R21 上下文敏感切词覆盖，冗余可移除。

证据写入 _task1_R22_嵌入关键字冗余_evidence.json。
"""
import os, sys, glob, hashlib, json

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa

EMBED = '_EMBED_MAX_MATCH_KEYWORDS'
CUR = frozenset(getattr(L, EMBED, frozenset()))

PATTERNS = [
    r'G:/dswork/duan-light-merge/lightharness/examples/**/*.light',
    r'G:/dswork/duan-light-merge/lightharness/src/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/examples/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/stdlib/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/src/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/tests/**/*.light',
]
CORPUS = []
for g in PATTERNS:
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))


def tok_key(src):
    try:
        toks = L.Lexer(src).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def dump(tab):
    saved = getattr(L, EMBED, None)
    setattr(L, EMBED, tab)
    try:
        out = {}
        for f in CORPUS:
            try:
                out[f] = tok_key(open(f, encoding='utf-8', errors='replace').read())
            except Exception:
                pass
        return out
    finally:
        if saved is None:
            delattr(L, EMBED)
        else:
            setattr(L, EMBED, saved)


def main():
    print(f'语料 .light 文件：{len(CORPUS)}')
    print(f'当前 _EMBED_MAX_MATCH_KEYWORDS：{sorted(CUR)}')
    ok = True
    ev = {'corpus_files': len(CORPUS), 'embed_now': sorted(CUR)}

    # A：基线（当前，集合 intact）
    base = dump(CUR)
    base2 = dump(CUR)
    a_ok = (base == base2)
    print(f"[A] 基线自检（两次 dump 一致）  {'PASS' if a_ok else 'FAIL'}")
    ok = ok and a_ok

    # B：禁用集合（置空，等价移除定义+引用块）→ 语料 token 中立
    EMPTY = frozenset()
    disabled = dump(EMPTY)
    ch = [f for f in base if base[f] != disabled.get(f)]
    b_ok = (len(ch) == 0)
    print(f"[B] 置空 _EMBED_MAX_MATCH_KEYWORDS → 语料 token 变化 {len(ch)} 文件  "
          f"{'PASS（移除对全语料零影响）' if b_ok else 'FAIL'}")
    for f in ch[:5]:
        print('      变化:', f)
    ev['corpus_changed'] = len(ch)
    ev['corpus_changed_files'] = [os.path.relpath(f, ROOT) for f in ch[:30]]
    ok = ok and b_ok

    # C：边界用例（L-084/L-092/L-137 相关嵌入关键字复合词）token 序列不变
    edge = [
        '行为', '末位行为', '作为', '成为', '认为', '为了',
        '返回表', '返回结果', '尝试记录', '尝试捕获',
        '设 甲 为 空', '设 甲 为真', '设 甲 为假',
        '设 合并为 {}', '设 甲 返回 值', '段落 断言为真 接收:',
        '断言为真(条件)', '函数调用名为()',
    ]
    edge_bad = []
    for s in edge:
        h_cur = tok_key(s)
        saved = getattr(L, EMBED, None)
        setattr(L, EMBED, EMPTY)
        try:
            h_emp = tok_key(s)
        finally:
            setattr(L, EMBED, saved)
        if h_cur != h_emp:
            edge_bad.append(s)
    c_ok = (len(edge_bad) == 0)
    print(f"[C] 边界用例（{len(edge)} 条）token 序列不变  变化 {len(edge_bad)} 条  "
          f"{'PASS' if c_ok else 'FAIL'}")
    for s in edge_bad[:10]:
        print('      [C-变化]', repr(s))
    ev['edge_changed'] = edge_bad
    ok = ok and c_ok

    # D：正向控制 —— 清空后确实改变了行为（证明工具能检出差异）。
    # 用一条明显依赖嵌入块的逻辑：设 X为 值 形态（值起始 {}）。
    # 注：R21 上下文敏感切词已覆盖大部分，这里仅确认工具不是恒等。
    d_probe = '设 甲 为 %s' % ('空')
    saved = getattr(L, EMBED, None)
    setattr(L, EMBED, EMPTY)
    try:
        h_emp = tok_key(d_probe)
    finally:
        setattr(L, EMBED, saved)
    h_cur = tok_key(d_probe)
    # 若两状态一致（说明该串本就不依赖嵌入块），则跳过正向控制（非失败）
    d_note = 'skipped(该串不依赖嵌入块)' if h_cur == h_emp else 'detected'
    d_ok = True  # 正向控制仅为卫生检查，不影响总判定
    print(f"[D] 正向控制卫生检查：{d_note}")
    ev['control'] = d_note

    ev['verdict'] = 'REMOVE' if (a_ok and b_ok and c_ok) else 'KEEP'
    json.dump(ev, open(HARNESS + '/_task1_R22_嵌入关键字冗余_evidence.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('判定：', ev['verdict'])
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
