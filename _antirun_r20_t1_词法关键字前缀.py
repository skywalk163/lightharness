# -*- coding: utf-8 -*-
# 任务1 反跑判据验证（词法嵌入最大匹配：去重占位/作用域匹配/删除属性/合并为 等）
#
# 判据 A（断裂必红）：把词法器回退到轮20起点（R20_PREFIX=d2857dd5^，即不含任务1修复）→
#          test_宿主上下文.light / test_宿主事件.light 必须 rc != 0（红）。
#          这两个文件正是本轮要清零的临时例外①②，其红是「关键字前缀标识符被切碎」
#          （典型 `设 合并为 {}` 无空格写法 → 合并为 被并入标识符、为 赋值关键字丢失 →
#           `{}` 处报「期望为/等于」）所致。
# 判据 B（恢复必绿）：恢复任务1修复版词法器 → 两个文件必须 rc == 0（绿）。
# 判据 C（无过合并 / 合法语法不被误并）：修复版下
#          - test_R20_关键字前缀标识符.light 必须 rc == 0（新增覆盖套件全绿）；
#          - 词法探针确认 甲加乙 仍切为 甲/加/乙（中缀运算符不并入），
#            设 X 为 Y / 返回 Y 仍作合法语句（为/返回 独立成 token）。
#
# 注：本脚本原地改 light-merge/src/lexer.py 做断裂，无论成败都以 finally 恢复修复版。
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
LIGHT = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
LEXER = os.path.join(LIGHT, 'src', 'lexer.py')
ENV = dict(os.environ)
ENV['LIGHT_MERGE'] = LIGHT
# 禁用字节码缓存：反复原地改写 lexer.py 时，否则同秒 mtime 会让 Python 复用旧 .pyc
# （HEAD 断裂态编译出的缓存）导致「恢复修复版」后仍跑 HEAD 逻辑 → 判据B 假红。
ENV['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

REGRESS_RED = ['test_宿主上下文.light', 'test_宿主事件.light']   # 断裂检测器（例外①②）
POSITIVE = 'test_R20_关键字前缀标识符.light'                      # 正向控制


def _run_case(name):
    # 清掉可能残留的 lexer .pyc，确保按当前 lexer.py 源重编译
    _purge_pyc()
    p = subprocess.run([sys.executable, '运行.py', 'examples/' + name],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=ENV, timeout=300)
    return p.returncode


def _purge_pyc():
    # 清掉所有可能残留的光明编译器字节码，确保按当前 lexer.py 源重编译。
    # 重点：src/__pycache__/lexer*.pyc（被 parser_core 直接 import），以及
    # cli/__pycache__（run 路径入口 cli.light 可能缓存旧 lexer 引用）。
    for base in (os.path.join(LIGHT, 'src'), os.path.join(LIGHT, 'cli')):
        pc = os.path.join(base, '__pycache__')
        if os.path.isdir(pc):
            for fn in os.listdir(pc):
                if fn.endswith('.pyc'):
                    try:
                        os.remove(os.path.join(pc, fn))
                    except OSError:
                        pass
    # 同时清 lightharness 侧可能缓存的编译器字节码
    for base in (os.path.join(ROOT, 'src'), os.path.join(ROOT, 'stdlib')):
        pc = os.path.join(base, '__pycache__')
        if os.path.isdir(pc):
            for fn in os.listdir(pc):
                if fn.endswith('.pyc'):
                    try:
                        os.remove(os.path.join(pc, fn))
                    except OSError:
                        pass


# R21 任务3 订正（2026-09-14）：本脚本原以「HEAD」为断裂态（回退到 HEAD 应复现红）。
# 但第20轮修复已提交进 HEAD（d2857dd5），故 HEAD 已是**修复后**版本，判据A 恒假。
# 断裂态改为钉住「第20轮修复的父提交」——d2857dd5^ == 49319306（第19轮），
# 实测该版本跑 REGRESS_RED 两例确为红（rc=1），修复态为绿（rc=0），判据恢复有效。
R20_PREFIX = 'd2857dd5^'   # 第20轮修复提交的父提交（= 第19轮 49319306）


def _head_lexer():
    return subprocess.run(['git', '-C', LIGHT, 'show', R20_PREFIX + ':src/lexer.py'],
                          capture_output=True, text=True).stdout


def _tok_check():
    """词法探针：修复版必须保留合法中缀/赋值语句语义。"""
    import importlib.util
    if LIGHT + os.sep + 'src' not in sys.path:
        sys.path.insert(0, os.path.join(LIGHT, 'src'))
    _purge_pyc()
    spec = importlib.util.spec_from_file_location('lexer_r20', LEXER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    L = mod.Lexer()
    L._deterministic = True

    def toks(s):
        out = L.tokenize(s)
        return [(t.type.name, t.value) for t in out
                if t.type.name not in ('WHITESPACE', 'NEWLINE', 'INDENT', 'DEDENT', 'EOF')]

    a = toks('甲加乙')
    # 期望 甲/加/乙 三段（中缀运算符不被并入标识符）
    ok_a = [v for _, v in a] == ['甲', '加', '乙']
    b = toks('设 合并为 {}')
    # 期望 合并 / 为 / { / }（为 赋值关键字被切出）
    ok_b = [v for _, v in b] == ['设', '合并', '为', '{', '}']
    c = toks('返回 真')
    ok_c = [v for _, v in c] == ['返回', '真']
    return ok_a and ok_b and ok_c, (a, b, c)


def main():
    # 保存修复版（当前磁盘状态）
    with io.open(LEXER, encoding='utf-8', newline='') as f:
        fixed = f.read()

    ok = True
    try:
        # ── 断裂：回退到第20轮修复的父提交（R20_PREFIX）──
        head = _head_lexer()
        if not head.strip():
            print('FAIL: 无法取得 HEAD lexer')
            return 1
        with io.open(LEXER, 'w', encoding='utf-8', newline='') as f:
            f.write(head)

        # 判据 A
        for n in REGRESS_RED:
            rc = _run_case(n)
            if rc == 0:
                print('判据A FAIL: 断裂态 %s 应为红，实际 rc=0' % n)
                ok = False
            else:
                print('判据A PASS: 断裂态 %s 红 (rc=%d)' % (n, rc))
    finally:
        # 无论如何先恢复修复版
        with io.open(LEXER, 'w', encoding='utf-8', newline='') as f:
            f.write(fixed)

    # 判据 B（修复版）
    for n in REGRESS_RED:
        rc = _run_case(n)
        if rc != 0:
            print('判据B FAIL: 修复态 %s 应绿，实际 rc=%d' % (n, rc))
            ok = False
        else:
            print('判据B PASS: 修复态 %s 绿 (rc=0)' % n)

    # 判据 C（无过合并 + 合法语法）
    rc_p = _run_case(POSITIVE)
    if rc_p != 0:
        print('判据C FAIL: 正向控制 %s 应绿，实际 rc=%d' % (POSITIVE, rc_p))
        ok = False
    else:
        print('判据C PASS: 正向控制 %s 绿 (rc=0)' % POSITIVE)
    tok_ok, detail = _tok_check()
    if not tok_ok:
        print('判据C FAIL: 词法探针未过（合法语法被误并）:', detail)
        ok = False
    else:
        print('判据C PASS: 词法探针过（甲加乙切分 / 合并为切出为 / 返回真独立）')

    print('ALL OK' if ok else 'HAS FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
