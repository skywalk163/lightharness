# -*- coding: utf-8 -*-
"""R37 任务5：代理循环统一（重命名）性能对比 + 改动文件 token 零变化取证。

结论预期：本轮为**内容保持的重命名**（git mv 不改内容；4 个 stdlib 文件的 comment
微调不改 token），故 tokenize 零变化、性能按构造不变。本脚本给出实测数据佐证。
"""
import os, sys, glob, time, subprocess, statistics

ROOT = os.path.dirname(os.path.abspath(__file__))
LM = os.path.join(ROOT, '..', 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
import lexer

CORPUS_ROOTS = [
    os.path.join(ROOT, 'src'), os.path.join(ROOT, 'examples'), os.path.join(ROOT, 'stdlib'),
    os.path.join(LM, 'examples'), os.path.join(LM, 'src', 'stdlib'),
]


def collect():
    files = []
    for r in CORPUS_ROOTS:
        files += glob.glob(os.path.join(r, '**', '*.light'), recursive=True)
    return files


def _sig(text):
    # 与项目反跑口径一致：过滤 EOF/NEWLINE（注释剥离、行尾记号不计语义）
    return [(x.type.name, x.value) for x in lexer.Lexer(text, deterministic=True).tokenize()
            if x.type.name not in ('EOF', 'NEWLINE')]


def tok(path):
    return _sig(open(path, encoding='utf-8-sig', errors='replace').read())


def head_bytes(rel):
    """取 HEAD 版本文件内容（相对 lightharness 的路径）。"""
    r = subprocess.run(['git', 'show', f'HEAD:{rel}'], cwd=ROOT, capture_output=True)
    return r.stdout.decode('utf-8') if r.returncode == 0 else None


def tok_text(text):
    return _sig(text)


def main():
    files = collect()
    chars = sum(len(open(f, encoding='utf-8-sig', errors='replace').read()) for f in files)
    print(f'=== 性能对比（统一后）===')
    print(f'语料：{len(files)} 文件 / {chars} 字符')
    ts = []
    for i in range(3):
        t0 = time.perf_counter()
        for f in files:
            tok(f)
        ts.append(time.perf_counter() - t0)
    print(f'3 轮 tokenize 耗时：' + ', '.join(f'{t*1000:.0f}ms' for t in ts))
    print(f'均值 {statistics.mean(ts)*1000:.0f} ms/轮（统一前为内容字节相同的同一负载，Δ 按构造为 0）')

    print()
    print('=== 改动文件 token 零变化取证（当前 vs HEAD）===')
    checks = [
        ('stdlib/代理运行时.light', 'stdlib/代理循环.light'),   # 重命名：新名 vs 旧名
        ('stdlib/事件总线.light', 'stdlib/事件总线.light'),
        ('stdlib/代理工具集.light', 'stdlib/代理工具集.light'),
        ('stdlib/并发.light', 'stdlib/并发.light'),
        ('stdlib/重试.light', 'stdlib/重试.light'),
    ]
    ok = True
    for cur_rel, head_rel in checks:
        cur = tok(os.path.join(ROOT, cur_rel))
        hb = head_bytes(head_rel)
        if hb is None:
            print(f'  ✗ {cur_rel}: HEAD 无 {head_rel}')
            ok = False
            continue
        ref = tok_text(hb)
        same = (cur == ref)
        ok = ok and same
        print(f'  {"✓" if same else "✗"} {cur_rel}  vs  HEAD:{head_rel}  → token {"一致" if same else "不一致"} ({len(cur)} tokens)')
    print()
    print('判定：' + ('全部 token 一致 → 零回归' if ok else '存在 token 变化 → 需排查'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
