# -*- coding: utf-8 -*-
"""T-0448：工具面装配表判据。

三层：
  1. 映射层（纯数据）：DSH standard 的每个工具名都有叶子，首项与 DSH 包名叶子一致；
     未知工具名返回 []（不瞎猜）；
  2. 预设叶子口径：standard 覆盖 todo/skill/web/present/subagent/goal；
     brainstorm 不含任何写类叶子；minimal 只留 bash；组合串取交集；
  3. 装配报告：用真实注册表（158 个工具名）跑标准类预设，标准预设不得只剩 4 个工具；
     minimal 只留 bash，brainstorm 只留读文件 / 搜索文件。

反证（summary 附记录）：把模块里 `"todo_write": ["tool-todo"]` 一行删掉，
test_dsh标准工具名全有叶子 立红。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

# DSH standard 的模型可见工具名 → 期望主叶子（首项）
DSH_STANDARD = [
    ('bash', 'tool-bash'),
    ('read_file', 'tool-fs-read'),
    ('write_file', 'tool-fs-write'),
    ('edit_file', 'tool-fs-write'),
    ('search_files', 'tool-fs-search'),
    ('glob', 'tool-fs-search'),
    ('grep', 'tool-fs-search'),
    ('todo_write', 'tool-todo'),
    ('todo_read', 'tool-todo'),
    ('ask_user_question', 'tool-ask-user'),
    ('session_query', 'tool-session-query'),
    ('search', 'tool-web'),
    ('web_fetch', 'tool-web'),
    ('skill', 'tool-skill'),
    ('subagent', 'tool-subagent'),
    ('subagent_fork', 'tool-subagent-fork'),
    ('list_agents', 'tool-subagent-list-agents'),
    ('send_message', 'tool-subagent'),
    ('present', 'present'),
    ('schedule', 'tool-schedule'),
    ('jobs', 'tool-jobs'),
    ('job_status', 'tool-jobs'),
    ('goal', 'tool-goal'),
]

_DSH_LITERAL = '[' + ', '.join('"%s"' % n for n, _ in DSH_STANDARD) + ']'

WRITE_LEAVES = ['tool-bash', 'terminal-bash', 'persistent-bash', 'pty',
                'tool-pwsh', 'terminal-pwsh', 'persistent-pwsh', 'tool-fs-write']

DRIVER = '''
从 工具面装配 导入 叶子映射, 补充叶子, 未映射默认保留, 装配报告, 不上叶子

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 首项(表):
  如果 长度(表) == 0:
    返回 ""
  返回 表[0]

段落 主程():
  设 名表 为 __DSH_NAMES__
  遍历 名 之 名表:
    打印 "DSH:" + 名 + "=" + 首项(叶子映射(名))
  打印 "unknown=" + 逗号连接(叶子映射("查天气这种不存在的工具"))
  打印 "非字符串=" + 逗号连接(叶子映射(123))
  打印 "叶子_standard=" + 逗号连接(补充叶子("standard"))
  打印 "叶子_ptc=" + 逗号连接(补充叶子("ptc"))
  打印 "叶子_cordis=" + 逗号连接(补充叶子("cordis"))
  打印 "叶子_default=" + 逗号连接(补充叶子("default"))
  打印 "叶子_brainstorm=" + 逗号连接(补充叶子("brainstorm"))
  打印 "叶子_minimal=" + 逗号连接(补充叶子("minimal"))
  打印 "叶子_topdown=" + 逗号连接(补充叶子("topdown"))
  打印 "叶子_组合=" + 逗号连接(补充叶子("standard+brainstorm"))
  打印 "保留_standard=" + 转字符串(未映射默认保留("standard"))
  打印 "保留_brainstorm=" + 转字符串(未映射默认保留("brainstorm"))
  打印 "保留_minimal=" + 转字符串(未映射默认保留("minimal"))
  打印 "保留_组合=" + 转字符串(未映射默认保留("standard+brainstorm"))
  打印 "不上_SSH执行=" + 转字符串(不上叶子("SSH执行"))
  打印 "不上_读文件=" + 转字符串(不上叶子("读文件"))
主程()
'''

REGISTRY_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 装配报告

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  设 注册表 为 组装注册表()
  设 名表 为 注册表.名单()
  设 条目 为 []
  遍历 名 之 名表:
    设 项 为 {"标识": 名}
    条目.追加(项)
  打印 "注册表总数=" + 转字符串(长度(名表))
  设 标 为 装配报告(条目, "standard")
  打印 "报告_standard_保留数=" + 转字符串(长度(标["保留"]))
  打印 "报告_standard_注销数=" + 转字符串(长度(标["注销"]))
  打印 "报告_standard_未映射数=" + 转字符串(长度(标["未映射"]))
  设 简 为 装配报告(条目, "minimal")
  打印 "报告_minimal_保留=" + 逗号连接(简["保留"])
  打印 "报告_minimal_注销数=" + 转字符串(长度(简["注销"]))
  设 脑 为 装配报告(条目, "brainstorm")
  打印 "报告_brainstorm_保留=" + 逗号连接(脑["保留"])
  设 组 为 装配报告(条目, "standard+brainstorm")
  打印 "报告_组合_保留=" + 逗号连接(组["保留"])
主程()
'''


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC, env=env)
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


def _missing_module(out):
    return ('lightplugin' in out and
            ('ModuleNotFound' in out or '导入失败' in out or 'No module' in out))


def test_dsh标准工具名全有叶子(tmp_path):
    rc, out, kv = _run(DRIVER.replace('__DSH_NAMES__', _DSH_LITERAL), tmp_path, 't0448_driver.light')
    assert rc == 0, out
    for name, leaf in DSH_STANDARD:
        got = kv.get('DSH:' + name, '')
        assert got != '', ('DSH 工具名没有叶子映射', name, out)
        assert got == leaf, ('首项与 DSH 包名叶子不一致', name, got, leaf, out)


def test_未知工具不瞎猜(tmp_path):
    rc, out, kv = _run(DRIVER.replace('__DSH_NAMES__', _DSH_LITERAL), tmp_path, 't0448_unknown.light')
    assert rc == 0, out
    assert kv.get('unknown') == '', ('未知工具名应返回空表', out)
    assert kv.get('非字符串') == '', out
    assert kv.get('不上_SSH执行') in ('True', '真'), out
    assert kv.get('不上_读文件') in ('False', '假'), out


def test_standard补充叶子覆盖关键族(tmp_path):
    rc, out, kv = _run(DRIVER.replace('__DSH_NAMES__', _DSH_LITERAL), tmp_path, 't0448_std.light')
    assert rc == 0, out
    leaves = [x for x in kv.get('叶子_standard', '').split(',') if x]
    for need in ('tool-todo', 'tool-skill', 'tool-web', 'present',
                 'tool-subagent', 'tool-goal'):
        assert need in leaves, ('standard 补充叶子缺 ' + need, out)
    # ptc / cordis / default 同为全集口径
    for pid in ('ptc', 'cordis', 'default'):
        got = [x for x in kv.get('叶子_' + pid, '').split(',') if x]
        assert got == leaves, (pid, '应为全集口径', out)
    assert kv.get('保留_standard') in ('True', '真'), out


def test_brainstorm不含写类叶子(tmp_path):
    rc, out, kv = _run(DRIVER.replace('__DSH_NAMES__', _DSH_LITERAL), tmp_path, 't0448_brain.light')
    assert rc == 0, out
    leaves = [x for x in kv.get('叶子_brainstorm', '').split(',') if x]
    for bad in WRITE_LEAVES:
        assert bad not in leaves, ('brainstorm 不应含写类叶子 ' + bad, out)
    assert 'tool-fs-read' in leaves and 'tool-fs-search' in leaves, out
    assert kv.get('保留_brainstorm') in ('False', '假'), out
    # 组合串 standard+brainstorm 同样收紧
    combo = [x for x in kv.get('叶子_组合', '').split(',') if x]
    for bad in WRITE_LEAVES:
        assert bad not in combo, ('组合串不应含写类叶子 ' + bad, out)
    assert kv.get('保留_组合') in ('False', '假'), out


def test_minimal只留bash与topdown减写(tmp_path):
    rc, out, kv = _run(DRIVER.replace('__DSH_NAMES__', _DSH_LITERAL), tmp_path, 't0448_min.light')
    assert rc == 0, out
    minimal = [x for x in kv.get('叶子_minimal', '').split(',') if x]
    assert minimal and minimal[0] == 'tool-bash', out
    assert 'tool-fs-read' not in minimal and 'tool-fs-write' not in minimal, out
    assert kv.get('保留_minimal') in ('False', '假'), out
    top = [x for x in kv.get('叶子_topdown', '').split(',') if x]
    for bad in WRITE_LEAVES:
        assert bad not in top, ('topdown 不应含写类叶子 ' + bad, out)
    assert 'tool-fs-read' in top and 'tool-fs-search' in top, out


def test_装配报告标准预设不砍成4个(tmp_path):
    rc, out, kv = _run(REGISTRY_DRIVER, tmp_path, 't0448_registry.light')
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：装配报告用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    total = int(kv.get('注册表总数', '0'))
    kept = int(kv.get('报告_standard_保留数', '0'))
    dropped = int(kv.get('报告_standard_注销数', '0'))
    unmapped = int(kv.get('报告_standard_未映射数', '0'))
    assert total >= 100, ('注册表规模异常（任务卡实测 148+）', total, out)
    assert kept == total, ('standard 不得再砍工具', kept, total, out)
    assert dropped == 0, ('standard 有工具被注销', out)
    assert unmapped > 0, ('应当存在未映射工具并默认保留', out)
    assert kept != 4, ('又回到了只剩 4 个工具的老毛病', out)


def test_装配报告minimal与brainstorm收紧(tmp_path):
    rc, out, kv = _run(REGISTRY_DRIVER, tmp_path, 't0448_registry_tight.light')
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：装配报告用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert kv.get('报告_minimal_保留') == 'bash', ('minimal 应只留 bash', out)
    assert kv.get('报告_brainstorm_保留') == '读文件,搜索文件', ('brainstorm 应只留只读', out)
    assert kv.get('报告_组合_保留') == '读文件,搜索文件', ('standard+brainstorm 应只留只读', out)