# -*- coding: utf-8 -*-
"""R23 任务3 反跑：COMMON_COMPOUND_WORDS「184 → 37 条」精简的零回归验证。

断裂态 = 最近一个不含 R23 标记的祖先提交的 src/lexer.py（COMMON_COMPOUND_WORDS 184 条）
修复态 = 当前工作区 src/lexer.py（COMMON_COMPOUND_WORDS 37 条 = 17 真护栏 + 20 隔离非中立护栏）

【隔离口径说明】本轮任务1/2/3 都改 src/lexer.py，工作区是三改动的**合并态**。
  祖先提交（HEAD）同时含旧 IDENTIFIER_SAFE 5 条 + _TRAILING_ALIAS_MERGE 1 条 +
  CCW 184 条，故 [B]（祖先 vs 修复）是**三轮合并口径**；任务3 的**净改动隔离**
  由 [C] 承担 —— 在修复态原地补回 147 条已删条目（其余改动全部不动），
  若语料 token 零变化即证明「147 条删除」对全语料零影响。

判据：
  [A] 基线自检：两侧各两次 dump 一致。
  [B] 真实源 token 零变化（祖先 vs 修复，三轮合并口径；生成产物树
      light-merge/bootstrap/** 漂移只记录、不门控——不在任何测试断言路径）。
  [C] 任务3 净改动隔离·批量补回：把 147 条已删条目**一次性全部补回** → 语料 token
      零变化 ⇒ 逐条中立的可加性成立，批量删除与逐条删除等价。
  [D] 删除条目逐条冗余验证（147 条）：在「原 CCW（184）「状态下逐条撤离 → 全语料
      （仅扫含该词的候选文件）token 零变化 ⇒ 逐条删除安全，非批量。
  [D2] 保留条目必要性分类（**信息项，不门控**）：语料非中立 / 仅隔离非中立 /
      条件中立。保留是保守选择——留一条冗余条目不是回归，删除才是风险（[C]/[D] 已证安全）。
  [E] B 组（20 条）单列复核：语料中立 ∧ 该词自身 token 必变（隔离护栏）。
  [F] codegen 输出不变：内建名迁移探针在两侧 `light compile`（src 后端）生成的
      Python 文本 sha256 一致（任务3 验证标准③）。
  [G] 迁移目标登记复核：147 条删除条目按 code_generator 内建登记分类，与决策 JSON 一致；
      「分类①=builtin_map 已登记 ⇒ 无需新增」结论可复核。

反跑脚本在 finally 中恢复 src/lexer.py（sha256 校验）与全部内存态模块属性。
证据写入 _task3_R23_CCW精简_证据.json。
"""
import os
import sys
import glob
import json
import hashlib
import tempfile
import subprocess
import importlib.util
import ast

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
CG = os.path.join(LIGHTP, 'src', 'code_generator.py')
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

