# -*- coding: utf-8 -*-
"""R23 任务2 反跑脚本：IDENTIFIER_SAFE_KEYWORDS 清表（后缀位置上下文规则替代）。

断裂态 vs 修复态：
  断裂态 = git HEAD 的 lexer.py（含 IDENTIFIER_SAFE_KEYWORDS 5条 + SUFFIX_ONLY 3条）
  修复态 = 工作区 lexer.py（两表已删，后缀位置上下文规则替代）
判据：
  A（基线自检）：修复态两次全量 dump token 一致。
  B（清表中立·语料级）：断裂态 vs 修复态全语料（.light）token 序列逐文件一致。
  C（契约正向控制·词法层）：词中/词尾并入（处理函数/可打印/我的标准库/学生模块/
     输出格式）+ 词首语句切分（打印甲/打印结果/模块甲/标准库甲）+ 嵌入关键字保留
     （学生模块等于甲 / 打印甲加1 / 甲加可打印）。
  D（statement 词首）：打印 "x" 输出 KEYWORD(打印)。
本脚本只读语料、不动源文件；断裂态模块从 git show 提取到临时目录加载。
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


def load_head_lexer(tmpdir):
    head = subprocess.run(['git', '-C', LIGHTP, 'show', 'HEAD:src/lexer.py'],
                          capture_output=True)
    p = os.path.join(tmpdir, 'lexer_head_r23t2.py')
    open(p, 'wb').write(head.stdout)
    sys.path.insert(0, tmpdir)
    sys.path.insert(0, LIGHTP + '/src')
    import lexer_head_r23t2 as LB
    return LB


def tok_key(lexer_cls, s):
    try:
        toks = lexer_cls(s).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def sig(lexer_cls, s):
    return [(t.type.name, t.value) for t in lexer_cls(s).tokenize() if t.type.name != 'EOF']


CONTRACT_MERGE = ['处理函数', '可打印', '我的标准库', '学生模块', '输出格式', '输出结果']
CONTRACT_SPLIT = ['打印甲', '打印结果', '模块甲', '标准库甲']


def main():
    ok = True
    tmpdir = tempfile.mkdtemp(prefix='r23t2_')
    sys.path.insert(0, LIGHTP + '/src')
    import lexer as LN
    try:
        LB = load_head_lexer(tmpdir)

        def dump(mod):
            return {f: tok_key(mod.Lexer, open(f, encoding='utf-8', errors='replace').read())
                    for f in CORPUS}

        b1 = dump(LN)
        b2 = dump(LN)
        a_ok = (b1 == b2)
        print(f"[A] 基线自检（修复态两次 dump 一致，{len(CORPUS)} 文件）  {'PASS' if a_ok else 'FAIL'}")
        ok = ok and a_ok

        head = dump(LB)
        ch = [f for f in b1 if b1[f] != head.get(f)]
        b_ok = (len(ch) == 0)
        print(f"[B] 断裂态(HEAD 有表) vs 修复态(无表) -> 语料 token 变化 {len(ch)} 文件  "
              f"{'PASS（清表对全语料零影响）' if b_ok else 'FAIL'}")
        for f in ch[:5]:
            print('      变化:', f)
        ok = ok and b_ok

        c_ok = True
        for w in CONTRACT_MERGE:
            s = sig(LN.Lexer, w)
            good = (s == [('IDENTIFIER', w)])
            c_ok = c_ok and good
            if not good:
                print(f"      [C-FAIL] {w} -> {s}")
        for w in CONTRACT_SPLIT:
            s = sig(LN.Lexer, w)
            kw = {'打印甲': '打印', '打印结果': '打印', '模块甲': '模块', '标准库甲': '标准库'}[w]
            good = (s[0] == ('KEYWORD', kw) and s[1] == ('IDENTIFIER', w[len(kw):]))
            c_ok = c_ok and good
            if not good:
                print(f"      [C-FAIL] {w} -> {s}")
        s = sig(LN.Lexer, '学生模块等于甲')
        e1 = ('KEYWORD', '等于') in s
        s = sig(LN.Lexer, '打印甲加1')
        e2 = ('KEYWORD', '加') in s and s[0] == ('KEYWORD', '打印')
        s = sig(LN.Lexer, '甲加可打印')
        e3 = ('KEYWORD', '加') in s and s[-1] == ('IDENTIFIER', '可打印')
        c_ok = c_ok and e1 and e2 and e3
        if not (e1 and e2 and e3):
            print(f"      [C-FAIL] 嵌入关键字守卫 {e1}/{e2}/{e3}")
        print(f"[C] 契约正向控制（并入 {len(CONTRACT_MERGE)} 词 + 词首切分 {len(CONTRACT_SPLIT)} 词"
              f" + 嵌入守卫 3 例）  {'PASS' if c_ok else 'FAIL'}")
        ok = ok and c_ok

        s = sig(LN.Lexer, '打印 "x"')
        d_ok = (s[0] == ('KEYWORD', '打印'))
        print(f"[D] 打印 语句词首（打印 \"x\" -> KEYWORD 打印）  {'PASS' if d_ok else 'FAIL'}")
        ok = ok and d_ok
    finally:
        pass
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
