# -*- coding: utf-8 -*-
"""T-0509：可逆性分级 → 执行前确认门控（接线判据）。

覆盖四层：
  1. 策略层（纯逻辑）：默认「只读/可逆放行、半可逆提示、不可逆确认」；
     覆盖配置、未分级、缺档、非法值的兜底（不确定 → 确认）；
  2. 档位解析：原名 / 语义名（file.write）/ 条目回填（"可逆性" 字段）三条路
     都能落到同一档，语义名不因查表落空而降级；
  3. 执行器接线：不可逆动作触发确认（无审批通道即拒绝、批准后放行）、
     只读/可逆零拦截、半可逆与未分级只留痕、异步与并发路径与同步同判；
  4. 前置校验：bash rm/mv 目标越根、写文件越界、覆盖未读均被拒；
     校验复用 工具_路径安全（本驱动直测 校验破坏性命令目标）。

运行方式：python -m pytest -q tests/test_T0509_守卫接线.py
平台说明：判据只跑 python -m pytest，不含 head/grep/awk/!/$() 等 POSIX 语法；
Windows 若子进程输出触发 GBK 解码错误，加 PYTHONUTF8=1 再跑（不是产物问题）。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

只读, 可逆, 半可逆, 不可逆 = 'read_only', 'reversible', 'semi', 'irreversible'
放行, 提示, 校验, 确认 = '放行', '提示', '校验', '确认'


def _run(driver, tmp_path, name, root=None):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    if root is not None:
        env['T0509_ROOT'] = str(root).replace('\\', '/')
        env['HARNESS_ROOT'] = str(root).replace('\\', '/')
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC,
                          env=env, encoding='utf-8', errors='replace')
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


# ---- 驱动 1：策略层（纯逻辑，不执行工具）----
POLICY_DRIVER = '''
从 工具面装配 导入 造门控配置, 门控动作, 是合法门控动作, 门控事由, 工具门控判定
从 工具面装配 导入 门控放行, 门控提示, 门控校验, 门控确认, 门控动作表
从 工具执行 导入 建注册表, 具注册工具, 级公开
从 工具面装配 导入 可逆性条目键
从 JSON 导入 序列化JSON

段落 回声(参数, 令牌 = 空):
  返回 "ok"

段落 主程():
  设 默认 为 造门控配置()
  打印("只读=" + 门控动作(默认, "read_only", 真))
  打印("可逆=" + 门控动作(默认, "reversible", 真))
  打印("半可逆=" + 门控动作(默认, "semi", 真))
  打印("不可逆=" + 门控动作(默认, "irreversible", 真))
  打印("未分级=" + 门控动作(默认, "irreversible", 假))
  打印("非法档=" + 门控动作(默认, "danger", 真))
  打印("空配置=" + 门控动作(空, "irreversible", 真))
  打印("动作表=" + 序列化JSON(门控动作表))
  打印("合法动作=" + 序列化JSON([是合法门控动作("放行"), 是合法门控动作("校验"),
    是合法门控动作("确认"), 是合法门控动作("乱写")]))
  设 宽 为 造门控配置(["irreversible": "校验", "semi": "放行",
    "read_only": "乱写", "未分级": "确认"])
  打印("宽不可逆=" + 门控动作(宽, "irreversible", 真))
  打印("宽半可逆=" + 门控动作(宽, "semi", 真))
  打印("宽只读=" + 门控动作(宽, "read_only", 真))
  打印("宽未分级=" + 门控动作(宽, "irreversible", 假))
  设 严 为 造门控配置(["irreversible": "确认"])
  打印("严不可逆=" + 门控动作(严, "irreversible", 真))
  # 档位解析：原名 / 语义名 / 条目回填
  设 注册 为 建注册表()
  具注册工具(注册, "读文件", 级公开, 回声)
  具注册工具(注册, "写文件", 级公开, 回声)
  具注册工具(注册, "自造样本", 级公开, 回声)
  字典设置(注册["工具表"][可逆性条目键(注册, "自造样本")], "可逆性", "semi")
  设 读判 为 工具门控判定(默认, 注册, "file.read")
  打印("读判=" + 读判["动作"] + "|" + 读判["档"] + "|" + 转字符串(读判["显式"]))
  设 写判 为 工具门控判定(默认, 注册, "file.write")
  打印("写判=" + 写判["动作"] + "|" + 写判["档"] + "|" + 转字符串(写判["显式"]))
  设 造判 为 工具门控判定(默认, 注册, "自造样本")
  打印("造判=" + 造判["动作"] + "|" + 造判["档"] + "|" + 转字符串(造判["显式"]))
  设 未知判 为 工具门控判定(默认, 注册, "完全没登记的工具")
  打印("未知判=" + 未知判["动作"] + "|" + 转字符串(未知判["显式"]))
  打印("写判事由含档=" + 转字符串(字符串包含(写判["事由"], "irreversible")))
  打印("未知判事由=" + 未知判["事由"])

主程()
'''


# ---- 驱动 2：执行器接线 + 前置校验 + 异步/并发同判 ----
EXEC_DRIVER = '''
从 工具执行 导入 建注册表, 具注册工具, 级公开, 建执行器, 执行工具
从 工具执行 导入 具异步执行, 具并发执行, 门控日志, 策略滑动窗
从 工具面装配 导入 造门控配置, 可逆性条目键
从 工具_路径安全 导入 校验破坏性命令目标
从 文件系统 导入 写入文件
从 JSON 导入 序列化JSON

段落 回显(参数, 令牌 = 空):
  返回 "ok"

段落 跑出(执行器, 工具名, 参数):
  返回 执行工具(执行器, 工具名, 级公开, "tester", 参数, 空)

段落 码(结果):
  返回 转字符串(结果["错误码"])

异步 段落 主程():
  设 根 为 环境变量("T0509_ROOT", "")
  设 注册 为 建注册表()
  具注册工具(注册, "读文件", 级公开, 回显)
  具注册工具(注册, "写文件", 级公开, 回显)
  具注册工具(注册, "编辑文件", 级公开, 回显)
  具注册工具(注册, "bash", 级公开, 回显)
  具注册工具(注册, "todo_write", 级公开, 回显)
  具注册工具(注册, "自造工具", 级公开, 回显)
  具注册工具(注册, "半可逆样本", 级公开, 回显)
  字典设置(注册["工具表"][可逆性条目键(注册, "半可逆样本")], "可逆性", "semi")

  # 限流放宽：本驱动连跑十余次，避免默认 10/1000ms 误伤判据
  设 器 为 建执行器(1000, 100000, 0, 策略滑动窗, 注册)
  设 批器 为 建执行器(1000, 100000, 0, 策略滑动窗, 注册)
  字典设置(批器, "审批通道", 真)
  字典设置(批器, "审批结果", "allowed-once")

  # 1) 只读 / 半可逆 / 未分级：零拦截（软守卫只留痕）
  设 r1 为 跑出(器, "读文件", ["路径": "note.txt"])
  打印("只读=" + r1["状态"])
  设 r2 为 跑出(器, "半可逆样本", ["x": 1])
  打印("半可逆=" + r2["状态"])
  设 r3 为 跑出(器, "自造工具", ["x": 1])
  打印("未分级=" + r3["状态"])

  # 2) 不可逆：确认门控（无通道拒绝 / 批准放行）
  设 r4 为 跑出(器, "todo_write", ["列表": []])
  打印("不可逆=" + r4["状态"] + "|" + 码(r4))
  设 r5 为 跑出(批器, "todo_write", ["列表": []])
  打印("不可逆批准=" + r5["状态"])

  # 3) 写文件覆盖：未读即拒；读过仍需确认（默认），批准后放行
  写入文件(根 + "/other.txt", "orig")
  设 w1 为 跑出(器, "写文件", ["路径": "other.txt", "内容": "x"])
  打印("覆盖未读=" + w1["状态"] + "|" + 码(w1))
  设 w2 为 跑出(器, "读文件", ["路径": "other.txt"])
  打印("覆盖前读=" + w2["状态"])
  设 w3 为 跑出(器, "写文件", ["路径": "other.txt", "内容": "y"])
  打印("覆盖已读未批=" + w3["状态"] + "|" + 码(w3))
  设 w4 为 跑出(批器, "读文件", ["路径": "other.txt"])
  打印("批准前读=" + w4["状态"])
  设 w5 为 跑出(批器, "写文件", ["路径": "other.txt", "内容": "z"])
  打印("覆盖已读批准=" + w5["状态"])
  设 w6 为 跑出(器, "写文件", ["路径": "../escape.txt", "内容": "x"])
  打印("越界写=" + w6["状态"] + "|" + 码(w6))
  设 e1 为 跑出(器, "编辑文件", ["路径": "../escape2.txt", "旧文本": "a", "新文本": "b"])
  打印("越界编辑=" + e1["状态"] + "|" + 码(e1))

  # 4) bash：良性放行；rm 目标越根即拒；递归强删交 T-0510 高危门（不回归）
  设 b1 为 跑出(器, "bash", ["命令": "echo hi"])
  打印("bash良性=" + b1["状态"])
  设 b2 为 跑出(器, "bash", ["命令": "rm ../outside.txt"])
  打印("bash越界rm=" + b2["状态"] + "|" + 码(b2))
  设 b3 为 跑出(器, "bash", ["命令": "rm -rf build"])
  打印("bash递归=" + b3["状态"] + "|" + 码(b3))

  # 5) 异步 / 并发与同步同判
  设 a1 为 等待 具异步执行(器, "todo_write", 级公开, "tester", ["列表": []], 空)
  打印("异步不可逆=" + a1["状态"] + "|" + 码(a1))
  设 a2 为 等待 具异步执行(器, "读文件", 级公开, "tester", ["路径": "note.txt"], 空)
  打印("异步只读=" + a2["状态"])
  设 c1 为 等待 具并发执行(器, [
    {"工具名": "todo_write", "参数": ["列表": []]},
    {"工具名": "读文件", "参数": ["路径": "note.txt"]}], 级公开, "tester", 空)
  打印("并发=" + 序列化JSON([c1[0]["状态"], c1[1]["状态"]]))

  # 6) 配置放宽：irreversible → 校验（强制校验后放行，硬拒绝仍生效）
  设 宽 为 建执行器(1000, 100000, 0, 策略滑动窗, 注册, 空, 空,
    造门控配置(["irreversible": "校验"]))
  设 q1 为 跑出(宽, "todo_write", ["列表": []])
  打印("配置校验=" + q1["状态"])
  设 q2 为 跑出(宽, "写文件", ["路径": "other.txt", "内容": "w"])
  打印("配置校验覆盖=" + q2["状态"] + "|" + 码(q2))

  # 7) 路径安全直测（复用 工具_路径安全，不另造路径校验）
  设 p1 为 校验破坏性命令目标("rm build.tmp", 根)
  设 p2 为 校验破坏性命令目标("rm -rf " + 根 + "/build", 根)
  设 p3 为 校验破坏性命令目标("rm /etc/passwd", 根)
  设 p4 为 校验破坏性命令目标("echo hi", 根)
  设 p5 为 校验破坏性命令目标("mv -f src.txt " + 根 + "/dst.txt", 根)
  打印("路径=" + 序列化JSON([p1["通过"], p2["通过"], p3["通过"], p4["通过"],
    p5["通过"]]))

  # 8) 门控日志：半可逆/未分级留痕，只读无痕
  设 日志 为 门控日志(器)
  设 动作表 为 []
  遍历 项 之 日志:
    动作表.追加(项["工具名"] + ":" + 项["动作"])
  打印("日志=" + 序列化JSON(动作表))

异步 运行 主程()
'''


@pytest.fixture(scope='module')
def 策略层(tmp_path_factory):
    d = tmp_path_factory.mktemp('t0509_policy')
    return _run(POLICY_DRIVER, d, 't0509_policy.light')


@pytest.fixture(scope='module')
def 执行层(tmp_path_factory):
    d = tmp_path_factory.mktemp('t0509_exec')
    root = d / 'root'
    root.mkdir()
    return _run(EXEC_DRIVER, d, 't0509_exec.light', root=root)


def _b(值):
    return 值 in ('True', '真')


# ---------------------------------------------------------------------------
# 1. 策略层：强度只随不可逆程度递增
# ---------------------------------------------------------------------------
def test_默认策略按不可逆程度递增(策略层):
    rc, out, kv = 策略层
    assert rc == 0, out
    assert kv.get('只读') == 放行, out
    assert kv.get('可逆') == 放行, out
    assert kv.get('半可逆') == 提示, out
    assert kv.get('不可逆') == 确认, out
    assert json.loads(kv['动作表']) == [放行, 提示, 校验, 确认], out


def test_不确定与缺档偏向确认(策略层):
    rc, out, kv = 策略层
    assert rc == 0, out
    assert kv.get('未分级') == 提示, ('未显式分级默认软提示（不误拦插件/自造工具）', out)
    assert kv.get('非法档') == 确认, ('非法档必须 fail-closed 到确认', out)
    assert kv.get('空配置') == 确认, ('空配置回落默认策略', out)
    assert json.loads(kv['合法动作']) == [True, True, True, False], out


def test_配置覆盖与非法值忽略(策略层):
    rc, out, kv = 策略层
    assert rc == 0, out
    assert kv.get('宽不可逆') == 校验, out
    assert kv.get('宽半可逆') == 放行, out
    assert kv.get('宽只读') == 放行, ('非法动作值应被忽略，保持默认放行', out)
    assert kv.get('宽未分级') == 确认, out
    assert kv.get('严不可逆') == 确认, out


def test_档位解析覆盖原名语义名与回填(策略层):
    rc, out, kv = 策略层
    assert rc == 0, out
    # 语义名 file.read / file.write 必须经条目原名回落到静态表，不能降到「未分级」
    assert kv.get('读判') == 放行 + '|' + 只读 + '|True', out
    assert kv.get('写判') == 确认 + '|' + 不可逆 + '|True', out
    assert kv.get('造判') == 提示 + '|' + 半可逆 + '|True', out
    # 完全未登记的名字：动作软提示，且文案说明「未显式分级」
    assert kv.get('未知判') == 提示 + '|False', out
    assert _b(kv.get('写判事由含档', 'False')), out
    assert '未显式分级' in kv.get('未知判事由', ''), out


# ---------------------------------------------------------------------------
# 2. 执行器：只读/可逆零拦截，软守卫只留痕
# ---------------------------------------------------------------------------
def test_只读与合法可逆不被门控(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('只读') == 'ok', ('read_only 不得被门控', out)
    assert kv.get('半可逆') == 'ok', ('semi 只提示，不得拦', out)
    assert kv.get('未分级') == 'ok', ('未分级软提示，不得拦', out)
    assert kv.get('异步只读') == 'ok', out
    日志 = json.loads(kv['日志'])
    文本 = '|'.join(日志)
    assert '读文件:提示' not in 文本 and '读文件:校验' not in 文本, ('只读不应留门控痕', 日志)
    assert '半可逆样本:提示' in 文本, ('semi 应留软守卫痕', 日志)
    assert '自造工具:提示' in 文本, ('未分级应留痕', 日志)


# ---------------------------------------------------------------------------
# 3. 不可逆：确认门控（同步/异步/并发同判）
# ---------------------------------------------------------------------------
def test_不可逆工具无审批即拒绝(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('不可逆') == 'permission_denied|REVERSIBILITY_CONFIRM', out
    assert kv.get('异步不可逆') == 'permission_denied|REVERSIBILITY_CONFIRM', (
        '异步路径必须与同步同判', out)
    assert json.loads(kv['并发']) == ['permission_denied', 'ok'], (
        '并发路径：不可逆拒绝、只读放行', out)


def test_审批通道批准后放行(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('不可逆批准') == 'ok', ('allowed-once 应放行', out)


# ---------------------------------------------------------------------------
# 4. 前置校验：覆盖「已读」、路径越界、bash rm/mv 目标
# ---------------------------------------------------------------------------
def test_写文件覆盖未读被拒且读过仍需确认(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('覆盖前读') == 'ok', out
    assert kv.get('覆盖未读') == 'permission_denied|GUARD_PRECHECK_FAILED', (
        '覆盖已存在文件前未读 → 拒绝', out)
    assert kv.get('覆盖已读未批') == 'permission_denied|REVERSIBILITY_CONFIRM', (
        '读过之后覆盖仍需确认（默认按规范）', out)
    assert kv.get('覆盖已读批准') == 'ok', out


def test_路径越界在执行前被拒(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('越界写') == 'permission_denied|GUARD_PRECHECK_FAILED', out
    assert kv.get('越界编辑') == 'permission_denied|GUARD_PRECHECK_FAILED', out


def test_bash目标校验与高危门不回归(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('bash良性') == 'ok', ('非破坏性命令不得误拦', out)
    assert kv.get('bash越界rm') == 'permission_denied|GUARD_PRECHECK_FAILED', (
        'rm 目标越根 → 前置校验拒绝', out)
    assert kv.get('bash递归') == 'permission_denied|CMD_RISK_CONFIRM', (
        '递归强删仍走 T-0510 高危门，错误码不变', out)
    assert json.loads(kv['路径']) == [True, True, False, True, True], out


# ---------------------------------------------------------------------------
# 5. 门控可配：放宽到「校验」后不可逆工具可执行，但硬校验仍生效
# ---------------------------------------------------------------------------
def test_配置放宽到校验后保留硬拒绝(执行层):
    rc, out, kv = 执行层
    assert rc == 0, out
    assert kv.get('配置校验') == 'ok', ('irreversible→校验：校验通过后放行', out)
    assert kv.get('配置校验覆盖') == 'permission_denied|GUARD_PRECHECK_FAILED', (
        '放宽动作不得绕过前置校验', out)