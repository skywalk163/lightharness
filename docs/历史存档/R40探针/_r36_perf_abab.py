# -*- coding: utf-8 -*-
"""R36 任务3：性能 A/B 验证（ABAB 交替，消除系统噪声/顺序偏差）。

对比：
  A = HEAD 版 lexer.py（R35 收口态，R21 闸门3 每次成词都做 `_OPERATOR_KEYWORDS - self._P0A_UNARY_PREFIX_KW` 集合差）
  B = 当前工作树 lexer.py（R36 预计算 `_OPERATOR_KEYWORDS_NO_UNARY_PREFIX` 模块常量）
判据：对全语料 .light 文件反复 tokenize，ABAB 交替取平均，比较每轮耗时。

用法：python _r36_perf_abab.py [轮数]
"""
import sys, os, glob, time, importlib.util, tempfile, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
LIGHT_MERGE_SRC = os.path.join(ROOT, '..', 'light-merge', 'src')

CORPUS_ROOTS = [
    os.path.join(ROOT, 'examples'),
    os.path.join(ROOT, 'src'),
    os.path.join(ROOT, '..', 'light-merge', 'examples'),
    os.path.join(ROOT, '..', 'light-merge', 'src', 'stdlib'),
]


def collect_corpus():
    files = []
    for r in CORPUS_ROOTS:
        files += glob.glob(os.path.join(r, '**', '*.light'), recursive=True)
    texts = []
    for f in files:
        try:
            texts.append(open(f, encoding='utf-8-sig', errors='replace').read())
        except Exception:
            pass
    return texts


def load_lexer_variant(tag, src_text):
    """把给定 lexer.py 源码作为独立模块载入，返回 Lexer 类。"""
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(f'_lex_{tag}', loader=None))
    # 提供稳定模块名避免与已导入冲突
    name = f'_r36_lexer_{tag}'
    spec = importlib.util.spec_from_file_location(name, os.path.join(tempfile.gettempdir(), f'{name}.py'))
    # 直接 exec 源码到新模块命名空间
    import types
    m = types.ModuleType(name)
    m.__dict__['__name__'] = name
    # lexer.py 可能依赖同目录其它模块；把 light-merge/src 加入 sys.path 已由调用方处理
    exec(compile(src_text, f'<{tag}>', 'exec'), m.__dict__)
    return m.Lexer


def round_time(Lexer, texts):
    t0 = time.perf_counter()
    for txt in texts:
        list(Lexer(txt, deterministic=True).tokenize())
    return time.perf_counter() - t0


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    sys.path.insert(0, LIGHT_MERGE_SRC)
    texts = collect_corpus()
    total_chars = sum(len(t) for t in texts)
    print(f'语料：{len(texts)} 文件，{total_chars} 字符，每轮 tokenize 全部')

    head_src = open(os.path.join(ROOT, '..', 'light-merge', 'src', 'lexer.py'),
                    encoding='utf-8-sig').read() if False else None
    # A = HEAD 版（git 快照），B = 当前工作树
    import subprocess
    head_src = subprocess.run(
        ['git', 'show', 'HEAD:src/lexer.py'],
        cwd=os.path.join(ROOT, '..', 'light-merge'),
        capture_output=True).stdout.decode('utf-8')
    cur_src = open(os.path.join(ROOT, '..', 'light-merge', 'src', 'lexer.py'),
                   encoding='utf-8-sig').read()

    LexerA = load_lexer_variant('A_head', head_src)
    LexerB = load_lexer_variant('B_cur', cur_src)

    # 预热
    for L in (LexerA, LexerB):
        round_time(L, texts[:max(1, len(texts) // 5)])

    order = []
    times_a, times_b = [], []
    for i in range(n):
        if i % 2 == 0:
            ta = round_time(LexerA, texts); times_a.append(ta); order.append('A')
        else:
            tb = round_time(LexerB, texts); times_b.append(tb); order.append('B')
    # 交替顺序：偶数轮 A 先，奇数轮 B 先 —— 上面对半，再反向补一轮消除首因
    # 反向轮：B 先 A 后
    for i in range(n):
        if i % 2 == 0:
            tb = round_time(LexerB, texts); times_b.append(tb); order.append('B')
        else:
            ta = round_time(LexerA, texts); times_a.append(ta); order.append('A')

    ma, mb = sum(times_a) / len(times_a), sum(times_b) / len(times_b)
    delta = (mb - ma) / ma * 100
    print(f'顺序: {"".join(order)}')
    print(f'A(HEAD) 平均: {ma*1000:.2f} ms/轮  (n={len(times_a)})')
    print(f'B(预计算)平均: {mb*1000:.2f} ms/轮  (n={len(times_b)})')
    print(f'Δ(B-A): {delta:+.3f}%  （负=预计算更快）')
    # 判定
    if abs(delta) < 1.0:
        print('结论：差异在 ±1% 噪声带内，性能无显著变化（预期回收被噪声淹没，属正常）。')
    elif delta < 0:
        print(f'结论：预计算版更快 {abs(delta):.2f}%，语义等价前提下为净收益。')
    else:
        print(f'结论：预计算版反而慢 {delta:.2f}%，需排查（理论上不该发生）。')


if __name__ == '__main__':
    main()
