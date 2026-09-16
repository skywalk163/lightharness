# -*- coding: utf-8 -*-
"""R24 并发写入检测：committed HEAD(ca5741a8) vs 当前工作区 src/lexer.py 的全语料 token A/B。

用途：多 agent 并行改同一棵 src/lexer.py 时，判定「工作区未提交改动」是否已破坏行为。
只读快照 + sha256 外部写入检测；不做任何文件写入。
"""
import os
import sys
import glob
import json
import time
import hashlib
import tempfile
import importlib.util
import statistics
import subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')

PATTERNS = [
    HARNESS + '/examples/**/*.light',
    HARNESS + '/src/**/*.light',
    HARNESS + '/tests/**/*.light',
    LIGHTP + '/examples/**/*.light',
    LIGHTP + '/stdlib/**/*.light',
    LIGHTP + '/bootstrap/**/*.light',
    LIGHTP + '/src/**/*.light',
    LIGHTP + '/tests/**/*.light',
]
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
GENERATED_TREES = [os.path.join(LIGHTP, 'bootstrap')]


def sha256_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def read(f):
    with open(f, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def load_lexer(src_text, modname):
    d = tempfile.mkdtemp(prefix='lxr_wip_')
    p = os.path.join(d, modname + '.py')
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src_text)
    # 让临时模块能 import 到同目录的 tokens/keywords 等（从 src 拷贝符号搜索路径）
    sys.path.insert(0, os.path.join(LIGHTP, 'src'))
    spec = importlib.util.spec_from_file_location(modname, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def tok_key(mod, src):
    try:
        toks = mod.Lexer(src, deterministic=True).tokenize()
        return hashlib.sha256(
            repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__ + ':' + str(e)[:40]


def is_generated(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED_TREES)


def main():
    head_rev = subprocess.check_output(
        ['git', '-C', LIGHTP, 'rev-parse', 'HEAD'], encoding='utf-8').strip()
    head_text = subprocess.check_output(
        ['git', '-C', LIGHTP, 'show', 'HEAD:src/lexer.py'], encoding='utf-8')
    cur_text = read(LEXER)

    print('语料 .light 文件：%d' % len(CORPUS))
    print('HEAD      = %s  sha=%s' % (head_rev[:12], sha256_text(head_text)[:16]))
    print('工作区 WIP sha=%s  %s' % (sha256_text(cur_text)[:16],
                                     '（与 HEAD 相同）' if cur_text == head_text else '（已改动）'))

    base = load_lexer(head_text, '_lxr_head_r24')
    wip = load_lexer(cur_text, '_lxr_wip_r24')

    print('HEAD  CS=%d  trailing=%d' % (
        len(base._COMPOUND_SAFE_SINGLE_KEYWORDS),
        len(getattr(base.Lexer, '_TRAILING_ALIAS_CLASS', ()))))
    print('WIP   CS=%d  trailing=%d' % (
        len(wip._COMPOUND_SAFE_SINGLE_KEYWORDS),
        len(getattr(wip.Lexer, '_TRAILING_ALIAS_CLASS', ()))))

    TEXTS = {f: read(f) for f in CORPUS}
    sha_probe0 = sha256_text(cur_text)

    t0 = time.time()
    d_head = {f: tok_key(base, TEXTS[f]) for f in CORPUS}
    t_head = time.time() - t0
    t0 = time.time()
    d_wip = {f: tok_key(wip, TEXTS[f]) for f in CORPUS}
    t_wip = time.time() - t0

    ch = [f for f in CORPUS if d_head[f] != d_wip.get(f)]
    ch_real = [f for f in ch if not is_generated(f)]
    ch_gen = [f for f in ch if is_generated(f)]
    err_wip = [f for f in CORPUS if d_wip[f].startswith('ERR:')]
    err_head = [f for f in CORPUS if d_head[f].startswith('ERR:')]

    print('[A] 外部写入检测：%s' % ('OK（快照未变）'
                                   if sha256_text(read(LEXER)) == sha_probe0 else '★ 文件已被再次写入'))
    print('[B] token 变化：真实源 %d 文件 ｜生成树 %d 文件' % (len(ch_real), len(ch_gen)))
    for f in ch_real[:25]:
        print('      真实源:', os.path.relpath(f, ROOT))
    for f in ch_gen[:8]:
        print('      生成树:', os.path.relpath(f, ROOT))
    print('[C] 抛异常：HEAD %d ｜ WIP %d' % (len(err_head), len(err_wip)))
    for f in err_wip[:10]:
        print('      WIP 异常:', os.path.relpath(f, ROOT), d_wip[f][:70])
    print('[D] 性能：HEAD %.2fs  WIP %.2fs  ×%.3f' % (t_head, t_wip, t_head / t_wip if t_wip else 0))

    out = {
        'head_rev': head_rev,
        'head_sha': sha256_text(head_text),
        'wip_sha': sha256_text(cur_text),
        'corpus_files': len(CORPUS),
        'head_cs': sorted(base._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'wip_cs': sorted(wip._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'head_trailing': sorted(getattr(base.Lexer, '_TRAILING_ALIAS_CLASS', ())),
        'wip_trailing': sorted(getattr(wip.Lexer, '_TRAILING_ALIAS_CLASS', ())),
        'changed_real': [os.path.relpath(f, ROOT) for f in ch_real],
        'changed_generated': [os.path.relpath(f, ROOT) for f in ch_gen],
        'err_head': [os.path.relpath(f, ROOT) for f in err_head],
        'err_wip': [os.path.relpath(f, ROOT) for f in err_wip],
        'time_head_s': round(t_head, 2),
        'time_wip_s': round(t_wip, 2),
    }
    json.dump(out, open(HARNESS + '/_r24_wip_ab.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('证据 → _r24_wip_ab.json')


if __name__ == '__main__':
    main()
