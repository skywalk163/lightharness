# -*- coding: utf-8 -*-
"""R30 归因：区分 19 处语料变化来自「我的任务1/2改动」还是「并发任务3改动」。"""
import os
import re
import sys
import json
import glob
import shutil
import tempfile
import hashlib
import subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
PY = os.path.join(LIGHTP, '.venv', 'Scripts', 'python.exe')
REAL_SRC = LIGHTP + '/src'
TMP = tempfile.mkdtemp(prefix='r30_attr_')
TMP_SRC = TMP + '/src'

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
REL = [os.path.relpath(f, ROOT).replace('\\', '/') for f in CORPUS]

BRANCH_ADD = ("                if _ctx_call or not self._at_statement_start(source, pos):\n"
              "                    # ── R30 任务1/2：词首前缀类（位/应/除）→ 整体并入标识符 ──\n"
              "                    # 位/应 非关键字、除 被 DUAL 抑制后成标识符；其后随关键字\n"
              "                    # （与/或/非/当）在词中会劈开复合名。命中前缀类即整体并入。\n"
              "                    if full_identifier[0] in _P0A_HEAD_MERGE_PREFIX:\n"
              "                        _tokens_append(_Token(_TokenType.IDENTIFIER, full_identifier, line, current_col))\n"
              "                        consumed += len(full_identifier)\n"
              "                        current_col += len(full_identifier)\n"
              "                        continue\n"
              "                    _lead_kw, _lead_len = _match_kw(source, pos)")
BRANCH_ORIG = ("                if _ctx_call or not self._at_statement_start(source, pos):\n"
               "                    _lead_kw, _lead_len = _match_kw(source, pos)")
SIX = ['位与', '位异或', '位或', '位非', '应当', '除非']


def build_minus_mine():
    text = open(os.path.join(REAL_SRC, 'lexer.py'), encoding='utf-8').read()
    assert text.count(BRANCH_ADD) == 1, 'branch 不唯一: %d' % text.count(BRANCH_ADD)
    text = text.replace(BRANCH_ADD, BRANCH_ORIG, 1)
    # 把 6 条加回 CCW
    ins = ''.join("    '%s',  # R30 归因回填\n" % e for e in SIX)
    m = re.search(r"COMMON_COMPOUND_WORDS = frozenset\(\{\n", text)
    assert m
    text = text[:m.end()] + ins + text[m.end():]
    shutil.copytree(REAL_SRC, TMP_SRC)
    open(os.path.join(TMP_SRC, 'lexer.py'), 'w', encoding='utf-8').write(text)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


PROBE = r'''
import sys, os, json, hashlib
CFG = json.load(open(os.path.join(r"@@CFGDIR@@", "cfg.json"), encoding="utf-8"))
sys.path.insert(0, CFG["src"])
import lexer as L
def tsha(t):
    try:
        k = L.Lexer(t, deterministic=True).tokenize()
        s = [(x.type.name, x.value) for x in k if x.type.name not in ('EOF','NEWLINE')]
    except Exception as e:
        return 'ERR:'+type(e).__name__
    return hashlib.sha256(json.dumps(s, ensure_ascii=False).encode('utf-8')).hexdigest()
out = {}
for r in CFG["rel"]:
    p = os.path.join(CFG["root"], r)
    try: t = open(p, encoding='utf-8', errors='replace').read()
    except Exception: continue
    out[r] = tsha(t)
print("@@R@@")
print(json.dumps({'ccw': sorted(L.COMMON_COMPOUND_WORDS), 'per': out}, ensure_ascii=False))
'''


def run_probe(src):
    cfg = {'src': src, 'root': ROOT, 'rel': REL}
    json.dump(cfg, open(os.path.join(TMP, 'cfg.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    pp = os.path.join(TMP, 'probe.py')
    open(pp, 'w', encoding='utf-8').write(PROBE.replace('@@CFGDIR@@', TMP))
    r = subprocess.run([PY, pp], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=600, cwd=TMP)
    return json.loads(r.stdout.split('@@R@@', 1)[1].strip())


def main():
    base = json.load(open(os.path.join(HARNESS, '_r29_baseline_tokens.json'), encoding='utf-8'))['per_file']
    mm_sha = build_minus_mine()
    print('minus-mine variant sha =', mm_sha)
    mm = run_probe(TMP_SRC)
    cur = run_probe(REAL_SRC)
    print('minus-mine CCW =', mm['ccw'])
    print('current   CCW =', cur['ccw'])

    b = base
    d_mm = [r for r in REL if r in b and mm['per'].get(r) != b[r]]
    d_cur = [r for r in REL if r in b and cur['per'].get(r) != b[r]]
    print('\n[任务3] minus-mine vs 基线 变化 %d: %s' % (len(d_mm), d_mm[:25]))
    print('\n[整体] current   vs 基线 变化 %d: %s' % (len(d_cur), d_cur[:25]))
    # 我的净效果：current vs minus-mine
    d_mine = [r for r in REL if cur['per'].get(r) != mm['per'].get(r)]
    print('\n[我的净效果] current vs minus-mine 变化 %d: %s' % (len(d_mine), d_mine[:25]))


if __name__ == '__main__':
    main()
