# -*- coding: utf-8 -*-
"""T-0532 判据：T-0496 ~ T-0531 工具面强化批次的文档收口。

只读三份文档 + 本判据，不跑 .light、不改 src：
  1. CHANGELOG.md 顶部 [未发布] 节必须新增本批小节，含四个卡号锚点、两个口径词与三个实测数字；
  2. docs/功能对标/对标清单.json 的 条目 里 #388 起至少 8 条，id 覆盖六条线，证据非空且文件真实存在；
  3. docs/功能对标/模式规格.md 的「按需披露」紧邻参数下沉、「软提示」紧邻预算信号。

反证（内存级篡改，不动仓库文件）：
  - 删掉 CHANGELOG 里任一卡号锚点 → _check_changelog 抛 AssertionError；
  - 清空任一新条目的 证据 → _check_ledger 抛 AssertionError。
"""
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG_REL = 'CHANGELOG.md'
LEDGER_REL = os.path.join('docs', '功能对标', '对标清单.json')
SPEC_REL = os.path.join('docs', '功能对标', '模式规格.md')

ANCHORS = ('T-0496', 'T-0518', 'T-0528', 'T-0531')
LINE_ANCHORS = ('T-0497', 'T-0498', 'T-0502', 'T-0504', 'T-0508',
                'T-0512', 'T-0513', 'T-0515', 'T-0517',
                'T-0522', 'T-0526', 'T-0529', 'T-0530')
TERMS = ('参数下沉', '预算信号')
FACTS = ('559 → 206', '-63%', '6/6', '5/6', '641')

NEW_MIN = 388
REQUIRED_IDS = (
    'T-0496-domain', 'T-0502-semantic-name', 'T-0504-error-envelope',
    'T-0508-reversibility', 'T-0512-budget', 'T-0515-trace',
    'T-0517-result-envelope', 'T-0528-ci-ledger',
)
ENTRY_FIELDS = ('编号', 'id', '功能', '原版包', '光明模块',
                '状态', '证据', '本轮目标', '反跑判据', '语言缺陷')
EVIDENCE_RE = re.compile(r'^(.+?\.(?:light|py|md|json|txt))(?=$|[：:（( ])')


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def _load_ledger():
    return json.loads(_read(LEDGER_REL))


def _unreleased_section(text):
    start = '## [未发布]'
    i = text.find(start)
    assert i >= 0, 'CHANGELOG 缺 %s 节' % start
    j = text.find('## [', i + len(start))
    assert j > i, 'CHANGELOG 的 %s 节没有结束边界' % start
    return text[i:j]


def _check_changelog(text):
    section = _unreleased_section(text)
    for anchor in ANCHORS:
        assert anchor in section, '顶部 [未发布] 节缺卡号锚点 %s' % anchor
    for anchor in LINE_ANCHORS:
        assert anchor in section, '顶部 [未发布] 节缺六条线/修复卡锚点 %s' % anchor
    for term in TERMS:
        assert term in section, '顶部 [未发布] 节缺口径词 %s' % term
    for fact in FACTS:
        assert fact in section, '顶部 [未发布] 节缺实测数字 %s（必须与收口报告一致）' % fact
    # 本批只追加：T-0489 的历史小节必须原样在位
    assert '### 系统提示上下文接线：环境 / 权限 / 技能 / MCP 进真实会话（T-0489）' in section, (
        'T-0489 历史小节被覆盖或丢失——CHANGELOG 只许追加新节')


def _new_entries(data):
    entries = data.get('条目')
    assert isinstance(entries, list), '对标清单缺 条目 数组'
    return [e for e in entries if isinstance(e.get('编号'), int) and e['编号'] >= NEW_MIN]


def _check_evidence_shape(entry):
    for item in entry['证据']:
        assert isinstance(item, str) and item.strip(), (
            '#%s 的 证据 里有空项：%r' % (entry['编号'], item))
        match = EVIDENCE_RE.match(item)
        assert match, '#%s 的证据没指向文件：%r' % (entry['编号'], item)
        rel = match.group(1).replace('\\', '/')
        assert os.path.exists(os.path.join(ROOT, rel)), (
            '#%s 的证据文件不存在：%s' % (entry['编号'], rel))


