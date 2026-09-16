# -*- coding: utf-8 -*-
"""R30 v2 隔离验证：把词首前缀类（位/应/除）判定从「非语句起始/调用」条件内
提升到条件外（覆盖语句起始非调用形态，如 `除非 条件:`）。

用法：
  python _r30v2_iso.py            # 父：构造变体 + 子进程跑 G1/G3
  python _r30v2_iso.py child <srcdir> <outjson>   # 子：以 srcdir 为 lexer 源跑判据
"""
import os
import sys
import json
import glob
import shutil
import hashlib
import tempfile
import subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
SRC = LIGHTP + '/src/lexer.py'

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

OLD1 = """            if (len(full_identifier) > 1
                    and full_identifier not in _ALL_KEYWORDS_WITH_VERBS
                    and full_identifier not in user_definitions
                    and full_identifier not in _common_compounds):
                _ctx_tail = pos + len(full_identifier)"""

NEW1 = """            if (len(full_identifier) > 1
                    and full_identifier not in _ALL_KEYWORDS_WITH_VERBS
                    and full_identifier not in user_definitions
                    and full_identifier not in _common_compounds):
                # ── R30v2：词首前缀类（位/应/除）→ 任何位置整串并入标识符 ──
                # 位/应 非关键字、除 被 DUAL 抑制后成标识符；其后随关键字
                # （与/或/非/当）在词中会劈开复合名（除非 → 除+非）。命中即并入。
                if full_identifier[0] in _P0A_HEAD_MERGE_PREFIX:
                    _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                    consumed += len(full_identifier)
                    current_col += len(full_identifier)
                    continue
                _ctx_tail = pos + len(full_identifier)"""

OLD2 = """                    # ── R30 任务1/2：词首前缀类（位/应/除）→ 整体并入标识符 ──
                    # 位/应 非关键字、除 被 DUAL 抑制后成标识符；其后随关键字
                    # （与/或/非/当）在词中会劈开复合名。命中前缀类即整体并入。
                    if full_identifier[0] in _P0A_HEAD_MERGE_PREFIX:
                        _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))
                        consumed += len(full_identifier)
                        current_col += len(full_identifier)
                        continue
"""

PATCH = [(OLD1, NEW1), (OLD2, '')]


def child(srcdir, outjson):
    sys.path.insert(0, srcdir)
    import lexer

    def seq(text):
        try:
            t = lexer.Lexer(text, deterministic=True).tokenize()
            return [(x.type.name, x.value) for x in t if x.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            return ['ERR:' + type(e).__name__ + ':' + str(e)[:40]]

    def tsha(text):
        return hashlib.sha256(json.dumps(seq(text), ensure_ascii=False).encode('utf-8')).hexdigest()

    base = json.load(open(os.path.join(HARNESS, '_r29_baseline_tokens.json'), encoding='utf-8'))['per_file']
    changed, compared, skipped = [], 0, []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        if rel not in base:
            continue
        if base[rel].startswith('ERR:'):
            skipped.append(rel)
            continue
        try:
            t = open(f, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        s = tsha(t)
        if s.startswith('ERR:'):
            continue
        compared += 1
        if s != base[rel]:
            changed.append(rel)

    # G3 形态（含语句起始非调用）
    def is_merged(tokens, w):
        return any(t[0] == 'IDENTIFIER' and t[1] == w for t in tokens)

    forms = {
        '位与': ['设 位与 为 7', '位与(1, 2)', '返回 位与(1)', '设 x 为 [ 位与 ]',
                '如果 位与 那么 返回 1', '段落 位与 接收 a:\n  返回 a'],
        '位异或': ['位异或(1, 2)', '设 位异或 为 7', '返回 位异或(1)'],
        '位或': ['位或(1, 2)', '设 位或 为 7'],
        '位非': ['位非(1)', '设 位非 为 7'],
        '应当': ['应当(1)', '如果 应当 那么:\n  返回 1', '设 应当 为 7', '返回 应当(1)'],
        '除非': ['除非(1)', '除非 条件:\n  返回 1', '设 除非 为 7', '返回 除非(1)',
                '如果 除非 那么 返回 1'],
    }
    g3 = {}
    for w, cases in forms.items():
        g3[w] = {c: is_merged(seq(c), w) for c in cases}
    # 反向形态：独立关键字 / 关键字
    rev = {
        '位独立': seq('设 位 为 1'),
        '当循环': seq('当 x > 0:\n  返回 1'),
        '非逻辑': seq('设 y 为 非 真'),
        '与运算': seq('设 z 为 甲 与 乙'),
        '除法': seq('设 q 为 甲 除 乙'),
    }
    json.dump({'srcdir': srcdir, 'ccw': sorted(lexer.COMMON_COMPOUND_WORDS),
               'prefix': sorted(lexer._P0A_HEAD_MERGE_PREFIX),
               'compared': compared, 'changed': changed, 'g1_zero': not changed,
               'skipped_base_err': skipped, 'g3': g3, 'rev': rev},
              open(outjson, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def parent():
    variants = {}

    def make(tag, patch):
        src = open(SRC, encoding='utf-8').read()
        for old, new in patch:
            assert old in src, 'anchor missing for %s:\n%s' % (tag, old[:80])
            src = src.replace(old, new, 1)
        d = tempfile.mkdtemp(prefix='r30v2_' + tag + '_')
        shutil.copytree(LIGHTP + '/src', d + '/src',
                        ignore=shutil.ignore_patterns('__pycache__'), dirs_exist_ok=True)
        open(d + '/src/lexer.py', 'w', encoding='utf-8').write(src)
        return d

    variants['current'] = make('cur', [])
    variants['patched'] = make('pat', PATCH)

    results = {}
    for tag, srcdir in variants.items():
        outj = HARNESS + '/_r30v2_%s.json' % tag
        r = subprocess.run([sys.executable, os.path.abspath(__file__), 'child',
                            srcdir + '/src', outj], capture_output=True, text=True)
        if r.returncode != 0:
            print('[%s] child FAILED:\n%s\n%s' % (tag, r.stdout[-2000:], r.stderr[-2000:]))
            return
        results[tag] = json.load(open(outj, encoding='utf-8'))

    cur, pat = results['current'], results['patched']
    print('=' * 72)
    print('[current] CCW=%s prefix=%s' % (cur['ccw'], cur['prefix']))
    print('  G1: 可比 %d | 零变化=%s | 变化 %d' % (cur['compared'], cur['g1_zero'], len(cur['changed'])))
    print('[patched] CCW=%s prefix=%s' % (pat['ccw'], pat['prefix']))
    print('  G1: 可比 %d | 零变化=%s | 变化 %d' % (pat['compared'], pat['g1_zero'], len(pat['changed'])))
    if pat['changed']:
        print('  patched 变化文件: %s' % pat['changed'][:12])
    print('\n[patched] G3 正向形态：')
    for w, cases in pat['g3'].items():
        bad = [c for c, ok in cases.items() if not ok]
        print('  %-6s %d/%d 通过 %s' % (w, len(cases) - len(bad), len(cases),
                                        ('✗ 失败: %r' % bad) if bad else ''))
    print('\n[patched] 反向形态：')
    for k, v in pat['rev'].items():
        print('  %-8s %s' % (k, v))


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'child':
        child(sys.argv[2], sys.argv[3])
    else:
        parent()
