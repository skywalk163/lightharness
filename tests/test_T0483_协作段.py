# -*- coding: utf-8 -*-
"""T-0483：协作与长任务提示段判据。

判据全部走 .light 侧真实段落：子进程 `python 运行.py <driver>`，driver 调
`协作段文本(工具名表)`，把多行文本压平成单行键值输出，Python 侧再还原断言。

覆盖任务卡验收：
  - 派发子任务 + 目标 → 同条消息并发 / 结束回合等结果 / 收齐 / 连续 3 轮 / blocked_reason；
  - 只有 bash → 仅并发写一条，且不含「子代理」；
  - 工作流提交 → 「仅显式要求」；
  - 空工具表 → 标准工具面，子代理与目标两组都在；
  - 不承诺不存在能力（subagent_fork / list_agents / run_code）；
  - 所有输出长度 ≤ 1200。

反跑锚点（见 .hive/summary.md）：
  ① 把「连续 3 轮」改成「卡住就 blocked」→ 第一组断言红；
  ② 删「只等结果时结束回合」→ 第一组与空工具表组断言红；
  ③ 无工具/无关工具仍输出全部段落 → 「只有 bash」组断言红。
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

DRIVER = r'''
从 提示_协作段 导入 协作段文本

段落 压平(文本):
  设 文本 为 替换字符串(文本, "\r", "<CR>")
  设 文本 为 替换字符串(文本, "\n", "<NL>")
  返回 文本

段落 主程():
  打印("dual=" + 压平(协作段文本(["派发子任务", "目标"])))
  打印("bash=" + 压平(协作段文本(["bash"])))
  打印("goal=" + 压平(协作段文本(["目标"])))
  打印("sub=" + 压平(协作段文本(["subagent"])))
  打印("wf=" + 压平(协作段文本(["工作流提交"])))
  打印("wf_alias=" + 压平(协作段文本(["workflow"])))
  打印("empty=" + 压平(协作段文本([])))
  打印("default=" + 压平(协作段文本()))
  打印("unknown=" + 压平(协作段文本(["别的工具"])))
主程()
'''

_KEYS = ('dual', 'bash', 'goal', 'sub', 'wf', 'wf_alias',
         'empty', 'default', 'unknown')


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET', 'HARNESS_MCP_CONFIG')}
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run(source, tmp_path):
    path = tmp_path / 'collab_probe.light'
    path.write_text(source, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', errors='replace',
                          timeout=TIMEOUT_SEC, env=_env())
    kv = {}
    for line in (proc.stdout or '').splitlines():
        if '=' in line and not line.startswith('['):
            key, value = line.split('=', 1)
            kv.setdefault(key.strip(), value.strip())
    return proc.returncode, (proc.stdout or '') + (proc.stderr or ''), kv


def _restore(value):
    """把 light 侧压平的多行文本还原成真实文本。"""
    return value.replace('<CR>', '\r').replace('<NL>', '\n')


@pytest.fixture(scope='module')
def 文本表(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0483')
    rc, out, kv = _run(DRIVER, tmp)
    assert rc == 0, 'T-0483 协作段探针应 rc=0，实际 %s\n--- 输出 ---\n%s' % (rc, out[-4000:])
    缺键 = [k for k in _KEYS if k not in kv]
    assert not 缺键, '探针缺少输出键 %s\n--- 输出 ---\n%s' % (缺键, out[-4000:])
    return {k: _restore(kv[k]) for k in _KEYS}


def test_派发子任务与目标的关键纪律(文本表):
    文本 = 文本表['dual']
    for 关键词 in ('同一条消息', '只等结果时结束回合', '不要 sleep 或轮询',
                   '收齐', '按工具定义', '8',
                   'complete', 'active', '连续 3 轮', 'blocked_reason'):
        assert 关键词 in 文本, '派发子任务+目标文本缺 %r：\n%s' % (关键词, 文本)


def test_只有bash只出并发写一条且不含子代理(文本表):
    文本 = 文本表['bash']
    条目 = [行 for 行 in 文本.splitlines() if 行.startswith('- ')]
    assert len(条目) == 1, '只有 bash 时应仅一条指导，实际 %d 条：\n%s' % (len(条目), 文本)
    for 关键词 in ('bash / 格式化器 / 生成器可能覆盖并发编辑',
                   'review 最终 diff', '跑相关测试'):
        assert 关键词 in 文本, '并发写条目缺 %r：\n%s' % (关键词, 文本)
    for 禁词 in ('子代理', '收齐', 'blocked_reason', '仅显式要求'):
        assert 禁词 not in 文本, '只有 bash 时不应出现 %r：\n%s' % (禁词, 文本)


def test_工作流门控只在显式要求(文本表):
    for 键 in ('wf', 'wf_alias'):
        文本 = 文本表[键]
        assert '仅显式要求' in 文本, '%s 缺工作流门控：\n%s' % (键, 文本)
        assert '一两个委派用普通子代理' in 文本, '%s 缺普通子代理兜底：\n%s' % (键, 文本)


def test_空工具表按标准工具面给出子代理与目标两组(文本表):
    for 键 in ('empty', 'default'):
        文本 = 文本表[键]
        for 关键词 in ('同一条消息', '只等结果时结束回合', '收齐', '按工具定义',
                       'complete', '连续 3 轮', 'blocked_reason',
                       '仅显式要求', 'bash / 格式化器 / 生成器'):
            assert 关键词 in 文本, '%s（标准工具面）缺 %r：\n%s' % (键, 关键词, 文本)


def test_单工具裁剪与无关工具返回空(文本表):
    assert '同一条消息' in 文本表['sub']
    assert 'blocked_reason' not in 文本表['sub']
    assert 'blocked_reason' in 文本表['goal']
    assert '同一条消息' not in 文本表['goal']
    assert 文本表['unknown'] == '', '无关工具表应返回空串，实际 %r' % 文本表['unknown']


def test_不承诺不存在能力且长度受控(文本表):
    for 键, 文本 in 文本表.items():
        for 禁词 in ('subagent_fork', 'list_agents', 'run_code'):
            assert 禁词 not in 文本, '%s 含不存在能力 %r' % (键, 禁词)
        assert len(文本) <= 1200, '%s 长度 %d 超过 1200' % (键, len(文本))
