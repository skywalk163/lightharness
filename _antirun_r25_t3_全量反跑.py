# -*- coding: utf-8 -*-
"""R25 任务3 全量反跑：断裂态（git HEAD，pre-任务1）vs 修复态（工作树，含任务1）对比。

对比维度：
  [A] 全语料 token 序列对比（836 文件）：任务1 单字后缀规则改为正面类别 F（43 字），
      应做到语料 token 序列**零变化**（词尾并入是等价重写）。
  [B] 核心用例编译对比（断裂态 vs 修复态 rc 一致）：L-084/L-092/L-119/L-120 +
      本轮新增 test_R25_词尾并入正向/边界反向。

修复态直接 import 工作树 lexer（磁盘现状，已含任务1）；断裂态用 `git show HEAD:src/lexer.py`
临时导入为独立模块（不污染工作树）。核心用例编译需磁盘 lexer：断裂态阶段把 HEAD lexer
落到磁盘、跑完即 sha256 还原，全程外部写入检测。

输出：_task3_R25_反跑结果.json + 控制台摘要。
"""
import os
import sys
import json
import time
import glob
import hashlib
import subprocess
import importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
PY = os.path.join(LIGHTP, '.venv', 'Scripts', 'python.exe')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

CORE = [
    'examples/test_L084.light', 'examples/test_L092.light',
    'examples/test_L119.light', 'examples/test_L120.light',
    'examples/test_R25_词尾并入正向.light',
    'examples/test_R25_词尾并入边界反向.light',
]


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def load_text_as(tag, text):
    d = os.path.join(os.environ.get('TEMP', '/tmp'), 'lxr_t3_' + tag)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'lxr_%s.py' % tag)
    open(p, 'w', encoding='utf-8', newline='').write(text)
    spec = importlib.util.spec_from_file_location('lxr_%s' % tag, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['lxr_%s' % tag] = mod
    spec.loader.exec_module(mod)
    return mod


def run_light(rel):
    r = subprocess.run([PY, os.path.join(HARNESS, '运行.py'), os.path.join(HARNESS, rel)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, cwd=HARNESS)
    return r.returncode


def main():
    t0 = time.time()
    # 修复态：工作树 lexer（已含任务1）
    import lexer as fix_mod  # noqa: E402
    fix_sha = sha_text(read(LEXER))
    print('修复态(工作树) lexer sha=%s ｜ CS=%d  F=%d ｜ 语料 %d 文件'
          % (fix_sha[:12], len(fix_mod.Lexer.compound_safe_single_keywords),
             len(fix_mod.Lexer._TRAILING_ALIAS_CLASS), len(CORPUS)))

    # 断裂态：git HEAD lexer 临时导入
    head_text = subprocess.check_output(['git', 'show', 'HEAD:src/lexer.py'],
                                        cwd=LIGHTP).decode('utf-8')
    head_mod = load_text_as('head', head_text)
    print('断裂态(git HEAD) lexer ｜ CS=%d  F(TRAILING_ALIAS_CLASS)=%d'
          % (len(head_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
             len(head_mod.Lexer._TRAILING_ALIAS_CLASS)))

    # [A] 全语料 token 对比
    changed = []
    for f in CORPUS:
        t = read(f)
        try:
            a = repr([(x.type.name, x.value)
                      for x in head_mod.Lexer(t, deterministic=True).tokenize()
                      if x.type.name not in ('EOF', 'NEWLINE')])
        except Exception as e:  # noqa
            a = 'ERR:' + type(e).__name__
        try:
            b = repr([(x.type.name, x.value)
                      for x in fix_mod.Lexer(t, deterministic=True).tokenize()
                      if x.type.name not in ('EOF', 'NEWLINE')])
        except Exception as e:  # noqa
            b = 'ERR:' + type(e).__name__
        if a != b:
            changed.append(os.path.relpath(f, ROOT).replace('\\', '/'))
    print('[A] 全语料 token 对比：%d/%d 文件变化' % (len(changed), len(CORPUS)))

    # [B] 核心用例编译对比（断裂态需落磁盘，sha 守护还原）
    rc_fix = {}
    for rel in CORE:
        rc_fix[rel] = run_light(rel)
    print('[B] 修复态 核心用例 rc：%s' % rc_fix)

    # 落 HEAD lexer 到磁盘（sha 守护：确保开始前磁盘仍是修复态）
    if sha_text(read(LEXER)) != fix_sha:
        raise RuntimeError('★ 外部写入检测：工作树 lexer 已被并发改动')
    open(LEXER, 'w', encoding='utf-8', newline='').write(head_text)
    rc_head = {}
    try:
        for rel in CORE:
            rc_head[rel] = run_light(rel)
    finally:
        # 还原修复态（_fix_backup 为 __main__ 缓存的工作树原文）
        open(LEXER, 'w', encoding='utf-8', newline='').write(_fix_backup)
        restored = sha_text(read(LEXER))
        assert restored == fix_sha, '★ 还原失败：sha=%s (期望 %s)' % (restored[:12], fix_sha[:12])
    print('[B] 断裂态 核心用例 rc：%s' % rc_head)

    compile_changed = [rel for rel in CORE if rc_head.get(rel) != rc_fix.get(rel)]
    print('[B] 核心用例 rc 变化：%s' % (compile_changed if compile_changed else '无'))

    result = {
        'corpus_files': len(CORPUS),
        'token_changed_count': len(changed),
        'token_changed_files': changed[:20],
        'token_regression_ok': len(changed) == 0,
        'core_rc_fix': rc_fix,
        'core_rc_head': rc_head,
        'core_compile_changed': compile_changed,
        'core_compile_ok': len(compile_changed) == 0,
        'seconds': round(time.time() - t0, 1),
    }
    json.dump(result, open(HARNESS + '/_task3_R25_反跑结果.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n[A] token 零变化：%s' % result['token_regression_ok'])
    print('[B] 核心编译不变：%s' % result['core_compile_ok'])
    print('结果：lightharness/_task3_R25_反跑结果.json')


# 修复态原文缓存（用于 finally 还原）
_fix_backup = None


if __name__ == '__main__':
    _fix_backup = read(LEXER)
    main()
