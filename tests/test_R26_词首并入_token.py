# -*- coding: utf-8 -*-
"""第26轮任务4：词首并入通用化 token 层测试套件。

覆盖面（对应任务书 §任务4）：
  1. TestHeadMergePositive      —— CS 有效词首并入类别（CS ∪ _P0A_HEAD_MERGE_SINGLE = 30 字）
                                   每字 1 个真实感复合名，断言整体成 IDENTIFIER；
  2. TestKeywordPriorityAtHead  —— 多字关键字最长匹配优先于 CS 单字词首并入（段落/接口/跳出/尝试）；
  3. TestHardStmtKeywords       —— 硬语句关键字在词首必须切分（16 词）；
  4. TestOperatorKeywords       —— 运算符关键字在词首（后随空白）必须切分（11 词）；
  5. TestValueLiterals          —— 值字面量 真/假/空 后随空白切分、后随汉字并入；
  6. TestMixedScenarios         —— 并入与切分在同一 token 流中共存；
  7. TestProtectionTableShape   —— 保护表形态断言（CS=16 / 正面类别=22 / 净增量=14 / F=43）；
  8. TestCorpusZeroTokenChange  —— 全语料 token 零变化（基线文件存在时启用）。

前置：light-merge/.venv 的 python；LIGHT_MERGE 环境变量可覆盖源码根。
"""

import json
import os
import sys

import pytest

LIGHT_MERGE_PATH = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
sys.path.insert(0, os.path.join(LIGHT_MERGE_PATH, 'src'))

import lexer  # noqa: E402
from lexer import Lexer  # noqa: E402


# ── 词首并入有效类别 = CS ∪ 正面类别（30 字，与第25轮原 CS 30 字一致）──
HEAD_MERGE_WORDS = [
    '列', '段', '空', '真', '的', '则', '对', '长',
    '过', '自', '是', '出', '引', '加', '减', '乘',
    '除', '类', '模', '接', '试', '跳', '首', '末',
    '余', '配', '例', '断', '常', '到',
]

# 每字一个真实感复合名（已实测在词首位置并入 IDENTIFIER）
HEAD_MERGE_NAMES = {
    '列': '列数', '段': '段数', '空': '空格', '真': '真的', '的': '的确',
    '则': '规则', '对': '对象', '长': '长度', '过': '过程', '自': '自己',
    '是': '是否', '出': '出错', '引': '引号', '加': '加法', '减': '减法',
    '乘': '乘法', '除': '除法', '类': '类别', '模': '模拟', '接': '接数',
    '试': '试数', '跳': '跳数', '首': '首字母', '末': '月末', '余': '余额',
    '配': '配置', '例': '例如', '断': '断言', '常': '常数', '到': '到达',
}

HARD_STMT_KEYWORDS = [
    '如果', '那么', '否则', '段落', '函数', '类型', '捕获', '等待',
    '设', '己', '返回', '尝试', '为', '打印', '导入', '导出',
]

OPERATOR_KEYWORDS = [
    '加', '减', '乘', '除', '模', '余', '与', '或', '非', '等于', '不等于',
]

VALUE_LITERALS = ['真', '假', '空']

CORPUS_BASELINE = os.path.join(
    os.environ.get('LIGHARNESS', r'G:\dswork\duan-light-merge\lightharness'),
    '_task4_R26_语料token基线.json')


def tokenize_text(text):
    """返回 [(type_name, value)]，保留 EOF 便于边界断言。"""
    tokens = Lexer(text, deterministic=True).tokenize()
    return [(t.type.name, t.value) for t in tokens]


def stream(text):
    """返回去除 EOF/NEWLINE 的可见 token 流。"""
    return [(k, v) for k, v in tokenize_text(text) if k not in ('EOF', 'NEWLINE')]


def assert_identifier(tokens, expected_name, idx=0):
    kind, value = tokens[idx]
    assert kind == 'IDENTIFIER', (
        '期望 IDENTIFIER，实得 %s（%r）' % (kind, value))
    assert value == expected_name, (
        "期望标识符 '%s'，实得 '%s'" % (expected_name, value))


