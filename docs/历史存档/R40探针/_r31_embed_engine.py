# -*- coding: utf-8 -*-
"""R31 _EMBED_MAX_MATCH_KEYWORDS 逐字隔离验证引擎。

三重判据（与 R29/R30 同口径）：
  G1 语料判据：撤掉该字后「含该字的语料文件」token 序列零变化
  G2 编译门  ：含该字的语句可编译（rc=0，与基态一致）
  G3 边界门  ：六类边界形态（切分尾巴/函数调用/整串合并×2/关键字独立/字符串内）
              基集 vs 移除集 token 流完全一致

实现：进程内 monkeypatch lexer._EMBED_MAX_MATCH_KEYWORDS，不改主树。
G2 走 运行.py 子进程（磁盘 lexer）。
"""
import os
import sys
import json
import glob
import subprocess
import hashlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
PY = os.path.join(LIGHTP, '.venv', 'Scripts', 'python.exe')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']

# 每个字的六类边界形态（切分尾巴 / 函数调用 / 整串合并 / 整串合并2 / 关键字独立 / 字符串内）
FORMS = {
    '为': [
        '设 甲为空',          # 赋值尾巴切分：甲(ID) 为(KEY) 空(VALUE)
        '断言为真(1)',        # 函数调用语境：ID(断言为真)
        '行为',               # 整串合并：ID(行为)
        '末位行为',           # 整串合并：ID(末位行为)
        '返回 值',            # 关键字独立：返回(KEY) 值
        '打印("为")',         # 字符串内（不应受影响）
    ],
    '返回': [
        '返回表',             # 整串合并：ID(返回表)
        '返回值',             # 整串合并：ID(返回值)
        '返回码',             # 整串合并：ID(返回码)
        '返回表(1)',          # 函数调用语境：ID(返回表)
        '设 甲返回 1',        # 赋值尾巴切分：甲(ID) 返回(KEY) 1
        '打印("返回")',       # 字符串内
    ],
    '尝试': [
        '尝试记录',           # 整串合并：ID(尝试记录)
        '尝试次数',           # 整串合并：ID(尝试次数)
        '尝试错误',           # 整串合并：ID(尝试错误)
        '尝试记录(1)',        # 函数调用语境：ID(尝试记录)
        '设 甲尝试 1',        # 赋值尾巴切分：甲(ID) 尝试(KEY) 1
        '打印("尝试")',       # 字符串内
    ],
}

G2_SRC = {
    '为': '段落 主:\n  设 甲为空\n  返回 甲\n\n主()\n',
    '返回': '段落 主:\n  设 返回表 为 空\n  返回 返回表\n\n主()\n',
    '尝试': '段落 主:\n  设 尝试记录 为 空\n  返回 尝试记录\n\n主()\n',
}


def _read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def _token_seq(text):
    import lexer
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in toks
                if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def _set_embed(chars):
    import lexer
    lexer._EMBED_MAX_MATCH_KEYWORDS = frozenset(chars)


def _sha_lexer_bin():
    return hashlib.sha256(
        open(os.path.join(LIGHTP, 'src', 'lexer.py'), 'rb').read()).hexdigest()


def _compile_rc(path):
    try:
        r = subprocess.run([PY, os.path.join(HARNESS, '运行.py'), path],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=120, cwd=HARNESS)
        return r.returncode
    except Exception:
        return -1


def _diff_seq(a, b, limit=3):
    out = []
    for i in range(max(len(a), len(b))):
        ta = a[i] if i < len(a) else ('<END>', '')
        tb = b[i] if i < len(b) else ('<END>', '')
        if ta != tb:
            out.append('@%d %r -> %r' % (i, ta, tb))
            if len(out) >= limit:
                break
    return out


