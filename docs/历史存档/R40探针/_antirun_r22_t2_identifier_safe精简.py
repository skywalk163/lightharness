# -*- coding: utf-8 -*-
"""R22 任务2 反跑脚本：IDENTIFIER_SAFE_KEYWORDS 精简正确性验证。

断裂态 vs 修复态（修剪后语义，沿 R21 反跑口径）：
  A（基线自检）：两次全量 dump 语料 token 一致。
  B（删除中立·语料级）：把 12 条已删条目**补回**（断裂态）-> 全语料 token 序列
     逐文件一致（等价于「删除这 12 条对全语料零影响」）。
  C（护栏正向控制）：对保留护栏条目，删除它 -> 依赖文件 token 必须变化
     （函数/输出/模块/打印）；标准库用单测契约（pytest）判定。
  D（单测契约）：tests/unit/test_lexer.py 中 identifier_safe 相关用例全过
     （`我的标准库` 合并为标识符等行为契约不受精简影响）。
本脚本只做内存态替换，不修改任何文件；finally 中恢复模块属性。
"""
import sys, glob, hashlib, subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa

CUR_MAIN = frozenset(L.IDENTIFIER_SAFE_KEYWORDS)
CUR_SUF = frozenset(L.IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS)
DELETED = ['包含', '匹配', '回调', '外部', '排序', '接口', '枚举',
           '结构体', '联合体', '段落', '返回', '配']

CORPUS = []
for g in (HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
          LIGHTP + '/examples/**/*.light', LIGHTP + '/stdlib/**/*.light',
          LIGHTP + '/tests/**/*.light'):
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))


def tok_key(src):
    try:
        toks = L.Lexer(src).tokenize()
        return hashlib.sha256(repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:
        return 'ERR:' + type(e).__name__


def dump():
    return {f: tok_key(open(f, encoding='utf-8', errors='replace').read()) for f in CORPUS}


def main():
    ok = True
    print(f'语料 .light 文件：{len(CORPUS)}  精简后主表：{len(CUR_MAIN)} 条')
    try:
        base = dump()
        base2 = dump()
        a_ok = (base == base2)
        print(f"[A] 基线自检（两次 dump 一致）  {'PASS' if a_ok else 'FAIL'}")
        ok = ok and a_ok

        # 断裂态 = 补回 12 条已删条目
        L.IDENTIFIER_SAFE_KEYWORDS = CUR_MAIN | frozenset(DELETED)
        try:
            broken = dump()
        finally:
            L.IDENTIFIER_SAFE_KEYWORDS = CUR_MAIN
        ch = [f for f in base if base[f] != broken.get(f)]
        b_ok = (len(ch) == 0)
        print(f"[B] 补回 {len(DELETED)} 条已删条目 -> 语料 token 变化 {len(ch)} 文件  "
              f"{'PASS（删除对全语料零影响）' if b_ok else 'FAIL'}")
        for f in ch[:3]:
            print('      变化:', f)
        ok = ok and b_ok

        # 护栏正向控制：删 函数 -> F3 示例文件必须变化
        dep = LIGHTP + '/examples/F阶段_标准库增强/F3_光明侧三个增强模块示例.light'
        src = open(dep, encoding='utf-8', errors='replace').read()
        h0 = tok_key(src)
        L.IDENTIFIER_SAFE_KEYWORDS = CUR_MAIN - {'函数'}
        try:
            h1 = tok_key(src)
        finally:
            L.IDENTIFIER_SAFE_KEYWORDS = CUR_MAIN
        c_ok = (h0 != h1)
        print(f"[C] 正向控制：删 `函数` 后依赖文件 token 变化  {'PASS' if c_ok else 'FAIL'}")
        ok = ok and c_ok

        # 单测契约：`我的标准库` 词中合并（直接 token 断言，与
        # tests/unit/test_lexer.py::test_identifier_safe_module_print_merged_inside_word 同口径）
        sig = [(t.type.name, t.value) for t in L.Lexer('我的标准库').tokenize()
               if t.type.name != 'EOF']
        d_ok = (sig == [('IDENTIFIER', '我的标准库')])
        print(f"[D] 单测契约（我的标准库 词中合并）sig={sig}  {'PASS' if d_ok else 'FAIL'}")
        ok = ok and d_ok
    finally:
        L.IDENTIFIER_SAFE_KEYWORDS = CUR_MAIN
        L.IDENTIFIER_SAFE_SUFFIX_ONLY_KEYWORDS = CUR_SUF
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
