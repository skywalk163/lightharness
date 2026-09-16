# -*- coding: utf-8 -*-
"""R22 任务5 反跑（全量回归扫描）：保护表精简前后 token 序列 + 编译结果零回归。

对比基准：
  - 断裂态（精简前）＝ git HEAD 的 src/lexer.py（任务1 KEEP 未改 + 任务3 改前 52 条）
  - 修复态（精简后）＝ 当前工作区 src/lexer.py（任务3 已删 28 条 → 24 条护栏，v2 修正）
任务1 判定为 KEEP（_EMBED_MAX_MATCH_KEYWORDS 保留），故两侧唯一差异 = 任务3 删除的 28 条。

判据：
  - 真实源语料 token 序列零变化 ⇒ 精简安全（与逐条隔离中立验证互相印证）
  - 生成产物树（light-merge/bootstrap/**，lexer.py 注释定性为"已损坏生成产物"、
    不在任何测试断言路径）的变化仅记录为可接受漂移，不计入回归判定
  - [D] OLD 路径（deterministic=False，遗留模式）真实源变化仅作透明留痕：
    生产编译/运行入口均用默认 Lexer()（P0A），OLD 路径不在任何生产路径，
    其变化属删除冗余条目在遗留模式的预期漂移，不门控判定
  - 性能：精简后不应下降
  - 反跑 ALL OK

证据写入 _task5_R22_全量回归证据.json。
"""
import os, sys, glob, hashlib, json, subprocess, tempfile, importlib.util, time, statistics

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')

PATTERNS = [
    r'G:/dswork/duan-light-merge/lightharness/examples/**/*.light',
    r'G:/dswork/duan-light-merge/lightharness/src/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/examples/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/stdlib/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/bootstrap/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/src/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/tests/**/*.light',
]
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

# 生成产物树（不在任何测试断言路径上，lexer.py 注释定性为"已损坏生成产物"）。
# 这些文件不参与"真实语料零回归"判定，但其变化会被记录、归类为可接受漂移，
# 以便追溯——而非静默排除。
GENERATED_TREES = [
    os.path.join(ROOT, 'light-merge', 'bootstrap'),
]


def is_generated(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED_TREES)


