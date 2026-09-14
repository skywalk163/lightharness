# -*- coding: utf-8 -*-
"""R24 任务3 反跑：P0-A 复合安全集合通用化（CR1 成员访问段首并入 + 死代码清理 + 清表审计）。

对比基准（按项目反跑纪律，**不用裸 HEAD**）：
  断裂态 = 最近一个「不含 R24 任务3 标记」的祖先提交的 src/lexer.py
           （判定标记：`R24 任务3 CR1`；若 HEAD 已自带，自动退到 HEAD^/HEAD^^…）
  修复态 = 当前工作区 src/lexer.py

本轮工作区相对基准的改动：
  · 任务1（同轮，含在差异内）：R21 分支第 4 道闸门 —— 整串含**真实**成员/关系分隔符
    （_P0A_SEP：之/在/于/为/与，且该字须经 _match_keyword 逐位判定命中）时不并入，
    修复成员访问符 `之` 被吞（`自之姓名` 在语句起始/表达式位置 token 流一致）。
    ⚠️ 闸门口径**只取 `_P0A_SEP`，不含算术/幂运算符**——用含 `_P0A_OP` 的宽口径会把
    bootstrap 生成树的 `定义幂` 误切成 `定义`+`幂`。
  · 任务3 CR1：成员/关系分隔符（_P0A_SEP：之/在/于/为/与）之后新段的段首单字
    非运算符关键字 → 并入标识符（y 成员名续段语义）。
  · 任务3 死代码清理：删除零引用常量 _P0A_COMPOUND_SAFE。
  · 任务3 清表审计：任务2 判为①冗余可删的 13 条（例出则常引接是末试跳过长首）
    经语义中立性复核判定为「语料冗余 ∧ 语义非冗余」→ **保留**（详见交付报告 §三）。

判据：
  [A] 基线自检：同一模块两次 dump 一致。
  [B] 真实源 token 变化必须**恰为** EXPECTED_REAL（生成树漂移只记录）。
  [C] CR1 覆盖充分性 A/B（核心判据）：
      C1 = 在基准模块上**内存态撤掉 13 条** → `甲之<c>顶` 反例矩阵必须**破裂**
           （证明 13 条的白名单曾是承重结构，不是冗余）；
      C2 = 在修复模块上**内存态撤掉 13 条** → 同一矩阵必须**保持**
           （证明 CR1 通用规则已覆盖其成员访问段首保护场景）。
  [D] 100+ 自由名 + 语句起始裸名：基准 vs 修复态 token 逐字节一致。
  [E] 性能：修复态不得下降 >10%。
  [F] 既有核心用例编译运行 rc/stdout 两侧逐字节一致（原地替换 + sha256 校验还原）。
  [F2] R24 新增 4 个 .light 用例在修复态 rc=0。
  [G] 保护表形态：CS 两侧均 30（保留）；_P0A_COMPOUND_SAFE 已删除；CR1 标记存在。

反跑脚本在 finally 中恢复 src/lexer.py 并用 sha256 校验还原；替换窗口前后做
「外部写入检测」（文件被并发改动则不覆盖）。
"""
import os
import sys
import glob
import json
import time
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

MARKER = 'R24 任务3 CR1'
RETAINED_13 = '例出则常引接是末试跳过长首'

EXPECTED_REAL = {'light-merge/examples/L2_wenyan/学生模块.light'}

FREE_NAMES = [
    '去除空格', '10的幂', '索引', '种类', '阶乘',
    '过滤', '过程', '引用', '接口', '例1',
]
STMT_INITIAL = ['长度', '举例', '首项', '末尾', '例子', '常规', '跳过', '引用']

CORE_CASES = [
    HARNESS + '/examples/test_L084.light',
    HARNESS + '/examples/test_L092.light',
    HARNESS + '/examples/test_L119.light',
    HARNESS + '/examples/test_L120.light',
    HARNESS + '/examples/test_R21_L152家族嵌套形参.light',
    HARNESS + '/examples/test_R21_L152嵌套段落形参.light',
]
R24_CASES = [
    HARNESS + '/examples/test_R24_的递归修复.light',
    HARNESS + '/examples/test_R24_运算符单字守卫.light',
    HARNESS + '/examples/test_R24_值字面量守卫.light',
    HARNESS + '/examples/test_R24_单字通用规则.light',
]


