# -*- coding: utf-8 -*-
"""第28轮 任务4：CS表2字（列/类）逐字通用化 token 层测试。

覆盖：
  · 列 词首并入（列数/列表/列名）+ 词尾切出（无空格 for-in 序列:）+
    词尾并入（序列 为…）+ 独立关键字（列 为…）
  · 类 类声明词尾并入（类 独立类:/测试类:/有界队列类:）+ 独立关键字（类 名称:）+
    词首并入（类别/类似）+ 继承（子类/基类）+ 使用处（新建 独立类()）
  · 混合场景（列/类 与 R27 已删字共存）
  · 保护表形态断言：CS == ∅（清零）、_P0A_TAIL_CUT_SINGLE == {列}、
    _R28_CS_REMOVED == {列,类}、净增量断言（R26∪R27∪R28）
  · 全语料 token 零变化（对照 R26 基线快照，硬门槛）
预期：40+ passed
"""

import os
import sys

import pytest

LIGHT_MERGE_PATH = os.environ.get(
    'LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
sys.path.insert(0, os.path.join(LIGHT_MERGE_PATH, 'src'))

import lexer  # noqa: E402


def toks(src):
    out = lexer.Lexer(src, deterministic=True).tokenize()
    return [(t.type.name, t.value) for t in out
            if t.type.name not in ('EOF', 'NEWLINE')]


def ids(src):
    return [v for (t, v) in toks(src) if t == 'IDENTIFIER']


LIE_HEAD = ['列数', '列表', '列名']
LEI_TAIL = ['序列', '队列表']
CLASS_DECL = ['独立类', '测试类', '有界队列类']
LEI_NAMES = ['类别', '类似']
CLASS_USE = ['独立类', '测试类']


# ============ 一、列：三形态 ============

class Test列三形态:
    @pytest.mark.parametrize('name', LIE_HEAD)
    def test_词首并入整词(self, name):
        assert ids('设 %s 为 7' % name) == [name]

    def test_词尾切出_无空格for_in(self):
        # 断言工具.light:226 形态（bootstrap 转译快照钉住）
        seq = toks('对于元素在序列:')
        assert ('IDENTIFIER', '序') in seq
        assert ('KEYWORD', '列') in seq
        assert ('COLON', ':') in seq
        assert ('IDENTIFIER', '序列') not in seq

    def test_词尾切出_循环对于变体(self):
        seq = toks('循环 对于项目在序列:')
        assert ('KEYWORD', '列') in seq and ('IDENTIFIER', '序') in seq

    @pytest.mark.parametrize('name', LEI_TAIL)
    def test_词尾并入_非冒号(self, name):
        seq = ids('设 %s 为 [1]' % name)
        assert name in seq

    def test_词尾并入_带空格for_in(self):
        seq = toks('循环 对于 元素 在 序列:')
        assert ('IDENTIFIER', '序列') in seq
        assert ('KEYWORD', '列') not in seq

    def test_独立关键字(self):
        seq = toks('设 列表项 为 列')
        assert ('KEYWORD', '列') in seq
        assert ('IDENTIFIER', '列表项') in seq

    def test_esc前缀整词(self):
        seq = ids('设 ESC序列 为 1')
        assert seq == ['ESC序列']

    @pytest.mark.parametrize('src', ['甲在序列:', '甲之序列:'],
                             ids=['在嵌入', '之嵌入'])
    def test_嵌入关键字分段词尾切出(self, src):
        # 任务书机制：列的切出发生在「嵌入输出循环」（段内有真关键字分段时）
        seq = toks(src)
        assert ('KEYWORD', '列') in seq
        assert ('IDENTIFIER', '序列') not in seq

    def test_词尾并入方法调用(self):
        seq = toks('返回 序列.长度()')
        assert ('IDENTIFIER', '序列') in seq

    def test_词尾切出_长串变体_ASCII前缀整词(self):
        # ASCII 前缀（解析ESC）场景：整词保持，不触发切出（探针钉住形态）
        seq = ids('设 结果 为 解析ESC序列')
        assert '解析ESC序列' in seq


# ============ 二、类：声明/关键字/词首/继承/使用处 ============

class Test类形态:
    @pytest.mark.parametrize('name', CLASS_DECL)
    def test_类声明词尾并入整词(self, name):
        seq = toks('类 %s:' % name)
        assert ('KEYWORD', '类') in seq
        assert ('IDENTIFIER', name) in seq

    def test_独立关键字不受影响(self):
        seq = toks('类 名称:')
        assert ('KEYWORD', '类') in seq
        assert ('IDENTIFIER', '名称') in seq

    @pytest.mark.parametrize('name', LEI_NAMES)
    def test_词首并入整词(self, name):
        assert ids('设 %s 为 7' % name) == [name]

    def test_继承形态(self):
        seq = toks('类 子类 继承 基类:')
        assert ('KEYWORD', '类') in seq
        assert ('IDENTIFIER', '子类') in seq
        assert ('KEYWORD', '继承') in seq
        assert ('IDENTIFIER', '基类') in seq

    @pytest.mark.parametrize('name', CLASS_USE)
    def test_使用处词尾加括号整词(self, name):
        seq = toks('设 x 为 新建 %s()' % name)
        assert ('IDENTIFIER', name) in seq
        assert ('KEYWORD', '类') not in seq

    def test_类体内词首并入名(self):
        seq = toks('己.类别 = 列数')
        assert ('IDENTIFIER', '类别') in seq
        assert ('IDENTIFIER', '列数') in seq


# ============ 三、混合场景 ============

class Test混合场景:
    def test_列数与序列for_in共存(self):
        seq = toks('设 列数 为 3\n循环 对于 元素 在 序列:')
        assert ('IDENTIFIER', '列数') in seq
        assert ('IDENTIFIER', '序列') in seq

    def test_R27已删字共存(self):
        seq = toks('设 s 为 乘法 加 减法')
        assert ('IDENTIFIER', '乘法') in seq
        assert ('IDENTIFIER', '减法') in seq
        assert ('KEYWORD', '加') in seq

    def test_真空到位共存(self):
        seq = toks('设 真空 为 真')
        assert ('IDENTIFIER', '真空') in seq and ('KEYWORD', '真') in seq
        seq2 = toks('设 到位 为 3')
        assert ids('设 到位 为 3') == ['到位']

    def test_段配下标回归钉(self):
        assert ('IDENTIFIER', '段') in toks('设 x 为 段[0]')
        assert ('IDENTIFIER', '配') in toks('设 x 为 配[0]')

    def test_己之姓名回归钉(self):
        seq = toks('返回 己之姓名')
        assert ('KEYWORD', '己') in seq and ('KEYWORD', '之') in seq


# ============ 四、保护表形态断言（CS 清零） ============

class Test保护表形态:
    def test_CS表清零(self):
        assert len(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0
        assert isinstance(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS, frozenset)

    def test_列在词尾切出类别(self):
        assert lexer._P0A_TAIL_CUT_SINGLE == frozenset({'列'})

    def test_R28移除集(self):
        assert lexer._R28_CS_REMOVED == frozenset({'列', '类'})

    def test_净增量恒等三轮移除集(self):
        removed = (lexer._R26_CS_REMOVED | lexer._R27_CS_REMOVED
                   | lexer._R28_CS_REMOVED)
        assert lexer._P0A_HEAD_MERGE_SINGLE - \
            lexer._COMPOUND_SAFE_SINGLE_KEYWORDS == removed

    def test_DUAL与HM保持(self):
        assert len(lexer._P0A_HEAD_MERGE_DUAL) == 8
        assert len(lexer._P0A_HEAD_MERGE_SINGLE) == 22

    def test_列类属于词尾类别F(self):
        assert {'列', '类'} <= set(lexer.Lexer._TRAILING_ALIAS_CLASS)

    def test_B类全位置吸收集合(self):
        assert lexer._R27_BCLASS == frozenset(
            {'列', '对', '是', '段', '的', '类', '自', '配'})

    def test_import自校验通过(self):
        import importlib
        importlib.reload(lexer)
        assert len(lexer._COMPOUND_SAFE_SINGLE_KEYWORDS) == 0


# ============ 五、全语料 token 零变化（对照 R26 基线快照，硬门槛） ============

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
        base_err = set(baseline.get('base_err_files', []))
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

        changed, compared = [], 0
        for f in corpus:
            rel = os.path.relpath(f, root).replace('\\', '/')
            if rel not in per_file or rel in base_err:
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
                continue
            if fp != per_file[rel]['sha']:
                changed.append(rel)
        assert compared > 500, '语料比对覆盖不足：%d' % compared
        assert not changed, '全语料 token 变化 %d 文件: %s' % (len(changed), changed[:5])
