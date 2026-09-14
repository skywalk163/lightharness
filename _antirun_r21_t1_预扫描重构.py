# -*- coding: utf-8 -*-
"""R21 任务1 反跑：预扫描重构（基于「分隔符前必为空白」修复 L-152）

⚠️ 交叉影响说明：第21轮任务2（上下文敏感切词）**也会**修复 L-152 的运行期症状
（形参名 `函数值` 在非语句起始位置被整体成词）。因此本反跑把任务1 的贡献**隔离**到
预扫描 `definitions` 层，并额外做一次「双断裂」运行期对照。

判据：
  A（definitions 断裂态）：撤销任务1 修复 → 嵌套段落 `函数值` **不**进入 definitions
  A2（双断裂运行期）：撤销任务1 **且** 停用任务2 → L-152 复现用例 rc=1
  B（修复态运行期）：恢复后 → 复现用例 rc=0，且 token 中 `函数值` 为单个 IDENTIFIER
  C（正向控制）：模块级同形态 `段落 模块级形参 接收 函数值:` rc=0 且 token 正确
  D（definitions 安全性）：断裂态相对修复态**多出的**名字，必须是修复态某名的**真前缀**
     （即它们只是「段名被截断」产生的错误名，不是合法标识符被删）

纪律：字节级改写，finally 逆序恢复全部锚点，并按 sha256 校验恢复到原始字节。
"""
import os, sys, json, subprocess, hashlib, glob

ROOT = r'G:/dswork/duan-light-merge/lightharness'
LIGHTP = r'G:/dswork/duan-light-merge/light-merge'
LEX = LIGHTP + r'/src/lexer.py'
PY = sys.executable
REPRO = 'examples/test_R21_L152嵌套段落形参.light'

# (修复态锚点, 断裂态锚点)
T1 = (b'if _preceded_ok and (_a >= _header_end', b'if (_a >= _header_end')
T2 = (b'if (len(full_identifier) > 1', b'if (False and len(full_identifier) > 1')

DUMP = r'''
import sys, json, glob, os
sys.path.insert(0, r'%s/src')
os.environ.setdefault('LIGHT_MERGE', r'%s')
from lexer import Lexer
out = {}
for f in sorted(glob.glob(r'%s/examples/test_*.light')):
    try:
        src = open(f, encoding='utf-8').read()
        out[os.path.basename(f)] = sorted(Lexer()._scan_user_definitions(src))
    except Exception as e:
        out[os.path.basename(f)] = ['<ERR:' + type(e).__name__ + '>']
print(json.dumps(out, ensure_ascii=False))
''' % (LIGHTP, LIGHTP, ROOT)

PROBE_SRC = ('段落 小于判断 接收 甲:\n  返回 甲 + 1\n段落 主:\n'
             '  段落 内层返回 接收 函数值:\n      返回 函数值(9)\n'
             '  断言相等(内层返回(小于判断), 10, "x")\n主()\n')
MOD_SRC = '段落 模块级形参 接收 函数值:\n    返回 函数值(3)\n'
L152_KEY = 'test_R21_L152嵌套段落形参.light'


def sha():
    return hashlib.sha256(open(LEX, 'rb').read()).hexdigest()


def repl(old, new):
    data = open(LEX, 'rb').read()
    assert data.count(old) == 1, f'锚点不唯一: {old!r} count={data.count(old)}'
    open(LEX, 'wb').write(data.replace(old, new))


def run_repro():
    env = dict(os.environ)
    env['LIGHT_MERGE'] = LIGHTP
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    p = subprocess.run([PY, '运行.py', REPRO], cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=env, timeout=300)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def token_seq(src):
    code = (
        "import sys;sys.path.insert(0,r'%s/src');"
        "from lexer import Lexer;"
        "t=Lexer().tokenize(%r);"
        "print('|'.join(x.type.name+':'+x.value for x in t if isinstance(x.value,str)))"
        % (LIGHTP, src)
    )
    p = subprocess.run([PY, '-c', code], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=120)
    return (p.stdout or '').strip()


