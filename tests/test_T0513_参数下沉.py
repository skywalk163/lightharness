# -*- coding: utf-8 -*-
"""T-0513：工具参数键名下沉 schema description（提示词压缩）判据。

四层：
  1. 词法层：改动的 src 模块 tokenize 零异常（复用 R38 的 lexer 手法）；
  2. 基线层：下沉前的常驻文本必须逐字等于真实系统提示的段（防止度量基线漂移）；
  3. 完整性层：移出常驻区的每条信息都能在 schema description 里读到——
     参数细节覆盖真实 schema 的全部 properties 键名，行为要点也一并保留；
     常驻区不再出现任何实参键名（下沉 ≠ 删除，只换了存放位置）；
  4. 行为层：回填只改 description，parameters/name 与调用方式零变化；幂等；
     别名（read_file/grep）与未知工具口径正确；节省量字符/token 双口径可量化。

反证（summary 附记录）：把 参数细节表 里 bash 的「超时」删掉，
test_参数细节覆盖真实schema全部键名 立红；把 常驻工具规则文本 里的
「见其 schema description」改回旧契约的键名清单，test_常驻区不再出现实参键名 立红。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
RUNNER = os.path.join(ROOT, '运行.py')
sys.path.insert(0, os.path.join(ROOT, '..', 'light-merge', 'src'))
import lexer  # noqa: E402

ASSEMBLY = os.path.join(SRC, '工具面装配.light')
PRESENTATION = os.path.join(SRC, '工具展示.light')
TIMEOUT_SEC = 180

# 期望下沉覆盖的工具（规范名 = 真实 schema 的 name）
EXPECTED_TOOLS = ['bash', '读文件', '写文件', '编辑文件', '搜索文件']

# 每个工具旧常驻段里不可丢的行为要点（移出后必须能在 schema description 读到）
BEHAVIOR_PHRASES = {
    'bash': '一次调用只做一件事',
    '读文件': '返回带行号',
    '写文件': '覆盖已有文件前先读',
    '编辑文件': '唯一命中',
    '搜索文件': '再读命中文件确认',
}

DRIVER = '''
从 JSON 导入 序列化JSON
从 内置核心字典 导入 字典设置, 字典键列表, 字典获取
从 内置核心列表 导入 列表追加
从 内置核心字符串 导入 字符串包含
从 工具面装配 导入 下沉前常驻文本, 下沉后常驻文本, 下沉节省, 参数细节, 参数下沉标记
从 工具面装配 导入 回填描述, 回填工具定义, 旧常驻段表, 旧实参契约段
从 系统提示 导入 bash指导段, 读文件指导段, 写文件指导段, 编辑文件指导段, 搜索文件指导段, 实参契约段
从 工具_bash 导入 造bash工具定义
从 工具_读文件 导入 造读文件工具定义
从 工具_写文件 导入 造写文件工具定义
从 工具_编辑文件 导入 造编辑文件工具定义
从 工具_搜索文件 导入 造搜索文件工具定义

段落 造定义表():
  设 表 为 []
  列表追加(表, 造bash工具定义())
  列表追加(表, 造读文件工具定义())
  列表追加(表, 造写文件工具定义())
  列表追加(表, 造编辑文件工具定义())
  列表追加(表, 造搜索文件工具定义())
  返回 表

段落 取参数键表(工具模式):
  返回 字典键列表(工具模式["parameters"]["properties"])

段落 缺键(文本, 键表):
  设 结果 为 []
  遍历 键 之 键表:
    如果 字符串包含(文本, 键) == 假:
      列表追加(结果, 键)
  返回 结果

段落 命中键(文本, 键表):
  设 结果 为 []
  遍历 键 之 键表:
    如果 字符串包含(文本, 键) == 真:
      列表追加(结果, 键)
  返回 结果

段落 主程():
  设 结果 为 {}
  设 基线 为 {}
  字典设置(基线, "bash", 旧常驻段表["bash"] == bash指导段())
  字典设置(基线, "读文件", 旧常驻段表["读文件"] == 读文件指导段())
  字典设置(基线, "写文件", 旧常驻段表["写文件"] == 写文件指导段())
  字典设置(基线, "编辑文件", 旧常驻段表["编辑文件"] == 编辑文件指导段())
  字典设置(基线, "搜索文件", 旧常驻段表["搜索文件"] == 搜索文件指导段())
  字典设置(基线, "实参契约", 旧实参契约段 == 实参契约段())
  字典设置(结果, "基线", 基线)

  设 后文本 为 下沉后常驻文本()
  设 工具表 为 []
  遍历 定 之 造定义表():
    设 名 为 定["name"]
    设 键表 为 取参数键表(定)
    设 原描述 为 定["description"]
    设 细节 为 参数细节(名)
    设 回填 为 回填描述(名, 原描述)
    设 新定 为 回填工具定义(定)
    设 项 为 {}
    字典设置(项, "名", 名)
    字典设置(项, "参数键", 键表)
    字典设置(项, "细节", 细节)
    字典设置(项, "细节缺键", 缺键(细节, 键表))
    字典设置(项, "常驻含键", 命中键(后文本, 键表))
    字典设置(项, "参数未改", 新定["parameters"] == 定["parameters"])
    字典设置(项, "名未改", 新定["name"] == 名)
    字典设置(项, "原描述前缀保留", 字符串包含(回填, 原描述))
    字典设置(项, "含下沉标记", 字符串包含(回填, 参数下沉标记))
    字典设置(项, "幂等", 回填描述(名, 回填) == 回填)
    字典设置(项, "原定义未被就地改", 定["description"] == 原描述)
    列表追加(工具表, 项)
  字典设置(结果, "工具", 工具表)

  设 别名 为 {}
  字典设置(别名, "read_file", 参数细节("read_file") == 参数细节("读文件"))
  字典设置(别名, "read_alias", 参数细节("read") == 参数细节("读文件"))
  字典设置(别名, "grep", 参数细节("grep") == 参数细节("搜索文件"))
  字典设置(别名, "未知为空", 参数细节("查天气") == "")
  字典设置(结果, "别名", 别名)
  字典设置(结果, "未知回填原样", 回填描述("查天气", "原描述") == "原描述")

  字典设置(结果, "度量", 下沉节省())
  字典设置(结果, "前字符", 字符串长度(下沉前常驻文本()))
  字典设置(结果, "后字符", 字符串长度(后文本))
  字典设置(结果, "后文本", 后文本)
  打印 序列化JSON(结果)

主程()
'''


def _tokenize_ok(path):
    text = open(path, encoding='utf-8-sig', errors='replace').read()
    list(lexer.Lexer(text, deterministic=True).tokenize())
    return True


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC, env=env)
    payload = None
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith('{'):
            try:
                payload = json.loads(line)
                break
            except ValueError:
                continue
    return proc.returncode, proc.stdout + proc.stderr, payload


@pytest.fixture(scope='module')
def downshift(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0513')
    rc, out, payload = _run(DRIVER, tmp, 't0513_downshift.light')
    assert rc == 0, out
    assert payload is not None, ('驱动未输出 JSON 结果', out[-1200:])
    return payload


# --------------------------------------------------------------------
# 1) 词法层：改动模块 tokenize 零异常（复用 R38 的 lexer 手法）
# --------------------------------------------------------------------
@pytest.mark.parametrize('path', [ASSEMBLY, PRESENTATION])
def test_改动模块tokenize正常(path):
    assert _tokenize_ok(path), f'{path} tokenize 应无异常'


# --------------------------------------------------------------------
# 2) 基线层：下沉前文本逐字取自真实系统提示
# --------------------------------------------------------------------
def test_度量基线取自真实系统提示(downshift):
    baseline = downshift['基线']
    for key in ('bash', '读文件', '写文件', '编辑文件', '搜索文件', '实参契约'):
        assert baseline.get(key) is True, (
            f'下沉前基线[{key}] 与 系统提示 的真实段不一致——'
            f'度量基线已漂移，节省量不可信'
        )


# --------------------------------------------------------------------
# 3) 完整性层：键名下沉到 schema description，常驻区不再重复
# --------------------------------------------------------------------
def test_参数细节覆盖真实schema全部键名(downshift):
    tools = downshift['工具']
    assert [t['名'] for t in tools] == EXPECTED_TOOLS, tools
    for t in tools:
        assert t['参数键'], ('真实 schema 没有参数键，判据失效', t)
        assert t['细节'], ('缺少参数细节', t['名'])
        assert t['细节缺键'] == [], (
            f"{t['名']} 的 schema description 细节缺参数键 {t['细节缺键']}"
            f"（下沉不等于删除）"
        )


def test_常驻区不再出现实参键名(downshift):
    for t in downshift['工具']:
        assert t['常驻含键'] == [], (
            f"常驻区仍出现 {t['名']} 的实参键名 {t['常驻含键']}——参数没有真正下沉"
        )
    # 常驻区也不应再出现带键名的旧句式
    resident = downshift['后文本']
    for bad in ('实参键是「命令」', '实参键是「路径」', 'read_file 用「路径」'):
        assert bad not in resident, f'常驻区仍含旧键名句式：{bad}'


def test_移出的行为要点仍可读到(downshift):
    by_name = {t['名']: t for t in downshift['工具']}
    for name, phrase in BEHAVIOR_PHRASES.items():
        assert name in by_name, (name, by_name.keys())
        assert phrase in by_name[name]['细节'], (
            f'{name} 移出常驻区的行为要点「{phrase}」在 schema description 里读不到'
        )


# --------------------------------------------------------------------
# 4) 行为层：回填只改 description，签名/调用方式不变，幂等
# --------------------------------------------------------------------
def test_回填不改变参数签名与调用方式(downshift):
    for t in downshift['工具']:
        assert t['参数未改'] is True, (t['名'], 'parameters 被改动')
        assert t['名未改'] is True, (t['名'], 'name 被改动')
        assert t['原定义未被就地改'] is True, (t['名'], '回填就地修改了原定义（应返回副本）')


def test_回填保留原描述且幂等(downshift):
    for t in downshift['工具']:
        assert t['原描述前缀保留'] is True, (t['名'], '回填丢弃了原 description')
        assert t['含下沉标记'] is True, (t['名'], '回填未写入下沉标记')
        assert t['幂等'] is True, (t['名'], '重复回填会重复追加')


def test_别名与未知工具口径一致(downshift):
    alias = downshift['别名']
    for key in ('read_file', 'read_alias', 'grep', '未知为空'):
        assert alias[key] is True, (key, alias)
    assert downshift['未知回填原样'] is True, '未知工具的回填应原样返回'


# --------------------------------------------------------------------
# 5) 节省量可量化（字符 + token 双口径）
# --------------------------------------------------------------------
def test_节省量可量化(downshift):
    m = downshift['度量']
    before = downshift['前字符']
    after = downshift['后字符']
    assert before > 0 and after > 0, (before, after)
    assert before == after + m['节省字符'], (
        '字符账不平', before, after, m['节省字符'])
    assert m['节省字符'] > 0, ('常驻区没有省下字符', m)
    assert m['节省token'] > 0, ('常驻区没有省下 token', m)
    assert m['节省比'] >= 0.5, (
        f"常驻区压缩比不足：{m['节省比']:.2%}（应 >= 50%）")
    # token 双口径自洽：省 <= 前，且后 token 明显小于前 token
    assert m['后token'] < m['前token'] * 0.5, m
    # 回填是按需展开的 schema 成本，单独记账且为正
    assert m['回填字符'] > 0, m
