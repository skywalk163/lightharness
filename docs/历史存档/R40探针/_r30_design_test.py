# -*- coding: utf-8 -*-
"""R30 任务1/2 设计验证（隔离法，不碰主树）。

1) 读真实 lexer.py，套用两处编辑（新增前缀类 + 主循环分支），写临时副本 src。
2) 父进程用**真实** lexer 生成基线（CCW=10）。
3) 子进程用**临时** lexer：
   - CCW 不变 → 应等于基线（新规则在条目仍登记时休眠）；
   - 逐条从 CCW 移除 → 目标词是否整体并入 + 语料是否零变化。
4) 对比输出。
"""
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
TMP = tempfile.mkdtemp(prefix='r30_iso_')
TMP_SRC = TMP + '/src'

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
REL = [os.path.relpath(f, ROOT).replace('\\', '/') for f in CORPUS]

TARGETS = ['位与', '位异或', '位或', '位非', '应当', '除非']
FORMS = ['返回 %s(1)', '设 x 为 [ %s ]', '如果 %s 那么 返回 1', '设 %s 为 7']

# ── 两处编辑 ───────────────────────────────────────────────────────────
ANCHOR_CLASS = ("assert _P0A_HEAD_MERGE_DUAL == frozenset(\n"
                "    {'乘', '减', '加', '除', '模', '真', '空', '到'}), (\n"
                "    'R27 DUAL 类别漂移：应恒为 8 字（乘减加除模真空到）')")
CLASS_ADD = ANCHOR_CLASS + """

# ── R30 任务1/2：词首【前缀类】——非关键字(位/应)/被DUAL抑制(除)开头的复合名 ──
# 位与/位异或/位或/位非（首字 位，非关键字）、应当（首字 应，非关键字）、
# 除非（首字 除，DUAL 抑制后成标识符）在**非语句起始/调用语境**下需整词并入；
# 其后随关键字（与/或/非/当/异）会把复合名劈开，且无既有通用规则覆盖
# （HM/DUAL 仅对「词首关键字」生效，位/应 非关键字故不适用）。
# 本类别以**首字**为键，命中即整体并入（见 _tokenize_chinese_sequence 主循环）。
_P0A_HEAD_MERGE_PREFIX = frozenset({'位', '应', '除'})
assert _P0A_HEAD_MERGE_PREFIX == frozenset({'位', '应', '除'}), (
    'R30 词首前缀类漂移：应恒为 3 字（位应除）')"""

ANCHOR_BRANCH = ("                if _ctx_call or not self._at_statement_start(source, pos):\n"
                 "                    _lead_kw, _lead_len = _match_kw(source, pos)")
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


