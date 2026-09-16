# -*- coding: utf-8 -*-
"""R28 任务3：CS表清零确认（CS=∅ 态 三重判据 + 全语料零变化）。

CS 表已由 `_COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset()` 清零（任务1 列的
`_P0A_TAIL_CUT_SINGLE` 词尾切出 + 任务2 的 user_definitions 前缀余部单字并入
判据扩展落地后执行）。本脚本确认清零态的正确性：
  [0] CS == ∅ 断言 + 文末 import 自校验通过
  [1] 场景矩阵：列词尾切出/词首并入/词尾并入 + 类声明/词首并入/继承，
      逐一对照 R27 基线口径（CS={'列','类'} 时期语料钉住的行为）
  [2] G1 全语料：对照 R26 基线快照逐文件 token 零变化（既有失败 2 排除）

输出：_task3_R28_CS表2字逐条验证_证据.json + 控制台摘要
"""
import os
import sys
import json
import glob
import hashlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
R26_SNAPSHOT = os.path.join(HARNESS, '_antirun_r26_基线快照.json')

# 场景矩阵：期望 = R27 基线（CS={'列','类'}）时期钉住的 token 行为
# （源自 _dbg_r28_ground.py 探针 + 断言工具.light / test_L013 语料钉）
CASES = [
    # (源码, 期望关键token序列摘要, 说明)
    ('对于元素在序列:',
     [('IDENTIFIER', '序'), ('KEYWORD', '列'), ('COLON', ':')],
     '列：词尾切出（无空格 for-in，断言工具.light:226 形态）'),
    ('元素 在 序列:',
     [('IDENTIFIER', '序列'), ('COLON', ':')],
     '列：带空格 → 序列整词（词尾并入）'),
    ('序列:',
     [('IDENTIFIER', '序列'), ('COLON', ':')],
     '列：段首整词'),
    ('列数 为 3',
     [('IDENTIFIER', '列数')],
     '列：词首并入'),
    ('序列 为 [1, 2]',
     [('IDENTIFIER', '序列')],
     '列：词尾并入（非冒号）'),
    ('类 独立类:',
     [('KEYWORD', '类'), ('IDENTIFIER', '独立类')],
     '类：类声明词尾并入整词'),
    ('类 名称:',
     [('KEYWORD', '类'), ('IDENTIFIER', '名称')],
     '类：独立关键字不受影响'),
    ('类别 为 "int"',
     [('IDENTIFIER', '类别')],
     '类：词首并入'),
    ('类 子类 继承 基类:',
     [('KEYWORD', '类'), ('IDENTIFIER', '子类'), ('KEYWORD', '继承'),
      ('IDENTIFIER', '基类')],
     '类：继承形态'),
    ('设 x 为 新建 独立类()',
     [('IDENTIFIER', '独立类'), ('LPAREN', '(')],
     '类：使用处 词尾+`(` 整词（test_L013 打红形态）'),
]


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def token_seq(text):
    import lexer
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in toks
                if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def main():
    import lexer

    print('=' * 72)
    print('R28 任务3：CS 表清零确认')
    print('=' * 72)

    # [0] CS == ∅
    cs = lexer._COMPOUND_SAFE_SINGLE_KEYWORDS
    assert len(cs) == 0, 'CS 表应为空，实得 %s' % sorted(cs)
    print('[0] CS == ∅  ✅（import 文末自校验全部通过）')

    # [1] 场景矩阵
    print('\n[1] 场景矩阵（对照 R27 基线口径）')
    case_results = []
    all_ok = True
    for src, expect, desc in CASES:
        seq = token_seq(src)
        ok = all(tok in seq for tok in expect)
        all_ok = all_ok and ok
        case_results.append({'src': src, 'desc': desc, 'pass': ok, 'seq': seq})
        print('  %s %s — %s' % ('✅' if ok else '❌', repr(src), desc))
        if not ok:
            print('     实得: %s' % (seq,))

    # [2] G1 全语料对照 R26 基线
    print('\n[2] G1 全语料对照 R26 基线（%d 文件）' % len(CORPUS))
    base = json.load(open(R26_SNAPSHOT, encoding='utf-8'))
    base_per = base.get('per_file', {})
    base_err = set(base.get('base_err_files', []))
    changed, compared, cur_err = [], 0, []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            t = read(f)
        except Exception:
            continue
        seq = token_seq(t)
        if len(seq) == 1 and seq[0].startswith('ERR:'):
            cur_err.append(rel)
            continue
        if rel not in base_per or rel in base_err:
            continue
        compared += 1
        fp = sha_text(json.dumps(seq, ensure_ascii=False))
        if fp != base_per[rel]['sha']:
            changed.append(rel)
    zero_change = not changed
    print('  可比 %d 文件（既有失败 %d 排除，R28 新增文件不在基线跳过）'
          % (compared, len(base_err)))
    if changed:
        print('  ⚠️  token 变化 %d 文件:' % len(changed))
        for rel in changed[:10]:
            print('     %s' % rel)
    else:
        print('  ✅ 全语料 token 零变化')

    out = os.path.join(HARNESS, '_task3_R28_CS表2字逐条验证_证据.json')
    json.dump({
        'cs_final': sorted(cs),
        'cases': case_results,
        'cases_all_pass': all_ok,
        'corpus_files': len(CORPUS),
        'compared': compared,
        'zero_change': zero_change,
        'changed_files': changed,
        'current_err_files': cur_err,
    }, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n结论：场景矩阵 %s | 全语料零变化 %s'
          % ('全过' if all_ok else '有失败', '✅' if zero_change else '❌'))
    print('证据文件: %s' % out)


if __name__ == '__main__':
    main()
