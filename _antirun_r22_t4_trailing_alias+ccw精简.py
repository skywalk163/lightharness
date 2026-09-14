# -*- coding: utf-8 -*-
"""R22 任务4 反跑脚本：_TRAILING_ALIAS_MERGE + COMMON_COMPOUND_WORDS TierB 精简验证。

断裂态 vs 修复态（修剪后语义，沿 R21 反跑口径）：
  A（基线自检）：两次全量 dump 语料 token 一致。
  B（删除中立·语料级）：把 9 条 TAM 已删条目 + 32 条 CCW TierB 已删条目**补回**
     （断裂态）-> 全语料 token 序列逐文件一致（删除对全语料零影响）。
  C（护栏正向控制）：删 `己` -> lightharness/examples/test_L120.light token 变化
     （L-120 复现用例依赖，精简后仍护栏）；清空 CCW 整表 -> 语料 token 变化。
  D（L-120 关联验证）：lightharness/examples/test_L120.light 编译 rc=0。
本脚本只做内存态替换与只读验证，不修改任何文件；finally 中恢复模块属性。
"""
import sys, glob, hashlib, subprocess

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa

CUR_TAM = frozenset(L._TRAILING_ALIAS_MERGE)          # {'己'}
CUR_CCW = frozenset(L.COMMON_COMPOUND_WORDS)          # 184 条
TAM_DELETED = ['遍', '捕', '抛', '终', '返', '设', '承', '宏', '掷']
TIERB = ['压缩模量', '去重行', '各乘数据', '各减数据', '各加数据', '各除数据', '弹性模量',
         '当前含', '当前含水', '当前环节', '当前环节数', '当家', '当选', '承载力', '承载能力',
         '文本去重行', '格式模式', '清除率', '清除速率', '滚动乘积', '滚动加权', '滚动求和',
         '生成分析阶段', '甲位与乙', '终期折现因子', '联合体成员', '跳过迭代', '过滤模二零',
         '过滤模二非零', '过滤模十零', '过滤模零', '过滤模零集合']

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
    print(f'语料 .light 文件：{len(CORPUS)}  TAM：{len(CUR_TAM)} 条  CCW：{len(CUR_CCW)} 条')
    try:
        base = dump()
        base2 = dump()
        a_ok = (base == base2)
        print(f"[A] 基线自检（两次 dump 一致）  {'PASS' if a_ok else 'FAIL'}")
        ok = ok and a_ok

        # 断裂态 = 补回全部已删条目（9 TAM + 32 CCW）
        L._TRAILING_ALIAS_MERGE = CUR_TAM | frozenset(TAM_DELETED)
        L.COMMON_COMPOUND_WORDS = CUR_CCW | frozenset(TIERB)
        try:
            broken = dump()
        finally:
            L._TRAILING_ALIAS_MERGE = CUR_TAM
            L.COMMON_COMPOUND_WORDS = CUR_CCW
        ch = [f for f in base if base[f] != broken.get(f)]
        b_ok = (len(ch) == 0)
        print(f"[B] 补回 {len(TAM_DELETED)}+{len(TIERB)} 条已删条目 -> 语料 token 变化 {len(ch)} 文件  "
              f"{'PASS（删除对全语料零影响）' if b_ok else 'FAIL'}")
        for f in ch[:3]:
            print('      变化:', f)
        ok = ok and b_ok

        # 护栏正向控制①：删 `己` -> test_L120.light token 变化
        dep = HARNESS + '/examples/test_L120.light'
        src = open(dep, encoding='utf-8', errors='replace').read()
        h0 = tok_key(src)
        L._TRAILING_ALIAS_MERGE = CUR_TAM - {'己'}
        try:
            h1 = tok_key(src)
        finally:
            L._TRAILING_ALIAS_MERGE = CUR_TAM
        c1_ok = (h0 != h1)
        print(f"[C1] 正向控制：删 `己` 后 test_L120.light token 变化  {'PASS' if c1_ok else 'FAIL'}")
        ok = ok and c1_ok

        # 护栏正向控制②：清空 CCW 整表 -> 语料 token 变化（harness 有效性）
        L.COMMON_COMPOUND_WORDS = frozenset()
        try:
            empty = dump()
        finally:
            L.COMMON_COMPOUND_WORDS = CUR_CCW
        n = sum(1 for f in base if base[f] != empty.get(f))
        c2_ok = (n > 0)
        print(f"[C2] 正向控制：清空 CCW 后语料 token 变化 {n} 文件（应 >0）  {'PASS' if c2_ok else 'FAIL'}")
        ok = ok and c2_ok

        # D：L-120 复现用例编译运行仍绿（lightharness/运行.py，与回归门禁同路径）
        r = subprocess.run([sys.executable, HARNESS + '/运行.py', dep],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300)
        d_ok = (r.returncode == 0)
        print(f"[D] L-120 关联验证：test_L120.light 编译运行 rc={r.returncode}  "
              f"{'PASS' if d_ok else 'FAIL'}")
        if not d_ok:
            print((r.stdout or '') + (r.stderr or ''))
        ok = ok and d_ok
    finally:
        L._TRAILING_ALIAS_MERGE = CUR_TAM
        L.COMMON_COMPOUND_WORDS = CUR_CCW
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