def assert_keyword(tokens, expected_kw, idx=0):
    kind, value = tokens[idx]
    assert kind == 'KEYWORD', (
        '期望 KEYWORD，实得 %s（%r）' % (kind, value))
    assert value == expected_kw, (
        "期望关键字 '%s'，实得 '%s'" % (expected_kw, value))


def keyword_index(tokens, kw):
    for i, (kind, value) in enumerate(tokens):
        if kind == 'KEYWORD' and value == kw:
            return i
    return -1


# ════════════════════════════════════════════════════════════════════
# 1. 正向：30 字词首并入
# ════════════════════════════════════════════════════════════════════
class TestHeadMergePositive:
    """CS 有效词首并入类别 30 字：词首 + 后随汉字 → 整体 IDENTIFIER。"""

    @pytest.mark.parametrize('word', HEAD_MERGE_WORDS)
    def test_head_merge(self, word):
        name = HEAD_MERGE_NAMES[word]
        tokens = stream('%s 为 7' % name)
        assert_identifier(tokens, name, 0)

    @pytest.mark.parametrize('word', HEAD_MERGE_WORDS)
    def test_head_merge_at_assignment_target(self, word):
        """词首并入名可作「设」的赋值目标。"""
        name = HEAD_MERGE_NAMES[word]
        tokens = stream('设 %s 为 7' % name)
        assert_keyword(tokens, '设', 0)
        assert_identifier(tokens, name, 1)

    @pytest.mark.parametrize('word', HEAD_MERGE_WORDS)
    def test_head_merge_not_split_into_keyword(self, word):
        """词首并入后不得残留该单字关键字 token。"""
        name = HEAD_MERGE_NAMES[word]
        tokens = stream('%s 为 7' % name)
        assert (word, ) not in [(k, v) for k, v in tokens if k == 'KEYWORD'], (
            '%s 未被并入，仍输出 KEYWORD' % word)


# ════════════════════════════════════════════════════════════════════
# 2. 多字关键字最长匹配优先
# ════════════════════════════════════════════════════════════════════
class TestKeywordPriorityAtHead:
    """多字关键字与 CS 单字词首冲突时，最长关键字匹配优先（仍输出 KEYWORD）。"""

    @pytest.mark.parametrize('kw,head,rest', [
        ('段落', '段落数', '5'),
        ('接口', '接口', '"API"'),
        ('跳出', '跳出', '"循环"'),
        ('尝试', '尝试', '"执行"'),
    ])
    def test_multichar_keyword_wins(self, kw, head, rest):
        tokens = stream('%s 为 %s' % (head, rest))
        assert_keyword(tokens, kw, 0)


# ════════════════════════════════════════════════════════════════════
# 3. 硬语句关键字必须切分
# ════════════════════════════════════════════════════════════════════
class TestHardStmtKeywords:
    """硬语句关键字在词首必须切分为 KEYWORD。"""

    def test_如果(self):
        t = stream('如果 真 那么')
        assert_keyword(t, '如果', 0)
        assert_keyword(t, '真', 1)
        assert_keyword(t, '那么', 2)

    def test_否则如果(self):
        """否则如果 由 否则 + 如果 两个关键字构成（词法层不合并）。"""
        t = stream('否则如果 条件')
        assert_keyword(t, '否则', 0)
        assert_keyword(t, '如果', 1)
        assert_identifier(t, '条件', 2)

    def test_设_为(self):
        t = stream('设 X 为 5')
        assert_keyword(t, '设', 0)
        assert_identifier(t, 'X', 1)
        assert_keyword(t, '为', 2)

    def test_返回(self):
        t = stream('返回 5')
        assert_keyword(t, '返回', 0)

    def test_尝试(self):
        t = stream('尝试:')
        assert_keyword(t, '尝试', 0)

    def test_捕获(self):
        t = stream('捕获 异常 错误:')
        assert_keyword(t, '捕获', 0)
        assert_identifier(t, '异常', 1)
        assert_identifier(t, '错误', 2)

    def test_打印(self):
        t = stream('打印 "hello"')
        assert_keyword(t, '打印', 0)

    def test_导入(self):
        t = stream('导入 模块')
        assert_keyword(t, '导入', 0)

    def test_导出(self):
        t = stream('导出 函数')
        assert_keyword(t, '导出', 0)

    def test_段落(self):
        t = stream('段落 名:')
        assert_keyword(t, '段落', 0)
        assert_identifier(t, '名', 1)

    def test_类型(self):
        t = stream('类型 为 "int"')
        assert_keyword(t, '类型', 0)

    def test_函数(self):
        t = stream('函数 名 接收 参数:')
        assert_keyword(t, '函数', 0)

    def test_等待(self):
        t = stream('等待 1')
        assert_keyword(t, '等待', 0)

    def test_己(self):
        t = stream('设 己 为 5')
        assert_keyword(t, '设', 0)
        assert_keyword(t, '己', 1)
        assert_keyword(t, '为', 2)

    def test_否则(self):
        t = stream('否则:')
        assert_keyword(t, '否则', 0)

    def test_那么(self):
        t = stream('如果 真 那么')
        assert_keyword(t, '那么', 2)


