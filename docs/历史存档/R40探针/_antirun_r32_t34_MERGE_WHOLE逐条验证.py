# -*- coding: utf-8 -*-
"""R32 任务3/4：_P0A_MERGE_WHOLE 10 条逐条隔离验证（G1 语料判据）。

对每条整串构建「仅移除该条」的变体 lexer 模块，跑全语料 tokenize，
与基线（当前工作区 lexer.py）逐文件比对 token 序列 sha256。
  变化文件数 = 0  → G1 通过（该条可删候选）
  变化文件数 > 0  → G1 失败（真护栏，保留）
另跑「全部通过者并集」变体，验证合并删除仍零变化。

口径：lightharness + light-merge 全部 .light，deterministic=True，
过滤 EOF/NEWLINE。变体由 src/lexer.py 行级手术生成（锚点断言保护），
不触碰真实 lexer.py。
"""
import glob
import hashlib
import importlib
import json
import os
import sys
import time

ROOT = r'G:/dswork/duan-light-merge'
# 验证基线 = 编辑前快照（git show HEAD:src/lexer.py，即 R32 任务3/4 动工前的
# lexer.py；src 当时干净）。用快照而非工作区文件，保证脚本在正式编辑落盘后
# 仍可复现逐条隔离验证。
SRC = os.path.join(ROOT, 'lightharness', '_r32_lexer_head.py')
LH = os.path.join(ROOT, 'lightharness')
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
sys.path.insert(0, LH)

ENTRIES = ['导出事件表', '整理模型消息', '退出码', '接收参数', '非空块',
           '外部命令', '排序依据', '输出块表', '返回码', '记录类型']
# 任务3 = 前 5 条（导出事件表/整理模型消息/退出码/接收参数/非空块）
# 任务4 = 后 5 条（外部命令/排序依据/输出块表/返回码/记录类型）
# 用法：python <本脚本> [t3|t4|all]   （缺省 all）
SCOPE = (sys.argv[1] if len(sys.argv) > 1 else 'all').lower()
if SCOPE == 't3':
    ENTRIES = ENTRIES[:5]
elif SCOPE == 't4':
    ENTRIES = ENTRIES[5:]

PATTERNS = [ROOT + '/lightharness/examples/**/*.light',
            ROOT + '/lightharness/src/**/*.light',
            ROOT + '/lightharness/tests/**/*.light',
            ROOT + '/light-merge/examples/**/*.light',
            ROOT + '/light-merge/stdlib/**/*.light',
            ROOT + '/light-merge/bootstrap/**/*.light',
            ROOT + '/light-merge/src/**/*.light',
            ROOT + '/light-merge/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
READ = {f: open(f, encoding='utf-8', errors='replace').read() for f in CORPUS}


def build_variant(tag, remove):
    """从 src/lexer.py 生成移除 remove 中整串的变体模块，返回模块名。"""
    lines = open(SRC, encoding='utf-8').read().splitlines(keepends=True)
    i0 = next(i for i, l in enumerate(lines)
              if l.strip() == '_P0A_MERGE_WHOLE = frozenset({')
    i1 = next(i for i in range(i0 + 1, len(lines)) if lines[i].strip() == '})')
    import re
    text = ''.join(lines[i0:i1 + 1])
    dropped = []
    for e in remove:
        pat = "'" + e + "'"
        assert text.count(pat) == 1, (tag, e, text.count(pat))
        new = re.sub(r"'%s'\s*,\s*" % e, '', text, count=1)
        if new == text:
            new = re.sub(r",\s*'%s'" % e, '', text, count=1)
        assert new != text, (tag, e)
        text, _ = re.subn(pat, pat, new, count=1)
        dropped.append(e)
    assert sorted(dropped) == sorted(remove), (tag, dropped, remove)
    lines[i0:i1 + 1] = [text]
    name = '_r32_var_' + tag
    path = os.path.join(LH, name + '.py')
    open(path, 'w', encoding='utf-8').write(''.join(lines))
    mod = importlib.import_module(name)
    mw = mod.Lexer._P0A_MERGE_WHOLE
    assert not (set(remove) & set(mw)), (tag, '未删净')
    return name, mod, len(mw)


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False).encode()).hexdigest()


def seqs_of(mod):
    out = {}
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        try:
            toks = mod.Lexer(READ[f], deterministic=True).tokenize()
            out[rel] = [(t.type.name, t.value) for t in toks
                        if t.type.name not in ('EOF', 'NEWLINE')]
        except Exception as e:
            out[rel] = ['ERR:' + type(e).__name__]
    return out


def main():
    base_mod = importlib.import_module('lexer')
    base = seqs_of(base_mod)
    base_mw = sorted(base_mod.Lexer._P0A_MERGE_WHOLE)
    print('语料文件数：%d   基线 _P0A_MERGE_WHOLE(%d)=%s' % (
        len(CORPUS), len(base_mw), base_mw))
    print('基线 token 总数：%d' % sum(len(s) for s in base.values()))
    print()

    removable, keepers = [], []
    for e in ENTRIES:
        t0 = time.time()
        tag = 'e%d' % ENTRIES.index(e) if SCOPE == 'all' else '%s%d' % (SCOPE, ENTRIES.index(e))
        name, mod, n = build_variant(tag, {e})
        cur = seqs_of(mod)
        changed = [r for r in base if sha(cur[r]) != sha(base[r])]
        err = {r for r in cur if len(cur[r]) == 1 and cur[r][0].startswith('ERR:')}
        base_err = {r for r in base if len(base[r]) == 1 and base[r][0].startswith('ERR:')}
        new_err = sorted(err - base_err)
        ok = not changed and not new_err
        (removable if ok else keepers).append(e)
        print('G1 %-8s %-8s 变化文件=%-3d 新增错误=%-2d  %.1fs  %s'
              % (e, '通过' if ok else '失败', len(changed), len(new_err),
                 time.time() - t0,
                 ('' if ok else '  例: ' + ', '.join(changed[:3]))))
    print()
    print('G1 通过（可删候选 %d）：%s' % (len(removable), removable))
    print('G1 失败（真护栏 %d）：%s' % (len(keepers), keepers))

    if removable:
        t0 = time.time()
        name, mod, n = build_variant(SCOPE + '_union', removable)
        cur = seqs_of(mod)
        changed = [r for r in base if sha(cur[r]) != sha(base[r])]
        err = {r for r in cur if len(cur[r]) == 1 and cur[r][0].startswith('ERR:')}
        base_err = {r for r in base if len(base[r]) == 1 and base[r][0].startswith('ERR:')}
        print()
        print('并集删除(%d 条→剩 %d 条) 变化文件=%d 新增错误=%d  %.1fs'
              % (len(removable), n, len(changed), len(err - base_err), time.time() - t0))
        if changed:
            for r in changed[:20]:
                print('   ', r)
        else:
            print('✅ 并集删除后全语料 token 零变化')
        json.dump({'scope': SCOPE, 'removable': removable, 'keepers': keepers,
                   'union_changed': changed,
                   'final_merge_whole': sorted(mod.Lexer._P0A_MERGE_WHOLE)},
                  open(os.path.join(LH, '_r32_%s_g1_结果.json' % SCOPE), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
