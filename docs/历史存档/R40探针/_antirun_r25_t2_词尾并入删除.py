# -*- coding: utf-8 -*-
"""R25 任务2 逐条验证：18 个「词尾并入」候选单字能否从 CS 表删除。

工作区状态：**已含任务1**（单字词尾并入已改为正面规则 `_TRAILING_ALIAS_CLASS = F`）。
因此「撤掉 CS 条目」只剩下「词首并入」这一个语义后果——本脚本就是测这个后果。

每个候选字 c 走三道门，全部通过才算「可删」：

  [G1] 全语料判据③：撤掉 c 后，所有**含 c 的语料文件** token 序列零变化；
  [G2] 词首编译门（R25）：构造**语句起始裸名**复合词（该字在词首、未声明、
       非 `设 X 为` 形式），在撤掉态下词法结果必须与基线一致——即该词仍整词成
       IDENTIFIER（一旦被切成 关键字+余字，编译必然失败）。本脚本用**词法级等价**
       实现该门，等价于原 design 的 subprocess 编译门，且无需改磁盘、不触发模块级
       代数断言（到/真/空 属 DUAL，磁盘改写会令断言①崩）。
  [G3] 边界形态门：任务书点名的六类边界形态 + 该字的代表词尾复合名，token 流不变。

实现要点（修复原版缺陷）：
  - 原版 `drop_c_text` + `load()` 把删字的 lexer.py 重写后**重新 import**，触发模块级
    断言① `_COMPOUND_SAFE_SINGLE_KEYWORDS == (F−TAM)|DUAL` —— 因 DUAL 硬编码含
    到/真/空，删这些字后断言崩，脚本中断。
  - 本版改用**内存态 monkeypatch**：同时改写模块级常量 `_COMPOUND_SAFE_SINGLE_KEYWORDS`
    与类属性 `Lexer.compound_safe_single_keywords`（lexer.py 中还有 6 处读模块级常量，
    只改类属性会漏掉它们导致 G1 误判）。运行时改模块级变量**不重跑** import 期断言，
    故彻底绕开崩溃。这正是工作记忆要求的「隔离单改动优先内存态」。
  - 不触碰磁盘上的 src/lexer.py，无需 sha256 还原（无写入）。
"""
import os
import sys
import glob
import json
import time

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))
import lexer  # noqa: E402

# 任务书「词尾并入 17 条」清单（配/段合并为一行，实际逐字验证 18 字）
CANDS = '出列则到常引接断末的真类试跳过长配段'

# 每字的代表**词首**复合名（该字在词首、全语料基线均整词成 IDENTIFIER）
HEAD_WORD = {
    '出': '出错', '列': '列数', '则': '则例', '到': '到底', '常': '常规',
    '引': '引导', '接': '接受', '断': '断定', '末': '末尾', '的': '的确',
    '真': '真值', '类': '类别', '试': '试用', '跳': '跳闸', '过': '过程',
    '长': '长度', '配': '配给', '段': '段号',
}

# 每字的代表**词尾**复合名（任务书表格场景，用于 [G3] 正向复核）
TAIL_WORD = {
    '出': '标准输出', '列': '日期列', '则': '规则', '到': '文件未找到',
    '常': '首异常', '引': '最后索引', '接': '符号链接', '断': '截断',
    '末': '月末', '的': '成绩的长度', '真': '标准输出失真', '类': '有界队列类',
    '试': '测试', '跳': '最后心跳跳过', '过': '通过', '长': '块长',
    '配': '配置项', '段': '代码段',
}

