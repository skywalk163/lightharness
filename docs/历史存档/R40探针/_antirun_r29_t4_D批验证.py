# -*- coding: utf-8 -*-
"""R29 任务4：D批（其他类型 8条）CCW 逐条隔离验证。

三重判据（与任务书同口径）：
  G1 语料判据：撤掉该条目后全语料 token 序列零变化
  G2 编译门  ：含该条目的语句 编译 rc 撤掉前后一致（且最好 rc=0）
  G3 边界门  ：六类边界形态 token 流不变

D批条目：函数对象 常量时间比较 幂次 枚举值 正则匹配 环境枚举 结构体值 记录类型
输出：_task4_R29_D批验证_证据.json + 控制台摘要
"""
import os
import sys
import json
import glob
import hashlib
import subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
PY = os.path.join(LIGHTP, '.venv', 'Scripts', 'python.exe')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

D_BATCH = ['函数对象', '常量时间比较', '幂次', '枚举值',
           '正则匹配', '环境枚举', '结构体值', '记录类型']

# G3 边界形态（每条目一组代码片段，覆盖 独立/词首/词中/词尾/调用/上下文）
def g3_forms(w):
    return [
        '设 %s 为 7' % w,            # 独立单词（设名）
        '段落 %s 接收 a:\n  返回 a' % w,   # 段落名
        '返回 %s(1)' % w,            # 函数调用形态
        '设 x 为 [ %s ]' % w,        # 列表元素
        '如果 %s 那么 返回 1' % w,    # 条件上下文
        '打印("%s")' % w,            # 字符串内（不应受影响）
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


def set_ccw(words):
    import lexer
    fs = frozenset(words)
    lexer.COMMON_COMPOUND_WORDS = fs


def compile_rc(path):
    """用运行.py 编译运行 .light，返回 rc。"""
    try:
        r = subprocess.run([PY, os.path.join(HARNESS, '运行.py'), path],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=60, cwd=HARNESS)
        return r.returncode
    except Exception:
        return -1


def diff_seq(a, b, limit=3):
    out = []
    for i in range(max(len(a), len(b))):
        ta = a[i] if i < len(a) else ('<END>', '')
        tb = b[i] if i < len(b) else ('<END>', '')
        if ta != tb:
            out.append('@%d %r -> %r' % (i, ta, tb))
            if len(out) >= limit:
                break
    return out


def main():
    import lexer
    base_ccw = sorted(lexer.COMMON_COMPOUND_WORDS)
    missing = [w for w in D_BATCH if w not in base_ccw]
    assert not missing, 'D批条目不在CCW: %s' % missing

    print('=' * 72)
    print('R29 任务4：D批 CCW 逐条隔离验证（%d 条，语料 %d 文件）'
          % (len(D_BATCH), len(CORPUS)))
    print('=' * 72)

    # 预读语料 + 基线
    texts, base_tokens, base_errs = {}, {}, []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        texts[rel] = read(f)
        seq = token_seq(texts[rel])
        base_tokens[rel] = seq
        if len(seq) == 1 and seq[0].startswith('ERR:'):
            base_errs.append(rel)
    print('基线完成：成功 %d | 既有失败 %d'
          % (len(base_tokens) - len(base_errs), len(base_errs)))

    # G3 基线（CS 基态）
    g3_src = {w: g3_forms(w) for w in D_BATCH}
    g3_base = {w: [token_seq(s) for s in ss] for w, ss in g3_src.items()}

    # G2 编译探针文件（每条目一个最小可编译文件）
    g2_dir = os.path.join(HARNESS, '_r29_d_g2')
    os.makedirs(g2_dir, exist_ok=True)
    g2_files = {}
    for w in D_BATCH:
        p = os.path.join(g2_dir, '_g2_%d.light' % D_BATCH.index(w))
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('段落 主:\n  设 %s 为 7\n  返回 %s\n\n主()\n' % (w, w))
        g2_files[w] = p

    evidence = {}
    print('\n%-12s %-8s %-6s %-6s %s' % ('条目', 'G1', 'G2', 'G3', '结论'))
    print('-' * 64)
    for w in D_BATCH:
        reduced = [x for x in base_ccw if x != w]
        set_ccw(reduced)
        # G1
        changed = {}
        for rel, t in texts.items():
            if w not in t:
                continue
            seq = token_seq(t)
            if seq != base_tokens[rel]:
                changed[rel] = diff_seq(base_tokens[rel], seq)
        # G3
        g3_bad = []
        for i, line in enumerate(g3_src[w]):
            cur = token_seq(line)
            if cur != g3_base[w][i]:
                g3_bad.append({'form': line[:30], 'diff': diff_seq(g3_base[w][i], cur)})
        # G2（撤掉态编译 rc）
        g2_rc_removed = compile_rc(g2_files[w])
        set_ccw(base_ccw)
        # G2（基态编译 rc）
        g2_rc_base = compile_rc(g2_files[w])

        g1_pass = not changed
        g2_pass = (g2_rc_base == g2_rc_removed) and (g2_rc_base == 0)
        g3_pass = not g3_bad
        ok = g1_pass and g2_pass and g3_pass
        evidence[w] = {
            'g1_changed_files': changed, 'g1_changed_count': len(changed),
            'g1_pass': g1_pass,
            'g2_rc_base': g2_rc_base, 'g2_rc_removed': g2_rc_removed,
            'g2_pass': g2_pass,
            'g3_fail': g3_bad, 'g3_pass': g3_pass,
            'verdict': '可删' if ok else '保留',
        }
        print('%-12s %-8s %-6s %-6s %s' % (
            w, 'PASS' if g1_pass else 'FAIL(%d)' % len(changed),
            'PASS' if g2_pass else 'FAIL(%d/%d)' % (g2_rc_base, g2_rc_removed),
            'PASS' if g3_pass else 'FAIL', evidence[w]['verdict']))
        for rel, d in list(changed.items())[:3]:
            print('     G1 %s: %s' % (rel, d[:2]))
        for bad in g3_bad:
            print('     G3 %s: %s' % (bad['form'], bad['diff'][:2]))

    # 清理 G2 临时文件
    for p in g2_files.values():
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.rmdir(g2_dir)
    except OSError:
        pass

    out = os.path.join(HARNESS, '_task4_R29_D批验证_证据.json')
    json.dump({'d_batch': D_BATCH, 'corpus_files': len(CORPUS),
               'base_err_files': base_errs, 'evidence': evidence},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    deletable = [w for w in D_BATCH if evidence[w]['verdict'] == '可删']
    print('-' * 64)
    print('可删 %d 条: %s' % (len(deletable), '、'.join(deletable)))
    print('保留 %d 条: %s' % (len(D_BATCH) - len(deletable),
                              '、'.join(w for w in D_BATCH if w not in deletable)))
    print('证据文件: %s' % out)


if __name__ == '__main__':
    main()
