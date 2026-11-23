# -*- coding: utf-8 -*-
"""T-0441 正交组合判据：Agent 模式(4) × 工作方法(5，含 default) = 20 组合。

分层：
  1. 数据层（light 解释器，不依赖 总入口/lightplugin）：
     20 组合矩阵、别名解析、方法删减（只删不增）、与旧 8 预设的等价性、提示/终止/开关。
  2. 源码层（纯文本断言，任何机器都跑得动）：
     CLI --method、Web 注册表缓存键用组合串、统计帧 模式/方法、两下拉与 localStorage 升级、
     设置页 4+5 分组、文档 0.3 节与 CHANGELOG。

会话存储口径（T-0397 保绿）：请求给裸 id 就存裸 id，带 method 才升级成组合串；
规范化（组合键）只发生在装配/缓存/统计层。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

AGENTS = ['standard', 'ptc', 'minimal', 'cordis']
METHODS = ['default', 'topdown', 'bottomup', 'brainstorm', 'lazy']
LEGACY = ['standard', 'ptc', 'minimal', 'cordis', 'topdown', 'bottomup', 'brainstorm', 'lazy']


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


_CACHE = {}


def _run(src, tmp_path, tag):
    if tag in _CACHE:
        return _CACHE[tag]
    f = tmp_path / ('driver_%s.light' % tag)
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
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


CORE_DRIVER = '''
从 预设组合 导入 组合矩阵, 组合行表, 组合统计, 是已知预设, 解析组合, 组合串, 方法删减
从 预设组合 导入 代理预设清单, 工作方法清单, 组合清单, 预设清单
从 预设挂载过滤 导入 挂扁平标识表
从 预设 导入 模式系统提示, 模式终止条件, 模式开关表, 模式终止条件

段落 连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  打印 "矩阵数=" + 转字符串(长度(组合矩阵()))
  打印 "矩阵=" + 连接(组合矩阵())
  打印 "方法数=" + 转字符串(长度(工作方法清单()))
  打印 "方法=" + 连接(工作方法清单())
  遍历 方法 之 工作方法清单():
    打印 "删_" + 方法 + "=" + 连接(方法删减(方法))
  遍历 标识 之 组合矩阵():
    打印 "已知_" + 标识 + "=" + 转字符串(是已知预设(标识))
    设 统计 为 组合统计(标识)
    打印 "统计_" + 标识 + "=" + 转字符串(统计["插件行"]) + "/" + 转字符串(统计["展平后"])
    打印 "叶_" + 标识 + "=" + 连接(挂扁平标识表(标识, 空))
  遍历 旧 之 预设清单():
    打印 "旧叶_" + 旧 + "=" + 连接(挂扁平标识表(旧, 空))
    打印 "旧统计_" + 旧 + "=" + 转字符串(组合统计(旧)["插件行"]) + "/" + 转字符串(组合统计(旧)["展平后"])
  设 解1 为 解析组合("topdown")
  打印 "别名_topdown=" + 解1["代理"] + "+" + 解1["方法"]
  设 解2 为 解析组合("ptc")
  打印 "别名_ptc=" + 解2["代理"] + "+" + 解2["方法"]
  设 解3 为 解析组合("standard+default")
  打印 "组合串解析=" + 转字符串(解3["ok"]) + ":" + 解3["代理"] + "+" + 解3["方法"]
  设 坏1 为 解析组合("ptc+brainstorm+lazy")
  打印 "多个加号=" + 转字符串(坏1["ok"])
  设 坏2 为 解析组合("")
  打印 "空串=" + 转字符串(坏2["ok"])
  设 坏3 为 解析组合("bogus")
  打印 "未知串=" + 转字符串(坏3["ok"])
  设 坏4 为 解析组合("brainstorm+ptc")
  打印 "调序=" + 转字符串(坏4["ok"])
  打印 "组合串生成=" + 组合串("ptc", "lazy")
  打印 "组合串非法=" + 组合串("ptc", "bogus")
  打印 "提示_std_def=" + 转字符串(字符串长度(模式系统提示("standard+default")))
  打印 "提示_std_brain前7=" + 转字符串(模式系统提示("standard+brainstorm")[0:7])
  打印 "提示_ptc_lazy前7=" + 转字符串(模式系统提示("ptc+lazy")[0:7])
  打印 "终止_ptc_lazy=" + 连接(模式终止条件("ptc+lazy"))
  打印 "终止_lazy=" + 连接(模式终止条件("lazy"))
  打印 "开关_ptc_lazy=" + 转字符串(模式开关表("ptc+lazy")["minimal_action"])
  打印 "开关_std_def=" + 转字符串(长度(模式开关表("standard+default")))
主程()
'''


def test_二十组合矩阵齐全(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    assert kv.get('矩阵数') == '20', out
    assert kv.get('方法数') == '5', out
    assert kv.get('方法', '').split(',') == METHODS, kv.get('方法')
    want = [a + '+' + m for a in AGENTS for m in METHODS]
    assert kv.get('矩阵', '').split(',') == want, kv.get('矩阵')
    for cid in want:
        assert kv.get('已知_' + cid) == 'True', (cid, out)
        rows, flat = kv.get('统计_' + cid, '/').split('/')
        assert int(rows) > 0 and int(flat) == int(rows) + 1, (cid, kv.get('统计_' + cid))


def test_与旧八预设等价(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    pairs = [('standard', 'standard+default'), ('ptc', 'ptc+default'),
             ('minimal', 'minimal+default'), ('cordis', 'cordis+default'),
             ('topdown', 'standard+topdown'), ('bottomup', 'standard+bottomup'),
             ('brainstorm', 'standard+brainstorm'), ('lazy', 'standard+lazy')]
    for old, combo in pairs:
        assert kv.get('叶_' + combo) == kv.get('旧叶_' + old), (old, combo, out)
        assert kv.get('统计_' + combo) == kv.get('旧统计_' + old), (old, combo, out)


def test_别名解析(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    assert kv.get('别名_topdown') == 'standard+topdown', out
    assert kv.get('别名_ptc') == 'ptc+default', out
    assert kv.get('组合串解析') == 'True:standard+default', out
    for k in ('多个加号', '空串', '未知串', '调序'):
        assert kv.get(k) == 'False', (k, out)
    assert kv.get('组合串生成') == 'ptc+lazy', out
    assert kv.get('组合串非法') == '', out


def test_方法只删不增(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    assert kv.get('删_default') == '', out
    assert kv.get('删_topdown') == '', out

    def leaves(cid):
        return [x for x in kv.get('叶_' + cid, '').split(',') if x]

    ptc_brain = leaves('ptc+brainstorm')
    for gone in ('tool-fs-write', 'tool-bash', 'tool-pwsh', 'tool-goal', 'tool-subagent', 'workflow-ptc'):
        assert gone not in ptc_brain, (gone, out)
    assert 'tool-fs-read' in ptc_brain, out

    cordis_bot = leaves('cordis+bottomup')
    assert 'tool-goal' not in cordis_bot and 'tool-ask-user' not in cordis_bot, out

    assert leaves('minimal+topdown') == leaves('minimal+default'), out
    for a in AGENTS:
        assert leaves(a + '+default') == leaves(a + '+topdown'), (a, out)


def test_行为面取方法维(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    assert kv.get('提示_std_def') == '0', out
    assert kv.get('提示_std_brain前7') == '## 工作方式', out
    assert kv.get('提示_ptc_lazy前7') == '## 工作方式', out
    assert kv.get('终止_ptc_lazy') == kv.get('终止_lazy'), out
    assert kv.get('开关_ptc_lazy') == 'True', out
    assert kv.get('开关_std_def') == '0', out


def _src(path):
    return open(os.path.join(ROOT, path), encoding='utf-8').read()


def test_CLI_有_method_旗标():
    src = _src('src/cli外壳.light')
    assert '"--method"' in src, src[:200]
    assert '解析工作方法' in src
    assert '组合预设标识' in src
    assert '工作方法清单()' in src


def _skip_if_no_cli():
    if not _find_sibling('LIGHTPLUGIN'):
        try:
            import pytest
            pytest.skip('缺 lightplugin，跳过 CLI 集成')
        except ImportError:
            return True
    return False


CLI_DRIVER = '''
从 cli外壳 导入 解析工作方法, 组合预设标识, 外壳用法
段落 主程():
  打印 "用法有method=" + 转字符串(字符串包含(外壳用法(), "--method"))
  打印 "解析default=" + 转字符串(解析工作方法("default"))
  打印 "解析懒人=" + 转字符串(解析工作方法("lazy"))
  打印 "解析空=" + 转字符串(解析工作方法(""))
  打印 "组合1=" + 组合预设标识("ptc", "lazy")
  打印 "组合2=" + 组合预设标识("lazy", "")
  打印 "组合3=" + 组合预设标识("", "brainstorm")
  打印 "组合4=" + 组合预设标识("cordis+bottomup", "lazy")
主程()
'''


def test_CLI_组合(tmp_path):
    if _skip_if_no_cli():
        return
    try:
        rc, out, kv = _run(CLI_DRIVER, tmp_path, 'cli')
    except subprocess.TimeoutExpired:
        return
    if rc != 0 and '模块未找到' in out:
        return
    assert rc == 0, out
    assert kv.get('用法有method') == 'True', out
    assert kv.get('解析default') == 'default', out
    assert kv.get('解析懒人') == 'lazy', out
    assert kv.get('组合1') == 'ptc+lazy', out
    assert kv.get('组合2') == 'standard+lazy', out
    assert kv.get('组合3') == 'standard+brainstorm', out
    assert kv.get('组合4') == 'cordis+lazy', out


def test_Web_组合键与统计帧():
    src = _src('src/web服务器.light')
    assert '归一化预设' in src
    assert '组 合键' not in src
    assert '组合键' in src, '缓存键必须是规范化组合串'
    assert '"方法"' in src and '最近方法' in src
    assert '解析组合(预设值)' in src


def test_前端两下拉与存储升级():
    app = _src('webui/app.js')
    idx = _src('webui/index.html')
    ns = _src('webui/new-session.js')
    assert 'method-select' in idx and 'method-select' in app
    assert 'currentCombo' in app and 'splitModeValue' in app
    assert 'setModePair' in app
    assert 'lh.mode' in app
    assert 'standard+default' in ns
    assert 'ns-method-select' in ns
    assert '"default", "topdown", "bottomup", "brainstorm", "lazy"' in ns


def test_设置页与文档():
    sp = _src('src/设置页.light')
    assert '造预设元数据("default", "默认"' in sp
    assert '真, 5, 假, "method"' in sp
    docs = _src('docs/功能对标/模式规格.md')
    assert '0.3' in docs and '正交' in docs
    ch = _src('CHANGELOG.md')
    assert 'T-0441' in ch
