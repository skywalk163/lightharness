# -*- coding: utf-8 -*-
"""查出 4 个 bootstrap 生成产物树的 token 漂移点（用于报告说明）。"""
import sys, os, subprocess, hashlib, tempfile, importlib.util, difflib, glob

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
sys.path.insert(0, LIGHTP + '/src')

FILES = sorted(glob.glob(LIGHTP + '/bootstrap/**/*.light', recursive=True))


def load(src_text, name):
    d = tempfile.mkdtemp(prefix='lxrd_')
    p = os.path.join(d, name + '.py')
    open(p, 'w', encoding='utf-8', newline='').write(src_text)
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


revs = subprocess.check_output(['git', '-C', LIGHTP, 'log', '--format=%H', '-n', '30'],
                               encoding='utf-8').split()
base_rev = base_text = None
for rev in revs:
    t = subprocess.check_output(['git', '-C', LIGHTP, 'show', '%s:src/lexer.py' % rev],
                                encoding='utf-8')
    if '_TRAILING_ALIAS_CLASS' not in t:
        base_rev, base_text = rev, t
        break
base = load(base_text, 'b')
edit = load(open(LIGHTP + '/src/lexer.py', encoding='utf-8', newline='').read(), 'e')


def toks(mod, s):
    return ['%s:%s' % (t.type.name, t.value) for t in mod.Lexer(s).tokenize()
            if t.type.name != 'EOF']


n = 0
for f in FILES:
    s = open(f, encoding='utf-8', errors='replace').read()
    a, b = toks(base, s), toks(edit, s)
    if a == b:
        continue
    n += 1
    print('### ' + os.path.relpath(f, ROOT))
    d = list(difflib.unified_diff(a, b, 'base', 'edit', lineterm='', n=1))
    for line in d[:24]:
        print('   ', line)
    print()
print('漂移文件数:', n, '/', len(FILES))
