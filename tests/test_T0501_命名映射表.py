# -*- coding: utf-8 -*-
"""T-0501：语义化命名方案与 tool_NN → 语义名映射表判据。

校验对象是文档里的机器可读块（docs/工具命名规范.light.md §6），不校验注册表本身
（本卡红线：只产出方案，不动 registry）。

钉住的不变量（对应规范 §8）：
  1. 完整性：160 行、编号连续 0..159、tool 键与编号一致、现名互不重复；
  2. 合法性：语义名匹配 `<域>.<动作>` 的 ASCII 蛇形语法、长度上限；
  3. 唯一性：语义名互不重复，且与现名、与 mcp__ 前缀不冲突；
  4. 域对齐：域 ∈ T-0496 的 24 个枚举值，前缀 == 域（唯一例外 横切 → xcut）；
  5. 兼容标注：只有「保留别名 / 直接改名」两种，保留别名 ⟺ 现名 ∈ 别名保留名单；
  6. 与真实注册表逐位一致（环境里挂了 lightplugin 时强校验；未挂载则跳过，不假绿不假红）。

运行方式：python -m pytest -q tests/test_T0501_命名映射表.py
Windows 本机若子进程输出触发 GBK 解码错误，加 PYTHONUTF8=1 再跑（不是产物问题）。
"""
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'docs', '工具命名规范.light.md')
RUNNER = os.path.join(ROOT, '运行.py')

BEGIN = '<!-- T0501-映射表-开始 -->'
END = '<!-- T0501-映射表-结束 -->'

# T-0496 的 domain 枚举（src/工具面装配.light §9：域覆盖表 ∪ 域规则表 ∪ 默认域）
DOMAINS = {
    'host', 'credential', 'storage', 'webhook', 'browser', 'desktop', 'voice',
    'lsp', 'ctx', 'generative', 'team', 'extension', 'workflow', 'session',
    'config', 'file', 'shell', 'web', 'skill', 'delegation', 'attachment',
    'acp', '横切', '其他',
}
# 域前缀转写：只允许「横切 → xcut」一条（函数名必须 ASCII），其余原样
PREFIX = {'横切': 'xcut', '其他': 'misc'}
# 动词族：动作首词必须能落到词表里的某个前缀族，防止写成 do_it / tool_2 之类
ACTION_RE = re.compile(r'^[a-z][a-z0-9_]*$')
NAME_RE = re.compile(r'^([a-z]+)\.([a-z][a-z0-9_]*)$')
MAX_LEN = 40
MAX_ACTION = 24
POLICIES = {'保留别名', '直接改名'}


def _read_doc():
    assert os.path.isfile(DOC), '缺少规范文档：%s' % DOC
    with open(DOC, encoding='utf-8') as f:
        return f.read()


def _load_table():
    text = _read_doc()
    assert BEGIN in text and END in text, '规范文档缺少 §6 映射表标记'
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    body = body.strip()
    assert body.startswith('```json') and body.endswith('```'), '映射表必须包在 json 代码块里'
    body = body[len('```json'):-len('```')].strip()
    return json.loads(body)


TABLE = _load_table()
ROWS = TABLE['工具']
KEEP = TABLE['别名保留名单']


# ---------------------------------------------------------------- 1 完整性
def test_映射表完整性与编号口径():
    assert TABLE['版本'] == 'T-0501'
    assert TABLE['基线工具数'] == len(ROWS) == 160, (TABLE['基线工具数'], len(ROWS))
    # 编号连续、tool 键与编号严格一致（tool_NN 的口径 = 0 基登记序）
    assert [r['编号'] for r in ROWS] == list(range(160)), '编号必须是连续 0..159'
    for r in ROWS:
        assert r['tool'] == 'tool_%d' % r['编号'], (r['tool'], r['编号'])
        assert set(r) == {'编号', 'tool', '现名', '域', '语义名', '兼容'}, r
        assert r['现名'] and r['域'] and r['语义名'], r
    # 现名互不重复（一个现名只能映射到一个语义名）
    names = [r['现名'] for r in ROWS]
    assert len(set(names)) == 160, '现名重复：%s' % [n for n in names if names.count(n) > 1]


# ---------------------------------------------------------------- 2 合法性
def test_语义名语法与长度():
    for r in ROWS:
        new = r['语义名']
        m = NAME_RE.match(new)
        assert m, '语义名不合语法：%s（应为 <域>.<动作>）' % new
        assert new.isascii(), '语义名必须纯 ASCII：%s' % new
        assert len(new) <= MAX_LEN, '语义名过长：%s' % new
        act = m.group(2)
        assert ACTION_RE.match(act), act
        assert len(act) <= MAX_ACTION, '动作词过长：%s' % new
        assert '__' not in new and '..' not in new, '连续分隔符：%s' % new
        # 动作用对象名，不用 do/tool/exec 这类无语义通配词（shell.run 是唯一例外；
        # tool_task_* 里的 tool 是对象名「工具任务」，不算通配词）
        first = act.split('_')[0]
        assert act not in ('do', 'exec', 'tmp', 'x'), '动作用了无语义通配词：%s' % new
        assert not act.startswith(('do_', 'exec_', 'tmp_')), '动作用了无语义通配词：%s' % new
        assert first != 'do', '动作用了无语义通配词：%s' % new


