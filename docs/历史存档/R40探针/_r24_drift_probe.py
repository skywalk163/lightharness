# -*- coding: utf-8 -*-
"""R24 生成树漂移根因探针：对 4 个 bootstrap 漂移文件的差异行，逐行对比
HEAD（ca5741a8 = R23 tip）与修复态 lexer 的 token 序列，判定真因。

用法： python _r24_drift_probe.py
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)              # duan-light-merge
LM = os.path.join(ROOT, 'light-merge')    # 仓库
SRC = os.path.join(LM, 'src')
LEXER = os.path.join(SRC, 'lexer.py')

BASELINE_REV = 'ca5741a8'
PROBE_LINES = [
    (os.path.join(LM, 'bootstrap/release/stdlib/对象池缓存.light'), 22),
    (os.path.join(LM, 'bootstrap/release/stdlib/对象池缓存.light'), 32),
    (os.path.join(LM, 'bootstrap/release/stdlib/CSV读写器.light'), 51),
    (os.path.join(LM, 'bootstrap/release/stdlib/CSV读写器.light'), 72),
    (os.path.join(LM, 'bootstrap/release/stdlib/文件系统.light'), 17),
    (os.path.join(LM, 'bootstrap/release/stdlib/断言工具.light'), 56),
    (os.path.join(LM, 'bootstrap/release/stdlib/断言工具.light'), 61),
    (os.path.join(LM, 'bootstrap/release/stdlib/断言工具.light'), 329),
]


def load_baseline_lexer_source():
    out = subprocess.run(['git', 'show', f'{BASELINE_REV}:src/lexer.py'],
                         cwd=LM, capture_output=True)
    if out.returncode != 0:
        raise SystemExit('git show 失败: ' + out.stderr.decode('utf-8', 'replace'))
    return out.stdout.decode('utf-8')


def make_lexer(module_source, tag):
    """把一个 lexer.py 源码加载成模块（独立命名空间，避免缓存串味）。"""
    import types
    mod = types.ModuleType(f'_probe_lexer_{tag}')
    mod.__file__ = f'<probe:{tag}>'
    # 需要 src 目录在 sys.path 上，供其内部 import keywords 等
    if SRC not in sys.path:
        sys.path.insert(0, SRC)
    code = compile(module_source, mod.__file__, 'exec')
    exec(code, mod.__dict__)
    return mod


def dump(mod, source, label):
    lex = mod.Lexer()
    toks = list(lex.tokenize(source))
    return [(t.type.name, t.value) for t in toks]


def main():
    with open(LEXER, 'r', encoding='utf-8') as f:
        head_src = load_baseline_lexer_source()
        cur_src = f.read()
    head = make_lexer(head_src, 'head')
    cur = make_lexer(cur_src, 'cur')

    for path, lineno in PROBE_LINES:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        line = lines[lineno - 1] if lineno - 1 < len(lines) else ''
        stripped = line.strip()
        rel = os.path.relpath(path, LM)
        print('=' * 78)
        print(f'{rel}:{lineno}')
        print(f'  行内容: {stripped!r}')
        try:
            ht = dump(head, line, 'H')
        except Exception as e:
            ht = f'<ERR {type(e).__name__}: {e}>'
        try:
            ct = dump(cur, line, 'C')
        except Exception as e:
            ct = f'<ERR {type(e).__name__}: {e}>'
        print(f'  HEAD: {ht}')
        print(f'  CUR : {ct}')
        print(f'  差异: {"YES" if ht != ct else "no"}')


if __name__ == '__main__':
    main()
