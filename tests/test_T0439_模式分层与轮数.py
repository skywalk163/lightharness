# -*- coding: utf-8 -*-
"""T-0439 判据：模式分层（Agent 模式 / 工作方法）+ 运行轮数上调。

分四组：

  第 1 组 数据层：预设分组() / 预设清单(类别) / 组合清单 的 类别 字段；
  第 2 组 设置层：智能预设元数据表 的 类别/分组名、预设分组按序() 两组；
  第 3 组 轮数：代理 默认最大步数 96 + HARNESS_MAX_STEPS 覆盖、目标续跑 64；
  第 4 组 呈现与文档：index.html / app.js / new-session.js 两组 optgroup，
    模式规格与配置参考/CHANGELOG 有对应章节。

反证（贴见 .hive/summary.md）：
  - 预设分组() 的 method 组混入 standard → 第 1 组立红；
  - 预设清单() 忽略类别参数 → 第 1 组立红；
  - 默认最大步数 改回 25 → 第 3 组立红；
  - 模式规格把 `### 终止条件` 改成 `### 结束条件` → T-0406 第 0 组自检立红。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

AGENT = ['standard', 'ptc', 'minimal', 'cordis']
METHOD = ['topdown', 'bottomup', 'brainstorm', 'lazy']
ALL8 = ['standard', 'ptc', 'minimal', 'cordis', 'topdown', 'bottomup', 'brainstorm', 'lazy']

DRIVER = '''
从 预设组合 导入 预设分组, 预设清单, 预设类别, 组合清单, 是代理模式, 是工作方法
从 设置页 导入 智能预设元数据表, 预设分组按序, 造分组名
从 目标续跑 导入 续默认最大轮数
从 步数上限 导入 步数缺省, 步数上限, 解析最大步数
从 内置核心字典 导入 字典包含键

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
  设 分组 为 预设分组()
  打印 "agent=" + 逗号连接(分组["agent"])
  打印 "method=" + 逗号连接(分组["method"])
  打印 "全部=" + 逗号连接(预设清单())
  打印 "代理数=" + 转字符串(长度(预设清单("agent")))
  打印 "方法数=" + 转字符串(长度(预设清单("method")))
  打印 "未知数=" + 转字符串(长度(预设清单("no-such-kind")))
  打印 "空串数=" + 转字符串(长度(预设清单("")))
  打印 "空值数=" + 转字符串(长度(预设清单(空)))
  打印 "creat类别=" + 预设类别("cordis")
  打印 "懒类别=" + 预设类别("lazy")
  打印 "未知类别=" + 预设类别("no-such-mode")
  打印 "非串类别=" + 预设类别(7)
  打印 "标代理=" + 转字符串(是代理模式("standard"))
  打印 "标方法=" + 转字符串(是工作方法("standard"))
  打印 "懒方法=" + 转字符串(是工作方法("lazy"))
  设 清单 为 组合清单()
  打印 "组合键数=" + 转字符串(长度(清单))
  设 缺类 为 0
  设 错类 为 0
  遍历 标识 之 预设清单():
    如果 (字典包含键(清单[标识], "类别") == 假):
      设 缺类 为 缺类 + 1
    否则:
      如果 (清单[标识]["类别"] != 预设类别(标识)):
        设 错类 为 错类 + 1
  打印 "缺类别=" + 转字符串(缺类)
  打印 "错类别=" + 转字符串(错类)
  设 元表 为 智能预设元数据表()
  打印 "元标准类=" + 元表["standard"]["类别"]
  打印 "元标准组=" + 元表["standard"]["分组名"]
  打印 "元懒组=" + 元表["lazy"]["分组名"]
  打印 "元PTC类=" + 元表["ptc"]["类别"]
  设 分组序 为 预设分组按序()
  打印 "组序数=" + 转字符串(长度(分组序))
  打印 "组0名=" + 分组序[0]["分组"]
  打印 "组1名=" + 分组序[1]["分组"]
  打印 "组0数=" + 转字符串(长度(分组序[0]["预设"]))
  打印 "组1数=" + 转字符串(长度(分组序[1]["预设"]))
  打印 "组0首=" + 分组序[0]["预设"][0]["id"]
  打印 "组1首=" + 分组序[1]["预设"][0]["id"]
  打印 "步数缺省=" + 转字符串(步数缺省)
  打印 "步数上限=" + 转字符串(步数上限)
  打印 "续轮数=" + 转字符串(续默认最大轮数)
  # 优先级/回落/钳制在 步数上限.解析最大步数（请求 > 环境 > 缺省）里验证
  设 覆盖 为 解析最大步数(空, "123")
  打印 "覆盖步数=" + 转字符串(覆盖["值"]) + "/" + 转字符串(覆盖["来源"])
  设 坏值 为 解析最大步数(空, "abc")
  打印 "坏值步数=" + 转字符串(坏值["值"])
  设 零值 为 解析最大步数(空, "0")
  打印 "零值步数=" + 转字符串(零值["值"])
  设 超限 为 解析最大步数(空, "5000")
  打印 "超限步数=" + 转字符串(超限["值"])
  设 空值 为 解析最大步数(空, "")
  打印 "空值步数=" + 转字符串(空值["值"])
  打印 "造组代理=" + 造分组名("agent")
  打印 "造组方法=" + 造分组名("method")
  打印 "造组空=" + 造分组名("")
主程()
'''

_CACHE = {}


def _find_sibling(name):
    explicit = os.environ.get(name, '')
    dirs = [explicit] if explicit else []
    key = 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        dirs.append(os.path.join(here, key))
        dirs.append(os.path.join(here, 'duan-light-merge', key))
    dirs.append('/home/skywalk/dswork/' + key)
    for d in dirs:
        if d and os.path.isdir(d):
            return os.path.normpath(d)
    return ''


def _run(tmp_path, tag, extra_env=None):
    """同一 tag 只跑一次；返回 (rc, 合并输出, kv)。"""
    if tag in _CACHE:
        return _CACHE[tag]
    f = tmp_path / ('driver_%s.light' % tag)
    f.write_text(DRIVER, encoding='utf-8')
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_MAX_STEPS')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    _CACHE[tag] = (p.returncode, p.stdout + p.stderr, kv)
    return _CACHE[tag]


def _ok(tmp_path, tag, extra_env=None):
    rc, out, kv = _run(tmp_path, tag, extra_env)
    assert rc == 0 and kv, 'driver 未跑通（tag=%s）:\n%s' % (tag, out[-2500:])
    return kv


# ---------------------------------------------------------------- 第 1 组：数据层


def test_第1组_预设分组两组且顺序正确(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['agent'].split(',') == AGENT, kv['agent']
    assert kv['method'].split(',') == METHOD, kv['method']
    assert kv['全部'].split(',') == ALL8, kv['全部']


def test_第1组_预设清单按类别过滤且向后兼容(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['代理数'] == '4' and kv['方法数'] == '4', kv
    assert kv['未知数'] == '0', '未知类别必须返回空列表，实为 %s' % kv['未知数']
    assert kv['空串数'] == '8' and kv['空值数'] == '8', '空串/空值都必须 = 全部 8 项'
    assert kv['标代理'] == 'True' and kv['标方法'] == 'False'
    assert kv['懒方法'] == 'True'


def test_第1组_类别字段单一真相(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['组合键数'] == '8'
    assert kv['缺类别'] == '0', '有 %s 个组合条目缺 类别' % kv['缺类别']
    assert kv['错类别'] == '0', '类别与 预设类别() 不一致的条目数：%s' % kv['错类别']
    assert kv['creat类别'] == 'agent' and kv['懒类别'] == 'method'
    assert kv['未知类别'] == '' and kv['非串类别'] == ''


# ---------------------------------------------------------------- 第 2 组：设置层


def test_第2组_设置页元数据带类别与分组名(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['元标准类'] == 'agent' and kv['元标准组'] == 'Agent 模式', kv
    assert kv['元懒组'] == '工作方法', kv
    assert kv['造组代理'] == 'Agent 模式' and kv['造组方法'] == '工作方法'
    assert kv['造组空'] == ''


def test_第2组_预设分组按序是两组四加四(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['组序数'] == '2', kv['组序数']
    assert kv['组0名'] == 'Agent 模式' and kv['组1名'] == '工作方法', kv
    assert kv['组0数'] == '4' and kv['组1数'] == '4', kv
    assert kv['组0首'] == 'standard' and kv['组1首'] == 'topdown', kv


# ---------------------------------------------------------------- 第 3 组：轮数


def test_第3组_单轮步数默认96(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['步数缺省'] == '96', '单轮步数缺省应回 96，实为 %s' % kv['步数缺省']
    assert kv['步数上限'] == '1000'
    assert kv['续轮数'] == '64', '目标续跑应回 64，实为 %s' % kv['续轮数']


def test_第3组_环境变量可覆盖且非法值回落(tmp_path):
    kv = _ok(tmp_path, 'base')
    assert kv['覆盖步数'] == '123/环境', kv['覆盖步数']
    assert kv['坏值步数'] == '96', '非法值必须回落 96，实为 %s' % kv['坏值步数']
    assert kv['零值步数'] == '96', '0 必须回落 96，实为 %s' % kv['零值步数']
    assert kv['超限步数'] == '96', '超上限按非法处理并回落 96，实为 %s' % kv['超限步数']
    assert kv['空值步数'] == '96', '空串必须回落 96，实为 %s' % kv['空值步数']
    assert kv['步数缺省'] == '96', '常量本身不应被环境变量改写'


# ---------------------------------------------------------------- 第 4 组：呈现与文档


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


def test_第4组_三处前端都按两组渲染():
    index = _read('webui', 'index.html')
    assert '<optgroup label="Agent 模式">' in index
    assert '工作方法（随下一条消息生效）' in index

    app = _read('webui', 'app.js')
    assert 'MODE_GROUPS' in app
    assert '"Agent 模式"' in app and '"工作方法"' in app
    assert 'optgroup' in app, 'app.js 重建下拉必须产出 optgroup'
    # T-0403 的边界判据仍在：热点文件源码里不得出现方法 id 字面量
    assert 'topdown' not in app and 'brainstorm' not in app

    ns = _read('webui', 'new-session.js')
    assert 'modeGroups' in ns and '"Agent 模式"' in ns and '"工作方法"' in ns
    assert ('["standard", "cordis", "ptc", "minimal", "topdown", "bottomup", '
            '"brainstorm", "lazy"]') in ns, 'T-0403 的模式顺序判据被破坏'


def test_第4组_文档章节齐全():
    spec = _read('docs', '功能对标', '模式规格.md')
    assert '## 0.1 分层：Agent 模式 / 工作方法（T-0439）' in spec
    assert '## 0.2 轮数预算（T-0439）' in spec
    assert 'tool-ralph' in spec and '256' in spec

    cfg = _read('docs', '配置参考.md')
    assert 'HARNESS_MAX_STEPS' in cfg and '运行轮数（T-0439）' in cfg

    log = _read('CHANGELOG.md')
    assert 'T-0439' in log and 'Agent 模式' in log and '工作方法' in log


def test_第4组_目标续跑常量与代理源码口径一致():
    src = _read('src', '目标续跑.light')
    assert '设 续默认最大轮数 为 64' in src
    step = _read('src', '步数上限.light')
    assert '设 步数缺省 为 96' in step
    agent = _read('src', '代理.light')
    assert '属性 最大步数 等于 96' in agent
    assert '从 步数上限 导入 步数缺省' in agent, '代理必须从 步数上限 取缺省，不许再抄一份常量'
    assert '设 己.最大步数 为 步数缺省' in agent
    combined = _read('src', '预设组合.light')
    assert '"类别": 类别代理' in combined and '"类别": 类别方法' in combined
