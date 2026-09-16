# -*- coding: utf-8 -*-
"""R32 任务3/4 G3 边界门：逐条边界形态 token 比对（基线 vs 移除该条变体）。

变体模块 _r32_var_e0..e9 由 _antirun_r32_t34_MERGE_WHOLE逐条验证.py 生成，
e_i = 移除 ENTRIES[i] 单条。比对形态：
  F1 整串作变量名     设 X 为 1
  F2 整串作函数名     返回 X(1)
  F3 成员访问         设 r 为 结果.X
  F4 段落名           段落 X:
  F5 传参位置         断言相等(X, 1, "t")
G3 通过条件：4-5 种形态 token 流与基线完全一致。
"""
import importlib
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
sys.path.insert(0, os.path.join(ROOT, 'light-merge', 'src'))
sys.path.insert(0, os.path.join(ROOT, 'lightharness'))

ENTRIES = ['导出事件表', '整理模型消息', '退出码', '接收参数', '非空块',
           '外部命令', '排序依据', '输出块表', '返回码', '记录类型']

base = importlib.import_module('lexer')

FORMS = lambda X: [
    ('F1 变量名',  '设 X 为 1'.replace('X', X)),
    ('F2 函数名',  '返回 X(1)'.replace('X', X)),
    ('F3 成员访问', '设 r 为 结果.X'.replace('X', X)),
    ('F4 段落名',  '段落 X:\n    返回 1\n'.replace('X', X)),
    ('F5 传参',    '断言相等(X, 1, "t")'.replace('X', X)),
]


def tk(mod, src):
    try:
        return [(t.type.name, t.value) for t in
                mod.Lexer(src, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def main():
    print('=== 语料命中扫描（856 文件，含注释行） ===')
    import glob
    pats = [ROOT + p for p in (
        '/lightharness/examples/**/*.light', '/lightharness/src/**/*.light',
        '/lightharness/tests/**/*.light', '/light-merge/examples/**/*.light',
        '/light-merge/stdlib/**/*.light', '/light-merge/bootstrap/**/*.light',
        '/light-merge/src/**/*.light', '/light-merge/tests/**/*.light')]
    corpus = sorted(set(sum((glob.glob(g, recursive=True) for g in pats), [])))
    for e in ENTRIES:
        hits = []
        for f in corpus:
            s = open(f, encoding='utf-8', errors='replace').read()
            n = s.count(e)
            if n:
                hits.append((os.path.relpath(f, ROOT).replace('\\', '/'), n))
        print('%-8s 命中 %d 处 / %d 文件  %s' % (
            e, sum(n for _, n in hits), len(hits),
            hits[:4] if hits else '(语料 0 命中)'))
    print()
    print('=== G3 边界门（基线 vs 移除该条变体） ===')
    verdict = {}
    for i, e in enumerate(ENTRIES):
        mod = importlib.import_module('_r32_var_e%d' % i)
        rows = []
        bad = []
        for tag, src in FORMS(e):
            a, b = tk(base, src), tk(mod, src)
            same = a == b
            rows.append('%s %s' % (tag, '一致' if same else '变化'))
            if not same:
                bad.append((tag, src, a, b))
        verdict[e] = not bad
        print('%-8s %s  %s' % (e, 'G3通过' if not bad else 'G3失败',
                               ' | '.join(rows)))
        for tag, src, a, b in bad:
            print('    [%s] %r' % (tag, src))
            print('      基线: %s' % ' | '.join(f'{k}:{v}' for k, v in a))
            print('      变体: %s' % ' | '.join(f'{k}:{v}' for k, v in b))
    print()
    print('G3 通过：%s' % [e for e in ENTRIES if verdict[e]])
    print('G3 失败：%s' % [e for e in ENTRIES if not verdict[e]])


if __name__ == '__main__':
    main()
