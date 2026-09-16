# -*- coding: utf-8 -*-
"""R35 终验反跑（任务4）：真实已改 lexer vs 改动前 HEAD，全语料零回归 + G3 + 变异反跑。

三项：
  A. G1 语料门：当前 lexer（MERGE_WHOLE 2 条 + GR-2b）vs HEAD（3 条，无 GR-2b）
     ⇒ 必须 0 变化 / 0 新错
  B. G3 边界门：3 条 × 5 形态，当前 vs HEAD token 流一致
  C. 变异反跑：把 GR-2b 关掉（闸门3 恢复 `_OPERATOR_KEYWORDS` 全禁）而 非空块 仍不在
     MERGE_WHOLE ⇒ G3「非空块 F2/F5」必须 **变红**（证明 GR-2b 是活规则，非假绿）
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = r'G:/dswork/duan-light-merge'
SRC = os.path.join(ROOT, 'light-merge', 'src')
PATS = [ROOT + p for p in (
    '/lightharness/examples/**/*.light', '/lightharness/src/**/*.light',
    '/lightharness/tests/**/*.light', '/light-merge/examples/**/*.light',
    '/light-merge/stdlib/**/*.light', '/light-merge/bootstrap/**/*.light',
    '/light-merge/src/**/*.light', '/light-merge/tests/**/*.light')]

ENTRIES = ['整理模型消息', '非空块', '记录类型']
FORMS = lambda X: [
    ('F1 设名',     '设 X 为 1\n'.replace('X', X)),
    ('F2 函数名',   '返回 X(1)\n'.replace('X', X)),
    ('F3 成员访问', '设 r 为 结果.X\n'.replace('X', X)),
    ('F4 段落名',   '段落 X:\n    返回 1\n'.replace('X', X)),
    ('F5 传参位',   '断言相等(X, 1, "t")\n'.replace('X', X)),
]

CHILD = r'''
import glob, hashlib, json, os, sys
srcdir, out, cfg = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
sys.path.insert(0, srcdir)
import lexer
if cfg['mode'] == 'corpus':
    files = sorted(set(sum((glob.glob(g, recursive=True) for g in cfg['pats']), [])))
    per = {}
    for f in files:
        rel = os.path.relpath(f, cfg['root']).replace('\\', '/')
        try:
            src = open(f, encoding='utf-8').read()
            toks = [(t.type.name, t.value) for t in
                    lexer.Lexer(src, deterministic=True).tokenize()
                    if t.type.name not in ('EOF', 'NEWLINE')]
            per[rel] = hashlib.sha256(json.dumps(toks, ensure_ascii=False).encode()).hexdigest()
        except Exception as e:
            per[rel] = 'ERR:' + type(e).__name__
    json.dump(per, open(out, 'w', encoding='utf-8'))
else:
    res = {}
    for X in cfg['entries']:
        for tag, tpl in cfg['forms']:
            k = X + '|' + tag
            try:
                res[k] = [(t.type.name, t.value) for t in
                          lexer.Lexer(tpl.replace('X', X), deterministic=True).tokenize()
                          if t.type.name not in ('EOF', 'NEWLINE')]
            except Exception as e:
                res[k] = ['ERR:' + type(e).__name__]
    json.dump(res, open(out, 'w', encoding='utf-8'))
'''

# 变异：把 GR-2b 的「一元前缀例外」撤掉
MUT_OLD = """                            and _lead_kw not in (_OPERATOR_KEYWORDS
                                                 - self._P0A_UNARY_PREFIX_KW)
                            and (_lead_kw not in self._P0A_UNARY_PREFIX_KW
                                 or full_identifier[_lead_len:] not in user_definitions)"""
MUT_NEW = """                            and _lead_kw not in _OPERATOR_KEYWORDS"""


def build(name, lexer_text=None):
    tmp = tempfile.mkdtemp(prefix='r35f_')
    d = os.path.join(tmp, 'src')
    shutil.copytree(SRC, d, ignore=shutil.ignore_patterns('__pycache__'))
    if lexer_text is not None:
        open(os.path.join(d, 'lexer.py'), 'w', encoding='utf-8').write(lexer_text)
    return tmp, d


def run(d, mode):
    tmp = tempfile.mkdtemp(prefix='r35c_')
    ch = os.path.join(tmp, 'child.py')
    out = os.path.join(tmp, 'out.json')
    open(ch, 'w', encoding='utf-8').write(CHILD)
    cfg = {'mode': mode, 'pats': PATS, 'root': ROOT,
           'entries': ENTRIES, 'forms': FORMS('X')}
    r = subprocess.run([sys.executable, ch, 'child', d, out, json.dumps(cfg)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if not os.path.exists(out):
        raise SystemExit('子进程失败(%s): %s' % (mode, r.stderr[-1500:]))
    return json.load(open(out, encoding='utf-8'))


def fmt(toks):
    return ' '.join('%s·%s' % (k, v) for k, v in toks)


def main():
    head_text = subprocess.run(
        ['git', '-C', os.path.join(ROOT, 'light-merge'), 'show', 'HEAD:src/lexer.py'],
        capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    assert '_P0A_MERGE_WHOLE' in head_text, 'git show 失败'
    cur_text = open(os.path.join(SRC, 'lexer.py'), encoding='utf-8').read()

    print('=== A. G1 语料门：当前 vs HEAD ===')
    _, d_head = build('head', head_text)
    _, d_cur = build('cur')
    a = run(d_head, 'corpus')
    b = run(d_cur, 'corpus')
    ka = [k for k, v in a.items() if not v.startswith('ERR:')]
    changed = [k for k in ka if a[k] != b.get(k)]
    newerr = [k for k in ka if b.get(k, '').startswith('ERR:')]
    print('  可比文件=%d 变化=%d 新错=%d %s' % (
        len(ka), len(changed), len(newerr),
        '✅ 零回归' if not changed and not newerr else '★ 有回归'))
    for k in changed[:10]:
        print('     变化: %s' % k)
    g1_ok = not changed and not newerr

    print()
    print('=== B. G3 边界门：当前 vs HEAD ===')
    ga = run(d_head, 'forms')
    gb = run(d_cur, 'forms')
    g3_ok = True
    for X in ENTRIES:
        bad = [t for t, _ in FORMS(X) if ga[X + '|' + t] != gb[X + '|' + t]]
        print('  %-8s %s' % (X, 'G3通过' if not bad else 'G3失败 %s' % bad))
        for t in bad:
            g3_ok = False
            print('      [%s]' % t)
            print('        HEAD: %s' % fmt(ga[X + '|' + t]))
            print('        当前: %s' % fmt(gb[X + '|' + t]))

    print()
    print('=== C. 变异反跑：关掉 GR-2b（非空块 仍不在 MERGE_WHOLE）===')
    if MUT_OLD not in cur_text:
        print('  ★ 变异锚点未命中，跳过')
        mut_ok = False
    else:
        _, d_mut = build('mut', cur_text.replace(MUT_OLD, MUT_NEW, 1))
        gc = run(d_mut, 'forms')
        bad = [t for t, _ in FORMS('非空块')
               if ga['非空块|' + t] != gc['非空块|' + t]]
        print('  非空块 变异后 G3 失败形态：%s' % (bad if bad else '（无 → 规则不敏感！）'))
        for t in bad:
            print('      [%s]' % t)
            print('        HEAD  : %s' % fmt(ga['非空块|' + t]))
            print('        变异态: %s' % fmt(gc['非空块|' + t]))
        # 期望：F2/F5 变红 ⇒ 证明 GR-2b 承载 非空块 整词语义
        mut_ok = ('F2 函数名' in bad and 'F5 传参位' in bad)
        print('  判定：%s' % ('✅ 规则敏感（变异必红）' if mut_ok else '★ 规则不敏感'))

    print()
    print('=== 总判定 ===')
    print('  G1 零回归：%s' % ('通过' if g1_ok else '失败'))
    print('  G3 边界门：%s' % ('通过' if g3_ok else '失败'))
    print('  变异反跑：%s' % ('通过' if mut_ok else '失败'))
    ok = g1_ok and g3_ok and mut_ok
    json.dump({'g1_ok': g1_ok, 'g1_changed': changed, 'g3_ok': g3_ok,
               'mutation_ok': mut_ok,
               'merge_whole': sorted(json.loads(json.dumps(
                   ['整理模型消息', '记录类型'])))},
              open(os.path.join(ROOT, 'lightharness',
                                '_antirun_r35_final.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('  => %s' % ('全部通过' if ok else '有失败'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
