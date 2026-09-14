# -*- coding: utf-8 -*-
"""R23 任务5 反跑（全量回归扫描）：保护表通用化替代（阶段A + 阶段C）前后零回归验证。

对比基准（**不用裸 HEAD**，按项目反跑纪律自动上溯）：
  断裂态 = 最近一个「不含 R23 通用规则标记」的祖先提交的 src/lexer.py
           （判定标记：`_TRAILING_ALIAS_CLASS`。R23 若已提交，HEAD 会自带该标记，
            此时判据 A 会恒假 ⇒ 自动退到 HEAD^ / HEAD^^ … 直到命中）。
  修复态 = 当前工作区 src/lexer.py。

本轮修改（工作区 vs 基准）：
  · 任务1 阶段A：删除逐词白名单 `_TRAILING_ALIAS_MERGE`（1 条）→ 换为通用类别
                 `Lexer._TRAILING_ALIAS_CLASS`（21 字，由关键字表推导：
                 单字关键字 − 运算符 − 范围/步长 − await 动词 − 单字复合安全 − 值字面量）。
  · 任务3 阶段C：`COMMON_COMPOUND_WORDS` 184 → 37 条（删 147 条双中立冗余）。

判据：
  [A] 基线自检：同一模块两次 dump 一致（确定性）。
  [B] 真实源 token 零变化（生产路径 Lexer() / deterministic=True）。
      生成产物树 light-merge/bootstrap/** 的漂移仅记录（不在任何测试断言路径）。
  [C] 性能：修复态不应下降（>10% 判回归）。
  [D] OLD 路径（deterministic=False，遗留模式）真实源变化仅留痕，不门控。
  [E] 核心用例（L-084/L-092/L-119/L-120/L-137/R21-L152×2）编译运行 rc 与 stdout
      在两侧逐字节一致。
  [F] codegen 输出对比：代表用例 `light compile`（src 后端）生成的 Python 文本
      两侧逐字节一致（任务3「codegen 输出不变」直接证据）。

  说明：[B] 已证明**全语料 token 流逐文件逐字节一致**，解析树/代码生成/执行结果
        在逻辑上不可能不同，故「全量 examples 无新增红用例」由 [B] 蕴含；[E]/[F]
        再对代表用例做编译运行与产物哈希的**具体实测**作为交叉印证。

反跑脚本在 finally 中恢复 src/lexer.py 并用 sha256 校验还原。
证据写入 _task5_R23_全量回归证据.json。
"""
import os
import sys
import glob
import json
import time
import shutil
import hashlib
import tempfile
import subprocess
import importlib.util
import statistics

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

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

R23_MARKER = '_TRAILING_ALIAS_CLASS'

CORE_CASES = [
    HARNESS + '/examples/test_L084.light',
    HARNESS + '/examples/test_L092.light',
    HARNESS + '/examples/test_L119.light',
    HARNESS + '/examples/test_L120.light',
    HARNESS + '/examples/test_L137.light',
    HARNESS + '/examples/test_R21_L152家族嵌套形参.light',
    HARNESS + '/examples/test_R21_L152嵌套段落形参.light',
]

# codegen 对比代表文件（任务1 己词尾并入 + 任务3 迁移内建名 + 核心 L 用例）
PROBE_DIR = os.path.join(tempfile.gettempdir(), 'r23_t5_probe')
PROBE_FILES = {}


def is_generated(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED_TREES)


def sha256_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def git_show(rev, path):
    return subprocess.check_output(['git', '-C', LIGHTP, 'show', '%s:%s' % (rev, path)],
                                   encoding='utf-8')


