# -*- coding: utf-8 -*-
"""R27 任务3：CS表16字逐字隔离验证（三重判据 G1/G2/G3）。

验证方式：monkeypatch lexer 模块级 CS 常量 + 类属性，逐字移除后与基线比对。
  G1 语料判据：全语料 843 文件 token 序列零变化
  G2 词首编译门：{字}+复合名 词首裸名 `X名 为 7` 撤掉态与基线一致
  G3 边界形态门：六类边界形态 token 流不变（值字面量/下标/算术/范围/控制流/硬语句）

输出：_task3_R27_CS表16字逐条验证_证据.json + 控制台摘要
"""
import os
import sys
import json
import glob
import hashlib

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [HARNESS + '/examples/**/*.light', HARNESS + '/src/**/*.light',
            HARNESS + '/tests/**/*.light', LIGHTP + '/examples/**/*.light',
            LIGHTP + '/stdlib/**/*.light', LIGHTP + '/bootstrap/**/*.light',
            LIGHTP + '/src/**/*.light', LIGHTP + '/tests/**/*.light']
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))

CS16 = ['乘', '减', '到', '加', '模', '真', '空', '除',   # A类 DUAL
        '列', '对', '是', '段', '的', '类', '自', '配']   # B类 F∩CS

# G2 词首复合名（每字2个代表词）
G2_WORDS = {
    '乘': ['乘法', '乘积'], '减': ['减法', '减少'], '到': ['到位', '到底'],
    '加': ['加法', '加上'], '模': ['模组', '模块'], '真': ['真空', '真实'],
    '空': ['空格', '空白'], '除': ['除法', '除非'],
    '列': ['列数', '列表'], '对': ['对立', '对象'], '是': ['是否', '是的'],
    '段': ['段落', '段首'], '的': ['的确', '的话'], '类': ['类别', '类型'],
    '自': ['自然', '自己'], '配': ['配置', '配对'],
}

# G3 六类边界形态（每字一行代码片段）
G3_FORMS = {
    '乘': ['设 结果 为 甲 乘 乙', '设 乘法 为 7'],
    '减': ['设 结果 为 甲 减 乙', '设 减法 为 7'],
    '到': ['设 范围 为 从1到10', '设 到位 为 7'],
    '加': ['设 结果 为 甲 加 乙', '设 加法 为 7'],
    '模': ['设 结果 为 甲 模 乙', '设 模组 为 7'],
    '真': ['返回 真', '设 真空 为 对'],
    '空': ['返回 空', '设 空格 为 " "'],
    '除': ['设 结果 为 甲 除 乙', '设 除法 为 7'],
    '列': ['设 列表 为 [1, 2]', '设 列数 为 3'],
    '对': ['设 对象 为 空', '设 对立 为 7'],
    '是': ['如果 是否 那么 返回 1', '设 是否 为 7'],
    '段': ['设 首段 为 段[1]', '设 段落 为 7'],
    '的': ['设 目的 为 7', '如果 对的 那么 返回 1'],
    '类': ['设 类型 为 "int"', '类 名称:', '设 类别 为 7'],
    '自': ['返回 己之姓名', '设 自然 为 7'],
    '配': ['设 配置 为 配[0]', '设 配对 为 7'],
}


def read(f):
    return open(f, encoding='utf-8', errors='replace').read()


def sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def token_seq(text):
    import lexer
    try:
        toks = lexer.Lexer(text, deterministic=True).tokenize()
        return [(x.type.name, x.value) for x in toks if x.type.name not in ('EOF', 'NEWLINE')]
    except Exception as e:
        return ['ERR:' + type(e).__name__]


def set_cs(words):
    """设置 CS 表为给定字集（monkeypatch 模块常量 + 类属性）。"""
    import lexer
    fs = frozenset(words)
    lexer._COMPOUND_SAFE_SINGLE_KEYWORDS = fs
    lexer.Lexer.compound_safe_single_keywords = fs


