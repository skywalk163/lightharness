# -*- coding: utf-8 -*-
"""R33 任务1-4 反跑引擎：_P0A_NEVER_SPLIT 4 字逐条隔离验证（G1 语料判据）。

对 _P0A_NEVER_SPLIT 中每个字构建「仅移除该字」的变体 lexer 模块，跑全语料
tokenize，与基线（当前工作区 lexer.py）逐文件比对 token 序列 sha256。
  变化文件数 = 0  → G1 通过（该字可删候选）
  变化文件数 > 0  → G1 失败（真护栏，保留）
另跑「全部通过者并集」变体，验证合并删除仍零变化。

口径：lightharness + light-merge 全部 .light，deterministic=True，过滤 EOF/NEWLINE。
变体由 _r33_lexer_head.py（当前 lexer.py 快照）行级手术生成，不触碰真实 lexer.py。
撤字使该字进入 F → _TRAILING_ALIAS_CLASS → _P0A_HEAD_MERGE_SINGLE(HM)，会触发
L3881「HM == 22 字」自校验；该断言为设计守卫（不影响 token 流），隔离态下合法
放宽（撤字入 HM 属预期副作用，由 DUAL/词尾并入兜底），故变体生成时中性化该断言。
"""
import glob
import hashlib
import importlib
import json
import os
import sys
import time

ROOT = r'G:/dswork/duan-light-merge'
SRC = os.path.join(ROOT, 'lightharness', '_r33_lexer_head.py')
LH = os.path.join(ROOT, 'lightharness')
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
sys.path.insert(0, LH)

CHARS = ['模', '步', '至', '到']
# ASCII 标签（避免非 ASCII 模块名导入问题）
TAG = {'模': 'mo', '步': 'bu', '至': 'zhi', '到': 'dao'}

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


def remove_char_from_line(line, c):
    new = line.replace("'%s', " % c, '', 1)
    if new != line:
        return new
    new = line.replace(", '%s'" % c, '', 1)
    if new != line:
        return new
    return line.replace("'%s'" % c, '', 1)


def neutralize_hm_assert(lines):
    """移除 L3881 的 HM 硬自校验（隔离态下撤字入 HM 属预期副作用）。"""
    out = []
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.strip().startswith('assert _P0A_HEAD_MERGE_SINGLE == ('):
            i += 1
            while i < len(lines) and not lines[i].rstrip().endswith('))'):
                i += 1
            i += 1  # 跳过闭合行
            out.append('# _R33 isolation: HM 自校验在撤 NEVER_SPLIT 字时合法放宽'
                       '（该字入 HM 属预期副作用，由 DUAL/词尾并入兜底，不影响 token 流）\n')
            continue
        out.append(l)
        i += 1
    return out