# ════════════════════════════════════════════════════════════════════
# 4. 运算符关键字必须切分
# ════════════════════════════════════════════════════════════════════
class TestOperatorKeywords:
    """运算符在词首且后随空白时必须切分为 KEYWORD（词中才并入）。"""

    def test_加(self):
        t = stream('甲 加 乙')
        assert_identifier(t, '甲', 0)
        assert_keyword(t, '加', 1)
        assert_identifier(t, '乙', 2)

    @pytest.mark.parametrize('op', ['减', '乘', '除', '模', '与', '或'])
    def test_binary_op(self, op):
        t = stream('甲 %s 乙' % op)
        assert_keyword(t, op, 1)

    def test_非(self):
        t = stream('非 真')
        assert_keyword(t, '非', 0)
        assert_keyword(t, '真', 1)

    def test_等于(self):
        t = stream('甲 等于 乙')
        assert_keyword(t, '等于', 1)

    def test_不等于(self):
        t = stream('甲 不等于 乙')
        assert_keyword(t, '不等于', 1)

    def test_余_is_not_operator(self):
        """余 属 CS 字但非表达式运算符：词首后随汉字并入、后随空白切分。"""
        assert_identifier(stream('余额 为 100'), '余额', 0)
        assert_keyword(stream('甲 余 乙'), '余', 1)

    @pytest.mark.parametrize('op', OPERATOR_KEYWORDS)
    def test_operator_not_merged_when_followed_by_space(self, op):
        t = stream('甲 %s 乙' % op)
        assert_keyword(t, op, 1)  # %s 后随空白时应切分

    @pytest.mark.parametrize('op', ['加', '减', '乘', '除', '模'])
    def test_operator_merges_when_followed_by_han(self, op):
        """运算符后随汉字应并入标识符（词中位置）。"""
        name = '%s法' % op
        assert_identifier(stream('%s 为 "x"' % name), name, 0)


# ════════════════════════════════════════════════════════════════════
# 5. 值字面量
# ════════════════════════════════════════════════════════════════════
class TestValueLiterals:
    """真/假/空：后随空白 → 值字面量；后随汉字 → 并入标识符。"""

    @pytest.mark.parametrize('lit', VALUE_LITERALS)
    def test_literal_split_when_followed_by_space(self, lit):
        t = stream('返回 %s' % lit)
        assert_keyword(t, '返回', 0)
        assert_keyword(t, lit, 1)

    def test_真_followed_by_han_merges(self):
        assert_identifier(stream('真的 为 对'), '真的', 0)

    def test_空_followed_by_han_merges(self):
        assert_identifier(stream('空格 为 ""'), '空格', 0)

    def test_假_is_always_keyword(self):
        """假 在词首排除集内（值字面量），即使后随汉字也不并入标识符。"""
        t = stream('假名 为 "x"')
        assert_keyword(t, '假', 0)
        assert_identifier(t, '名', 1)

    @pytest.mark.parametrize('lit', VALUE_LITERALS)
    def test_literal_still_keyword_in_expression(self, lit):
        t = stream('设 X 为 %s' % lit)
        assert_keyword(t, lit, 3)