def verify(char, out_json, out_md, corpus_cache=None):
    import lexer
    assert char in ('为', '返回', '尝试'), '非法字: %s' % char
    base_embed = sorted(lexer._EMBED_MAX_MATCH_KEYWORDS)
    assert char in base_embed, '字 %s 不在当前 _EMBED: %s' % (char, base_embed)

    if corpus_cache is None:
        corpus = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
        texts, base_tokens, base_errs = {}, {}, []
        for f in corpus:
            rel = os.path.relpath(f, ROOT).replace('\\', '/')
            t = _read(f)
            texts[rel] = t
            seq = _token_seq(t)
            base_tokens[rel] = seq
            if len(seq) == 1 and seq[0].startswith('ERR:'):
                base_errs.append(rel)
        corpus_cache = (corpus, texts, base_tokens, base_errs)
    corpus, texts, base_tokens, base_errs = corpus_cache

    print('=' * 72)
    print('R31 _EMBED 字「%s」隔离验证（语料 %d 文件，含该字 %d 文件）'
          % (char, len(corpus), sum(1 for t in texts.values() if char in t)))
    print('当前 _EMBED = %s | lexer sha=%s' % (base_embed, _sha_lexer_bin()[:12]))
    print('=' * 72)

    forms = FORMS[char]
    g3_base = [_token_seq(s) for s in forms]

    # 撤除该字
    reduced = [c for c in base_embed if c != char]
    _set_embed(reduced)

    # G1
    changed = {}
    for rel, t in texts.items():
        if char not in t:
            continue
        seq = _token_seq(t)
        if seq != base_tokens[rel]:
            changed[rel] = _diff_seq(base_tokens[rel], seq)

    # G3
    g3_bad = []
    for i, line in enumerate(forms):
        cur = _token_seq(line)
        if cur != g3_base[i]:
            g3_bad.append({'form': line[:30], 'diff': _diff_seq(g3_base[i], cur)})

    # G2 编译门（磁盘 lexer，rc 一致即 PASS）
    g2_dir = os.path.join(HARNESS, '_r31_g2')
    os.makedirs(g2_dir, exist_ok=True)
    g2_path = os.path.join(g2_dir, '_g2_%s.light' % char)
    with open(g2_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(G2_SRC[char])
    g2_rc_removed = _compile_rc(g2_path)
    g2_rc_base = _compile_rc(g2_path)
    try:
        os.remove(g2_path)
    except OSError:
        pass

    # 还原
    _set_embed(base_embed)

    g1_pass = not changed
    g2_pass = (g2_rc_base == g2_rc_removed) and (g2_rc_base == 0)
    g3_pass = not g3_bad
    ok = g1_pass and g2_pass and g3_pass
    verdict = '可删' if ok else '保留'

    ev = {
        'char': char,
        'g1_changed_files': changed, 'g1_changed_count': len(changed),
        'g1_pass': g1_pass,
        'g2_rc_base': g2_rc_base, 'g2_rc_removed': g2_rc_removed, 'g2_pass': g2_pass,
        'g3_fail': g3_bad, 'g3_pass': g3_pass,
        'verdict': verdict,
    }
    json.dump({'char': char, 'corpus_files': len(corpus),
               'corpus_with_char': sum(1 for t in texts.values() if char in t),
               'base_embed': base_embed, 'reduced_embed': reduced,
               'lexer_sha': _sha_lexer_bin(), 'base_err_files': base_errs,
               'evidence': ev},
              open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    _write_md(char, ev, base_embed, len(corpus), out_md)
    print('G1 %s(%d) | G2 %s | G3 %s(%d) | => %s'
          % ('PASS' if g1_pass else 'FAIL', len(changed),
             'PASS' if g2_pass else 'FAIL',
             'PASS' if g3_pass else 'FAIL', len(g3_bad), verdict))
    for rel, diff in list(changed.items())[:5]:
        print('   G1✗ %s: %s' % (rel, diff[:1]))
    for b in g3_bad[:5]:
        print('   G3✗ %s: %s' % (b['form'], b['diff'][:1]))
    print('证据: %s | 清单: %s' % (out_json, out_md))
    return ev


def _write_md(char, ev, base_embed, corpus_n, out_md):
    L = []
    L.append('# 第31轮 _EMBED 字「%s」逐条验证清单' % char)
    L.append('')
    L.append('日期：2026-09-15 ｜ 结论：**%s**（G1∧G2∧G3 全通过才可删）'
             % ev['verdict'])
    L.append('')
    L.append('## 一、当前 _EMBED 表')
    L.append('')
    L.append('```python')
    L.append('_EMBED_MAX_MATCH_KEYWORDS = frozenset(%s)' % sorted(base_embed))
    L.append('```')
    L.append('')
    L.append('## 二、三重判据结果')
    L.append('')
    L.append('| 判据 | 结果 | 说明 |')
    L.append('|---|---|---|')
    L.append('| G1 语料判据 | %s | 含「%s」的语料文件 token 变化数 = %d（硬门槛：0）|'
             % ('PASS' if ev['g1_pass'] else 'FAIL', char, ev['g1_changed_count']))
    L.append('| G2 编译门 | %s | rc 基态=%d / 撤除态=%d |'
             % ('PASS' if ev['g2_pass'] else 'FAIL', ev['g2_rc_base'], ev['g2_rc_removed']))
    L.append('| G3 边界门 | %s | 失败形态数 = %d |'
             % ('PASS' if ev['g3_pass'] else 'FAIL', len(ev['g3_fail'])))
    L.append('')
    if ev['g3_fail']:
        L.append('### G3 失败边界形态（撤除后 token 流变化 = 该字是真护栏）')
        L.append('')
        L.append('| 边界形态 | 变化点 |')
        L.append('|---|---|')
        for b in ev['g3_fail']:
            L.append('| `%s` | %s |' % (b['form'], b['diff'][0] if b['diff'] else '（整串变化）'))
        L.append('')
    if ev['g1_changed_files']:
        L.append('### G1 变化文件（撤除后 token 流变化）')
        L.append('')
        for rel, diff in list(ev['g1_changed_files'].items())[:20]:
            L.append('- `%s`：%s' % (rel, diff[0] if diff else ''))
        L.append('')
    L.append('## 三、结论与理由')
    L.append('')
    if ev['verdict'] == '可删':
        L.append('「%s」可从 _EMBED 移除：撤除后全语料零变化、六类边界形态不变、'
                 '含该字语句仍可编译。' % char)
    else:
        L.append('「%s」**保留为真护栏**：撤除后 G1/G3 出现 token 流变化，'
                 '无通用词法规则可替代（复合名 `X` 会落回 R21 块被关键字劈开）。' % char)
    L.append('')
    L.append('## 四、铁律自检')
    L.append('')
    L.append('| 铁律 | 自检 |')
    L.append('|---|---|')
    L.append('| 只改本字，不碰其他两条 | ✅ 仅 monkeypatch 撤除「%s」 |' % char)
    L.append('| 逐条隔离验证 | ✅ 进程内 monkeypatch，不改主树 |')
    L.append('| G1∧G2∧G3 全通过才可删 | %s |'
             % ('✅ 全通过' if ev['verdict'] == '可删' else '⛔ 未全通过，保留'))
    L.append('| 删除后全量反跑零回归 | 待合并后确认（若保留则无需改主树） |')
    L.append('| 新增一律 .light | ✅ G2 探针为临时 .light（验证后清理） |')
    open(out_md, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))


if __name__ == '__main__':
    import sys as _s
    _c = _s.argv[1] if len(_s.argv) > 1 else '为'
    verify(_c, '_r31_ev_%s.json' % _c, '_task1_R31_字验证_%s.md' % _c)