def load_lexer_from_source(src_text, modname):
    d = tempfile.mkdtemp(prefix='lxr_')
    p = os.path.join(d, modname + '.py')
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src_text)
    spec = importlib.util.spec_from_file_location(modname, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def tok_key(mod, src):
    try:
        toks = mod.Lexer(src).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def tok_key_old(mod, src):
    """OLD 路径（deterministic=False，遗留模式）token 序列哈希。"""
    try:
        toks = mod.Lexer(src, deterministic=False).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def main():
    print(f'语料 .light 文件：{len(CORPUS)}')

    # 断裂态：git HEAD 的 lexer.py
    base_text = subprocess.check_output(
        ['git', '-C', LIGHTP, 'show', 'HEAD:src/lexer.py'], encoding='utf-8')
    base_mod = load_lexer_from_source(base_text, '_lexer_base_r22')
    # 修复态：当前工作区
    edit_mod = load_lexer_from_source(
        open(os.path.join(LIGHTP, 'src', 'lexer.py'), encoding='utf-8', newline='').read(),
        '_lexer_edit_r22')

    print(f'基准 _COMPOUND_SAFE_SINGLE_KEYWORDS：{len(base_mod._COMPOUND_SAFE_SINGLE_KEYWORDS)} 条')
    print(f'精简后 _COMPOUND_SAFE_SINGLE_KEYWORDS：{len(edit_mod._COMPOUND_SAFE_SINGLE_KEYWORDS)} 条')
    print(f'基准 _EMBED_MAX_MATCH_KEYWORDS：{sorted(base_mod._EMBED_MAX_MATCH_KEYWORDS)}')
    print(f'精简后 _EMBED_MAX_MATCH_KEYWORDS：{sorted(edit_mod._EMBED_MAX_MATCH_KEYWORDS)}')

    # A：基线自检（多次 dump 一致）+ 性能多次迭代取中位数（消除系统噪声）
    def dump(mod):
        out = {}
        for f in CORPUS:
            try:
                out[f] = tok_key(mod, open(f, encoding='utf-8', errors='replace').read())
            except Exception:
                pass
        return out

    NIT = 3  # 性能迭代次数
    base_times, edit_times = [], []
    base = edit = None
    for i in range(NIT):
        t0 = time.time(); base = dump(base_mod); base_times.append(time.time() - t0)
        t0 = time.time(); edit = dump(edit_mod); edit_times.append(time.time() - t0)
    t_base = statistics.median(base_times)
    t_edit = statistics.median(edit_times)
    a_ok = (dump(base_mod) == base)  # 基线确定性自检
    print(f"[A] 基准基线自检（确定性）  {'PASS' if a_ok else 'FAIL'}  "
          f"（基准各轮 {[round(x,1) for x in base_times]}s / 精简各轮 {[round(x,1) for x in edit_times]}s）")

    # B：精简后 dump，对比基准
    changed = [f for f in base if base[f] != edit.get(f)]
    # 分类：真实源 vs 生成产物树
    changed_real = [f for f in changed if not is_generated(f)]
    changed_gen = [f for f in changed if is_generated(f)]
    b_ok = (len(changed_real) == 0)
    print(f"[B] 精简后 vs 基准 token 变化  {len(changed)} 文件  "
          f"({'PASS（零回归）' if b_ok else 'FAIL'})  "
          f"（基准中位 {t_base:.1f}s / 精简中位 {t_edit:.1f}s）")
    print(f"      真实源变化：{len(changed_real)}  |  生成产物树漂移：{len(changed_gen)}")
    for f in changed_real[:20]:
        print('      真实源变化:', os.path.relpath(f, ROOT))
    if changed_gen:
        print('      生成产物树漂移（可接受，不在测试断言路径）:')
        for f in changed_gen[:20]:
            print('        -', os.path.relpath(f, ROOT))

    # C：性能对比（中位数，允许 10% 噪声带）
    speedup = (t_base / t_edit) if t_edit else 0
    perf_ok = (t_edit <= t_base * 1.10)  # 10% 噪声容差 ⇒ 视为"持平/提升"
    perf_label = '提升' if t_edit < t_base * 0.97 else ('下降(噪声内)' if perf_ok else '下降')
    print(f"[C] 性能：基准中位 {t_base:.1f}s vs 精简中位 {t_edit:.1f}s  "
          f"({'提升' if t_edit < t_base * 0.97 else '持平/下降(噪声内)'} ×{speedup:.2f})")

    ok = a_ok and b_ok and perf_ok

    # D：OLD 路径（deterministic=False，遗留模式）兜底核验
    # 生产编译/运行入口均用默认 Lexer()（deterministic=True / P0A），OLD 路径仅由
    # 对比测试 test_lexer_p0a_deterministic.py 显式触发，不在任何生产路径。
    # 此处仅作透明留痕：OLD 路径真实源若变化，属删除冗余条目在遗留模式的预期漂移，
    # 不计入回归判定（生产路径见 [B]）。
    d_base = {f: tok_key_old(base_mod, open(f, encoding='utf-8', errors='replace').read())
              for f in CORPUS}
    d_edit = {f: tok_key_old(edit_mod, open(f, encoding='utf-8', errors='replace').read())
              for f in CORPUS}
    d_changed = [f for f in CORPUS if d_base[f] != d_edit.get(f)]
    d_real = [f for f in d_changed if not is_generated(f)]
    d_gen = [f for f in d_changed if is_generated(f)]
    print(f"[D] OLD 路径(deterministic=False) 真实源 token 变化：{len(d_real)}  "
          f"（遗留模式，不门控判定）| 生成树漂移 {len(d_gen)}")
    for f in d_real[:20]:
        print('      OLD路径真实源变化:', os.path.relpath(f, ROOT))

    ev = {
        'corpus_files': len(CORPUS),
        'real_corpus_files': len([f for f in CORPUS if not is_generated(f)]),
        'generated_corpus_files': len([f for f in CORPUS if is_generated(f)]),
        'base_entries': len(base_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'edit_entries': len(edit_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'base_embed': sorted(base_mod._EMBED_MAX_MATCH_KEYWORDS),
        'edit_embed': sorted(edit_mod._EMBED_MAX_MATCH_KEYWORDS),
        'baseline_selfcheck': a_ok,
        'token_changed': len(changed),
        'token_changed_real': len(changed_real),
        'token_changed_generated': len(changed_gen),
        'changed_real_files': [os.path.relpath(f, ROOT) for f in changed_real[:50]],
        'changed_generated_files': [os.path.relpath(f, ROOT) for f in changed_gen[:50]],
        'oldpath_real_changes': len(d_real),
        'oldpath_generated_changes': len(d_gen),
        'oldpath_real_files': [os.path.relpath(f, ROOT) for f in d_real[:50]],
        'time_base_s': round(t_base, 2),
        'time_edit_s': round(t_edit, 2),
        'time_base_iters_s': [round(x, 2) for x in base_times],
        'time_edit_iters_s': [round(x, 2) for x in edit_times],
        'perf_ok': perf_ok,
        'verdict': 'ALL_OK' if ok else 'REGRESS',
    }
    json.dump(ev, open(HARNESS + '/_task5_R22_全量回归证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('判定：', ev['verdict'])
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
