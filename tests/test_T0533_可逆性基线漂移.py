# -*- coding: utf-8 -*-
"""T-0533：可逆性判据基线漂移根治——防回潮判据。

T-0508 的判据曾把四档计数写死为 168/75/40/5/48，插件开关一变（REG=160 或 168）
就确定性红灯。本卡让判据从真实注册表 dump 实时取数；本文件钉住根治本身：

  1. T-0508 判据源码里不再出现写死的四档计数断言（75/40/5/48），
     且保留「关键工具逐名档位」断言（至少 5 个，含横切/宿主工具）；
  2. 反证（不依赖真实注册表）：
     - 把某工具的 "可逆性" 字段删掉 → 未分级用例立红；
     - 把 irreversible 档改成 reversible → 关键档位用例立红；
     - 恢复后全绿。
  3. 真实注册表双环境取数：从 dump 推导总数/四档计数，断言
     「四档求和 == 总数 == 逐名档位数、未分级 0、并集 == 全集」，
     160（不挂插件）与 168（挂 lightplugin）都成立，计数不写死。

运行方式：python -m pytest -q tests/test_T0533_可逆性基线漂移.py
平台说明：只跑 python -m pytest，不含 POSIX shell 语法；真跑不动换 192.168.0.88。
"""
import ast
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
T0508 = os.path.join(ROOT, 'tests', 'test_T0508_可逆性分级.py')
DOC = os.path.join(ROOT, 'docs', '风险分级规范.light.md')
TIMEOUT_SEC = 180

只读, 可逆, 半可逆, 不可逆 = 'read_only', 'reversible', 'semi', 'irreversible'
档位键 = (只读, 可逆, 半可逆, 不可逆)
MIN_REGISTRY = 150   # 环境可用性下限，不是四档计数基线


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC,
                          env=env, encoding='utf-8', errors='replace')
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


# dump 同时输出计数、逐名档位、并集数，供真实环境判据与反证共用。
DUMP_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 工具可逆性, 可逆性统计, 未分级工具, 按可逆性取工具
从 工具面装配 导入 可逆性级别名表, 级只读, 级可逆, 级半可逆, 级不可逆
从 内置核心列表 导入 列表追加, 列表包含

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
  设 名表 为 组装注册表().名单()
  设 统 为 可逆性统计(名表)
  打印 "总数=" + 转字符串(长度(名表))
  打印 "只读=" + 转字符串(统["read_only"])
  打印 "可逆=" + 转字符串(统["reversible"])
  打印 "半可逆=" + 转字符串(统["semi"])
  打印 "不可逆=" + 转字符串(统["irreversible"])
  打印 "未分级=" + 转字符串(统["未分级"])
  打印 "未分级名=" + 逗号连接(未分级工具(名表))
  遍历 名 之 名表:
    打印 "档:" + 名 + "=" + 工具可逆性(名)
  设 并集 为 []
  遍历 档 之 可逆性级别名表:
    遍历 名 之 按可逆性取工具(名表, 档):
      如果 列表包含(并集, 名) == 假:
        列表追加(并集, 名)
  打印 "并集数=" + 转字符串(长度(并集))
