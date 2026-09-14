# -*- coding: utf-8 -*-
"""R23 任务1 反跑：`己` 词尾并入「逐词白名单 → 通用类别」替换的零回归验证。

【断裂态 / 修复态 的隔离口径（本脚本核心）】
  本轮任务1/2/3 都改 src/lexer.py，工作区是三方改动的**合并态**。若拿祖先提交
  （HEAD=e99bdb80，同时含旧 IDENTIFIER_SAFE 5 条 + _TRAILING_ALIAS_MERGE 1 条 +
  CCW 184 条）当「断裂态」，对比工作区就会把任务2/任务3 的改动一并算进来，
  **无法隔离任务1**。因此本脚本改用**内存态精确隔离**：

    断裂态 = 载入【当前工作区】src/lexer.py，再把类属性
             Lexer._TRAILING_ALIAS_CLASS 覆写为 frozenset({'己'})
             —— 等价还原 R22 遗留的 1 条白名单 `_TRAILING_ALIAS_MERGE = {'己'}`
                （已逐行核对：新旧实现除「集合来源」外代码结构完全一致，
                  两个引用点 2691/2841 与旧版 2742/2893 逐行同构）。
    修复态 = 载入【当前工作区】src/lexer.py 原样（21 字通用类别）。

  两侧源码**逐字节相同**，唯一差异就是那个集合 —— 这才是任务1 的净改动。

判据：
  [A] 基线自检：两侧各两次 dump 一致（确定性）。
  [B] 真实源 token 零变化：断裂态 vs 修复态，逐文件 sha256 一致
      ⇒ 把白名单换成通用类别，对全量生产语料零影响。
      生成产物树 light-merge/bootstrap/**（build_bootstrap_release.py 的构建输出，
      不在任何测试断言路径）的漂移单独记录，由 [B2] 判定其性质。
  [B2] 生成树漂移性质：对每个漂移文件做**二分归并比对**，证明差异是
      「≥2 颗 broken token 合并为 1 颗 fixed IDENTIFIER」的**纯并入**（无切分、
      无文本变化）⇒ 是通用规则覆盖更多单字的**正确性改进**，不是回归。
  [C] 正向控制①（白名单非空转）：修复态下把 `己` 从通用类别中剔除 → test_L120.light
      token 变化 ⇒ 词尾并入规则确实在起作用（判据非恒真）。
  [D] 正向控制②（旧白名单确实在起作用）：断裂态下把白名单清空 → test_L120.light
      token 变化 ⇒ 两侧 harness 有效。
  [E] 通用类别自证：按 lexer.py 现公式现算 == 现存类别 == 21 字期望值
      （证明非人工手抄，且与 L-120 语义一致）。
  [F] 覆盖验证：错误己/自己/爱己/知己 在修复态下均为单颗 IDENTIFIER；
      词首 `己姓名` 仍切分为 KEYWORD(己)+IDENTIFIER(姓名)（词首语义不变）；
      `甲加乙` 仍切分为 IDENTIFIER(甲)+KEYWORD(加)+IDENTIFIER(乙)（运算符不受影响）。
  [G] L-120 关联：test_L120.light 与 examples/test_R23_己词尾并入.light 编译运行 rc=0。
  [H] 收口自检（信息项）：模块已无 `_TRAILING_ALIAS_MERGE` 名字；另附祖先提交
      （HEAD）vs 修复态的全语料 token 变化数，作为「三轮合并零漂移」的旁证。

本脚本只做**内存态**模块属性替换与只读验证，不改任何文件；finally 中恢复模块属性，
并校验工作区 src/lexer.py 的 sha256 前后一致。
"""
import os
import sys
import glob
import json
import hashlib
import tempfile
import subprocess
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

R23_MARKER = '_TRAILING_ALIAS_CLASS'
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

# 生成产物树（build_bootstrap_release.py 的构建输出，不在任何测试断言路径）。
# 口径与第22轮 / 本轮任务5 一致：这些树的 token 漂移只记录、不门控。
GENERATED_TREES = [os.path.join(LIGHTP, 'bootstrap')]


def is_generated(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED_TREES)


