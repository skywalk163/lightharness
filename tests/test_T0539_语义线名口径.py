# -*- coding: utf-8 -*-
"""T-0539：系统提示正文与 README/快速开始/API参考 同步语义线名（T-0534 遗留）。

背景：T-0534 把模型面 function.name 从 tool_NN 换成语义线名（`<域>.<动作>` 的点号
转写成双下划线，如 workflow__todo_write / workflow__goal / web__search / shell__run /
ctx__select_blocks；核心 fs 四件套与 bash 沿用固定线名）。但系统提示正文（规划段 /
待办与目标段 / 工具选择段 / 逐工具指导段）仍按旧名 `todo_write / web_search / goal`
说话，README 等文档也没有交代线名口径 —— 模型收到的 function.name 与提示文案对不上。

本判据钉三件事：
  A. 生产提示原文（标准工具面、无上下文）里出现的是线名，且裸旧名只在「旧名/兼容/
     回名/别名」这类兼容说明行里保留；提示总长仍在预算内、未被截断。
  B. README / 快速开始 / API 参考同步线名口径：三份文档都点名线名，且不出现裸旧名。
  C. 兼容语义不回归：线名回名仍落回基线注册名（旧名解析能力保留，T-0534 红线）。

「裸旧名」检测器带反证：喂一行合成的「（todo_write）」必须被判红，避免判据写成
恒真。检测口径按行：该行只要出现 旧名 就必须同时出现兼容线索词，否则算裸名；
行内 `workflow__todo_write` 这类线名里包含的旧名片段（前两位是 `__`）不计。
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 300

旧名 = ['todo_write', 'web_search', 'web_fetch', 'goal']
# 文档侧只查三个无歧义的旧工具名：`goal` 在 API 参考里是 `/goal` 命令面与「goal 台账」
# 这类域名词（本来就不该算裸工具名），留到系统提示侧去钉。
旧名_文档 = ['todo_write', 'web_search', 'web_fetch']
线名 = ['workflow__todo_write', 'workflow__goal', 'web__search', 'web__fetch']
兼容线索 = ('旧名', '兼容', '回名', '别名')

DRIVER = '''
从 系统提示 导入 生产提示原文, 生产提示上限, 生产提示截断标记
从 总入口 导入 组装注册表
从 内置核心转换 导入 转字符串

段落 主程():
  设 文 为 生产提示原文()
  打印("LEN=" + 转字符串(字符串长度(文)))
  打印("上限=" + 转字符串(生产提示上限()))
  打印("截断=" + 转字符串(文.包含(生产提示截断标记)))
  设 标 为 组装注册表("standard")
  打印("R_TODO=" + 转字符串(标.回名("workflow__todo_write")))
  打印("R_WEB=" + 转字符串(标.回名("web__search")))
  打印("R_GOAL=" + 转字符串(标.回名("workflow__goal")))
  打印("R_OLD=" + 转字符串(标.回名("todo_write")))
  打印("BEGIN")
  打印(文)
  打印("END")

主程()
'''


def _裸旧名(文本, 名单=None):
    """返回 (旧名, 该行) 的裸名清单；空清单表示没有裸旧名。"""
    名单 = 名单 or 旧名
    bad = []
    for 行 in 文本.splitlines():
        if not any(名 in 行 for 名 in 名单):
            continue
        if any(词 in 行 for 词 in 兼容线索):
            continue
        for 名 in 名单:
            起 = 0
            while True:
                位 = 行.find(名, 起)
                if 位 < 0:
                    break
                if 行[max(0, 位 - 2):位] != '__':
                    bad.append((名, 行.strip()[:100]))
                    break
                起 = 位 + len(名)
    return bad


def _跑(tmp_path):
    path = tmp_path / 't0539_probe.light'
    path.write_text(DRIVER.lstrip('\n'), encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC,
                          env=env, encoding='utf-8', errors='replace')
    kv, 文本, 收 = {}, [], False
    for 行 in (proc.stdout or '').splitlines():
        if 行 == 'BEGIN':
            收 = True
            continue
        if 行 == 'END':
            收 = False
            continue
        if 收:
            文本.append(行)
        elif '=' in 行 and not 行.startswith('['):
            k, v = 行.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, (proc.stdout or '') + (proc.stderr or ''), kv, '\n'.join(文本)


def test_系统提示正文用语义线名(tmp_path):
    rc, out, kv, 提示 = _跑(tmp_path)
    assert rc == 0, out[-4000:]
    assert 提示, '探针没打印出生产提示原文'
    assert int(kv['LEN']) <= int(kv['上限']), ('提示超预算', kv['LEN'], kv['上限'])
    assert kv['截断'] == 'False', ('提示被截断，线名可能被砍掉', kv['LEN'])
    for 名 in 线名:
        assert 名 in 提示, ('系统提示正文没有用线名说话', 名)
    bad = _裸旧名(提示)
    assert not bad, ('系统提示正文仍出现裸旧名（旧名只该在兼容说明行保留）',
                     bad[:5])
    # 兼容说明是「有话说」而不是「说了但没指向线名」：旧名行必须挨着线名
    for 名, 行 in [(n, l) for n in 旧名 for l in 提示.splitlines() if n in l]:
        assert any(线 in 行 for 线 in 线名), ('旧名兼容说明行没给出线名口径', 名, 行)


def test_文档口径同步(tmp_path):
    rc, out, kv, _ = _跑(tmp_path)
    assert rc == 0, out[-4000:]
    文档 = {
        'README.md': os.path.join(ROOT, 'README.md'),
        'docs/快速开始.md': os.path.join(ROOT, 'docs', '快速开始.md'),
        'docs/API参考.md': os.path.join(ROOT, 'docs', 'API参考.md'),
    }
    for 名, 路径 in 文档.items():
        with open(路径, encoding='utf-8') as f:
            文 = f.read()
        for 线 in 线名:
            assert 线 in 文, ('%s 没同步线名口径' % 名, 线)
        bad = _裸旧名(文, 旧名_文档)
        assert not bad, ('%s 里出现裸旧名（旧名只该在兼容说明里保留）' % 名, bad[:5])


def test_兼容旧名解析不回归(tmp_path):
    rc, out, kv, _ = _跑(tmp_path)
    assert rc == 0, out[-4000:]
    assert kv['R_TODO'] == 'todo_write', ('线名回名没落回基线注册名', kv['R_TODO'])
    assert kv['R_WEB'] == 'web_search', ('线名回名没落回基线注册名', kv['R_WEB'])
    assert kv['R_GOAL'] == '目标', ('线名回名没落回基线注册名', kv['R_GOAL'])
    assert kv['R_OLD'] == 'todo_write', ('旧名解析能力被改名回归（T-0534 红线）', kv['R_OLD'])


def test_裸名检测器有反证能力():
    """检测器不能恒真：一行合成裸旧名必须被判红，一行兼容说明必须放过。"""
    裸 = _裸旧名('- 多步任务先落一份待办清单（todo_write），再开始动手。')
    assert 裸 and 裸[0][0] == 'todo_write', ('裸旧名检测器失效（恒真判据）', 裸)
    兼容 = _裸旧名('- 旧名 todo_write 仍是兼容别名，线名是 workflow__todo_write。')
    assert not 兼容, ('兼容说明行被误判成裸旧名', 兼容)
