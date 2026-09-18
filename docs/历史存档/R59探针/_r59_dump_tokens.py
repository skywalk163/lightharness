# -*- coding: utf-8 -*-
"""R57 任务1 语料 token A/B 转储/比对工具。

用法:
    python _r57_dump_tokens.py <lexer_py> <out_tsv> [detail_out.txt]

<lexer_py>  要加载的 lexer.py 路径（HEAD 版或当前版）。
<out_tsv>   每行: <相对路径>\t<token数>\t<sha1(repr(tokens))>
可选第三个参数 detail_out.txt: 对每个文件额外写出完整 token 列表（用于 diff 定位）。
"""
import sys, os, hashlib, io, time, importlib.util

ROOT = r'G:\dswork\duan-light-merge'
LM = os.path.join(ROOT, 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

_lexer_py, _out_tsv = sys.argv[1], sys.argv[2]
_detail = sys.argv[3] if len(sys.argv) > 3 else None

spec = importlib.util.spec_from_file_location('lexer_under_test', _lexer_py)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Lexer = mod.Lexer

ROOTS = [LM, os.path.join(ROOT, 'lightharness')]
SKIP_DIRS = {'.git', '__pycache__', '.venv', 'node_modules', '.mypy_cache'}
files = []
for r in ROOTS:
    for dp, dn, fn in os.walk(r):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.endswith('.light'):
                files.append(os.path.join(dp, f))
files.sort()

t0 = time.time()
nchg = 0
with io.open(_out_tsv, 'w', encoding='utf-8', newline='\n') as out, \
     (io.open(_detail, 'w', encoding='utf-8', newline='\n') if _detail else io.StringIO()) as det:
    for idx, p in enumerate(files):
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        try:
            src = io.open(p, encoding='utf-8').read()
        except Exception as e:  # noqa: BLE001
            out.write(f'{rel}\t-1\tREADERR:{type(e).__name__}\n')
            continue
        try:
            toks = Lexer().tokenize(src)
            sig = '|'.join(f'{t.type.name}\x01{t.value}' for t in toks)
            digest = hashlib.sha1(sig.encode('utf-8', 'replace')).hexdigest()[:16]
        except Exception as e:  # noqa: BLE001
            toks = None
            digest = f'ERR:{type(e).__name__}:{str(e)[:60]}'
        out.write(f'{rel}\t{len(toks) if toks is not None else -1}\t{digest}\n')
        if _detail:
            det.write(f'### {rel}\n')
            if toks is not None:
                det.write('\n'.join(f'  {t.type.name} {t.value!r}' for t in toks))
            else:
                det.write(f'  <ERR {digest}>')
            det.write('\n')
        if idx % 2000 == 0:
            sys.stderr.write(f'  ... {idx}/{len(files)} ({time.time()-t0:.0f}s)\n')
            sys.stderr.flush()

sys.stderr.write(f'DONE {len(files)} files in {time.time()-t0:.0f}s -> {_out_tsv}\n')
