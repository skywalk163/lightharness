# -*- coding: utf-8 -*-
"""R36 任务3 全量反跑（G1 零变化硬门槛）。

比对 HEAD 版 lexer（A）与当前工作树 lexer（B=预计算常量版）对全语料的 token 流，
要求逐文件、逐 token 完全一致（类型+值）。任一文件不一致即判定回归。

用法：python _antirun_r36_final.py
"""
import sys, os, glob, subprocess, importlib.util, json

ROOT = os.path.dirname(os.path.abspath(__file__))
LM = os.path.join(ROOT, '..', 'light-merge')
CORPUS_ROOTS = [
    os.path.join(ROOT, 'examples'), os.path.join(ROOT, 'src'),
    os.path.join(LM, 'examples'), os.path.join(LM, 'src', 'stdlib'),
]
sys.path.insert(0, os.path.join(LM, 'src'))


def collect():
    files = []
    for r in CORPUS_ROOTS:
        files += glob.glob(os.path.join(r, '**', '*.light'), recursive=True)
    out = []
    for f in files:
        try:
            out.append((f, open(f, encoding='utf-8-sig', errors='replace').read()))
        except Exception:
            pass
    return out


def load(tag, src):
    import types
    m = types.ModuleType(f'_r36_antirun_{tag}')
    exec(compile(src, f'<{tag}>', 'exec'), m.__dict__)
    return m.Lexer


def tokstream(Lexer, text):
    return [(t.type.name, t.value) for t in Lexer(text, deterministic=True).tokenize()]


def main():
    corpus = collect()
    print(f'反跑语料：{len(corpus)} 文件')
    head_src = subprocess.run(['git', 'show', 'HEAD:src/lexer.py'], cwd=LM,
                              capture_output=True).stdout.decode('utf-8')
    cur_src = open(os.path.join(LM, 'src', 'lexer.py'), encoding='utf-8-sig').read()
    LA, LB = load('A', head_src), load('B', cur_src)

    diffs = 0
    diff_files = []
    for f, text in corpus:
        try:
            a = tokstream(LA, text)
            b = tokstream(LB, text)
        except Exception as e:
            print(f'  [ERR] {os.path.basename(f)}: {e}')
            diffs += 1; diff_files.append((os.path.basename(f), f'异常:{e}'))
            continue
        if a != b:
            diffs += 1
            # 找首个差异位置
            for i in range(min(len(a), len(b))):
                if a[i] != b[i]:
                    diff_files.append((os.path.basename(f),
                                       f'pos{i}: A={a[i]} B={b[i]}'))
                    break
            else:
                diff_files.append((os.path.basename(f),
                                   f'len A={len(a)} B={len(b)}'))
    print(f'\n不一致文件数：{diffs} / {len(corpus)}')
    if diffs:
        for fn, d in diff_files[:20]:
            print(f'  ✗ {fn}: {d}')
        print('判定：存在 token 流回归 → 不合格')
        sys.exit(1)
    else:
        print('判定：全语料 token 流逐字节一致（G1 零变化）→ 合格')
        # 写一份快照供记录
        json.dump({'files': len(corpus), 'diffs': 0,
                   'note': 'R36 预计算常量 _OPERATOR_KEYWORDS_NO_UNARY_PREFIX 与 '
                           '内联集合差语义等价，全量 token 零变化'},
                  open(os.path.join(ROOT, '_antirun_r36_final.json'), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
