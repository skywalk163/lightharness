# -*- coding: utf-8 -*-
"""R29 任务4：D批删除后 全量反跑 —— 全语料 token 零变化验证。

对比口径：
  before = 当前 lexer + 加回 D 批 6 条（函数对象/常量时间比较/枚举值/正则匹配/环境枚举/结构体值）
  after  = 当前 lexer（已删 6 条，CCW 24 条）
  before 与 after 全语料 token 序列必须完全一致（零变化）⇒ 删除零回归。

用法：cd lightharness && python _antirun_r29_t4_D批全量反跑.py
退出码：0 = 全部零变化（ALL OK）；1 = 存在变化。
"""
import os
import sys
import glob

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

D_REMOVED = ['函数对象', '常量时间比较', '枚举值', '正则匹配', '环境枚举', '结构体值']


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


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
    after_ccw = sorted(lexer.COMMON_COMPOUND_WORDS)
    missing = [w for w in D_REMOVED if w in after_ccw]
    assert not missing, 'D批条目应已删除: %s' % missing

    print('=' * 72)
    print('R29 任务4：D批删除后 全量反跑（语料 %d 文件，CCW %d 条）'
          % (len(CORPUS), len(after_ccw)))
    print('=' * 72)

    base_errs = []
    texts = {}
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        texts[rel] = read(f)

    # 删除后状态（当前）token 基线
    after_tokens = {}
    for rel, t in texts.items():
        seq = token_seq(t)
        after_tokens[rel] = seq
        if len(seq) == 1 and seq[0].startswith('ERR:'):
            base_errs.append(rel)

    # 加回 D 批 6 条 → 删除前状态
    before_ccw = frozenset(after_ccw + D_REMOVED)
    lexer.COMMON_COMPOUND_WORDS = before_ccw
    changed = []
    for rel, t in texts.items():
        seq = token_seq(t)
        if seq != after_tokens[rel]:
            changed.append(rel)
    lexer.COMMON_COMPOUND_WORDS = frozenset(after_ccw)  # 还原

    # 汇总
    print('CCW after = %d 条 | before(加回6条) = %d 条'
          % (len(after_ccw), len(before_ccw)))
    print('既有失败文件（前后一致）: %d' % len(base_errs))
    if changed:
        print('✗ 变化文件 %d 个:' % len(changed))
        for rel in changed[:10]:
            print('   %s' % rel)
        print('=== 结果：存在变化（回归）===')
        return 1
    print('✓ 全语料 %d 文件 token 序列零变化（删除 D 批 6 条零回归）' % len(CORPUS))
    print('=== 结果：ALL OK ===')
    return 0


if __name__ == '__main__':
    sys.exit(main())