BOUNDARY = [
    '返回 真', '设 甲 为 真', '设 甲 为 空', '配[0]', '段[1]', '配[键]',
    '如果 甲 则 乙', '从 1 到 10', '甲 加 乙', '我的 书', '遍历 块长 之 项',
]

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def stream(mod, s):
    try:
        return [(t.type.name, t.value) for t in mod.Lexer(s, deterministic=True).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:  # noqa: BLE001
        return [('ERR', type(e).__name__)]


def patched(c):
    """返回 (orig_mod, orig_cls, newset)；调用方负责在 finally 还原。"""
    orig_mod = lexer._COMPOUND_SAFE_SINGLE_KEYWORDS
    orig_cls = lexer.Lexer.compound_safe_single_keywords
    newset = frozenset(orig_mod - {c})
    lexer._COMPOUND_SAFE_SINGLE_KEYWORDS = newset      # 模块级常量（6 处引用）
    lexer.Lexer.compound_safe_single_keywords = newset  # 类属性（2725/2802/2950）
    return orig_mod, orig_cls, newset


def restore(orig_mod, orig_cls):
    lexer._COMPOUND_SAFE_SINGLE_KEYWORDS = orig_mod
    lexer.Lexer.compound_safe_single_keywords = orig_cls


def main():
    orig_mod = lexer._COMPOUND_SAFE_SINGLE_KEYWORDS
    orig_cls = lexer.Lexer.compound_safe_single_keywords
    print('工作区 lexer ｜ CS=%d  词尾并入类别(F)=%d ｜ 语料 %d 文件'
          % (len(orig_mod), len(lexer.Lexer._TRAILING_ALIAS_CLASS), len(CORPUS)))
    print('[G0] F 是否覆盖候选：' + ''.join(
        '%s%s' % (c, '' if c in lexer.Lexer._TRAILING_ALIAS_CLASS else '✘') for c in CANDS))
    print('     （✘=不在F，删CS后词尾也不被并入，必保留）')

    TEXTS = {f: read(f) for f in CORPUS}
    evidence = {}
    for c in CANDS:
        t0 = time.time()
        o1, o2, _ = patched(c)
        try:
            # ---- [G1] 语料判据③（仅含 c 的文件） ----
            sub = {f: t for f, t in TEXTS.items() if c in t}
            drop_streams = {f: stream(lexer, t) for f, t in sub.items()}
            restore(o1, o2)
            base_streams = {f: stream(lexer, t) for f, t in sub.items()}
            changed = [os.path.relpath(f, ROOT).replace('\\', '/')
                       for f in sub if repr(base_streams[f]) != repr(drop_streams[f])]
            g1 = (len(changed) == 0)

            # ---- [G2] 词首编译门（词法级等价）：代表词首复合名在撤掉态须仍整词成 IDENTIFIER ----
            restore(o1, o2)
            base_head = stream(lexer, HEAD_WORD[c])
            o1, o2, _ = patched(c)
            drop_head = stream(lexer, HEAD_WORD[c])
            restore(o1, o2)
            # 基线须整词成 IDENTIFIER（设计前提）；撤掉态须与基线一致
            base_single = (len(base_head) == 1 and base_head[0][0] == 'IDENTIFIER'
                           and base_head[0][1] == HEAD_WORD[c])
            g2 = base_single and (base_head == drop_head)

            # ---- [G3] 边界形态 + 代表词尾复合名 ----
            restore(o1, o2)
            base_b = {s: stream(lexer, s) for s in BOUNDARY + [TAIL_WORD[c]]}
            o1, o2, _ = patched(c)
            drop_b = {s: stream(lexer, s) for s in BOUNDARY + [TAIL_WORD[c]]}
            restore(o1, o2)
            g3_bad = [s for s in base_b if base_b[s] != drop_b[s]]
            g3 = not g3_bad
        finally:
            restore(orig_mod, orig_cls)

        verdict = '可删' if (g1 and g2 and g3) else '保留'
        evidence[c] = {
            'head_word': HEAD_WORD[c], 'tail_word': TAIL_WORD[c],
            'in_F': c in lexer.Lexer._TRAILING_ALIAS_CLASS,
            'corpus_scanned': len(sub), 'corpus_changed': len(changed),
            'corpus_changed_files': changed[:12],
            'gate_corpus': g1, 'gate_head_compile': g2, 'gate_boundary': g3,
            'boundary_broken': g3_bad,
            'base_head_tokens': base_head, 'drop_head_tokens': drop_head,
            'verdict': verdict,
            'seconds': round(time.time() - t0, 1),
        }
        print('[%s] G1语料%s(%d变) G2词首%s G3边界%s ⇒ %s  (%.1fs)'
              % (c, '✔' if g1 else '✘', len(changed),
                 '✔' if g2 else '✘', '✔' if g3 else '✘', verdict, time.time() - t0))

    deletable = [c for c in CANDS if evidence[c]['verdict'] == '可删']
    keep = [c for c in CANDS if evidence[c]['verdict'] != '可删']
    cs_final = sorted(set(orig_mod) - set(deletable))
    json.dump({
        'candidates': CANDS,
        'per_entry': evidence,
        'deletable': deletable,
        'keep': keep,
        'cs_before': sorted(orig_mod),
        'cs_after_if_deleted': cs_final,
        'cs_size_before': len(orig_mod),
        'cs_size_after': len(cs_final),
        'corpus_files': len(CORPUS),
        'method': '内存态 monkeypatch 模块级常量+类属性；G2 词法级等价编译门',
    }, open(HARNESS + '/_task2_R25_词尾并入逐条验证_证据.json', 'w', encoding='utf-8'),
        ensure_ascii=False, indent=1)
    print('\n可删：%s' % (''.join(deletable) if deletable else '无'))
    print('保留：%s' % ''.join(keep))
    print('CS 表：%d → %d' % (len(orig_mod), len(cs_final)))
    print('证据：lightharness/_task2_R25_词尾并入逐条验证_证据.json')


if __name__ == '__main__':
    main()
