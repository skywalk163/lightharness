# -*- coding: utf-8 -*-
"""R28 任务3：CS 表清零（2→0）三重判据验证（G1 语料 / G2 词首编译门 / G3 边界形态）。

口径：基线 = 改造前快照（CS={'列','类'}，无 R28 规则）；现文件 = CS=∅ + R28 规则。
可删条件：G1 ∧ G2 ∧ G3 全通过（现文件 token 序列 == 基线 token 序列）。

运行：
  python lightharness/_antirun_r28_t3_CS表清零验证.py
"""
import os, sys, glob, types, importlib
ROOT = r'G:/dswork/duan-light-merge'
SRC = ROOT + '/light-merge/src'
sys.path.insert(0, SRC)

base_text = open(ROOT + '/lightharness/_r28_lexer_baseline.txt', encoding='utf-8').read()
base_mod = types.ModuleType('lexer_base')
base_mod.__file__ = SRC + '/lexer.py'
exec(compile(base_text, SRC + '/lexer.py', 'exec'), base_mod.__dict__)
import lexer as live
importlib.reload(live)

def toks(mod, text):
    try:
        return [(t.type.name, t.value) for t in mod.Lexer(text, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return [('ERR', type(e).__name__ + ':' + str(e)[:60])]

fail = 0
print('基线 CS =', sorted(base_mod._COMPOUND_SAFE_SINGLE_KEYWORDS))
print('现文件 CS =', sorted(live._COMPOUND_SAFE_SINGLE_KEYWORDS))
assert live._COMPOUND_SAFE_SINGLE_KEYWORDS == frozenset(), 'CS 未清零'
print()

# ── G1 语料判据：全语料 token 序列零变化 ──────────────────────────────
PAT = [ROOT + '/lightharness/examples/**/*.light', ROOT + '/lightharness/src/**/*.light',
       ROOT + '/lightharness/tests/**/*.light', ROOT + '/light-merge/examples/**/*.light',
       ROOT + '/light-merge/stdlib/**/*.light', ROOT + '/light-merge/bootstrap/**/*.light',
       ROOT + '/light-merge/src/**/*.light', ROOT + '/light-merge/tests/**/*.light']
files = sorted(set(sum((glob.glob(g, recursive=True) for g in PAT), [])))
g1_diff = 0
for f in files:
    src = open(f, encoding='utf-8', errors='replace').read()
    if toks(base_mod, src) != toks(live, src):
        g1_diff += 1
        print('  G1 变化:', os.path.relpath(f, ROOT))
print('G1 语料判据：%d/%d 文件变化  -> %s' % (g1_diff, len(files), 'PASS' if g1_diff == 0 else 'FAIL'))
fail += (g1_diff != 0)
print()

# ── G2 词首编译门：{词首复合名} 为 7 整词成单 token（IDENTIFIER/KW）────
# 说明：判据为「整词不被切开」（首 token 值 == 词首复合名），且基线/现文一致。
# `类型` 等本就是整词关键字（KEYWORD），`列数` 等为 IDENTIFIER，二者均合格。
G2 = ['列数 为 7', '列表 为 7', '类别 为 7', '类型 为 7', '类似 为 7']
for s in G2:
    word = s.split()[0]
    a, b = toks(base_mod, s), toks(live, s)
    whole = len(b) >= 1 and b[0][1] == word
    ok = (a == b) and whole
    if not ok:
        fail += 1
    print('G2 %-12r 基线=%s 现文=%s -> %s' % (s, a[:1], b[:1], 'PASS' if ok else 'FAIL'))
print()

# ── G3 边界形态门（含 列词尾切出 / 类声明 / 下标）────────────────────
G3 = [
    ('对于元素在序列:',              [('IDENTIFIER','对'),('KEYWORD','于'),('IDENTIFIER','元素'),
                                     ('KEYWORD','在'),('IDENTIFIER','序'),('KEYWORD','列'),('COLON',':')]),
    ('甲之序列:',                    [('IDENTIFIER','甲'),('KEYWORD','之'),('IDENTIFIER','序'),
                                     ('KEYWORD','列'),('COLON',':')]),
    ('序列:',                        [('IDENTIFIER','序列'),('COLON',':')]),
    ('序列 为 [1,2,3]',              None),
    ('列数 为 3',                    None),
    ('类 独立类:',                   [('KEYWORD','类'),('IDENTIFIER','独立类'),('COLON',':')]),
    ('类 名称:',                     [('KEYWORD','类'),('IDENTIFIER','名称'),('COLON',':')]),
    ('类 子类 继承 基类:',           [('KEYWORD','类'),('IDENTIFIER','子类'),('KEYWORD','继承'),
                                     ('IDENTIFIER','基类'),('COLON',':')]),
    ('类别 为 "int"',                None),
    ('段[1]',                        None),
    ('配[0]',                        None),
    ('甲 加 乙',                     None),
    ('返回 真',                      None),
]
for s, expect in G3:
    a, b = toks(base_mod, s), toks(live, s)
    shape_ok = (expect is None) or (b == expect)
    ok = (a == b) and shape_ok
    if not ok:
        fail += 1
    print('G3 %-18r 基线==现文:%s 形态:%s -> %s' % (s, a == b, shape_ok, 'PASS' if ok else 'FAIL'))
    if not ok:
        print('     基线=%s' % (a,))
        print('     现文=%s' % (b,))
print()
print('=' * 60)
print('R28 CS 表清零三重判据：%s（失败项 %d）' % ('ALL OK ✅' if fail == 0 else 'FAIL ❌', fail))