def dump_defs():
    p = subprocess.run([PY, '-c', DUMP], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=900)
    return json.loads(p.stdout.strip().splitlines()[-1])


def main():
    orig = sha()
    print(f'lexer.py 原始 sha256={orig[:12]}')
    ok = True

    defs_fixed = dump_defs()
    print(f'[D] 修复态 definitions 覆盖 {len(defs_fixed)} 个 examples 文件')

    applied = []

    def apply(fix_brk):                      # fix_brk=(FIX,BRK)
        repl(fix_brk[0], fix_brk[1])
        applied.append(fix_brk)

    def revert_all():
        for fix, brk in reversed(applied):
            data = open(LEX, 'rb').read()
            if brk in data:
                open(LEX, 'wb').write(data.replace(brk, fix))
        applied.clear()

    try:
        # ---------- A：definitions 断裂态 ----------
        # 真判别点是「嵌套段名被截断」：断裂态 `内层返回`→`内层`、`计算返回`→`计算`。
        # （`函数值` 因模块级段落 line22 早已登记，两态都在，不能作判据。）
        apply(T1)
        defs_old = dump_defs()
        _old = set(defs_old.get(L152_KEY, []))
        _new = set(defs_fixed.get(L152_KEY, []))
        a_missing = '内层返回' not in _old
        a_present = {'内层返回', '计算返回'} <= _new
        a_ok = a_missing and a_present
        print(f"[A] 断裂态 definitions 缺真嵌套段名 `内层返回`（且修复态含之）  "
              f"{'PASS' if a_ok else 'FAIL'}")
        if not a_ok:
            print('    断裂态 L152 defs =', sorted(_old))
        ok = ok and a_ok

        # ---------- D：多出的名字必须是被截断的真前缀 ----------
        bad = []
        for f, newset in defs_fixed.items():
            ns = set(newset)
            for extra in set(defs_old.get(f, [])) - ns:
                if not any(extra != y and y.startswith(extra) for y in ns):
                    bad.append((f, extra))
        d_ok = (len(bad) == 0)
        print(f"[D] 断裂态多出名字均为「被截断真前缀」  违规 {len(bad)} 处  "
              f"{'PASS' if d_ok else 'FAIL'}")
        for f, e in bad[:8]:
            print(f'    [D-FAIL] {f} 多出非前缀名: {e}')
        ok = ok and d_ok

        # ---------- A2：双断裂运行期 ----------
        apply(T2)
        rcA2, outA2 = run_repro()
        a2_ok = (rcA2 == 1)
        print(f"[A2] 双断裂（任务1+任务2 均停用）复现用例 rc={rcA2}（期望 1）  "
              f"{'PASS' if a2_ok else 'FAIL'}")
        if not a2_ok:
            print('    输出尾:', outA2.strip().splitlines()[-2:])
        ok = ok and a2_ok
    finally:
        revert_all()

    # ---------- B：修复态 ----------
    rcB, outB = run_repro()
    b_ok = (rcB == 0)
    print(f"[B] 修复态 复现用例 rc={rcB}（期望 0）  {'PASS' if b_ok else 'FAIL'}")
    if not b_ok:
        print('    输出尾:', outB.strip().splitlines()[-2:])
    ok = ok and b_ok

    seq = token_seq(PROBE_SRC)
    has_single = ('IDENTIFIER:函数值' in seq) and ('KEYWORD:函数' not in seq)
    print(f"[B] token 层：`函数值` 为单个 IDENTIFIER  {'PASS' if has_single else 'FAIL'}")
    ok = ok and has_single

    seqc = token_seq(MOD_SRC)
    c_ok = ('IDENTIFIER:函数值' in seqc) and ('KEYWORD:函数' not in seqc)
    print(f"[C] 模块级同形态 `函数值` 单个 IDENTIFIER  {'PASS' if c_ok else 'FAIL'}")
    ok = ok and c_ok

    now = sha()
    r_ok = (now == orig)
    print(f"[恢复] lexer.py sha256={now[:12]}（期望 {orig[:12]}）  {'PASS' if r_ok else 'FAIL'}")
    ok = ok and r_ok

    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