def _check_ledger(data):
    history = [e for e in data['条目'] if isinstance(e.get('编号'), int) and e['编号'] < NEW_MIN]
    assert len(history) == 381, (
        '历史条目应为 381 条，实际 %d 条——疑似覆盖旧条目' % len(history))
    by_number = {e['编号']: e for e in history}
    assert by_number[381].get('id') == 'T-0489-environment', (
        '#381 不是 T-0489 的 environment 条目——历史条目被改写')
    assert by_number[387].get('id') == 'T-0489-summary', (
        '#387 不是 T-0489-summary——历史条目尾部被改写')

    new = _new_entries(data)
    assert len(new) >= 8, '条目 #388 起至少 8 条，实际 %d 条' % len(new)
    numbers = sorted(e['编号'] for e in new)
    assert numbers == list(range(NEW_MIN, NEW_MIN + len(new))), (
        '新条目编号必须从 388 起连续，实际 %r' % numbers)
    ids = [e.get('id') for e in new]
    assert len(set(ids)) == len(ids), '新条目 id 有重复：%r' % ids
    assert len(set(REQUIRED_IDS) & set(ids)) >= 6, (
        '新条目 id 未覆盖六条线（至少 6/8）：%r' % sorted(set(REQUIRED_IDS) - set(ids)))

    for entry in new:
        for field in ENTRY_FIELDS:
            assert field in entry, '#%s 缺字段 %s' % (entry['编号'], field)
        assert entry['id'] and isinstance(entry['id'], str), '#%s 的 id 为空' % entry['编号']
        for field in ('功能', '状态', '本轮目标', '反跑判据'):
            value = entry[field]
            assert isinstance(value, str) and value.strip(), (
                '#%s 的 %s 为空' % (entry['编号'], field))
        assert isinstance(entry['证据'], list) and entry['证据'], (
            '#%s 的 证据 必须是非空数组' % entry['编号'])
        _check_evidence_shape(entry)
        assert isinstance(entry['语言缺陷'], list), '#%s 的 语言缺陷 必须是数组' % entry['编号']


def _nearest_distance(text, left, right):
    lefts = [m.start() for m in re.finditer(re.escape(left), text)]
    rights = [m.start() for m in re.finditer(re.escape(right), text)]
    assert lefts, '模式规格缺关键词 %s' % left
    assert rights, '模式规格缺关键词 %s' % right
    return min(abs(a - b) for a in lefts for b in rights)


def _check_spec(text):
    for keyword, anchor in (('按需披露', '参数下沉'), ('软提示', '预算信号')):
        distance = _nearest_distance(text, keyword, anchor)
        assert distance < 200, (
            '「%s」与「%s」相距 %d 字符，口径没有写在一起' % (keyword, anchor, distance))
    assert '不熔断' in text, '预算信号口径必须写明「不熔断」'
    assert '下沉不等于删除' in text, '参数下沉口径必须写明「下沉不等于删除」'


def test_changelog_顶部未发布节含本批锚点与实测数字():
    _check_changelog(_read(CHANGELOG_REL))


def test_对标清单_新增条目覆盖六条线且证据可点():
    _check_ledger(_load_ledger())


def test_模式规格_按需披露与软提示口径相邻():
    _check_spec(_read(SPEC_REL))


def test_反证_删卡号锚点转红():
    text = _read(CHANGELOG_REL)
    assert 'T-0528' in text
    mutated = text.replace('T-0528', 'T-9999', 1)
    with pytest.raises(AssertionError):
        _check_changelog(mutated)


def test_反证_清空证据转红():
    data = _load_ledger()
    new = _new_entries(data)
    assert new, '没有 #388 起的新条目，反证无从谈起'
    new[0]['证据'] = []
    with pytest.raises(AssertionError):
        _check_ledger(data)


def test_反证_删口径词转红():
    text = _read(CHANGELOG_REL)
    mutated = text.replace('预算信号', '预算额度')
    with pytest.raises(AssertionError):
        _check_changelog(mutated)