def diff_seq(a, b, limit=3):
    """返回 token 序列差异的可读摘要。"""
    out = []
    for i in range(max(len(a), len(b))):
        ta = a[i] if i < len(a) else ('<END>', '')
        tb = b[i] if i < len(b) else ('<END>', '')
        if ta != tb:
            out.append('@%d %r -> %r' % (i, ta, tb))
            if len(out) >= limit:
                break
    return out


def main():
    import lexer
    base_cs = sorted(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS)
    assert sorted(CS16) == base_cs, 'CS 表漂移: %s' % base_cs

    # 预读语料 + 基线 token
    print('语料 %d 文件，构建基线 token 序列...' % len(CORPUS))
    texts, base_tokens, base_errs = {}, {}, []
    for f in CORPUS:
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        texts[rel] = read(f)
        seq = token_seq(texts[rel])
        base_tokens[rel] = seq
        if seq and seq[0] == 'ERR:KeyboardInterrupt':
            pass
        if len(seq) == 1 and seq[0].startswith('ERR:'):
            base_errs.append(rel)
    print('基线完成：成功 %d | 既有失败 %d' % (len(base_tokens) - len(base_errs), len(base_errs)))

    # G2/G3 用例的基线
    g2_src = {c: ['段落 主:\n  设 %s 为 7\n  返回 %s\n' % (w, w) for w in ws]
              for c, ws in G2_WORDS.items()}
    g3_src = {c: ['段落 主:\n  %s\n  返回 0\n' % line for line in lines]
              for c, lines in G3_FORMS.items()}
    g2_base = {c: [token_seq(s) for s in ss] for c, ss in g2_src.items()}
    g3_base = {c: [token_seq(s) for s in ss] for c, ss in g3_src.items()}

    evidence = {}
    print('\n%-4s %-6s %-6s %-6s %s' % ('字', 'G1', 'G2', 'G3', '结论'))
    print('-' * 60)
    for c in CS16:
        reduced = [w for w in base_cs if w != c]
        set_cs(reduced)
        # G1
        changed = {}
        for rel, t in texts.items():
            seq = token_seq(t)
            if seq != base_tokens[rel]:
                changed[rel] = diff_seq(base_tokens[rel], seq)
        # G2
        g2_bad = []
        for w, seq in zip(G2_WORDS[c], g2_base[c]):
            cur = token_seq(g2_src[c][G2_WORDS[c].index(w)])
            if cur != seq:
                g2_bad.append({'word': w, 'diff': diff_seq(seq, cur)})
        # G3
        g3_bad = []
        for line, seq in zip(G3_FORMS[c], g3_base[c]):
            cur = token_seq(g3_src[c][G3_FORMS[c].index(line)])
            if cur != seq:
                g3_bad.append({'form': line, 'diff': diff_seq(seq, cur)})
        set_cs(base_cs)  # 恢复

        ok = (not changed) and (not g2_bad) and (not g3_bad)
        verdict = '可删' if ok else '保留'
        evidence[c] = {
            'g1_changed_files': changed, 'g1_changed_count': len(changed),
            'g2_fail': g2_bad, 'g3_fail': g3_bad,
            'g1_pass': not changed, 'g2_pass': not g2_bad, 'g3_pass': not g3_bad,
            'verdict': verdict,
        }
        print('%-4s %-6s %-6s %-6s %s' % (
            c, 'PASS' if not changed else 'FAIL(%d)' % len(changed),
            'PASS' if not g2_bad else 'FAIL', 'PASS' if not g3_bad else 'FAIL',
            verdict))
        if changed:
            for rel, d in list(changed.items())[:3]:
                print('     G1 %s: %s' % (rel, d[:2]))

    out = os.path.join(HARNESS, '_task3_R27_CS表16字逐条验证_证据.json')
    json.dump({'cs16': CS16, 'corpus_files': len(CORPUS),
               'base_err_files': base_errs, 'evidence': evidence},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    deletable = [c for c in CS16 if evidence[c]['verdict'] == '可删']
    print('-' * 60)
    print('可删 %d 字: %s' % (len(deletable), ''.join(deletable)))
    print('保留 %d 字: %s' % (16 - len(deletable),
                              ''.join(c for c in CS16 if c not in deletable)))
    print('证据文件: %s' % out)


if __name__ == '__main__':
    main()
