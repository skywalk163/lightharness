# -*- coding: utf-8 -*-
"""R35 G1 全语料引擎：临时副本 + 子进程（不碰主树）。

用法：
    python _r35_g1_engine.py                    # 只跑 reference（当前 lexer）
    python _r35_g1_engine.py <variant_name>     # 跑指定变体并与 reference 比对

变体在 VARIANTS 字典中定义：源文本替换列表 [(old, new), ...]。

口径：对全语料每文件 tokenize，取 token 列表 sha256，逐文件比对。
排除「基线即失败」的文件（ERR: 开头）。
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
CACHE = os.path.join(ROOT, 'lightharness', '_r35_g1_cache')
os.makedirs(CACHE, exist_ok=True)

PATS = [ROOT + p for p in (
    '/lightharness/examples/**/*.light', '/lightharness/src/**/*.light',
    '/lightharness/tests/**/*.light', '/light-merge/examples/**/*.light',
    '/light-merge/stdlib/**/*.light', '/light-merge/bootstrap/**/*.light',
    '/light-merge/src/**/*.light', '/light-merge/tests/**/*.light')]


def corpus():
    return sorted(set(sum((glob.glob(g, recursive=True) for g in PATS), [])))


# ---------- 子进程：用指定 srcdir 的 lexer 跑全语料 ----------
CHILD = r'''
import glob, hashlib, json, os, sys
srcdir, out, cfgjson = sys.argv[2], sys.argv[3], sys.argv[4]
cfg = json.load(open(cfgjson, encoding='utf-8'))
pats, root = cfg['pats'], cfg['root']
sys.path.insert(0, srcdir)
import lexer
files = sorted(set(sum((glob.glob(g, recursive=True) for g in pats), [])))
per = {}
for f in files:
    rel = os.path.relpath(f, root).replace('\\', '/')
    try:
        src = open(f, encoding='utf-8').read()
        toks = [(t.type.name, t.value) for t in lexer.Lexer(src, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
        per[rel] = hashlib.sha256(
            json.dumps(toks, ensure_ascii=False).encode()).hexdigest()
    except Exception as e:
        per[rel] = 'ERR:' + type(e).__name__
json.dump(per, open(out, 'w', encoding='utf-8'))
print('child done ' + str(len(per)))
'''


def materialize(name, patches=None):
    """生成（并缓存路径于返回值）含补丁的临时 src 副本目录。"""
    tmp = tempfile.mkdtemp(prefix='r35m_')
    d = os.path.join(tmp, 'src')
    shutil.copytree(SRC, d, ignore=shutil.ignore_patterns('__pycache__'))
    lp = os.path.join(d, 'lexer.py')
    if patches:
        t = open(lp, encoding='utf-8').read()
        for old, new in patches:
            if old not in t:
                raise SystemExit('补丁未命中: %r' % old[:80])
            t = t.replace(old, new, 1)
        open(lp, 'w', encoding='utf-8').write(t)
    return d


def run_variant(name, patches=None):
    """patches: [(old, new), ...] 施加于 lexer.py 源文本。None = 原样。"""
    cache = os.path.join(CACHE, name + '.json')
    if os.path.exists(cache):
        return json.load(open(cache, encoding='utf-8'))
    tmp = tempfile.mkdtemp(prefix='r35_')
    d = os.path.join(tmp, 'src')
    shutil.copytree(SRC, d, ignore=shutil.ignore_patterns('__pycache__'))
    lp = os.path.join(d, 'lexer.py')
    if patches:
        t = open(lp, encoding='utf-8').read()
        for old, new in patches:
            if old not in t:
                raise SystemExit('补丁未命中: %r' % old[:80])
            t = t.replace(old, new, 1)
        open(lp, 'w', encoding='utf-8').write(t)
    out = os.path.join(tmp, 'out.json')
    ch = os.path.join(tmp, 'child.py')
    cfg = os.path.join(tmp, 'cfg.json')
    open(ch, 'w', encoding='utf-8').write(CHILD)
    json.dump({'pats': PATS, 'root': ROOT}, open(cfg, 'w', encoding='utf-8'))
    r = subprocess.run([sys.executable, ch, 'child', d, out, cfg],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if not os.path.exists(out):
        raise SystemExit('子进程失败 %s\n%s' % (name, r.stderr[-2000:]))
    per = json.load(open(out, encoding='utf-8'))
    json.dump(per, open(cache, 'w', encoding='utf-8'), ensure_ascii=False)
    return per


def diff(a, b, label):
    ka = [k for k, v in a.items() if not v.startswith('ERR:')]
    changed = [k for k in ka if a[k] != b.get(k)]
    newerr = [k for k in ka if b.get(k, '').startswith('ERR:')]
    print('  %-28s 可比=%d 变化=%d 新错=%d %s' % (
        label, len(ka), len(changed), len(newerr),
        '★' if (changed or newerr) else 'OK'))
    for k in changed[:10]:
        print('       变化: %s' % k)
    for k in newerr[:5]:
        print('       新错: %s -> %s' % (k, b.get(k)))
    return changed, newerr


if __name__ == '__main__':
    ref = run_variant('reference')
    if len(sys.argv) > 1:
        name = sys.argv[1]
        from _r35_variants import VARIANTS
        patches = VARIANTS[name]
        per = run_variant(name, patches)
        print('=== G1 变体 %s vs reference ===' % name)
        diff(ref, per, name)
    else:
        print('reference: %d 文件' % len(ref))
        print('  基线失败文件: %d' % sum(
            1 for v in ref.values() if v.startswith('ERR:')))
