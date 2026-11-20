# -*- coding: utf-8 -*-
"""T-0419：tool-fs 读/写叶子拆分判据。

两层：
  1. 映射层（纯数据）：读文件→tool-fs-read，写文件→tool-fs-write，搜索→tool-fs-search；
  2. 装配层（依赖 总入口 → lightplugin）：8 预设实际挂出的工具名，
     brainstorm 必须只有 读文件/搜索文件，没有 写文件、没有 bash。

反证：把 总入口 的「写文件」映射改回 tool-fs，装配层 brainstorm 会重新出现 写文件，
本文件 test_brainstorm装配层无写文件 立红。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

DRIVER = '''
从 预设组合 导入 预设清单
从 总入口 导入 组装注册表, 工具名到叶子

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
  打印 "映射_读=" + 逗号连接(工具名到叶子("读文件"))
  打印 "映射_写=" + 逗号连接(工具名到叶子("写文件"))
  打印 "映射_搜=" + 逗号连接(工具名到叶子("搜索文件"))
  遍历 标识 之 预设清单():
    设 注册表 为 组装注册表(标识)
    打印 "装配_" + 标识 + "=" + 逗号连接(注册表.名单())
主程()
'''


def _run(tmp_path):
    path = tmp_path / 't0419_driver.light'
    path.write_text(DRIVER, encoding='utf-8')
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
    return ('lightplugin' in out and ('ModuleNotFound' in out or '导入失败' in out or 'No module' in out))


def test_映射层读写分离(tmp_path):
    rc, out, kv = _run(tmp_path)
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert kv.get('映射_读') == 'tool-fs-read', kv
    assert kv.get('映射_写') == 'tool-fs-write', kv
    assert kv.get('映射_搜') == 'tool-fs-search', kv


def test_brainstorm装配层无写文件(tmp_path):
    rc, out, kv = _run(tmp_path)
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out

    def tools(pid):
        return [x for x in kv.get('装配_' + pid, '').split(',') if x]

    brain = tools('brainstorm')
    assert '写文件' not in brain, ('brainstorm 装配层仍有写文件（映射/删表没拆干净）', out)
    assert 'bash' not in brain, ('brainstorm 装配层仍有 bash', out)
    assert '读文件' in brain, ('brainstorm 丢了读文件（删过头）', out)
    assert '搜索文件' in brain, out

    for pid in ('standard', 'ptc', 'cordis', 'topdown', 'bottomup', 'lazy'):
        t = tools(pid)
        assert '读文件' in t and '写文件' in t, (pid, '读写应同时在', out)
    assert tools('minimal') == ['bash'], out


def test_brainstorm叶子集不含写叶子(tmp_path):
    rc, out, kv = _run(tmp_path)
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：请在 192.168.0.88 上跑')
    assert rc == 0, out
    # 装配名单是最终口径；这里再从映射侧确认写文件只有 tool-fs-write 一个落点
    assert kv.get('映射_写') == 'tool-fs-write'
    assert kv.get('映射_读') != kv.get('映射_写')