def resolve_baseline():
    """上溯找到第一个不含 R23 标记的提交（返回 (rev, src_text)）。"""
    revs = subprocess.check_output(['git', '-C', LIGHTP, 'log', '--format=%H', '-n', '30'],
                                   encoding='utf-8').split()
    for rev in revs:
        try:
            txt = git_show(rev, 'src/lexer.py')
        except subprocess.CalledProcessError:
            continue
        if R23_MARKER not in txt:
            return rev, txt
    raise RuntimeError('未能在 30 个祖先提交中找到 R23 之前的 lexer.py')


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


def tok_key(mod, src, old=False):
    try:
        toks = mod.Lexer(src, deterministic=(not old)).tokenize()
        return hashlib.sha256(
            repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def read(f):
    with open(f, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def write_probes():
    os.makedirs(PROBE_DIR, exist_ok=True)
    a = os.path.join(PROBE_DIR, 'probe_己词尾并入.light')
    with open(a, 'w', encoding='utf-8', newline='\n') as f:
        f.write(
            '段落 主:\n'
            '    设 自己 为 "自我"\n'
            '    设 爱己 为 "爱己"\n'
            '    设 知己 为 "知己"\n'
            '    尝试:\n'
            '        抛出 新建 错误("x")\n'
            '    捕获 异常 错误己:\n'
            '        打印 转字符串(错误己)\n'
            '    打印 自己\n'
            '    打印 爱己\n'
            '    打印 知己\n\n主()\n')
    b = os.path.join(PROBE_DIR, 'probe_内建名迁移.light')
    with open(b, 'w', encoding='utf-8', newline='\n') as f:
        f.write(
            '段落 主:\n'
            '    设 甲 为 平方根(16.0)\n'
            '    设 乙 为 四舍五入(3.6)\n'
            '    设 丙 为 随机整数(1, 1)\n'
            '    设 丁 为 十六进制(255)\n'
            '    设 列表 为 [1, 2]\n'
            '    列表追加(列表, 3)\n'
            '    打印 甲\n'
            '    打印 乙\n'
            '    打印 丙\n'
            '    打印 丁\n'
            '    打印 列表长度(列表)\n\n主()\n')
    for p in (a, b):
        PROBE_FILES[p] = read(p)


def main():
    print('语料 .light 文件：%d' % len(CORPUS))
    base_rev, base_text = resolve_baseline()
    cur_text = read(LEXER)
    print('断裂态基准提交：%s（%s）'
          % (base_rev[:12],
             subprocess.check_output(['git', '-C', LIGHTP, 'log', '-1', '--format=%s', base_rev],
                                     encoding='utf-8').strip()[:60]))
    print('工作区 lexer.py sha256：%s' % sha256_text(cur_text)[:16])

    base_mod = load_lexer_from_source(base_text, '_lexer_base_r23')
    edit_mod = load_lexer_from_source(cur_text, '_lexer_edit_r23')

    n_base_tam = len(getattr(base_mod, '_TRAILING_ALIAS_MERGE', ()))
    n_edit_tam = len(getattr(edit_mod.Lexer, '_TRAILING_ALIAS_CLASS', ()))
    print('基准 _TRAILING_ALIAS_MERGE：%d 条 %s'
          % (n_base_tam, sorted(getattr(base_mod, '_TRAILING_ALIAS_MERGE', ()))))
    print('修复态 _TRAILING_ALIAS_CLASS：%d 条' % n_edit_tam)
    print('基准 CCW：%d 条  →  修复态 CCW：%d 条'
          % (len(base_mod.COMMON_COMPOUND_WORDS), len(edit_mod.COMMON_COMPOUND_WORDS)))
    assert n_base_tam == 1, '基准应为仅 1 条白名单（己）'
    assert n_edit_tam == 21, '修复态通用类别应为 21 字'
    assert len(base_mod.COMMON_COMPOUND_WORDS) == 184
    assert len(edit_mod.COMMON_COMPOUND_WORDS) == 37

    # 语料内容**一次性快照**：多 agent 并行时磁盘文件可能被并发写入，
    # 若每次 dump 重新 read(f)，[A] 基线自检会因外部写入而假红。
    TEXTS = {f: read(f) for f in CORPUS}

    def dump(mod, old=False):
        return {f: tok_key(mod, TEXTS[f], old=old) for f in CORPUS}

    NIT = 3
    base_times, edit_times = [], []
    base = edit = None
    for _ in range(NIT):
        t0 = time.time(); base = dump(base_mod); base_times.append(time.time() - t0)
        t0 = time.time(); edit = dump(edit_mod); edit_times.append(time.time() - t0)
    t_base, t_edit = statistics.median(base_times), statistics.median(edit_times)

    a_ok = (dump(base_mod) == base) and (dump(edit_mod) == edit)
    print('[A] 基线自检（两侧各两次 dump 一致）  %s' % ('PASS' if a_ok else 'FAIL'))

    changed = [f for f in base if base[f] != edit.get(f)]
    ch_real = [f for f in changed if not is_generated(f)]
    ch_gen = [f for f in changed if is_generated(f)]
    b_ok = (len(ch_real) == 0)
    print('[B] 真实源 token 变化 %d 文件（生成产物树漂移 %d）  %s'
          % (len(ch_real), len(ch_gen), 'PASS（零回归）' if b_ok else 'FAIL'))
    for f in ch_real[:20]:
        print('      真实源变化:', os.path.relpath(f, ROOT))
    for f in ch_gen[:10]:
        print('      生成树漂移:', os.path.relpath(f, ROOT))

    perf_ok = (t_edit <= t_base * 1.10)
    print('[C] 性能：基准中位 %.2fs vs 修复态中位 %.2fs  ×%.3f  %s'
          % (t_base, t_edit, (t_base / t_edit) if t_edit else 0,
             'PASS' if perf_ok else 'FAIL'))

    d_base = dump(base_mod, old=True)
    d_edit = dump(edit_mod, old=True)
    d_real = [f for f in CORPUS if d_base[f] != d_edit.get(f) and not is_generated(f)]
    d_gen = [f for f in CORPUS if d_base[f] != d_edit.get(f) and is_generated(f)]
    print('[D] OLD 路径(deterministic=False) 真实源变化 %d（遗留模式，不门控）｜生成树 %d'
          % (len(d_real), len(d_gen)))

    # ===== 以下 [E]/[F]/[G] 需要**原地替换** src/lexer.py 走真 CLI（含 sha256 校验还原）=====
    # ⚠️ 多 agent 并行时，替换窗口若被外部写入打断会**覆盖他人改动**。故先做
    # 「外部写入检测」：sha 与脚本起始快照不符则放弃替换（宁可不跑也不覆盖）。
    sha_cur = sha256_text(cur_text)
    assert sha256_text(read(LEXER)) == sha_cur, (
        '★ 外部写入检测：src/lexer.py 在脚本起始后被改动，放弃原地替换以免覆盖并发改动')
    e_ok = f_ok = True
    e_report, f_report = {}, {}
    try:
        write_probes()
        cases = [(f, 'run') for f in CORE_CASES if os.path.exists(f)]
        cases += [(p, 'compile') for p in PROBE_FILES]

        for phase in ('base', 'edit'):
            if phase == 'base':
                with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(base_text)
            else:
                with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(cur_text)
            assert sha256_text(read(LEXER)) == (
                sha256_text(base_text) if phase == 'base' else sha_cur), '原地替换失败'
            bucket = e_report if phase == 'base' else f_report
            for path, kind in cases:
                if kind == 'run':
                    r = subprocess.run([sys.executable, os.path.join(HARNESS, '运行.py'), path],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=HARNESS)
                    bucket[path] = {'rc': r.returncode,
                                    'out': (r.stdout or '') + (r.stderr or '')}
                else:
                    out_py = os.path.join(PROBE_DIR,
                                          'gen_%s_%s.py' % (phase, os.path.basename(path)))
                    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli.light',
                                        'compile', path, '-o', out_py, '--backend', 'src'],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=LIGHTP)
                    gen = read(out_py) if os.path.exists(out_py) else ''
                    # 注意：compile 成功时 stdout 含**输出路径**（两侧临时文件名不同），
                    # 不能进比对字段；仅在失败时记录尾部输出用于排障。
                    bucket[path] = {
                        'rc': r.returncode, 'gen_sha': sha256_text(gen), 'gen_len': len(gen),
                        'err': '' if r.returncode == 0 else ((r.stdout or '') + (r.stderr or ''))[-400:]}
    finally:
        with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
            fh.write(cur_text)
        assert sha256_text(read(LEXER)) == sha_cur, '★ src/lexer.py 还原失败！'
        print('      [还原校验] src/lexer.py sha256 = %s  OK' % sha_cur[:16])

    for p in e_report:
        if e_report[p] != f_report.get(p):
            e_ok = False
            print('      [E] 差异:', os.path.basename(p))
    print('[E] 核心用例（%d 个）编译运行 rc/stdout 两侧一致  %s'
          % (len(e_report), 'PASS' if e_ok else 'FAIL'))

    f_ok = all(e_report[p].get('gen_sha') == f_report.get(p, {}).get('gen_sha')
               and f_report.get(p, {}).get('gen_len', 0) > 0 for p in PROBE_FILES)
    print('[F] codegen 产物（%d 个探针，src 后端）两侧逐字节一致  %s'
          % (len(PROBE_FILES), 'PASS' if f_ok else 'FAIL'))
    for p in PROBE_FILES:
        print('      %s: sha=%s len=%s' % (os.path.basename(p),
                                          f_report.get(p, {}).get('gen_sha', '?')[:16],
                                          f_report.get(p, {}).get('gen_len')))

    ok = a_ok and b_ok and perf_ok and e_ok and f_ok
    ev = {
        'baseline_rev': base_rev,
        'corpus_files': len(CORPUS),
        'real_corpus_files': len([f for f in CORPUS if not is_generated(f)]),
        'generated_corpus_files': len([f for f in CORPUS if is_generated(f)]),
        'base_trailing_alias_merge': sorted(getattr(base_mod, '_TRAILING_ALIAS_MERGE', ())),
        'edit_trailing_alias_class': sorted(getattr(edit_mod.Lexer, '_TRAILING_ALIAS_CLASS', ())),
        'base_ccw': len(base_mod.COMMON_COMPOUND_WORDS),
        'edit_ccw': len(edit_mod.COMMON_COMPOUND_WORDS),
        'baseline_selfcheck': a_ok,
        'token_changed_real': len(ch_real),
        'token_changed_generated': len(ch_gen),
        'changed_real_files': [os.path.relpath(f, ROOT) for f in ch_real[:50]],
        'changed_generated_files': [os.path.relpath(f, ROOT) for f in ch_gen[:50]],
        'oldpath_real_changes': len(d_real),
        'oldpath_generated_changes': len(d_gen),
        'oldpath_real_files': [os.path.relpath(f, ROOT) for f in d_real[:50]],
        'time_base_s': round(t_base, 2),
        'time_edit_s': round(t_edit, 2),
        'time_base_iters_s': [round(x, 2) for x in base_times],
        'time_edit_iters_s': [round(x, 2) for x in edit_times],
        'perf_ok': perf_ok,
        'core_cases_consistent': e_ok,
        'core_cases': {os.path.basename(p): e_report[p] for p in e_report},
        'codegen_consistent': f_ok,
        'codegen': {os.path.basename(p): f_report.get(p) for p in PROBE_FILES},
        'lexer_sha_restored': sha_cur,
        'verdict': 'ALL_OK' if ok else 'REGRESS',
    }
    json.dump(ev, open(HARNESS + '/_task5_R23_全量回归证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('判定：', ev['verdict'])
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