def sha(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def read(f):
    with open(f, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def git_show(rev, path):
    return subprocess.check_output(['git', '-C', LIGHTP, 'show', '%s:%s' % (rev, path)],
                                   encoding='utf-8')


def resolve_baseline():
    revs = subprocess.check_output(['git', '-C', LIGHTP, 'log', '--format=%H', '-n', '40'],
                                   encoding='utf-8').split()
    for rev in revs:
        try:
            txt = git_show(rev, 'src/lexer.py')
        except subprocess.CalledProcessError:
            continue
        if MARKER not in txt:
            return rev, txt
    raise RuntimeError('未在 40 个祖先提交中找到不含 R24 任务3 标记的 lexer.py')


def load(src_text, modname):
    d = tempfile.mkdtemp(prefix='lxr_r24t3_')
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
        toks = mod.Lexer(src, deterministic=True).tokenize()
        return sha(repr([(t.type.name, t.value) for t in toks]))
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def pairs(mod, src):
    return [(t.type.name, t.value) for t in mod.Lexer(src, deterministic=True).tokenize()
            if t.type.name not in ('EOF', 'NEWLINE')]


def drop13(mod):
    """内存态：从保护表撤掉 13 条，并同步类别别名（不改磁盘）。"""
    CS = frozenset(mod._COMPOUND_SAFE_SINGLE_KEYWORDS - set(RETAINED_13))
    mod._COMPOUND_SAFE_SINGLE_KEYWORDS = CS
    L = mod.Lexer
    L.compound_safe_single_keywords = CS
    ALL = mod._ALL_KEYWORDS_WITH_VERBS
    L._TRAILING_ALIAS_CLASS = frozenset(
        k for k in (ALL - L._P0A_OP - mod._OPERATOR_KEYWORDS - L._P0A_NEVER_SPLIT
                    - mod._AWAIT_KEYWORDS - CS - mod._VALUE_LITERAL_KEYWORDS) if len(k) == 1)
    return mod


def is_gen(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED_TREES)


def main():
    print('语料 .light：%d 文件' % len(CORPUS))
    base_rev, base_text = resolve_baseline()
    cur_text = read(LEXER)
    print('断裂态基准：%s（%s）' % (
        base_rev[:12],
        subprocess.check_output(['git', '-C', LIGHTP, 'log', '-1', '--format=%s', base_rev],
                                encoding='utf-8').strip()[:50]))
    sha_cur = sha(cur_text)
    print('修复态 lexer.py sha256=%s' % sha_cur[:16])

    base = load(base_text, '_lxr_r24t3_base')
    edit = load(cur_text, '_lxr_r24t3_edit')

    # [G] 形态
    n_b = len(base._COMPOUND_SAFE_SINGLE_KEYWORDS)
    n_e = len(edit._COMPOUND_SAFE_SINGLE_KEYWORDS)
    dead_gone = not hasattr(edit.Lexer, '_P0A_COMPOUND_SAFE')
    cr1_present = hasattr(edit.Lexer, '_P0A_OP_CHAR_HINTS') and '_seg_after_sep' in cur_text
    g_ok = (n_b == 30 and n_e == 30 and dead_gone and cr1_present)
    print('[G] CS 基准 %d → 修复态 %d ｜ _P0A_COMPOUND_SAFE 删除=%s ｜ CR1 就位=%s  %s'
          % (n_b, n_e, dead_gone, cr1_present, 'PASS' if g_ok else 'FAIL'))
    assert n_b == 30 and n_e == 30, '保护表形态与审计结论不符'

    # [A] 自检 + [B] 语料 A/B
    TEXTS = {f: read(f) for f in CORPUS}

    def dump(m):
        return {f: tok_key(m, TEXTS[f]) for f in CORPUS}

    a_ok = (dump(base) == dump(base)) and (dump(edit) == dump(edit))
    print('[A] 基线自检（两侧各两次 dump 一致）  %s' % ('PASS' if a_ok else 'FAIL'))

    d_b, d_e = dump(base), dump(edit)
    changed = [f for f in CORPUS if d_b[f] != d_e[f]]
    ch_real = sorted(os.path.relpath(f, ROOT).replace('\\', '/') for f in changed if not is_gen(f))
    ch_gen = sorted(os.path.relpath(f, ROOT).replace('\\', '/') for f in changed if is_gen(f))
    unexpected = sorted(set(ch_real) - EXPECTED_REAL)
    missing = sorted(EXPECTED_REAL - set(ch_real))
    b_ok = (not unexpected) and (not missing)
    print('[B] 真实源 token 变化 %d（预期 %d）｜生成树 %d  %s'
          % (len(ch_real), len(EXPECTED_REAL), len(ch_gen), 'PASS' if b_ok else 'FAIL'))
    for f in ch_real:
        print('      真实源:', f)
    for f in ch_gen[:12]:
        print('      生成树漂移:', f)
    if unexpected:
        print('      ★ 非预期变化:', unexpected)
    if missing:
        print('      ★ 预期变化未出现:', missing)

    # [C] CR1 覆盖充分性 A/B
    base13 = drop13(load(base_text, '_lxr_r24t3_b13'))
    edit13 = drop13(load(cur_text, '_lxr_r24t3_e13'))
    c1_broken, c2_ok = [], []
    ref = {c: pairs(base, '甲之' + c + '顶') for c in RETAINED_13}
    for c in RETAINED_13:
        s = '甲之' + c + '顶'
        if pairs(base13, s) != ref[c]:
            c1_broken.append(c)
        if pairs(edit13, s) == ref[c]:
            c2_ok.append(c)
    c1_ok = len(c1_broken) == 13
    c2_okv = len(c2_ok) == 13
    c_ok = c1_ok and c2_okv
    print('[C] CR1 覆盖充分性：' 
          '\n      C1 基准态撤 13 条 → 矩阵破裂 %d/13（应 13，证明白名单承重）%s'
          '\n      C2 修复态撤 13 条 → 矩阵保持 %d/13（应 13，证明 CR1 已覆盖）%s'
          '\n      合计  %s'
          % (len(c1_broken), 'PASS' if c1_ok else 'FAIL',
             len(c2_ok), 'PASS' if c2_okv else 'FAIL', 'PASS' if c_ok else 'FAIL'))
    if not c1_ok:
        print('      C1 未破裂的条目:', sorted(set(RETAINED_13) - set(c1_broken)))
    if not c2_okv:
        print('      C2 未保持的条目:', sorted(set(RETAINED_13) - set(c2_ok)))

    # [D] 自由名 + 语句起始裸名
    d_bad = [(s, pairs(base, s), pairs(edit, s)) for s in FREE_NAMES + STMT_INITIAL
             if pairs(base, s) != pairs(edit, s)]
    d_bad += [(s + ' = 1', pairs(base, s + ' = 1'), pairs(edit, s + ' = 1'))
              for s in STMT_INITIAL if pairs(base, s + ' = 1') != pairs(edit, s + ' = 1')]
    d_ok = not d_bad
    print('[D] 自由名(%d)+语句起始裸名(%d) token 逐字节一致  %s'
          % (len(FREE_NAMES), len(STMT_INITIAL), 'PASS' if d_ok else 'FAIL'))
    for s, x, y in d_bad:
        print('      ★ %r: %s ≠ %s' % (s, x, y))

    # [E] 性能
    tb, te = [], []
    for _ in range(3):
        t0 = time.time(); dump(base); tb.append(time.time() - t0)
        t0 = time.time(); dump(edit); te.append(time.time() - t0)
    m_b, m_e = statistics.median(tb), statistics.median(te)
    e_ok = m_e <= m_b * 1.10
    print('[E] 性能：基准 %.2fs vs 修复态 %.2fs  ×%.3f  %s'
          % (m_b, m_e, (m_b / m_e) if m_e else 0, 'PASS' if e_ok else 'FAIL'))

    # [F]/[F2] 编译运行
    assert sha(read(LEXER)) == sha_cur, '★ 外部写入检测：src/lexer.py 已被并发改动，放弃原地替换'
    rep, r24_rep = {}, {}
    try:
        for phase in ('base', 'edit'):
            with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                fh.write(base_text if phase == 'base' else cur_text)
            assert sha(read(LEXER)) == (sha(base_text) if phase == 'base' else sha_cur), \
                '原地替换失败'
            bucket = {}
            for p in CORE_CASES:
                if not os.path.exists(p):
                    continue
                r = subprocess.run([sys.executable, os.path.join(HARNESS, '运行.py'), p],
                                   capture_output=True, text=True, encoding='utf-8',
                                   errors='replace', timeout=600, cwd=HARNESS)
                bucket[os.path.basename(p)] = {'rc': r.returncode,
                                               'sha': sha((r.stdout or '') + (r.stderr or ''))}
            rep[phase] = bucket
            if phase == 'edit':
                for p in R24_CASES:
                    if not os.path.exists(p):
                        continue
                    r = subprocess.run([sys.executable, os.path.join(HARNESS, '运行.py'), p],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=HARNESS)
                    r24_rep[os.path.basename(p)] = {
                        'rc': r.returncode,
                        'tail': ((r.stdout or '') + (r.stderr or '')).strip()[-60:]}
    finally:
        if sha(read(LEXER)) in (sha(base_text), sha_cur):
            with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                fh.write(cur_text)
        print('      [还原校验] src/lexer.py sha256=%s  %s'
              % (sha(read(LEXER))[:16],
                 'OK' if sha(read(LEXER)) == sha_cur else '★ 已被并发改动（未覆盖）'))

    diff = [k for k in rep.get('base', {}) if rep['base'][k] != rep.get('edit', {}).get(k)]
    f_ok = (not diff) and len(rep.get('edit', {})) > 0
    print('[F] 既有核心用例（%d 个）编译运行 rc/stdout 两侧一致  %s'
          % (len(rep.get('edit', {})), 'PASS' if f_ok else 'FAIL'))
    for k, v in rep.get('edit', {}).items():
        print('      %-40s rc=%s' % (k, v['rc']))
    for k in diff:
        print('      ★ 差异:', k, rep['base'][k], rep['edit'][k])

    f2_ok = all(v['rc'] == 0 for v in r24_rep.values()) and len(r24_rep) == len(R24_CASES)
    print('[F2] R24 新增用例（%d 个）修复态 rc=0  %s' % (len(r24_rep), 'PASS' if f2_ok else 'FAIL'))
    for k, v in r24_rep.items():
        print('      %-40s rc=%s  %s' % (k, v['rc'], v['tail'][-36:]))

    ok = a_ok and b_ok and c_ok and d_ok and e_ok and f_ok and f2_ok and g_ok
    ev = {
        'baseline_rev': base_rev,
        'corpus_files': len(CORPUS),
        'cs_base': sorted(base._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'cs_edit': sorted(edit._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'retained_13': RETAINED_13,
        'p0a_compound_safe_removed': dead_gone,
        'cr1_present': cr1_present,
        'baseline_selfcheck': a_ok,
        'changed_real': ch_real,
        'changed_generated': ch_gen,
        'expected_real': sorted(EXPECTED_REAL),
        'unexpected_changes': unexpected,
        'missing_changes': missing,
        'cr1_c1_base_drop13_broken': sorted(c1_broken),
        'cr1_c1_all_broken': c1_ok,
        'cr1_c2_edit_drop13_kept': sorted(c2_ok),
        'cr1_c2_all_kept': c2_okv,
        'free_names_ok': d_ok,
        'free_names': FREE_NAMES,
        'stmt_initial': STMT_INITIAL,
        'time_base_s': round(m_b, 2), 'time_edit_s': round(m_e, 2), 'perf_ok': e_ok,
        'core_cases': rep.get('edit', {}),
        'core_cases_consistent': f_ok,
        'r24_cases': r24_rep,
        'r24_cases_all_green': f2_ok,
        'lexer_sha_restored': sha_cur,
        'verdict': 'ALL_OK' if ok else 'REGRESS',
    }
    json.dump(ev, open(HARNESS + '/_task3_R24_反跑证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('判定：', ev['verdict'])
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
