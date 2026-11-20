"""T-0418 文档收口判据：判据写法、对标台账、用户面文档口径不得再漂移。

只读文本与 JSON，不起服务、不跑业务；任何一条红都表示「文档登记与实际不符」。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _读(相对):
    with open(os.path.join(ROOT, 相对), encoding='utf-8') as f:
        return f.read()


def test_判据不再用尾部窗口():
    源 = _读('tests/test_T0399_新会话对齐.py')
    assert 'entries[-5:]' not in 源, 'T-0399 又退回尾部 5 条窗口断言（追加即红）'
    assert 'tail = nums[-5:]' not in 源, 'T-0399 仍用 nums[-5:] 位置判据'
    assert '#366' in 源 and '#370' in 源, 'T-0399 没有按编号检查 #366~#370'


def test_对标台账状态与新增条目():
    with open(os.path.join(ROOT, 'docs', '功能对标', '对标清单.json'), encoding='utf-8') as f:
        表 = json.load(f)
    条 = 表['条目']
    编号 = [x['编号'] for x in 条]
    assert 编号 == sorted(编号), '对标清单编号乱序'
    assert len(编号) == len(set(编号)), '对标清单编号重复'
    assert 编号[-1] >= 378, 'T-0408 的 #378 没登记'
    索引 = {x['编号']: x for x in 条}

    assert '待合入' not in 索引[369]['状态'], '#369 仍挂「待合入」'
    for 号 in (371, 372, 373, 374, 375):
        状态 = 索引[号]['状态']
        assert 状态.startswith('done'), '#%d 已接线却仍写 %r' % (号, 状态)
        assert 'T-0407' in 状态, '#%d 状态没点名 T-0407' % 号
    assert '#371~#376' in 索引[376]['状态'], '#376 的文字口径没改成 #371~#376'
    assert 索引[377]['状态'].startswith('done（T-0407'), '#377 不是 T-0407 收口条目'
    assert 索引[378]['状态'].startswith('done（T-0408'), '#378 不是 T-0408 条目'
    for 号 in (377, 378):
        for 路径 in 索引[号]['证据']:
            纯 = 路径.split('（')[0].strip()
            assert os.path.exists(os.path.join(ROOT, 纯)), '#%d 证据不存在: %s' % (号, 纯)


def test_API参考覆盖T0407新增面():
    文 = _读('docs/API参考.md')
    for 词 in ('/goal', '/compact', 'X-LH-Interrupt', '202', '429', '409',
               '开始时刻', '完成时刻', '耗时秒', '速率', '轮次数', '完成时间',
               'brainstorm', 'topdown'):
        assert 词 in 文, 'API参考缺「%s」' % 词


def test_配置参考覆盖压缩三键与窗口口径():
    文 = _读('docs/配置参考.md')
    for 词 in ('HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_COMPACTION_THRESHOLD_RATIO',
               'HARNESS_COMPACTION_KEEP_COUNT', '32768'):
        assert 词 in 文, '配置参考缺「%s」' % 词
    assert '128000' in 文, '配置参考没交代 128000→32768 的变更'


def test_快速开始与README无陈旧口径():
    快 = _读('docs/快速开始.md')
    for 词 in ('模式规格.md', '排队', '插话', 'tok/s'):
        assert 词 in 快, '快速开始缺「%s」' % 词
    读我 = _读('docs/README.md')
    assert '模式规格.md' in 读我, 'docs/README 索引没加《模式规格》'
    assert '161 条' not in 读我 and '#1~#161' not in 读我, 'docs/README 仍写 161 条'
    assert '372' in 读我, 'docs/README 没更新对标条数'


def test_模式规格接线口径已翻正():
    文 = _读('docs/功能对标/模式规格.md')
    assert '接线在 T-0407' not in 文, '模式规格仍留「接线在 T-0407」的过期口径'
    assert '已接线（T-0407' in 文 or '接线已由 T-0407 落地' in 文, '模式规格没标已接线提交'
    assert '仍未接线（卡 T-0420）' in 文, 'plan 三项没有如实标「仍未接线（卡 T-0420）」'
    assert 'T-0419' in 文, 'brainstorm 拆叶子没有标「卡 T-0419」'


def test_CHANGELOG可按卡号检索():
    文 = _读('CHANGELOG.md')
    for 号 in ('T-0401', 'T-0402', 'T-0403', 'T-0404', 'T-0405', 'T-0406',
               'T-0408', 'T-0418'):
        assert 号 in 文, 'CHANGELOG 缺 %s 条目' % 号
