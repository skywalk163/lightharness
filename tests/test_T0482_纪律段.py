# -*- coding: utf-8 -*-
"""T-0482：工具使用纪律段判据。

判据全部走 .light 侧真实段落：子进程 `python 运行.py <driver>`，driver 调
`纪律段文本(工具名表)`，把多行文本压平成单行键值输出，Python 侧再还原断言。

覆盖任务卡验收：
  - 4 工具（bash/读文件/编辑文件/web_search）→ 退出码 / cat / 定向替换 / 不可信 四关键词齐；
  - 只有读文件 → 仅 1 条，且不含「退出码」；
  - 空工具表 / 无参 → 标准工具面，≥4 条；无关工具 → 空串；
  - 全文不含 apply_patch / run_code / workflow；
  - 与 `系统提示.实参契约段()` 句级查重：相同句子 0 处；
  - 所有输出长度 ≤ 900。

反跑锚点（见 .hive/summary.md）：
  ① 删「外部不可信」条 → test_四工具关键词齐 红；
  ② 把 cat 条改成「尽量别用」→ test_cat明确列举 红（要求 cat/sed/head/tail 原样出现）；
  ③ 加一句 apply_patch 说明 → test_红线禁词 红。
  恢复后全绿。
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

DRIVER = r'''
从 提示_纪律段 导入 纪律段文本
从 系统提示 导入 实参契约段

段落 压平(文本):
  设 文本 为 替换字符串(文本, "\r", "<CR>")
  设 文本 为 替换字符串(文本, "\n", "<NL>")
  返回 文本

段落 主程():
  打印("four=" + 压平(纪律段文本(["bash", "读文件", "编辑文件", "web_search"])))
  打印("read=" + 压平(纪律段文本(["读文件"])))
  打印("read_alias=" + 压平(纪律段文本(["read_file"])))
  打印("bash=" + 压平(纪律段文本(["bash"])))
  打印("edit=" + 压平(纪律段文本(["编辑文件"])))
  打印("web=" + 压平(纪律段文本(["web_fetch"])))
  打印("search=" + 压平(纪律段文本(["search_files"])))
  打印("empty=" + 压平(纪律段文本([])))
  打印("default=" + 压平(纪律段文本()))
  打印("unknown=" + 压平(纪律段文本(["别的工具"])))
  打印("contract=" + 压平(实参契约段()))
主程()
'''

_KEYS = ('four', 'read', 'read_alias', 'bash', 'edit', 'web', 'search',
         'empty', 'default', 'unknown', 'contract')

# 本仓不存在的 DSH 工具：文案里一律不许出现（连「不用 apply_patch」也不行）
禁词 = ('apply_patch', 'run_code', 'workflow')


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET', 'HARNESS_MCP_CONFIG')}
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run(source, tmp_path):
    path = tmp_path / 'discipline_probe.light'
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


def _条目(文本):
    return [行 for 行 in 文本.splitlines() if 行.startswith('- ')]


def _句子集(文本):
    """句级切分：按中文句读拆句，去掉列表序号/标题前缀，短于 4 字的碎片丢弃。"""
    结果 = set()
    for 句 in re.split(r'[。！？\n；;]', 文本):
        句 = re.sub(r'^\s*(?:\d+\)|[-*])\s*', '', 句).strip()
        if len(句) >= 4:
            结果.add(句)
    return 结果


@pytest.fixture(scope='module')
def 文本表(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0482')
    rc, out, kv = _run(DRIVER, tmp)
    assert rc == 0, 'T-0482 纪律段探针应 rc=0，实际 %s\n--- 输出 ---\n%s' % (rc, out[-4000:])
    缺键 = [k for k in _KEYS if k not in kv]
    assert not 缺键, '探针缺少输出键 %s\n--- 输出 ---\n%s' % (缺键, out[-4000:])
    return {k: _restore(kv[k]) for k in _KEYS}


def test_四工具关键词齐(文本表):
    文本 = 文本表['four']
    条目 = _条目(文本)
    assert len(条目) == 4, '4 工具应出 4 条纪律，实际 %d 条：\n%s' % (len(条目), 文本)
    for 关键词 in ('退出码', 'cat', '定向替换', '不可信'):
        assert 关键词 in 文本, '四工具文本缺 %r：\n%s' % (关键词, 文本)


def test_cat明确列举(文本表):
    """反跑②：改成「尽量别用」这类弱化措辞必须立红。"""
    文本 = _条目(文本表['four'])[1]
    assert 'cat/sed/head/tail' in 文本, '读文件纪律必须明确列举 cat/sed/head/tail：\n%s' % 文本
    assert '不要用 shell' in 文本, '读文件纪律需点明不要用 shell 读文件：\n%s' % 文本


def test_只有读文件只出一条且不含退出码(文本表):
    for 键 in ('read', 'read_alias'):
        文本 = 文本表[键]
        条目 = _条目(文本)
        assert len(条目) == 1, '%s 应仅 1 条，实际 %d 条：\n%s' % (键, len(条目), 文本)
        assert '退出码' not in 文本, '%s 不应出现 bash 的退出码纪律：\n%s' % (键, 文本)
        assert 'cat/sed/head/tail' in 文本, '%s 缺读文件纪律：\n%s' % (键, 文本)


def test_单工具各自裁剪(文本表):
    for 键, 关键词 in (('bash', '退出码'), ('edit', '定向替换'),
                      ('web', '不可信'), ('search', 'find / grep / rg')):
        文本 = 文本表[键]
        assert len(_条目(文本)) == 1, '%s 应仅 1 条：\n%s' % (键, 文本)
        assert 关键词 in 文本, '%s 缺 %r：\n%s' % (键, 关键词, 文本)
    assert 文本表['unknown'] == '', '无关工具表应返回空串，实际 %r' % 文本表['unknown']


def test_空工具表按标准工具面(文本表):
    for 键 in ('empty', 'default'):
        文本 = 文本表[键]
        条目 = _条目(文本)
        assert len(条目) >= 4, '%s（标准工具面）应至少 4 条，实际 %d 条：\n%s' % (
            键, len(条目), 文本)
        for 关键词 in ('退出码', 'cat/sed/head/tail', 'find / grep / rg',
                       '定向替换', '不可信'):
            assert 关键词 in 文本, '%s（标准工具面）缺 %r：\n%s' % (键, 关键词, 文本)


def test_红线禁词(文本表):
    """反跑③：加一句 apply_patch 说明必须立红。"""
    for 键, 文本 in 文本表.items():
        if 键 == 'contract':
            continue
        for 词 in 禁词:
            assert 词 not in 文本, '%s 含本仓不存在的工具 %r：\n%s' % (键, 词, 文本)


def test_与实参契约段句级查重(文本表):
    契约句 = _句子集(文本表['contract'])
    assert 契约句, '契约段句子集为空，查重判据失效'
    for 键, 文本 in 文本表.items():
        if 键 == 'contract':
            continue
        句子集 = _句子集(文本)
        重复 = 句子集 & 契约句
        assert not 重复, '%s 与实参契约段重复句子：%s' % (键, sorted(重复))


def test_长度受控(文本表):
    for 键, 文本 in 文本表.items():
        assert len(文本) <= 900, '%s 长度 %d 超过 900' % (键, len(文本))