# ════════════════════════════════════════════════════════════════════
# 6. 混合场景
# ════════════════════════════════════════════════════════════════════
class TestMixedScenarios:
    """并入与切分在同一 token 流中共存。"""

    def test_出错_with_如果(self):
        t = stream('设 出错 为 7')
        assert_keyword(t, '设', 0)
        assert_identifier(t, '出错', 1)
        assert_keyword(t, '为', 2)
        t2 = stream('如果 出错 > 5:')
        assert_keyword(t2, '如果', 0)
        assert_identifier(t2, '出错', 1)

    def test_类型_always_keyword(self):
        """类型 是多字关键字，恒切分（词首/词中均不变标识符）。"""
        assert_keyword(stream('类型 为 "int"'), '类型', 0)
        assert_keyword(stream('设 类型 为 "int"'), '类型', 1)

    def test_设置_with_设(self):
        t = stream('设 设置 为 真')
        assert_keyword(t, '设', 0)
        assert_identifier(t, '设置', 1)
        assert_keyword(t, '为', 2)
        assert_keyword(t, '真', 3)

    def test_加法_with_加_operator(self):
        assert_identifier(stream('加法 为 "运算"'), '加法', 0)
        t = stream('1 加 2')
        assert_keyword(t, '加', 1)

    def test_真的_with_返回(self):
        t = stream('设 真的 为 真')
        assert_identifier(t, '真的', 1)
        assert_keyword(t, '真', 3)

    def test_空格_with_空_literal(self):
        t = stream('设 空格 为 " "')
        assert_identifier(t, '空格', 1)
        assert_keyword(stream('设 空值 为 空'), '空', 3)

    def test_类_with_类别_分类(self):
        t = stream('类 类别:')
        assert_keyword(t, '类', 0)
        assert_identifier(t, '类别', 1)
        t2 = stream('属性 分类 等于 "子类型"')
        assert_identifier(t2, '分类', 1)

    def test_之_member_separator(self):
        """之 是成员分隔符，恒切分（R24 L-153 守护）。"""
        t = stream('对象之姓名')
        assert_identifier(t, '对象', 0)
        assert_keyword(t, '之', 1)
        assert_identifier(t, '姓名', 2)

    def test_对于_merged(self):
        assert_identifier(stream('设 对于 为 "针对"'), '对于', 1)

    def test_是否为_merged(self):
        t = stream('设 是否为 为 真')
        assert_identifier(t, '是否为', 1)
        assert_keyword(t, '为', 2)
        assert_keyword(t, '真', 3)

    def test_异常_with_常数(self):
        assert_identifier(stream('设 异常 为 "错误"'), '异常', 1)
        assert_identifier(stream('设 常数 为 3.14'), '常数', 1)

    def test_对于_对象_both_merged(self):
        t = stream('设 对于 为 "针对"')
        assert_identifier(t, '对于', 1)
        t2 = stream('设 对象 为 "实例"')
        assert_identifier(t2, '对象', 1)


