# -*- coding: utf-8 -*-
"""R21 任务2 反跑：词法上下文敏感切词

判据：
  A（断裂态）：停用 Task2 上下文敏感块（`if (False and ...)`）→
       未注册的 `去重占位` 在表达式中被切碎（出现 KEYWORD:去重 且无 IDENTIFIER:去重占位）
  B（修复态）：恢复后 → `去重占位` 整体成 IDENTIFIER
  C（正向控制，不变性）：语句起始 `如果条件:` 仍切出 KEYWORD:如果；
       运算符 `甲加乙` 仍切出 KEYWORD:加；`打印(甲)` 仍是 KEYWORD:打印
  D（运行期）：examples/test_R21_上下文敏感切词.light rc=0
  E（交叉）：examples/test_R21_L152嵌套段落形参.light rc=0（任务1 不被破坏）

纪律：字节级改写，finally 按 sha256 恢复；恢复后复跑确认。
"""
import os, sys, subprocess, hashlib

ROOT = r'G:/dswork/duan-light-merge/lightharness'
LIGHTP = r'G:/dswork/duan-light-merge/light-merge'
LEX = LIGHTP + r'/src/lexer.py'
PY = sys.executable

FIX_ANCHOR = b'if (len(full_identifier) > 1'
BRK_ANCHOR = b'if (False and len(full_identifier) > 1'

A_SRC = '设 结果 为 去重占位([1,1,2])'
STMT_SRC = '如果条件:\n    打印 甲'
OP_SRC = '设 结果 为 甲加乙'
PAREN_SRC = '打印(甲)'
RUNTIME = 'examples/test_R21_上下文敏感切词.light'
CROSS = 'examples/test_R21_L152嵌套段落形参.light'


def sha():
    return hashlib.sha256(open(LEX, 'rb').read()).hexdigest()


def patch_bytes(old, new):
    data = open(LEX, 'rb').read()
    assert data.count(old) == 1, f'锚点不唯一: {old!r} count={data.count(old)}'
    open(LEX, 'wb').write(data.replace(old, new))


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


def run_file(f):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = LIGHTP
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    p = subprocess.run([PY, '运行.py', f], cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=env, timeout=300)
    return p.returncode


def main():
    orig = sha()
    print(f'lexer.py 原始 sha256={orig[:12]}')
    ok = True
    try:
        # ---- A 判据：断裂态 ----
        patch_bytes(FIX_ANCHOR, BRK_ANCHOR)
        seqA = token_seq(A_SRC)
        a_ok = ('KEYWORD:去重' in seqA) and ('IDENTIFIER:去重占位' not in seqA)
        print(f"[A] 断裂态 表达式切碎 (KEYWORD:去重 出现)  {'PASS' if a_ok else 'FAIL'}")
        print(f'    {seqA}')
        ok = ok and a_ok
        # 断裂态下语句/运算符/括号控制项应仍正确（与本块无关）
        sA = token_seq(STMT_SRC)
        cA = ('KEYWORD:如果' in sA) and ('IDENTIFIER:条件' in sA)
        print(f"[C] 断裂态 语句起始仍正确  {'PASS' if cA else 'FAIL'}")
        ok = ok and cA
    finally:
        data = open(LEX, 'rb').read()
        if BRK_ANCHOR in data:
            open(LEX, 'wb').write(data.replace(BRK_ANCHOR, FIX_ANCHOR))

    # ---- B 判据：修复态 ----
    seqB = token_seq(A_SRC)
    b_ok = 'IDENTIFIER:去重占位' in seqB and 'KEYWORD:去重' not in seqB
    print(f"[B] 修复态 表达式整体成 IDENTIFIER  {'PASS' if b_ok else 'FAIL'}")
    print(f'    {seqB}')
    ok = ok and b_ok

    # ---- C 判据：正向控制（修复态） ----
    sB = token_seq(STMT_SRC)
    oB = token_seq(OP_SRC)
    pB = token_seq(PAREN_SRC)
    c_ok = (('KEYWORD:如果' in sB) and ('IDENTIFIER:条件' in sB)
            and ('KEYWORD:加' in oB) and ('KEYWORD:打印' in pB))
    print(f"[C] 正向控制：语句起始/运算符/括号关键字不变  {'PASS' if c_ok else 'FAIL'}")
    if not c_ok:
        print(f'    语句={sB}')
        print(f'    运算符={oB}')
        print(f'    括号={pB}')
    ok = ok and c_ok

    # ---- D 判据：运行期 ----
    rcD = run_file(RUNTIME)
    d_ok = (rcD == 0)
    print(f"[D] 运行期 {RUNTIME} rc={rcD}（期望 0）  {'PASS' if d_ok else 'FAIL'}")
    ok = ok and d_ok

    # ---- E 判据：交叉（任务1 不破） ----
    rcE = run_file(CROSS)
    e_ok = (rcE == 0)
    print(f"[E] 交叉 {CROSS} rc={rcE}（期望 0）  {'PASS' if e_ok else 'FAIL'}")
    ok = ok and e_ok

    # ---- 恢复校验 ----
    now = sha()
    r_ok = (now == orig)
    print(f"[恢复] lexer.py sha256={now[:12]}（期望 {orig[:12]}）  {'PASS' if r_ok else 'FAIL'}")
    ok = ok and r_ok

    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