DEC = json.load(open(HARNESS + '/_r23_t3_decision.json', encoding='utf-8'))
DELETED = DEC['deleted']
GUARD_A = DEC['kept_real_guard']       # 17 条真护栏
GUARD_B = DEC['kept_iso_guard']        # 20 条隔离非中立护栏


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def sha_file(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def read(p):
    with open(p, encoding='utf-8', errors='replace') as f:
        return f.read()


def resolve_baseline():
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
    raise RuntimeError('未找到 R23 之前的 lexer.py 基准')


def load_mod(src_text, name):
    d = tempfile.mkdtemp(prefix='lxr_t3_')
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


def ast_map_keys(path):
    """静态抽取 code_generator.py 中所有映射表的字符串键，返回 {表名: set}。"""
    tree = ast.parse(read(path))
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                nm = None
                if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) \
                        and tgt.value.id == 'self' and tgt.attr.endswith('_map'):
                    nm = tgt.attr
                elif isinstance(tgt, ast.Name) and tgt.id.isupper():
                    nm = '<module:' + tgt.id + '>'
                if nm and isinstance(node.value, ast.Dict):
                    ks = {k.value for k in node.value.keys
                          if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                    out.setdefault(nm, set()).update(ks)
    return out


def main():
    sha_before = sha_file(LEXER)
    ok = True
    print('语料 .light 文件：%d' % len(CORPUS))
    base_rev, base_text = resolve_baseline()
    cur_text = read(LEXER)
    base_mod = load_mod(base_text, '_lexer_base_r23t3')
    edit_mod = load_mod(cur_text, '_lexer_edit_r23t3')

    base_ccw = frozenset(base_mod.COMMON_COMPOUND_WORDS)
    cur_ccw = frozenset(edit_mod.COMMON_COMPOUND_WORDS)
    print('基准提交 %s：CCW %d 条' % (base_rev[:12], len(base_ccw)))
    print('修复态：CCW %d 条（保留 A %d + 保留 B %d）'
          % (len(cur_ccw), len(GUARD_A), len(GUARD_B)))
    assert set(DELETED) | set(GUARD_A) | set(GUARD_B) == base_ccw, '决策 JSON 与基准 CCW 不一致'
    assert cur_ccw == set(GUARD_A) | set(GUARD_B), '修复态 CCW 与决策 JSON 不一致'

    try:
        # 语料内容**一次性快照**：多 agent 并行时磁盘文件可能被并发写入，
        # 若每次 dump 重新 read(f)，[A] 基线自检会因外部写入而假红。
        TEXTS = {f: read(f) for f in CORPUS}

        b1 = {f: tok_key(base_mod, TEXTS[f]) for f in CORPUS}
        b2 = {f: tok_key(base_mod, TEXTS[f]) for f in CORPUS}
        e1 = {f: tok_key(edit_mod, TEXTS[f]) for f in CORPUS}
        e2 = {f: tok_key(edit_mod, TEXTS[f]) for f in CORPUS}
        a_ok = (b1 == b2) and (e1 == e2)
        print('[A] 基线自检（两侧各两次 dump 一致）  %s' % ('PASS' if a_ok else 'FAIL'))
        ok = ok and a_ok

        ch = [f for f in b1 if b1[f] != e1.get(f)]
        ch_real = [f for f in ch if not is_generated(f)]
        ch_gen = [f for f in ch if is_generated(f)]
        b_ok = (len(ch_real) == 0)
        print('[B] 真实源 token 变化 %d 文件（生成树漂移 %d）  %s'
              % (len(ch_real), len(ch_gen), 'PASS（零回归）' if b_ok else 'FAIL'))
        for f in ch_real[:10]:
            print('      真实源变化:', os.path.relpath(f, ROOT))
        for f in ch_gen[:10]:
            print('      生成树漂移:', os.path.relpath(f, ROOT))
        ok = ok and b_ok

        # [C] 批量补回 147 条 → 语料零变化
        edit_mod.COMMON_COMPOUND_WORDS = cur_ccw | frozenset(DELETED)
        try:
            restored = {f: tok_key(edit_mod, TEXTS[f]) for f in CORPUS}
        finally:
            edit_mod.COMMON_COMPOUND_WORDS = cur_ccw
        rc_ch = [f for f in e1 if e1[f] != restored.get(f)]
        c_ok = (len(rc_ch) == 0)
        print('[C] 批量补回 %d 条已删条目 → 语料 token 变化 %d 文件  %s'
              % (len(DELETED), len(rc_ch), 'PASS（删除对全语料零影响）' if c_ok else 'FAIL'))
        ok = ok and c_ok

        # [D] 删除条目**逐条**冗余验证（147 条，任务书要求"不得批量删除"）：
        #     在「原 CCW（184 条 = 现 37 + 已删 147）」状态下撤离该条 → 全语料 token
        #     零变化 ⇒ 该条冗余、删除安全。任何一条非零变化即判 FAIL。
        full_ccw = cur_ccw | frozenset(DELETED)
        d_bad = []
        for w in DELETED:
            cand = [f for f in CORPUS if w in TEXTS[f]]
            edit_mod.COMMON_COMPOUND_WORDS = full_ccw
            try:
                a = {f: tok_key(edit_mod, TEXTS[f]) for f in cand}
            finally:
                edit_mod.COMMON_COMPOUND_WORDS = cur_ccw
            edit_mod.COMMON_COMPOUND_WORDS = full_ccw - {w}
            try:
                b = {f: tok_key(edit_mod, TEXTS[f]) for f in cand}
            finally:
                edit_mod.COMMON_COMPOUND_WORDS = cur_ccw
            if any(a[f] != b[f] for f in cand):
                d_bad.append(w)
        d_ok = (len(d_bad) == 0)
        print('[D] 删除条目逐条冗余验证 %d 条（逐条撤离 → 全语料 token 零变化）  %s%s'
              % (len(DELETED), 'PASS' if d_ok else 'FAIL',
                 '' if d_ok else '  非冗余（不应删）：' + ' '.join(d_bad)))
        ok = ok and d_ok

        # [D2] 保留条目必要性分类（**信息项，不门控**）。保留是保守选择：留一条冗余
        #      条目不是回归；删除才是风险（已由 [C]/[D] 证明安全）。分类：
        #        · 语料非中立：撤条 → 某个含该词的语料文件 token 变化（真护栏）；
        #        · 仅隔离非中立：撤条 → 该词自身单独 tokenize 变化（隔离护栏）；
        #        · 条件中立：两项皆不成立 ⇒ 在当前合并态 lexer 下已冗余，本轮保守保留。
        guard_kind = {}
        for w in list(GUARD_A) + list(GUARD_B):
            cand = [f for f in CORPUS if w in TEXTS[f]]
            edit_mod.COMMON_COMPOUND_WORDS = cur_ccw - {w}
            try:
                after = {f: tok_key(edit_mod, TEXTS[f]) for f in cand}
                self_after = tok_key(edit_mod, w)
            finally:
                edit_mod.COMMON_COMPOUND_WORDS = cur_ccw
            self_before = tok_key(edit_mod, w)
            nch = sum(1 for f in cand if e1[f] != after.get(f))
            if nch:
                guard_kind[w] = 'corpus(%d files)' % nch
            elif self_before != self_after:
                guard_kind[w] = 'self'
            else:
                guard_kind[w] = 'conditional-neutral'
        n_corpus = sum(1 for v in guard_kind.values() if v.startswith('corpus'))
        n_self = sum(1 for v in guard_kind.values() if v == 'self')
        cond = sorted(w for w, v in guard_kind.items() if v == 'conditional-neutral')
        print('[D2] 保留条目必要性分类（信息项）：语料非中立 %d ｜仅隔离非中立 %d ｜条件中立 %d'
              % (n_corpus, n_self, len(cond)))
        if cond:
            print('      条件中立（当前合并态下已冗余；本轮保守保留，建议后轮追加删除）：'
                  + ' '.join(cond))

        # [E] B 组（20 条）单列复核：撤条后该词自身 token 必变（隔离护栏）
        e_bad = []
        for w in GUARD_B:
            edit_mod.COMMON_COMPOUND_WORDS = cur_ccw - {w}
            try:
                h1 = tok_key(edit_mod, w)
            finally:
                edit_mod.COMMON_COMPOUND_WORDS = cur_ccw
            h0 = tok_key(edit_mod, w)
            if h0 == h1:
                e_bad.append(w)
        e_ok = (len(e_bad) == 0)
        print('[E] B 组（%d 条）隔离非中立复核  %s%s'
              % (len(GUARD_B), 'PASS' if e_ok else 'FAIL',
                 '' if e_ok else '  自身未变：' + ' '.join(e_bad)))
        ok = ok and e_ok

        # [F] codegen 输出不变（原地替换 lexer.py 走真 CLI）
        # ⚠️ 多 agent 并行时，本步骤的原地替换窗口若被外部写入打断会**覆盖他人改动**。
        # 故进入替换前先做「外部写入检测」，一旦 sha 与脚本起始快照不符立即放弃替换。
        if sha_file(LEXER) != sha_before:
            raise RuntimeError('★ 外部写入检测：src/lexer.py 在脚本起始后被改动，'
                               '放弃原地替换以免覆盖并发改动')
        probe_dir = os.path.join(tempfile.gettempdir(), 'r23_t3_probe')
        os.makedirs(probe_dir, exist_ok=True)
        probe = os.path.join(probe_dir, 'probe_内建名迁移.light')
        with open(probe, 'w', encoding='utf-8', newline='\n') as f:
            f.write('段落 主:\n'
                    '    设 甲 为 平方根(16.0)\n'
                    '    设 乙 为 四舍五入(3.6)\n'
                    '    设 丙 为 随机整数(1, 1)\n'
                    '    设 丁 为 十六进制(255)\n'
                    '    设 列表 为 [1, 2]\n'
                    '    列表追加(列表, 3)\n'
                    '    打印 甲\n    打印 乙\n    打印 丙\n    打印 丁\n'
                    '    打印 列表长度(列表)\n\n主()\n')
        gen_sha = {}
        try:
            for phase, txt in (('base', base_text), ('edit', cur_text)):
                with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(txt)
                assert sha_file(LEXER) == sha_text(txt), '原地替换失败'
                out_py = os.path.join(probe_dir, 'gen_%s.py' % phase)
                if os.path.exists(out_py):
                    os.remove(out_py)
                subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli.light', 'compile',
                                probe, '-o', out_py, '--backend', 'src'],
                               capture_output=True, timeout=600, cwd=LIGHTP)
                gen_sha[phase] = sha_text(read(out_py)) if os.path.exists(out_py) else 'MISSING'
        finally:
            with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                fh.write(cur_text)
            assert sha_file(LEXER) == sha_text(cur_text), '★ src/lexer.py 还原失败！'
        f_ok = (gen_sha.get('base') == gen_sha.get('edit')) and gen_sha.get('edit') != 'MISSING'
        print('[F] codegen 产物 sha256：断裂态 %s / 修复态 %s  %s'
              % (gen_sha.get('base', '?')[:16], gen_sha.get('edit', '?')[:16],
                 'PASS（一致）' if f_ok else 'FAIL'))
        ok = ok and f_ok

        # [G] 迁移目标登记复核
        maps = ast_map_keys(CG)
        builtin = maps.get('builtin_map', set())
        other = set().union(*[v for k, v in maps.items() if k != 'builtin_map']) if maps else set()
        g_ok = True
        for w in DEC['del_cat1_builtin_map']:
            if w not in builtin:
                g_ok = False
                print('      [G] 分类① 未在 builtin_map 登记:', w)
        for w in DEC['del_cat2_other_map']:
            if w not in other:
                g_ok = False
                print('      [G] 分类② 未在其它映射登记:', w)
        print('[G] 迁移目标登记复核：分类① %d 条已在 builtin_map，分类② %d 条已在其它映射，'
              '分类③ %d 条无映射  %s'
              % (len(DEC['del_cat1_builtin_map']), len(DEC['del_cat2_other_map']),
                 len(DEC['del_cat3_no_map']), 'PASS' if g_ok else 'FAIL'))
        ok = ok and g_ok
    finally:
        try:
            base_mod.COMMON_COMPOUND_WORDS = base_ccw
            edit_mod.COMMON_COMPOUND_WORDS = cur_ccw
        except Exception:  # noqa
            pass
        same = (sha_before == sha_file(LEXER))
        print('[还原校验] src/lexer.py sha256 %s  %s'
              % (sha_before[:16], 'OK' if same else '★ 已变化！'))
        ok = ok and same

    json.dump({'baseline_rev': base_rev,
               'corpus_files': len(CORPUS),
               'real_corpus_files': len([f for f in CORPUS if not is_generated(f)]),
               'generated_corpus_files': len([f for f in CORPUS if is_generated(f)]),
               'base_ccw': len(base_ccw),
               'edit_ccw': len(cur_ccw),
               'deleted': len(DELETED),
               'guard_real': GUARD_A,
               'guard_iso': GUARD_B,
               'token_changed_real': len(ch_real),
               'token_changed_generated': len(ch_gen),
               'changed_real_files': [os.path.relpath(f, ROOT) for f in ch_real[:50]],
               'changed_generated_files': [os.path.relpath(f, ROOT) for f in ch_gen[:50]],
               'batch_restore_changed': len(rc_ch),
               'deleted_per_entry_nonneutral': d_bad,
               'retained_kind': guard_kind,
               'retained_conditional_neutral': cond,
               'codegen_gen_sha': gen_sha,
               'verdict': 'ALL_OK' if ok else 'REGRESS'},
              open(HARNESS + '/_task3_R23_CCW精简_证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
