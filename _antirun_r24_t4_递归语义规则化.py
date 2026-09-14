# -*- coding: utf-8 -*-
"""R24 任务4 反跑脚本：_match_keyword 递归语义规则化验证。

断裂态 vs 修复态：
  断裂态 = git HEAD 的 lexer.py（R23 提交：字面量 30 字白名单，无类别断言）
  修复态 = 工作区 lexer.py（类别代数文档 + import 时自校验断言）
判据：
  A（基线自检）：修复态两次全量 dump token 一致。
  B（规则化中立·语料级）：断裂态(HEAD) vs 修复态(合并态：任务1的修复+任务3的
     30→17精简+本任务断言)全语料 token 对比，差异文件必须 ⊆ 任务1 预期修正集合
     （`的` 递归吞分隔符修复场景：学生模块.light + test_R24_的递归修复.light）。
  C（递归语义正向控制）：之 成员访问切分（自之X/数列之长度/块长 之 块长表）、
     副作用回报自由名（去除空格/10的幂/种类/索引/阶乘/乘阶乘/加斐波那契）、
     双栖单字（甲加乙 切分 vs 加法 并入）、值字面量（返回 真 / 为 空）、
     TAM 词尾并入（错误己/自己）。
  D（断言有效性）：篡改字面量 1 字后重新加载必须 AssertionError（防断言失效）。
"""
import sys, os, glob, hashlib, subprocess, tempfile

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'

CORPUS = []
for g in (HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
          LIGHTP + '/examples/**/*.light', LIGHTP + '/stdlib/**/*.light',
          LIGHTP + '/tests/**/*.light'):
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))


def tok_key(lexer_cls, s):
    try:
        toks = lexer_cls(s).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def sig(lexer_cls, s):
    return [(t.type.name, t.value) for t in lexer_cls(s).tokenize() if t.type.name != 'EOF']


PROBES = [
    ("自之姓名", [("KEYWORD", "自"), ("KEYWORD", "之"), ("IDENTIFIER", "姓名")]),
    ("数列之长度", [("IDENTIFIER", "数列"), ("KEYWORD", "之"), ("IDENTIFIER", "长度")]),
    ("去除空格", [("IDENTIFIER", "去除空格")]),
    ("10的幂", [("NUMBER", 10), ("IDENTIFIER", "的幂")]),
    ("种类", [("IDENTIFIER", "种类")]),
    ("索引", [("IDENTIFIER", "索引")]),
    ("阶乘", [("IDENTIFIER", "阶乘")]),
    ("n乘阶乘(n)", [("IDENTIFIER", "n"), ("IDENTIFIER", "乘阶乘"),
                    ("LPAREN", "("), ("IDENTIFIER", "n"), ("RPAREN", ")")]),
    ("甲加乙", [("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("IDENTIFIER", "乙")]),
    ("甲乘乙", [("IDENTIFIER", "甲"), ("KEYWORD", "乘"), ("IDENTIFIER", "乙")]),
    ("加法(1,2)", [("IDENTIFIER", "加法"), ("LPAREN", "("), ("NUMBER", 1),
                   ("COMMA", ","), ("NUMBER", 2), ("RPAREN", ")")]),
    ("标准输出失真", [("IDENTIFIER", "标准输出失真")]),
    ("错误己", [("IDENTIFIER", "错误己")]),
    ("自己", [("IDENTIFIER", "自己")]),
    ("返回 真", [("KEYWORD", "返回"), ("KEYWORD", "真")]),
    ("设 甲 为 空", [("KEYWORD", "设"), ("IDENTIFIER", "甲"),
                     ("KEYWORD", "为"), ("KEYWORD", "空")]),
]


def main():
    ok = True
    tmpdir = tempfile.mkdtemp(prefix='r24t4_')
    sys.path.insert(0, LIGHTP + '/src')
    import lexer as LN
    try:
        head = subprocess.run(['git', '-C', LIGHTP, 'show', 'HEAD:src/lexer.py'],
                              capture_output=True)
        p = os.path.join(tmpdir, 'lexer_head_r24.py')
        open(p, 'wb').write(head.stdout)
        sys.path.insert(0, tmpdir)
        import lexer_head_r24 as LB

        def dump(mod):
            return {f: tok_key(mod.Lexer, open(f, encoding='utf-8', errors='replace').read())
                    for f in CORPUS}

        b1 = dump(LN)
        b2 = dump(LN)
        a_ok = (b1 == b2)
        print(f"[A] 基线自检（{len(CORPUS)} 文件两次 dump 一致）  {'PASS' if a_ok else 'FAIL'}")
        ok = ok and a_ok

        EXPECTED_T1 = {'test_R24_的递归修复.light', '学生模块.light'}  # 任务1 的修复预期变化
        head_map = dump(LB)
        ch = [f for f in b1 if b1[f] != head_map.get(f)]
        unexpected = [f for f in ch if not any(f.endswith(x) for x in EXPECTED_T1)]
        b_ok = (len(unexpected) == 0)
        print(f"[B] 断裂态(HEAD) vs 修复态(合并态) -> token 变化 {len(ch)} 文件，"
              f"超预期 {len(unexpected)} 文件  "
              f"{'PASS（变化均为任务1 的修复预期）' if b_ok else 'FAIL'}")
        for f in unexpected[:5]:
            print('      超预期:', f)
        ok = ok and b_ok

        c_ok = True
        for src, expect in PROBES:
            s = sig(LN.Lexer, src)
            if s != expect:
                c_ok = False
                print(f"      [C-FAIL] {src!r} -> {s}")
        print(f"[C] 递归语义正向控制（{len(PROBES)} 形态：之切分/副作用回报/双栖单字/值字面量/TAM）  "
              f"{'PASS' if c_ok else 'FAIL'}")
        ok = ok and c_ok

        # D：断言有效性——篡改字面量必须 AssertionError
        cur_src = open(os.path.join(LIGHTP, 'src', 'lexer.py'), encoding='utf-8').read()
        import re as _re
        _m = _re.search(r"_COMPOUND_SAFE_SINGLE_KEYWORDS = frozenset\(\{\n(.*?)\n\}\)", cur_src, _re.S)
        assert _m, "字面量块未找到"
        _body = _m.group(1)
        _first_entry = _re.search(r"'([^']+)'", _body)
        assert _first_entry, "字面量无条目"
        _w = _first_entry.group(1)
        _tampered_body = _body.replace(f"'{_w}'", f"'{_w}X'", 1)  # 篡改第1条目（加X→非单字）
        tampered = cur_src.replace(_body, _tampered_body, 1)
        d_ok = (tampered != cur_src)
        if d_ok:
            tp = os.path.join(tmpdir, 'lexer_bad.py')
            open(tp, 'w', encoding='utf-8').write(tampered)
            r = subprocess.run([sys.executable, '-c',
                                f"import sys; sys.path.insert(0, r'{LIGHTP}\\src'); "
                                f"sys.path.insert(0, r'{tmpdir}'); import lexer_bad"],
                               capture_output=True, text=True)
            d_ok = (r.returncode != 0 and 'R24' in (r.stderr or ''))
        print(f"[D] 断言有效性（篡改字面量 -> import AssertionError）  {'PASS' if d_ok else 'FAIL'}")
        ok = ok and d_ok
    finally:
        pass
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