def drift_kind(mod_b, mod_f, text):
    """二分归并比对：判断 broken→fixed 的差异是否为「纯并入」。

    返回 (n_broken, n_fixed, merges, ok)：merges 为 [(合并后标识符, [被吞 token…])]。
    ok=True 当且仅当两侧 token **值序列**完全可由「≥2 颗 broken token → 1 颗
    fixed IDENTIFIER」的归并解释（无切分、无凭空产生、无文本丢失）。
    """
    b = toks(mod_b, text)
    f = toks(mod_f, text)
    i = j = 0
    merges = []
    while i < len(b) and j < len(f):
        if b[i] == f[j]:
            i += 1
            j += 1
            continue
        if f[j][0] == 'IDENTIFIER':
            k = 1
            acc = b[i][1] if i < len(b) else None
            while acc != f[j][1] and i + k <= len(b):
                if i + k >= len(b):
                    break
                acc += b[i + k][1]
                k += 1
            if k >= 2 and acc == f[j][1]:
                merges.append((f[j][1], [t[1] for t in b[i:i + k]]))
                i += k
                j += 1
                continue
        return len(b), len(f), merges, False
    ok = (i == len(b)) and (j == len(f))
    return len(b), len(f), merges, ok

# 期望的通用类别（21 字）：单字关键字 − 运算符 − 范围/步长 − await − 单字复合安全 − 值字面量
EXPECT_21 = set('从匹否宏导己并异当承抛捕掷父现终若设跃返遍')
L120 = HARNESS + '/examples/test_L120.light'
R23_CASE = HARNESS + '/examples/test_R23_己词尾并入.light'


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def sha_file(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def read(p):
    with open(p, encoding='utf-8', errors='replace') as f:
        return f.read()


def resolve_baseline():
    """最近一个不含 R23 标记的祖先提交（供 [H] 旁证使用，非判据基线）。"""
    revs = subprocess.check_output(['git', '-C', LIGHTP, 'log', '--format=%H', '-n', '30'],
                                   encoding='utf-8').split()
    for rev in revs:
        try:
            txt = subprocess.check_output(
                ['git', '-C', LIGHTP, 'show', '%s:src/lexer.py' % rev], encoding='utf-8')
        except subprocess.CalledProcessError:
            continue
        if R23_MARKER not in txt:
            return rev, txt
    return None, None


def load_mod(src_text, name):
    d = tempfile.mkdtemp(prefix='lxr_t1_')
    p = os.path.join(d, name + '.py')
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src_text)
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def tok_key(mod, src):
    try:
        toks = mod.Lexer(src).tokenize()
        return hashlib.sha256(
            repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def toks(mod, src):
    return [(t.type.name, t.value) for t in mod.Lexer(src).tokenize()
            if t.type.name != 'EOF']


def run_light(path, timeout=600):
    r = subprocess.run([sys.executable, os.path.join(HARNESS, '运行.py'), path],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=timeout, cwd=HARNESS)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
    sha_before = sha_file(LEXER)
    ok = True
    print('语料 .light 文件：%d' % len(CORPUS))
    cur_text = read(LEXER)

    # ── 两侧源码逐字节相同，唯一差异：断裂态把类别压回旧白名单口径 {'己'} ──
    broken = load_mod(cur_text, '_lexer_broken_r23t1')
    fixed = load_mod(cur_text, '_lexer_fixed_r23t1')
    broken.Lexer._TRAILING_ALIAS_CLASS = frozenset({'己'})

    fixed_cls = frozenset(fixed.Lexer._TRAILING_ALIAS_CLASS)
    broken_cls = frozenset(broken.Lexer._TRAILING_ALIAS_CLASS)
    print('断裂态（= R22 遗留白名单口径）：_TRAILING_ALIAS_CLASS=%s' % sorted(broken_cls))
    print('修复态（= 通用类别）          ：%d 字' % len(fixed_cls))
    print('两侧源码同一份文本 sha256：%s（逐字节相同）' % sha_text(cur_text)[:16])

    try:
        # 语料内容**一次性快照**：多 agent 并行时磁盘文件可能被并发写入，
        # 若每次 dump 重新 read(f)，[A] 基线自检会因外部写入而假红。
        TEXTS = {f: read(f) for f in CORPUS}

        # [A] 基线自检
        b1 = {f: tok_key(broken, TEXTS[f]) for f in CORPUS}
        b2 = {f: tok_key(broken, TEXTS[f]) for f in CORPUS}
        f1 = {f: tok_key(fixed, TEXTS[f]) for f in CORPUS}
        f2 = {f: tok_key(fixed, TEXTS[f]) for f in CORPUS}
        a_ok = (b1 == b2) and (f1 == f2)
        print('[A] 基线自检（两侧各两次 dump 一致）  %s' % ('PASS' if a_ok else 'FAIL'))
        ok = ok and a_ok

        # [B] 真实源 token 零变化（任务1 净改动隔离；生成产物树单独记录）
        changed = [f for f in b1 if b1[f] != f1.get(f)]
        ch_real = [f for f in changed if not is_generated(f)]
        ch_gen = [f for f in changed if is_generated(f)]
        b_ok = (len(ch_real) == 0)
        print('[B] 任务1 净改动：真实源 token 变化 %d / %d 文件（生成树漂移 %d）  %s'
              % (len(ch_real), len([f for f in CORPUS if not is_generated(f)]),
                 len(ch_gen), 'PASS（零变化）' if b_ok else 'FAIL'))
        for f in ch_real[:10]:
            print('      真实源变化:', os.path.relpath(f, ROOT))
        ok = ok and b_ok

        # [B2] 生成树漂移性质：必须为「纯并入」（≥2 颗 token → 1 颗 IDENTIFIER）
        b2_ok = True
        for f in ch_gen:
            nb, nf, merges, kind_ok = drift_kind(broken, fixed, TEXTS[f])
            if not kind_ok or not merges:
                b2_ok = False
                print('      [B2] 非纯并入漂移：%s（%d→%d tokens, merges=%d）'
                      % (os.path.relpath(f, ROOT), nb, nf, len(merges)))
            else:
                for merged, parts in merges:
                    print('      [B2] %s：%s → IDENTIFIER(%s)'
                          % (os.path.relpath(f, ROOT), ' + '.join(parts), merged))
        print('[B2] 生成树漂移性质（纯并入=正确性改进）  %s'
              % ('PASS' if b2_ok else 'FAIL'))
        for f in ch_gen:
            print('      生成树漂移:', os.path.relpath(f, ROOT))
        ok = ok and b2_ok

        # [C] 正向控制①：修复态剔除 `己` → L-120 token 变化
        src120 = read(L120)
        h0 = tok_key(fixed, src120)
        fixed.Lexer._TRAILING_ALIAS_CLASS = fixed_cls - {'己'}
        try:
            h1 = tok_key(fixed, src120)
        finally:
            fixed.Lexer._TRAILING_ALIAS_CLASS = fixed_cls
        c1_ok = (h0 != h1)
        print('[C] 正向控制①：修复态剔除 `己` → test_L120.light token 变化  %s'
              % ('PASS' if c1_ok else 'FAIL'))
        ok = ok and c1_ok

        # [D] 正向控制②：断裂态清空白名单 → L-120 token 变化
        h0b = tok_key(broken, src120)
        broken.Lexer._TRAILING_ALIAS_CLASS = frozenset()
        try:
            h1b = tok_key(broken, src120)
        finally:
            broken.Lexer._TRAILING_ALIAS_CLASS = broken_cls
        d_ok = (h0b != h1b)
        print('[D] 正向控制②：断裂态清空白名单 → test_L120.light token 变化  %s'
              % ('PASS' if d_ok else 'FAIL'))
        ok = ok and d_ok

        # [E] 通用类别自证：按 lexer.py 现公式现算 == 现存 == 期望 21 字
        recomputed = frozenset(
            k for k in fixed._ALL_KEYWORDS_WITH_VERBS
            if len(k) == 1
            and k not in fixed.Lexer._P0A_OP
            and k not in fixed._OPERATOR_KEYWORDS
            and k not in fixed.Lexer._P0A_NEVER_SPLIT
            and k not in fixed._AWAIT_KEYWORDS
            and k not in fixed._COMPOUND_SAFE_SINGLE_KEYWORDS
            and k not in fixed._VALUE_LITERAL_KEYWORDS)
        e_ok = (recomputed == fixed_cls) and (fixed_cls == frozenset(EXPECT_21))
        print('[E] 通用类别自证：现算 %d 字 == 现存 %d 字 == 期望 %d 字  %s'
              % (len(recomputed), len(fixed_cls), len(EXPECT_21), 'PASS' if e_ok else 'FAIL'))
        if not e_ok:
            print('      现算^现存：', sorted(recomputed ^ fixed_cls))
            print('      现存^期望：', sorted(fixed_cls ^ frozenset(EXPECT_21)))
        ok = ok and e_ok

        # [F] 覆盖验证（词尾并入 / 词首语义 / 运算符）
        f_ok = True
        for w in ('自己', '爱己', '知己', '错误己'):
            got = toks(fixed, w)
            good = (got == [('IDENTIFIER', w)])
            f_ok = f_ok and good
            print('      %s -> %s  %s' % (w, got, 'OK' if good else 'BAD'))
        got_head = toks(fixed, '己姓名')
        head_ok = (got_head == [('KEYWORD', '己'), ('IDENTIFIER', '姓名')])
        got_op = toks(fixed, '甲加乙')
        op_ok = (got_op == [('IDENTIFIER', '甲'), ('KEYWORD', '加'), ('IDENTIFIER', '乙')])
        f_ok = f_ok and head_ok and op_ok
        print('      己姓名 -> %s  %s' % (got_head, 'OK' if head_ok else 'BAD'))
        print('      甲加乙 -> %s  %s' % (got_op, 'OK' if op_ok else 'BAD'))
        print('[F] 覆盖 + 反向验证（词尾并入 / 词首语义 / 运算符切分）  %s'
              % ('PASS' if f_ok else 'FAIL'))
        ok = ok and f_ok

        # [G] L-120 关联：两个用例编译运行 rc=0
        g_ok = True
        for p in (L120, R23_CASE):
            if not os.path.exists(p):
                print('      [G] 缺少用例：%s' % p)
                g_ok = False
                continue
            rc, out = run_light(p)
            print('      %s rc=%d  %s' % (os.path.basename(p), rc, 'OK' if rc == 0 else 'BAD'))
            if rc != 0:
                print(out[-800:])
                g_ok = False
        print('[G] L-120 关联用例编译运行  %s' % ('PASS' if g_ok else 'FAIL'))
        ok = ok and g_ok

        # [H] 收口自检 + 祖先提交旁证（信息项，不计入 PASS/FAIL）
        no_old = not hasattr(fixed, '_TRAILING_ALIAS_MERGE')
        print('[H1] 模块已无 _TRAILING_ALIAS_MERGE 名字  %s'
              % ('PASS' if no_old else 'FAIL'))
        ok = ok and no_old

        base_rev, base_text = resolve_baseline()
        anc_changed = None
        if base_rev:
            anc = load_mod(base_text, '_lexer_anc_r23t1')
            a1 = {f: tok_key(anc, TEXTS[f]) for f in CORPUS}
            anc_changed = [f for f in a1 if a1[f] != f1.get(f)]
            print('[H2] 旁证：祖先提交 %s vs 修复态，全语料 token 变化 %d / %d 文件'
                  % (base_rev[:12], len(anc_changed), len(CORPUS)))
            for f in anc_changed[:10]:
                print('       变化:', os.path.relpath(f, ROOT))
        else:
            print('[H2] 旁证：未找到祖先提交，跳过')
    finally:
        try:
            fixed.Lexer._TRAILING_ALIAS_CLASS = fixed_cls
            broken.Lexer._TRAILING_ALIAS_CLASS = broken_cls
        except Exception:  # noqa
            pass
        sha_after = sha_file(LEXER)
        same = (sha_before == sha_after)
        print('[还原校验] src/lexer.py sha256 %s → %s  %s'
              % (sha_before[:16], sha_after[:16],
                 'OK（未被改动）' if same else
                 '★ 外部写入：本脚本不写 lexer.py，检测到并发修改；'
                 '判据 [A]~[H1] 用起始快照计算仍然有效，但请择机重跑取干净快照'))
        ok = ok and same

    json.dump({'isolation': 'memory-level: same source, ONLY _TRAILING_ALIAS_CLASS differs',
               'baseline_rev_for_ancestor_note': base_rev,
               'corpus_files': len(CORPUS),
               'real_corpus_files': len([f for f in CORPUS if not is_generated(f)]),
               'generated_corpus_files': len([f for f in CORPUS if is_generated(f)]),
               'broken_trailing_alias': sorted(broken_cls),
               'fixed_trailing_alias_class': sorted(fixed_cls),
               'token_changed_real': len(ch_real),
               'token_changed_generated': len(ch_gen),
               'changed_real_files': [os.path.relpath(f, ROOT) for f in ch_real],
               'changed_generated_files': [os.path.relpath(f, ROOT) for f in ch_gen],
               'token_changed_vs_ancestor_note': (len(anc_changed) if anc_changed is not None else None),
               'verdict': 'ALL_OK' if ok else 'REGRESS'},
              open(HARNESS + '/_task1_R23_TRAILING_ALIAS清表_证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
