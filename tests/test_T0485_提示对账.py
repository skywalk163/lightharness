# -*- coding: utf-8 -*-
"""T-0485 判据：DSH 系统提示 17 条硬规则 → 本仓逐条对账表。

判据只读文档，不跑 .light、不碰 src。钉住的实测数字：
2047（默认提示字数）/ 168（standard 实发工具，88 挂 lightplugin）/
46,868（工具模式 JSON 字符）/ 4000（提示预算）/ 15（标准工具面口径）。
卡面基线 46,870 也必须在场，作为历史对照（差 2 字已在文档第 1 节说明）。

反跑锚点（本卡实测过）：
  - 删掉对账表第 17 行 → test_表格恰好17个数据行 红；
  - 把某行状态列改成占位值（非四值）→ test_状态列只取四个值 红；
  - 删掉差异清单第 1 条（apply_patch 替代）→ test_差异清单含两条替代 红。
  恢复后全绿。
"""
import os
import re

DOC_REL = os.path.join('docs', '功能对标', '提示对账.md')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROMPT_CHARS = 2047
TOOL_COUNT = 168
TOOL_SCHEMA_CHARS = 46868
TOOL_SCHEMA_BASELINE = 46870   # 卡面基线，文档必须保留作对照
BUDGET_CHARS = 4000
STANDARD_SURFACE = 15

STATUSES = {'已有', '本批', '未做', '有意不做'}


def _text():
    with open(os.path.join(ROOT, DOC_REL), encoding='utf-8') as fh:
        return fh.read()


def _between(text, start, end):
    """取 start 行之后、end 行之前的内容；缺任一端点直接断言失败（不让解析静默吞掉）。"""
    i = text.find(start)
    assert i >= 0, '文档缺小节：%s' % start
    j = text.find(end, i)
    assert j > i, '文档缺小节：%s' % end
    return text[i + len(start):j]


def _rows():
    body = _between(_text(), '## 2 逐条对账表', '## 3 ')
    rows = [ln.strip() for ln in body.splitlines() if ln.strip().startswith('|')]
    assert len(rows) >= 3, '对账表连表头都没有：%r' % rows
    data = []
    for ln in rows[2:]:  # 跳过表头 + 分隔行
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        assert len(cells) == 5, '每行必须 5 列（# / 规则 / 本仓 / 状态 / 卡号）：%r' % ln
        data.append(cells)
    return data


def test_文档存在且不超15KB():
    path = os.path.join(ROOT, DOC_REL)
    assert os.path.isfile(path), '缺对账文档：%s' % DOC_REL
    assert os.path.getsize(path) <= 15000, '文档超 15KB：%s 字节' % os.path.getsize(path)


def test_表格恰好17个数据行():
    data = _rows()
    assert len(data) == 17, '对账表必须恰好 17 行（DSH 17 条硬规则），实际 %d 行' % len(data)
    ids = [c[0] for c in data]
    assert ids == [str(i) for i in range(1, 18)], '行号必须 1..17 连续，实际 %r' % ids


def test_英文摘要不超过80字符():
    for cell in _rows():
        summary = cell[1]
        assert summary, '第 %s 行规则摘要为空' % cell[0]
        assert len(summary) <= 80, (
            '第 %s 行摘要 %d 字符，超过 80（不许大段复制上游原文）：%r'
            % (cell[0], len(summary), summary))


def test_状态列只取四个值():
    for cell in _rows():
        status = cell[3]
        assert status, '第 %s 行状态列为空' % cell[0]
        assert status in STATUSES, (
            '第 %s 行状态 %r 不在四值白名单 %s' % (cell[0], status, sorted(STATUSES)))


def test_未做行必须给卡号或理由():
    for cell in _rows():
        if cell[3] == '未做':
            assert ('T-04' in cell[4]) or ('有意不做' in cell[4]), (
                '第 %s 行记了 未做，但第五列既没有卡号也没有理由：%r' % (cell[0], cell[4]))


def _diff_items():
    body = _between(_text(), '## 3 差异清单', '## 4 ')
    # 每条以「N. 」开头；按编号切开，保证多行条目不会被拆散
    parts = re.split(r'\n(?=\d+\.\s)', body)
    return [p for p in parts if p.strip()]


def test_差异清单含两条替代():
    items = _diff_items()
    assert len(items) >= 6, '差异清单过短（%d 条），至少覆盖 apply_patch / run_code 等' % len(items)
    hits = {}
    for token in ('apply_patch', 'run_code'):
        matched = [p for p in items if token in p]
        assert matched, '差异清单缺 %s 的条目' % token
        assert any('替代' in p for p in matched), (
            '差异清单里 %s 那条没写替代方案' % token)
        hits[token] = matched[0]
    assert 'run_code' not in hits['apply_patch'], 'apply_patch 与 run_code 应分列不同条目'
    # 另两条本卡明确点名的差异，防止只留最省事的两条
    assert 'subagent_fork' in '\n'.join(items), '缺 subagent_fork 差异条'
    assert 'workflow' in '\n'.join(items), '缺 workflow 门控改写条'


def test_实测数字与常量一致():
    text = _text()
    assert str(PROMPT_CHARS) in text, '文档缺默认提示字数 %d' % PROMPT_CHARS
    assert str(TOOL_COUNT) in text, '文档缺实发工具数 %d' % TOOL_COUNT
    assert '{:,}'.format(TOOL_SCHEMA_CHARS) in text, (
        '文档缺工具模式字符实测值 %s' % '{:,}'.format(TOOL_SCHEMA_CHARS))
    assert '{:,}'.format(TOOL_SCHEMA_BASELINE) in text, (
        '文档必须保留卡面基线 %s 作对照' % '{:,}'.format(TOOL_SCHEMA_BASELINE))
    assert str(BUDGET_CHARS) in text, '文档缺提示预算 %d' % BUDGET_CHARS
    assert '%d 个' % STANDARD_SURFACE in text, '文档缺标准工具面口径 15 个'
    # 上游快照口径：530 非空行 / 30,285 字节，不能抄错
    assert '530 非空行' in text, '上游快照行数口径必须是 530 非空行'
    assert '30,285' in text, '上游快照字节数必须是 30,285'


def test_口径小节写清上游路径():
    text = _text()
    assert 'system-prompt.expected.md' in text, '第 1 节缺上游快照文件名'
    assert 'advanced-toolchain' in text, '第 1 节缺上游快照目录'
