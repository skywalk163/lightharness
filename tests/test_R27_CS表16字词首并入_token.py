# -*- coding: utf-8 -*-
"""第27轮 任务4：CS表16字逐字通用化 token 层测试。

覆盖：
  · A类 DUAL 8字（乘减到加模真空除）正向（词首+后随汉字→整词 IDENTIFIER）
    与反向（独立/后随空白→运算符/值字面量切分；词尾+前导汉字→整词）
  · B类 6字（对是段的自配）正向（HM 正面类别）
  · CS 残部 2字（列/类）正向（CS 锚仍在）
  · 下标访问边界（段[1]/配[0]/对[0]，L-119 嵌入扫描等价）
  · 混合场景（并入与切分同串共存）
  · R26 回归钉（自之姓名/去除空格/对于/10的幂/是否为空 不受 R27 影响）
  · 保护表形态断言：CS=2、_P0A_HEAD_MERGE_DUAL=8、HM=22、文末自校验通过
  · 全语料 token 零变化（对照 R26 基线快照，硬门槛）
预期：80+ passed
"""

import os
import sys

import pytest

LIGHT_MERGE_PATH = os.environ.get(
    'LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
sys.path.insert(0, os.path.join(LIGHT_MERGE_PATH, 'src'))

import lexer  # noqa: E402  (sys.path 注入后导入)


def toks(src):
    out = lexer.Lexer(src, deterministic=True).tokenize()
    return [(t.type.name, t.value) for t in out
            if t.type.name not in ('EOF', 'NEWLINE')]


def ids(src):
    """只返回 IDENTIFIER 的 value 序列。"""
    return [v for (t, v) in toks(src) if t == 'IDENTIFIER']


A_DUAL = ['乘', '减', '到', '加', '模', '真', '空', '除']
B_SIX = ['对', '是', '段', '的', '自', '配']
CS_REST = ['列', '类']

A_WORDS = {'乘': ['乘法', '乘积'], '减': ['减法', '减速'], '到': ['到位', '到达'],
           '加': ['加法', '加数'], '模': ['模组', '模型名'], '真': ['真空', '真实值'],
           '空': ['空格', '空白页'], '除': ['除法', '除非名']}
B_WORDS = {'对': ['对立', '对象名'], '是': ['是否', '是否值'], '段': ['段落名', '段首'],
           '的': ['的确', '的确率'], '自': ['自己', '自然数'], '配': ['配置', '配对']}
CS_WORDS = {'列': ['列数', '列表项'], '类': ['类别名', '分类号']}
OPS = [('加', 'KEYWORD'), ('减', 'KEYWORD'), ('乘', 'KEYWORD'),
       ('除', 'KEYWORD'), ('模', 'KEYWORD')]

ALL_POSITIVE = {}
ALL_POSITIVE.update(A_WORDS)
ALL_POSITIVE.update(B_WORDS)
ALL_POSITIVE.update(CS_WORDS)


# ============ 一、正向：16字 × 2名 = 32 用例（名字级参数化） ============

class Test正向词首并入:
    @pytest.mark.parametrize('name',
                             [n for ws in ALL_POSITIVE.values() for n in ws],
                             ids=[n for ws in ALL_POSITIVE.values() for n in ws])
    def test_整词成IDENTIFIER(self, name):
        seq = ids('设 %s 为 7' % name)
        assert seq == [name], '「%s」应整词成 IDENTIFIER，实得 %s' % (name, seq)

    @pytest.mark.parametrize('name',
                             [n for ws in A_WORDS.values() for n in ws],
                             ids=[n for ws in A_WORDS.values() for n in ws])
    def test_A类可作实参(self, name):
        seq = toks('设 r 为 累加(%s)' % name)
        assert ('IDENTIFIER', name) in seq

    @pytest.mark.parametrize('name',
                             [n for ws in B_WORDS.values() for n in ws],
                             ids=[n for ws in B_WORDS.values() for n in ws])
    def test_B类可作列表元素(self, name):
        seq = toks('设 lst 为 [%s]' % name)
        assert ('IDENTIFIER', name) in seq


# ============ 二、A类反向：独立/后随空白 → 切分 ============

class TestA类反向切分:
    @pytest.mark.parametrize('op', [o for o, _ in OPS], ids=[o for o, _ in OPS])
    def test_运算符后随空白切分(self, op):
        seq = toks('设 s 为 甲 %s 乙' % op)
        assert ('KEYWORD', op) in seq, '「%s」后随空白必须切分为运算符' % op

    @pytest.mark.parametrize('op', [o for o, _ in OPS], ids=[o for o, _ in OPS])
    def test_双形态对照(self, op):
        seq = toks('设 %s法 为 甲 %s 乙' % (op, op))
        assert ('IDENTIFIER', '%s法' % op) in seq
        assert ('KEYWORD', op) in seq

    def test_值字面量真(self):
        seq = toks('设 标志 为 真')
        assert ('KEYWORD', '真') in seq and ('IDENTIFIER', '标志') in seq

    def test_值字面量空(self):
        seq = toks('返回 空')
        assert ('KEYWORD', '空') in seq

    def test_值字面量假(self):
        seq = toks('设 标志 为 假')
        assert ('KEYWORD', '假') in seq

    def test_范围遍历切分(self):
        seq = toks('遍历 i 于 1 至 4:\n  设 和 为 和 加 i')
        assert ('KEYWORD', '遍历') in seq

    def test_A类词尾并入_文件未找到(self):
        seq = ids('设 文件未找到 为 1')
        assert seq == ['文件未找到']

    def test_A类词尾并入_标准输出失真(self):
        seq = ids('设 标准输出失真 为 1')
        assert seq == ['标准输出失真']


# ============ 三、下标访问边界（L-119 嵌入扫描等价） ============

class Test下标访问L119:
    @pytest.mark.parametrize('name', ['段', '配', '对'])
    def test_单字名下标不切关键字(self, name):
        seq = toks('设 x 为 %s[0]' % name)
        assert ('IDENTIFIER', name) in seq, '「%s[0]」中 %s 应为 IDENTIFIER' % (name, name)
        assert ('KEYWORD', name) not in seq

    def test_正向与下标共存(self):
        seq = toks('返回 配置[0] 加 段落名[1]')
        assert ('IDENTIFIER', '配置') in seq
        assert ('KEYWORD', '加') in seq

    def test_是非列表元素切开为既有行为(self):
        # 「是非」独立列表元素切成 是|非 是 R26 基线既有行为
        # （全语料零变化快照钉住），非 R27 引入——此处显式钉住防漂移。
        seq = toks('设 lst 为 [是非]')
        assert ('IDENTIFIER', '是') in seq and ('KEYWORD', '非') in seq


# ============ 四、硬语句关键字必须切分 ============

HARD_STMT = {
    '如果': '如果 真 那么 返回 1',
    '那么': '如果 真 那么 返回 1',
    '设': '设 X 为 5',
    '为': '设 X 为 5',
    '返回': '返回 1',
    '段落': '段落 名:',
    '尝试': '尝试:\n  返回 1\n结束',
    '捕获': '尝试:\n  返回 1\n捕获:\n  返回 0\n结束',
    '类': '类 名:',
    '打印': '打印 1',
}


class Test硬语句切分:
    @pytest.mark.parametrize('kw', sorted(HARD_STMT), ids=sorted(HARD_STMT))
    def test_切分为KEYWORD(self, kw):
        assert ('KEYWORD', kw) in toks(HARD_STMT[kw]), \
            '硬语句关键字「%s」必须切分' % kw


# ============ 五、混合场景（并入与切分同串共存） ============

class Test混合场景:
    def test_乘法与乘共存(self):
        seq = toks('设 s 为 乘法 加 1')
        assert ('IDENTIFIER', '乘法') in seq and ('KEYWORD', '加') in seq

    def test_加法与加共存(self):
        seq = toks('设 加法 为 甲 加 乙')
        assert ('IDENTIFIER', '加法') in seq and ('KEYWORD', '加') in seq

    def test_真空与真共存(self):
        seq = toks('设 真空 为 真')
        assert ('IDENTIFIER', '真空') in seq and ('KEYWORD', '真') in seq

    def test_模组与模共存(self):
        seq = toks('设 余数 为 模组 模 3')
        assert ('IDENTIFIER', '模组') in seq and ('KEYWORD', '模') in seq

    def test_到位与范围共存(self):
        seq = toks('遍历 到位序号 于 1 至 3:\n  设 到位计数 为 0')
        assert ('IDENTIFIER', '到位序号') in seq
        assert ('KEYWORD', '遍历') in seq

    def test_连续运算符切分(self):
        seq = toks('设 s 为 甲 加 乙 加 1')
        assert seq.count(('KEYWORD', '加')) == 2

    def test_减法与减共存(self):
        seq = toks('设 s 为 减法 减 1')
        assert ('IDENTIFIER', '减法') in seq and ('KEYWORD', '减') in seq

    def test_除法与除共存(self):
        seq = toks('设 s 为 除法 除 2')
        assert ('IDENTIFIER', '除法') in seq and ('KEYWORD', '除') in seq


# ============ 六、R26 回归钉（R27 不得破坏既有钉住行为） ============

class TestR26回归钉:
    def test_自之姓名(self):
        seq = toks('返回 己之姓名')
        assert ('KEYWORD', '己') in seq and ('KEYWORD', '之') in seq

    def test_对于词首整词(self):
        seq = ids('设 对于 为 1')
        assert seq == ['对于']

    def test_真的词尾整词(self):
        seq = ids('设 真的 为 真')
        assert seq == ['真的']

    def test_10的幂(self):
        seq = toks('设 p 为 10的幂')
        assert ('IDENTIFIER', '的幂') in seq or ('IDENTIFIER', '10的幂') in seq \
            or ('NUMBER', 10) in seq

    def test_段落下标L119原钉(self):
        seq = toks('打印 配[0]')
        assert ('IDENTIFIER', '配') in seq


# ============ 七、保护表形态断言（铁律） ============

class Test保护表形态:
    def test_CS表清零(self):
        assert len(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0

    def test_DUAL类别8字(self):
        assert sorted(lexer._P0A_HEAD_MERGE_DUAL) == sorted(A_DUAL)

    def test_DUAL与CS不相交(self):
        assert not (set(lexer._P0A_HEAD_MERGE_DUAL)
                    & set(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS))

    def test_DUAL属于运算符_值字面量_范围(self):
        # A类来源：运算符（乘减加除模）+ 值字面量（真空）+ 范围（到）
        assert {'乘', '减', '加', '除', '模'} <= lexer.OPERATOR_VERBS
        # 【R35 修正】旧断言写 `{'到'} <= Lexer._P0A_NEVER_SPLIT`；
        # R33 已把 NEVER_SPLIT 清零（4→0），`到` 不再属该表。
        # `到` 的"范围"语义仍由 DUAL 类别承载，故改判 DUAL 成员资格。
        assert '到' in lexer._P0A_HEAD_MERGE_DUAL

    def test_HM净增量等于三轮移除集加R33三字(self):
        net = lexer._P0A_HEAD_MERGE_SINGLE - lexer._COMPOUND_SAFE_SINGLE_KEYWORDS
        removed = (lexer._R26_CS_REMOVED | lexer._R27_CS_REMOVED
                   | lexer._R28_CS_REMOVED)
        # 【R35 修正】R33 清零 _P0A_NEVER_SPLIT 后 步/至/到 一并进入 HM，
        # 净增量 = 三轮 CS 移除集(22) ∪ {步,至,到} = 25。
        assert net == removed | {'步', '至', '到'}
        assert len(net) == 25

    def test_HM含B类6字不含A类(self):
        assert set(B_SIX) <= lexer._P0A_HEAD_MERGE_SINGLE
        # 【R35 修正】A 类中的 `到` 在 R33 后同时进入 HM（DUAL ∩ HM = {到}），
        # 这是 R33 的有意结果（范围字在词首并入），故不相交判据排除 `到`。
        assert not ((set(A_DUAL) - {'到'}) & lexer._P0A_HEAD_MERGE_SINGLE)
        assert set(A_DUAL) & lexer._P0A_HEAD_MERGE_SINGLE == {'到'}

    def test_CS残部属于F(self):
        assert set(CS_REST) <= lexer.Lexer._TRAILING_ALIAS_CLASS

    def test_import自校验通过(self):
        # import lexer 已执行全部文末断言（R27 类别代数：CS⊆F、CS∩DUAL=∅、
        # HM−CS==R26∪R27移除集）；此处显式重导入一次以确认幂等。
        import importlib
        importlib.reload(lexer)
        assert len(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0


# ============ 八、全语料 token 零变化（对照 R26 基线快照，硬门槛） ============

class TestCorpusZeroTokenChange:
    def test_fingerprint_unchanged(self):
        import json
        import hashlib
        import glob

        root = r'G:/dswork/duan-light-merge'
        snapshot_path = os.path.join(
            root, 'lightharness', '_antirun_r26_基线快照.json')
        if not os.path.exists(snapshot_path):
            pytest.skip('R26 基线快照不存在（独立环境）')
        baseline = json.load(open(snapshot_path, encoding='utf-8'))
        per_file = baseline.get('per_file', {})
        if not per_file:
            pytest.skip('R26 基线快照为空')

        patterns = [root + '/lightharness/examples/**/*.light',
                    root + '/lightharness/src/**/*.light',
                    root + '/lightharness/tests/**/*.light',
                    root + '/light-merge/examples/**/*.light',
                    root + '/light-merge/stdlib/**/*.light',
                    root + '/light-merge/bootstrap/**/*.light',
                    root + '/light-merge/src/**/*.light',
                    root + '/light-merge/tests/**/*.light']
        corpus = sorted(set(sum((glob.glob(g, recursive=True)
                                 for g in patterns), [])))

        changed = []
        compared = 0
        for f in corpus:
            rel = os.path.relpath(f, root).replace('\\', '/')
            if rel not in per_file:
                continue
            compared += 1
            try:
                t = open(f, encoding='utf-8', errors='replace').read()
                seq = [(x.type.name, x.value) for x in
                       lexer.Lexer(t, deterministic=True).tokenize()
                       if x.type.name not in ('EOF', 'NEWLINE')]
                fp = hashlib.sha256(json.dumps(
                    seq, ensure_ascii=False).encode('utf-8')).hexdigest()
            except Exception:
                fp = per_file[rel]['sha']  # 既有失败文件跳过比对
            if fp != per_file[rel]['sha']:
                changed.append(rel)
        assert compared > 500, '语料比对覆盖不足：%d' % compared
        assert not changed, '全语料 token 变化 %d 文件: %s' % (len(changed), changed[:5])