def build_variant(tag, remove):
    """从 SRC 生成移除 remove(单字) 的变体模块，返回 (name, mod)。"""
    lines = open(SRC, encoding='utf-8').read().splitlines(keepends=True)
    # 1) 行级手术：_P0A_NEVER_SPLIT = frozenset({'模', '步', '至', '到'})
    i0 = next(i for i, l in enumerate(lines)
              if l.strip().startswith('_P0A_NEVER_SPLIT = frozenset('))
    assert lines[i0].count("'%s'" % remove) == 1, (tag, remove)
    lines[i0] = remove_char_from_line(lines[i0], remove)
    assert "'%s'" % remove not in lines[i0], (tag, remove, lines[i0])
    # 2) 中性化 HM 硬自校验
    lines = neutralize_hm_assert(lines)
    # 3) 写模块并导入
    name = '_r33_var_' + tag
    path = os.path.join(LH, name + '.py')
    open(path, 'w', encoding='utf-8').write(''.join(lines))
    # 清理旧缓存
    sys.modules.pop(name, None)
    mod = importlib.import_module(name)
    ns = mod.Lexer._P0A_NEVER_SPLIT
    assert remove not in ns, (tag, '未删净', sorted(ns))
    return name, mod


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
    base_ns = sorted(base_mod.Lexer._P0A_NEVER_SPLIT)
    print('语料文件数：%d   基线 _P0A_NEVER_SPLIT(%d)=%s'
          % (len(CORPUS), len(base_ns), base_ns))
    print('基线 token 总数：%d' % sum(len(s) for s in base.values()))
    base_err = {r for r in base if len(base[r]) == 1 and base[r][0].startswith('ERR:')}
    print('基线即失败文件数（排除）：%d' % len(base_err))
    print()

    removable, keepers = [], []
    detail = {}
    for c in CHARS:
        t0 = time.time()
        name, mod = build_variant(TAG[c], c)
        cur = seqs_of(mod)
        changed = [r for r in base if sha(cur[r]) != sha(base[r])]
        changed = [r for r in changed if r not in base_err]
        new_err = sorted({r for r in cur if len(cur[r]) == 1
                          and cur[r][0].startswith('ERR:')} - base_err)
        ok = not changed and not new_err
        (removable if ok else keepers).append(c)
        detail[c] = {'changed': changed, 'new_err': new_err}
        print('G1 %-3s %-6s 变化文件=%-3d 新增错误=%-2d  %.1fs  %s'
              % (c, '通过' if ok else '失败', len(changed), len(new_err),
                 time.time() - t0,
                 ('' if ok else '  例: ' + ', '.join(changed[:3]))))
        if changed:
            for r in changed[:10]:
                # 显示 token 差异首处
                b, k = base[r], cur[r]
                diff = next((i for i in range(min(len(b), len(k)))
                             if b[i] != k[i]), min(len(b), len(k)))
                print('        %s  @%d  base=%s  var=%s'
                      % (r, diff, b[diff] if diff < len(b) else '∅',
                         k[diff] if diff < len(k) else '∅'))

    print()
    print('G1 通过（可删候选 %d）：%s' % (len(removable), removable))
    print('G1 失败（真护栏 %d）：%s' % (len(keepers), keepers))

    if removable:
        t0 = time.time()
        # union 变体：对快照一次性移除全部 removable（build_variant 一次只撤一字）
        lines = open(SRC, encoding='utf-8').read().splitlines(keepends=True)
        i0 = next(i for i, l in enumerate(lines)
                  if l.strip().startswith('_P0A_NEVER_SPLIT = frozenset('))
        for c in removable:
            lines[i0] = remove_char_from_line(lines[i0], c)
        lines = neutralize_hm_assert(lines)
        name = '_r33_var_union'
        open(os.path.join(LH, name + '.py'), 'w', encoding='utf-8').write(''.join(lines))
        sys.modules.pop(name, None)
        mod = importlib.import_module(name)
        cur = seqs_of(mod)
        changed = [r for r in base if sha(cur[r]) != sha(base[r]) and r not in base_err]
        new_err = sorted({r for r in cur if len(cur[r]) == 1
                          and cur[r][0].startswith('ERR:')} - base_err)
        print()
        print('并集删除(%s→剩 %d 字) 变化文件=%d 新增错误=%d  %.1fs'
              % (removable, len(mod.Lexer._P0A_NEVER_SPLIT),
                 len(changed), len(new_err), time.time() - t0))
        for r in changed[:20]:
            print('   ', r)
        if not changed and not new_err:
            print('✅ 并集删除后全语料 token 零变化')
        detail['union'] = {'removable': removable,
                           'changed': changed, 'new_err': new_err,
                           'final': sorted(mod.Lexer._P0A_NEVER_SPLIT)}

    json.dump({'base_ns': base_ns, 'removable': removable, 'keepers': keepers,
               'detail': {c: {'changed': d['changed'], 'new_err': d['new_err']}
                          for c, d in detail.items() if c in CHARS}},
              open(os.path.join(LH, '_antirun_r33_t1234_G1结果.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=1)
    print()
    print('G1 结果已写 _antirun_r33_t1234_G1结果.json')


if __name__ == '__main__':
    main()