# ════════════════════════════════════════════════════════════════════
# 7. 保护表形态断言
# ════════════════════════════════════════════════════════════════════
class TestProtectionTableShape:
    """保护表形态：R27 后 CS 残部 2 字（列/类），正面类别 22 字，
    DUAL 正面规则 8 字（R27 任务3 后口径；R26 时刻为 CS16/HM22/并集30）。"""

    def test_CS_table_cleared(self):
        assert len(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0, (
            'R28 任务3 后 CS 表应清零，实得 %s'
            % sorted(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS))

    def test_head_merge_class_exists(self):
        hm = lexer._P0A_HEAD_MERGE_SINGLE
        assert hm is not None
        assert len(hm) == 22, '词首并入正面类别应为 22 字，实得 %d' % len(hm)

    def test_head_split_class_exists(self):
        hs = lexer._P0A_HEAD_SPLIT_SINGLE
        assert hs is not None
        assert len(hs) == 42, '词首切分排除集应为 42 字，实得 %d' % len(hs)

    def test_effective_head_merge_with_dual_is_30(self):
        union = (lexer._COMPOUND_SAFE_SINGLE_KEYWORDS
                 | lexer._P0A_HEAD_MERGE_SINGLE | lexer._P0A_HEAD_MERGE_DUAL)
        assert len(union) == 30, (
            'CS ∪ HM ∪ DUAL 应为 30 字（= 第25轮原 CS），实得 %d' % len(union))
        assert set(union) == set(HEAD_MERGE_WORDS) | set(
            '乘减到加模真空除')

    def test_removed_14_covered_by_head_merge(self):
        removed = lexer._R26_CS_REMOVED
        assert len(removed) == 14, '任务3 移除的 CS 字应为 14 个'
        assert removed <= lexer._P0A_HEAD_MERGE_SINGLE, (
            '移除的 14 字必须全部由词首并入正面类别覆盖：%s'
            % sorted(removed - lexer._P0A_HEAD_MERGE_SINGLE))

    def test_r27_removed_6_covered_by_head_merge(self):
        removed = lexer._R27_CS_REMOVED
        assert len(removed) == 6, 'R27 任务3 移除的 B类 CS 字应为 6 个'
        assert removed <= lexer._P0A_HEAD_MERGE_SINGLE, (
            'R27 移除的 6 字必须全部由词首并入正面类别覆盖：%s'
            % sorted(removed - lexer._P0A_HEAD_MERGE_SINGLE))

    def test_head_merge_subset_of_trailing_class_F(self):
        assert lexer._P0A_HEAD_MERGE_SINGLE <= set(lexer.Lexer._TRAILING_ALIAS_CLASS), (
            '词首并入正面类别 ⊆ R25 词尾类别 F')

    def test_trailing_class_F_is_43(self):
        assert len(lexer.Lexer._TRAILING_ALIAS_CLASS) == 43, (
            'R25 词尾类别 F 应为 43 字，实得 %d' % len(lexer.Lexer._TRAILING_ALIAS_CLASS))

    def test_class_attribute_still_exposed(self):
        """嵌入式扫描仍引用实例属性 compound_safe_single_keywords。"""
        lxr = Lexer('设 列数 为 3', deterministic=True)
        assert len(lxr.compound_safe_single_keywords) == 0

    def test_stmt_head_single_is_21(self):
        assert len(lexer._R26_STMT_HEAD_SINGLE) == 21, (
            '单字语句关键字排除集应为 21 字，实得 %d' % len(lexer._R26_STMT_HEAD_SINGLE))


# ════════════════════════════════════════════════════════════════════
# 8. 全语料 token 零变化
# ════════════════════════════════════════════════════════════════════
class TestCorpusZeroTokenChange:
    """全语料 token 零变化：以 _task4_R26_语料token基线.json 为参照。"""

    @pytest.fixture(scope='class')
    def baseline(self):
        if not os.path.exists(CORPUS_BASELINE):
            pytest.skip('未找到语料基线 %s（先运行 _antirun_r26_t4_全量反跑.py --baseline）'
                        % CORPUS_BASELINE)
        with open(CORPUS_BASELINE, encoding='utf-8') as fh:
            return json.load(fh)

    def test_fingerprint_unchanged(self, baseline):
        """聚合指纹必须与基线一致（词首并入通用化为等价重写）。"""
        import hashlib
        current = lexer.__dict__.get('_R26_CORPUS_FINGERPRINT')
        if current is None:
            pytest.skip('当前 lexer 未暴露 _R26_CORPUS_FINGERPRINT，'
                        '请用 _antirun_r26_t4_全量反跑.py 比对')
        assert current == baseline.get('corpus_aggregate_fingerprint'), (
            '语料聚合指纹变化：%s -> %s'
            % (baseline.get('corpus_aggregate_fingerprint'), current))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