# ---------------------------------------------------------------- 3 唯一性
def test_语义名唯一且不与现名或MCP冲突():
    sem = [r['语义名'] for r in ROWS]
    dup = [s for s in sem if sem.count(s) > 1]
    assert not dup, '语义名重复：%s' % dup
    assert not (set(sem) & {r['现名'] for r in ROWS}), '语义名与现有工具名冲突'
    assert not any(s.startswith('mcp__') for s in sem), 'MCP 透传名不参与改名'
    # 同域同一动作只出现一次（config.list 与 config.preset_list 并存即违规）
    assert len(set(sem)) == 160


# ---------------------------------------------------------------- 4 域对齐
def test_域前缀与T0496枚举对齐():
    assert set(TABLE['域前缀转写']) <= set(PREFIX)
    for k, v in TABLE['域前缀转写'].items():
        assert PREFIX[k] == v, (k, v)
    used = set()
    for r in ROWS:
        dom = r['域']
        assert dom in DOMAINS, '域不在 T-0496 枚举内：%s（工具 %s）' % (dom, r['现名'])
        used.add(dom)
        pre = r['语义名'].split('.')[0]
        assert pre == PREFIX.get(dom, dom), \
            '域前缀与域不符：%s 的域=%s，前缀=%s' % (r['语义名'], dom, pre)
    # 枚举里除兜底「其他」外，本基线没有空转的域（新增工具会让这条变红，属预期）
    empty = {d for d in DOMAINS if d not in used} - {'其他'}
    assert not empty, '枚举域未被任何工具使用：%s' % empty


# ---------------------------------------------------------------- 5 兼容策略
def test_兼容策略标注完备():
    assert isinstance(KEEP, list) and len(KEEP) == 27, len(KEEP)
    assert len(set(KEEP)) == 27, '别名保留名单有重复'
    names = {r['现名'] for r in ROWS}
    assert set(KEEP) <= names, '保留名单里有表外的名字：%s' % (set(KEEP) - names)
    for r in ROWS:
        assert r['兼容'] in POLICIES, r['兼容']
        want = '保留别名' if r['现名'] in KEEP else '直接改名'
        assert r['兼容'] == want, \
            '%s 的兼容标注不对：%s（期望 %s）' % (r['现名'], r['兼容'], want)
    # 硬约束：ASCII 上游名（模型面已在用）一律留别名
    for r in ROWS:
        if r['现名'].isascii():
            assert r['兼容'] == '保留别名', 'ASCII 旧名必须留别名：%s' % r['现名']
    assert sum(1 for r in ROWS if r['兼容'] == '保留别名') == 27
    assert sum(1 for r in ROWS if r['兼容'] == '直接改名') == 133


# ---------------------------------------------------------------- 6 真实注册表
DUMP_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 工具域

段落 主程():
  设 注册表 为 组装注册表()
  遍历 名 之 注册表.名单():
    打印 名 + "|" + 工具域(名)
主程()
'''


def _lightplugin_dir():
    env = os.environ.get('LIGHTPLUGIN', '')
    cands = [env, os.path.join(ROOT, 'lightplugin'),
             os.path.normpath(os.path.join(ROOT, '..', 'lightplugin')),
             os.path.normpath(os.path.join(ROOT, '..', '..', 'lightplugin')),
             os.path.normpath(os.path.join(ROOT, '..', '..', '..', 'lightplugin'))]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, '集成', '工具总表.json')):
            return c
    return ''


def _registry(tmp_path):
    path = tmp_path / 't0501_registry.light'
    path.write_text(DUMP_DRIVER, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    plug = _lightplugin_dir()
    if plug:
        env['LIGHTPLUGIN'] = plug
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=240,
                          env=env, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        return None, (proc.stdout or '') + (proc.stderr or '')
    out = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if '|' in line and not line.startswith('['):
            name, dom = line.split('|', 1)
            out.append((name.strip(), dom.strip()))
    return out, ''


def test_与真实注册表逐位一致(tmp_path):
    reg, err = _registry(tmp_path)
    assert reg is not None, '注册表导出失败：%s' % err[-2000:]
    if len(reg) < 100:
        pytest.skip('当前环境未挂载 lightplugin（%d 个工具），跳过注册表强校验；'
                    '映射表本身的完整性判据已通过' % len(reg))
    assert len(reg) == len(ROWS), '注册表工具数与映射表不一致：%d vs %d' % (len(reg), len(ROWS))
    for r, (name, dom) in zip(ROWS, reg):
        assert r['现名'] == name, '登记序第 %d 位现名漂移：%s vs %s' % (r['编号'], r['现名'], name)
        assert r['域'] == dom, '%s 的域漂移：%s vs %s' % (name, r['域'], dom)