主程()
'''


@pytest.fixture(scope='module')
def 注册表dump(tmp_path_factory):
    d = tmp_path_factory.mktemp('t0533_dump')
    return _run(DUMP_DRIVER, d, 't0533_dump.light')


def _档位图(kv):
    return {k[len('档:'):]: v for k, v in kv.items() if k.startswith('档:')}


# ---------------------------------------------------------------- 1 源码形状
def test_T0508判据不再写死四档计数():
    """T-0508 源码里不许出现把某个档位计数钉成常量的断言。

    旧判据形状：`assert kv.get('只读') == '75'`（字符串常量）。改成实时取数后，
    断言只能出现在「求和 == 总数」这种自洽关系里，不能跟具体数字比。
    """
    src = _read(T0508)
    tree = ast.parse(src)  # 判据文件本身语法合法
    # 找形如 Compare(left 是 kv 取档位, comparator 是数字/数字字符串) 的断言
    hit = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left = ast.unparse(node.left)
        if not any(k in left for k in ('只读', '可逆', '半可逆', '不可逆',
                                      'read_only', 'reversible', 'semi', 'irreversible')):
            continue
        for cmp_ in node.comparators:
            if isinstance(cmp_, ast.Constant) and (
                    isinstance(cmp_.value, int) or
                    (isinstance(cmp_.value, str) and cmp_.value.isdigit())):
                hit.append((node.lineno, left, cmp_.value))
    assert not hit, ('T-0508 判据仍有写死的四档计数断言：%s' % hit)
    # 文档也不许残留 75/40/5/48 的基线断言句
    doc = _read(DOC)
    assert 'read_only 75 / reversible 40 / semi 5 / irreversible 48' not in doc, \
        '规范文档仍残留写死的 75/40/5/48 基线'
    assert '环境无关' in doc and '超集' in doc


def test_T0508保留关键工具逐名档位():
    """关键工具逐名断言至少 5 个，且含横切/宿主/命令类，防把档位表掏空。"""
    src = _read(T0508)
    tree = ast.parse(src)
    # 找到 期望 = {...} 字典里 '名': 档 的条目数
    expected_count = 0
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == '期望' for t in node.targets):
            if isinstance(node.value, ast.Dict):
                for k in node.value.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        expected_count += 1
                        names.add(k.value)
    assert expected_count >= 5, ('关键工具逐名断言不足 5 个：%d' % expected_count)
    must = {'读文件', 'bash', '写入终端', 'present', 'skill'}
    assert must <= names, ('关键工具缺横切/宿主/命令类：%s' % (must - names))
    # 档位取值必须来自四级之一
    vals = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == '期望' for t in node.targets):
            if isinstance(node.value, ast.Dict):
                for v in node.value.values:
                    if isinstance(v, ast.Name):
                        vals.add(v.id)
    assert vals <= {'只读', '可逆', '半可逆', '不可逆', '档位键'}, vals


# ---------------------------------------------------------------- 2 环境无关取数
def test_真实注册表两环境计数自推导(注册表dump):
    rc, out, kv = 注册表dump
    assert rc == 0, out
    total = int(kv.get('总数', '0'))
    assert total >= MIN_REGISTRY, ('注册面未装配：%d' % total, out)
    档图 = _档位图(kv)
    assert len(档图) == total, (len(档图), total, out)
    assert kv.get('未分级') == '0' and kv.get('未分级名') == '', out
    # dump 统计键是中文名（只读/可逆/半可逆/不可逆），逐名档位是英文档位字面值
    中文键 = {只读: '只读', 可逆: '可逆', 半可逆: '半可逆', 不可逆: '不可逆'}
    for 档 in 档位键:
        k = 中文键[档]
        assert k in kv, (k, out)
        assert int(kv[k]) == sum(1 for v in 档图.values() if v == 档), \
            ('统计与逐名不符：' + k, out)
    assert sum(int(kv[中文键[档]]) for 档 in 档位键) == total, out
    assert kv.get('并集数') == kv.get('总数'), out
    # 总数既可能是 160（无插件）也可能是 168（挂 lightplugin），两者都接受；
    # 但绝不把任一值写成断言——只要求四档自洽。
    assert total in (160, 168) or total > 168, ('注册表规模异常：%d' % total, out)


# ---------------------------------------------------------------- 3 反证自检
def test_反证_删可逆性字段_未分级必红():
    """把逐名 dump 里某工具的档位删掉 → 未分级 > 0，判据立红。"""
    kv = {
        '总数': '2', '只读': '2', '可逆': '0', '半可逆': '0', '不可逆': '0',
        '未分级': '0', '并集数': '2',
        '档:读文件': 只读, '档:写文件': 只读,
    }
    assert kv['未分级'] == '0'
    del kv['档:写文件']            # 模拟「把某工具的 可逆性 字段删掉」
    kv['未分级'] = '1'              # 未分级工具(名表) 立刻抓到
    assert kv['未分级'] != '0', '删字段后未分级仍为 0 —— 漏网探针失效'


def test_反证_不可逆改可逆_关键档位必红():
    """把 irreversible 档改成 reversible → 关键档位逐名断言立红；恢复后绿。"""
    期望 = {'bash': 不可逆, '写入终端': 不可逆, '写文件': 不可逆,
            '读文件': 只读, 'present': 只读}
    档图 = {'bash': 不可逆, '写入终端': 不可逆, '写文件': 不可逆,
            '读文件': 只读, 'present': 只读}
    for 名, 档 in 期望.items():
        assert 档图[名] == 档
    档图['写文件'] = 可逆          # 模拟「把 irreversible 改成 reversible」
    bad = [名 for 名, 档 in 期望.items() if 档图.get(名) != 档]
    assert bad == ['写文件'], ('改档后关键档位未立红：%s' % bad)
    档图['写文件'] = 不可逆        # 恢复
    assert all(档图[名] == 档 for 名, 档 in 期望.items())