def build_variant():
    text = open(os.path.join(REAL_SRC, 'lexer.py'), encoding='utf-8').read()
    assert text.count(ANCHOR_CLASS) == 1, 'anchor class 不唯一: %d' % text.count(ANCHOR_CLASS)
    assert text.count(ANCHOR_BRANCH) == 1, 'anchor branch 不唯一: %d' % text.count(ANCHOR_BRANCH)
    text = text.replace(ANCHOR_CLASS, CLASS_ADD, 1)
    text = text.replace(ANCHOR_BRANCH, BRANCH_ADD, 1)
    shutil.copytree(REAL_SRC, TMP_SRC)
    with open(os.path.join(TMP_SRC, 'lexer.py'), 'w', encoding='utf-8') as fh:
        fh.write(text)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def tok_sha_factory(lexer_mod):
    def f(text):
        try:
            toks = lexer_mod.Lexer(text, deterministic=True).tokenize()
            seq = [(x.type.name, x.value) for x in toks
                   if x.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            return 'ERR:' + type(e).__name__
        return hashlib.sha256(json.dumps(seq, ensure_ascii=False).encode('utf-8')).hexdigest()
    return f


def baseline_real():
    sys.path.insert(0, REAL_SRC)
    import lexer as L
    f = tok_sha_factory(L)
    out = {}
    for r, p in zip(REL, CORPUS):
        out[r] = f(open(p, encoding='utf-8', errors='replace').read())
    return out


PROBE = r'''
import sys, os, json, glob, hashlib
CFG = json.load(open(os.path.join(r"@@CFGDIR@@", "cfg.json"), encoding="utf-8"))
SRC = CFG["src"]; ROOT = CFG["root"]
REL = CFG["rel"]; TARGETS = CFG["targets"]; FORMS = CFG["forms"]
sys.path.insert(0, SRC)
import lexer as L

def tsha(text):
    try:
        t = L.Lexer(text, deterministic=True).tokenize()
        seq = [(x.type.name, x.value) for x in t if x.type.name not in ('EOF','NEWLINE')]
    except Exception as e:
        return 'ERR:' + type(e).__name__
    return hashlib.sha256(json.dumps(seq, ensure_ascii=False).encode('utf-8')).hexdigest()

def seq(text):
    try:
        t = L.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in t if x.type.name not in ('EOF','NEWLINE')]
    except Exception as e:
        return ['ERR:'+type(e).__name__]

base = sorted(L.COMMON_COMPOUND_WORDS)
texts = {r: open(os.path.join(ROOT, r), encoding='utf-8', errors='replace').read() for r in REL}

# (a) CCW 不变
full = {r: tsha(t) for r, t in texts.items()}
# (b) 逐条移除（只重验含该词的文件）
per = {}
forms = {}
for w in TARGETS:
    L.COMMON_COMPOUND_WORDS = frozenset(x for x in base if x != w)
    per[w] = {r: tsha(t) for r, t in texts.items() if w in t}
    forms[w] = {}
    for fm in FORMS:
        s = fm % w
        forms[w][s] = seq(s)
    L.COMMON_COMPOUND_WORDS = frozenset(base)
print("@@RESULT@@")
print(json.dumps({'ccw': base, 'full': full, 'per': per, 'forms': forms}, ensure_ascii=False))
'''


def main():
    vsha = build_variant()
    print('临时 variant lexer sha(text) = %s' % vsha)
    base = baseline_real()
    print('真实基线：语料 %d 文件' % len(base))

    json.dump({'src': TMP_SRC, 'root': ROOT, 'rel': REL,
               'targets': TARGETS, 'forms': FORMS},
              open(os.path.join(TMP, 'cfg.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    probe = PROBE.replace('@@CFGDIR@@', TMP)
    probe_path = os.path.join(TMP, 'probe.py')
    open(probe_path, 'w', encoding='utf-8').write(probe)
    r = subprocess.run([PY, probe_path], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=600, cwd=TMP)
    if '@@RESULT@@' not in (r.stdout or ''):
        print('探针失败:\n', (r.stdout or '')[-2000:], r.stderr[-2000:])
        return
    data = json.loads(r.stdout.split('@@RESULT@@', 1)[1].strip())
    print('临时 lexer CCW =', data['ccw'])

    # (a) 规则休眠检查
    chg_full = [k for k in REL if base[k] != data['full'][k]]
    print('\n[a] CCW 不变：语料变化 %d 文件 %s  => 新规则%s'
          % (len(chg_full), chg_full[:5], '休眠(零变化)' if not chg_full else '⚠️ 生效(异常!)'))

    # (b) 逐条移除
    print('\n[b] 逐条移除后语料变化 + 目标形态：')
    for w in TARGETS:
        chg = [k for k in data['per'][w] if base[k] != data['per'][w][k]]
        print('  %-6s 含该词文件=%d 变化=%d %s | 返回W(1)=%s'
              % (w, len(data['per'][w]), len(chg), chg[:4],
                 data['forms'][w]['返回 %s(1)' % w]))
    # 目标词形态细节
    print('\n[c] 目标词「返回 W(1)」token（移除该词后）：')
    for w in TARGETS:
        print('  %-6s %s' % (w, data['forms'][w]['返回 %s(1)' % w]))


if __name__ == '__main__':
    main()
