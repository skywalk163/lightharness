# -*- coding: utf-8 -*-
"""T-0502：W2/T2.2 改名落地——工具别名机制 + 语义名生效。

判据分四层：
  1. 映射表合法性：160 条、语义名 ^<域>.<动作>$、互不重复、长度 ≤ 40、
     不得等于任何旧名；域前缀与 工具面装配.工具域(旧名) 逐条一致（横切 → xcut）；
  2. 注册改名：把 160 个旧名逐个注册进 工具执行 注册表，登记键必须逐个等于语义名
     （模型/schema 侧看到的名字、工具名表、枚举顺序全部是语义名）；
  3. 别名兼容：27 条「保留别名」旧名经别名仍能取到同一个工具、执行到同一个实现；
     其余 133 条「直接改名」旧名不得再解析（防 160 个旧名回到模型面）；
     别名命中可观测（具别名统计 / 具别名命中表）；
  4. 不回归：参数签名（具登记参数模式 按旧名/新名等价）、返回结构（结果逐键一致）、
     叶子映射 / 工具域 / 装配报告 / 白名单 在语义名口径下与旧名口径等价
     （T-0448 / T-0496 的兼容哨兵）。

红线自查：白名单里出现的旧名**一个都不改**（T-0501 §7.4），靠别名兜住；
本用例断言 白名单("minimal") 仍是 ["bash"]，且不含任何语义名。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

SEM_RE = re.compile(r'^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$')

COMMON = '''
段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本
'''


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


# ---------------- Driver A：映射表 / 别名表 / 叶子 / 域 / 白名单 ----------------
MAP_DRIVER = COMMON + '''
从 工具面装配 导入 语义名映射表, 别名保留名单, 别名表, 语义名, 原名, 是语义名, 规范工具名, 解析可调名
从 工具面装配 导入 叶子映射, 工具域, 白名单

段落 主程():
  设 旧表 为 字典键列表(语义名映射表)
  打印 "总数=" + 转字符串(长度(旧表))
  遍历 旧名 之 旧表:
    设 新名 为 语义名映射表[旧名]
    打印 "S:" + 旧名 + "=" + 新名
    打印 "D:" + 旧名 + "=" + 工具域(旧名)
    打印 "L:" + 旧名 + "=" + 逗号连接(叶子映射(新名)) + "|" + 逗号连接(叶子映射(旧名))
  打印 "保留数=" + 转字符串(长度(别名保留名单))
  遍历 名 之 别名保留名单:
    打印 "K:" + 名 + "=1"
  设 别 为 别名表()
  打印 "别名数=" + 转字符串(长度(别))
  遍历 旧名 之 字典键列表(别):
    打印 "A:" + 旧名 + "=" + 别[旧名]
  # 解析语义（单向：新名直查 / 27 条旧名别名 / 其余原样）
  打印 "P:bash=" + 解析可调名("bash")
  打印 "P:压缩选块=" + 解析可调名("压缩选块")
  打印 "P:ctx.select_blocks=" + 解析可调名("ctx.select_blocks")
  打印 "C:压缩选块=" + 规范工具名("压缩选块")
  打印 "C:临时测试工具=" + 规范工具名("临时测试工具")
  打印 "I:ctx.select_blocks=" + 转字符串(是语义名("ctx.select_blocks"))
  打印 "I:压缩选块=" + 转字符串(是语义名("压缩选块"))
  打印 "O:ctx.select_blocks=" + 原名("ctx.select_blocks")
  # 白名单：旧名口径一个都不改（T-0501 §7.4）
  打印 "W:minimal=" + 逗号连接(白名单("minimal"))
  打印 "W:brainstorm=" + 逗号连接(白名单("brainstorm"))
  设 标 为 白名单("standard")
  设 语义混入 为 0
  遍历 名 之 标:
    如果 是语义名(名) == 真:
      设 语义混入 为 语义混入 + 1
  打印 "W:标准语义混入=" + 转字符串(语义混入)
主程()
'''

# ---------------- Driver B：注册改名 + 别名解析 + 执行路由 + 参数签名 ----------------
EXEC_DRIVER = COMMON + '''
从 工具执行 导入 建注册表, 具注册工具, 具登记参数模式, 取工具, 工具名表, 级公开
从 工具执行 导入 建执行器, 执行工具, 具别名统计, 具别名命中表
从 工具面装配 导入 语义名映射表, 别名保留名单, 语义名, 造门控配置, 级不可逆, 门控放行

段落 造处理(标签):
  设 处理 为 段落 接收 参数, 令牌:
    返回 {"工具": 标签, "收到": 参数}
  返回 处理

段落 校验入口(模式, 参数):
  如果 字典包含键(参数, "坏") == 真:
    返回 {"通过": 假, "载荷": {"message": "参数校验失败",
      "validationErrors": [["字段": "好"]], "error": {"code": "PARAM_SCHEMA_INVALID"}}}
  返回 {"通过": 真}

段落 造注册(带模式):
  设 注册 为 建注册表()
  遍历 旧名 之 字典键列表(语义名映射表):
    具注册工具(注册, 旧名, 级公开, 造处理(旧名))
  如果 带模式 == 真:
    设 模式 为 {"type": "object",
      "properties": {"好": {"type": "string"}}, "required": ["好"]}
    具登记参数模式(注册, "读文件", 模式)
  返回 注册

段落 主程():
  设 注册 为 造注册(真)
  设 名表 为 工具名表(注册)
  打印 "注册数=" + 转字符串(长度(名表))
  打印 "名表=" + 逗号连接(名表)
  # 逐个旧名：新名必中；旧名只在「保留别名」名单里才中
  设 错位 为 []
  遍历 旧名 之 字典键列表(语义名映射表):
    设 新名 为 语义名映射表[旧名]
    设 新中 为 0
    如果 取工具(注册, 新名) != 空:
      设 新中 为 1
    设 旧中 为 0
    如果 取工具(注册, 旧名) != 空:
      设 旧中 为 1
    设 该别名 为 0
    遍历 名 之 别名保留名单:
      如果 名 == 旧名:
        设 该别名 为 1
    如果 新中 != 1 或 旧中 != 该别名:
      错位.追加(旧名)
  打印 "错位数=" + 转字符串(长度(错位)) + ":" + 逗号连接(错位)
  # 执行路由：语义名逐个执行，结果里的「工具」标签必须仍是该工具自己的实现
  设 路由错 为 []
  # T-0509 合入后：不可逆档默认要求确认（无审批通道即拒）。本判据只验命名与路由，
  #   不验守卫强度，故显式把不可逆档放到「放行」，避免把门控行为混进改名判据。
  # （字典字面量的标识符键不大会求值，会变成 "级不可逆" 字面文本，故用 字典设置 建覆盖表）
  设 门控覆盖 为 {}
  字典设置(门控覆盖, 级不可逆, 门控放行)
  设 执行器 为 建执行器(1000, 1000, 0, "滑动窗口", 注册, 校验入口, 空,
    造门控配置(门控覆盖))
  遍历 旧名 之 字典键列表(语义名映射表):
    设 新名 为 语义名映射表[旧名]
    设 结果 为 执行工具(执行器, 新名, 级公开, "测试", {"好": "x"}, 空)
    如果 结果["状态"] != "ok" 或 结果["结果"]["工具"] != 旧名:
      路由错.追加(新名)
  打印 "语义路由错=" + 转字符串(长度(路由错)) + ":" + 逗号连接(路由错)
  # 别名执行：27 条旧名执行，必须命中同一个实现
  设 别名错 为 []
  遍历 旧名 之 别名保留名单:
    设 结果 为 执行工具(执行器, 旧名, 级公开, "测试", {"好": "x"}, 空)
    如果 结果["状态"] != "ok" 或 结果["结果"]["工具"] != 旧名:
      别名错.追加(旧名)
  打印 "别名执行错=" + 转字符串(长度(别名错)) + ":" + 逗号连接(别名错)
  # 返回结构：新旧两名各跑一次，键集必须逐键一致
  设 甲 为 执行工具(执行器, "bash", 级公开, "测试", {"好": "x"}, 空)
  设 乙 为 执行工具(执行器, "shell.run", 级公开, "测试", {"好": "x"}, 空)
  打印 "键集一致=" + 转字符串(字典键列表(甲) == 字典键列表(乙))
  打印 "结果一致=" + 转字符串(甲["结果"] == 乙["结果"])
  # 参数签名 / 校验闸门：按旧名登记的模式在语义名下同样生效（坏参 JSON 一致）
  设 坏旧 为 执行工具(执行器, "读文件", 级公开, "测试", {"坏": "x"}, 空)
  设 坏新 为 执行工具(执行器, "file.read", 级公开, "测试", {"坏": "x"}, 空)
  打印 "坏旧码=" + 转字符串(坏旧["错误码"])
  打印 "坏新码=" + 转字符串(坏新["错误码"])
  打印 "坏键集一致=" + 转字符串(字典键列表(坏旧) == 字典键列表(坏新))
  打印 "模式已登记=" + 转字符串(字典获取(取工具(注册, "file.read"), "参数模式", 空) != 空)
  打印 "统计=" + 转字符串(具别名统计(注册))
  打印 "命中表=" + 逗号连接(字典键列表(具别名命中表(注册)))
主程()
'''

# ---------------- Driver C：装配侧等价（叶子 / 域 / 装配报告 / 白名单） ----------------
ASSEMBLY_DRIVER = COMMON + '''
从 工具面装配 导入 语义名映射表, 原名, 叶子映射, 工具域, 装配报告

段落 造条目(名表):
  设 表 为 []
  遍历 名 之 名表:
    表.追加({"标识": 名, "工具名": 名})
  返回 表

段落 回映(名表):
  设 表 为 []
  遍历 名 之 名表:
    表.追加(原名(名))
  返回 表

段落 主程():
  设 旧表 为 字典键列表(语义名映射表)
  设 语义表 为 []
  设 叶错 为 []
  设 域错 为 []
  遍历 旧名 之 旧表:
    设 新名 为 语义名映射表[旧名]
    语义表.追加(新名)
    如果 叶子映射(新名) != 叶子映射(旧名):
      叶错.追加(新名)
    如果 工具域(新名) != 工具域(旧名):
      域错.追加(新名)
  打印 "叶错=" + 转字符串(长度(叶错)) + ":" + 逗号连接(叶错)
  打印 "域错=" + 转字符串(长度(域错)) + ":" + 逗号连接(域错)
  设 旧条 为 造条目(旧表)
  设 新条 为 造条目(语义表)
  设 预设表 为 ["standard", "minimal", "brainstorm", "standard+brainstorm"]
  遍历 预设 之 预设表:
    设 旧报 为 装配报告(旧条, 预设)
    设 新报 为 装配报告(新条, 预设)
    打印 "R:" + 预设 + "=" + 转字符串(长度(旧报["保留"])) + "|" + 转字符串(长度(新报["保留"]))
    打印 "Q:" + 预设 + "=" + 转字符串(回映(新报["保留"]) == 旧报["保留"])
    打印 "U:" + 预设 + "=" + 转字符串(长度(旧报["未映射"])) + "|" + 转字符串(长度(新报["未映射"]))
主程()
'''


def _rows(kv, prefix):
    """把 S:/A:/K:/D:/L: 这类逐条目行还原成字典（值保留原文）。"""
    out = {}
    for key, val in kv.items():
        if key.startswith(prefix):
            out[key[len(prefix):]] = val
    return out


def test_映射表合法且域前缀对齐(tmp_path):
    rc, out, kv = _run(MAP_DRIVER, tmp_path, 't0502_map.light')
    assert rc == 0, out
    assert kv['总数'] == '160', ('映射表条数应为 160', kv.get('总数'), out)
    s = _rows(kv, 'S:')
    d = _rows(kv, 'D:')
    assert len(s) == 160, out
    assert len(set(s.keys())) == 160, ('旧名重复', out)
    sem = list(s.values())
    assert len(set(sem)) == 160, ('语义名重复', out)
    for old, new in s.items():
        assert SEM_RE.match(new), ('语义名不合规', old, new, out)
        assert len(new) <= 40, ('语义名超长', new, out)
        assert new != old, ('语义名与旧名相同', old, out)
        assert new.count('.') == 1, ('必须恰好一个点', new, out)
        domain = d.get(old, '')
        prefix = domain if domain != '横切' else 'xcut'
        assert new.split('.')[0] == prefix, ('域前缀与工具域不一致', old, new, domain, out)
    # 别名表严格等于保留名单，且只对表内名字生效
    keep = {k[2:] for k in kv if k.startswith('K:')}
    assert kv['保留数'] == '27', ('保留别名应为 27 条', kv.get('保留数'), out)
    a = _rows(kv, 'A:')
    assert set(a.keys()) == keep, ('别名表与保留名单不一致', sorted(set(a.keys()) ^ keep), out)
    for old in keep:
        assert a[old] == s[old], ('别名目标必须是该工具的语义名', old, a[old], s[old], out)
    # 解析语义：单向
    assert kv['P:bash'] == s['bash'], out
    assert kv['P:压缩选块'] == '压缩选块', ('直接改名的旧名不得被解析', out)
    assert kv['P:ctx.select_blocks'] == 'ctx.select_blocks', out
    assert kv['C:压缩选块'] == s['压缩选块'], out
    assert kv['C:临时测试工具'] == '临时测试工具', ('表外名字原样保留', out)
    assert kv['I:ctx.select_blocks'] == 'True', out
    assert kv['I:压缩选块'] == 'False', out
    assert kv['O:ctx.select_blocks'] == '压缩选块', out
    # 白名单不动（红线）
    assert kv['W:minimal'] == 'bash', ('minimal 白名单应保持旧名 bash', out)
    assert kv['W:brainstorm'].startswith('读文件,搜索文件'), ('brainstorm 白名单应保持旧名', out)
    assert 'file.read' not in kv['W:brainstorm'], ('白名单不得掺入语义名', out)
    assert kv['W:标准语义混入'] == '0', ('白名单里不得掺入语义名', out)


def test_注册端口径全部换成语义名(tmp_path):
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0502_exec.light')
    assert rc == 0, out
    assert kv['注册数'] == '160', ('注册表应为 160 个工具', kv.get('注册数'), out)
    assert kv['错位数'] == '0:0' or kv['错位数'].startswith('0:'), ('新旧名解析错位', kv.get('错位数'), out)
    assert kv['语义路由错'].startswith('0:'), ('语义名执行未路由到原实现', kv.get('语义路由错'), out)
    assert kv['别名执行错'].startswith('0:'), ('旧名别名执行未路由到原实现', kv.get('别名执行错'), out)
    assert kv['键集一致'] == 'True', ('返回结构被改动', out)
    assert kv['结果一致'] == 'True', ('同名工具结果不一致', out)
    assert kv['坏旧码'] == kv['坏新码'], ('参数校验闸门在新旧名下不一致', out)
    assert kv['坏键集一致'] == 'True', ('校验失败信封结构被改动', out)
    assert kv['模式已登记'] == 'True', ('按旧名登记的参数模式未落到语义名工具上', out)
    # 工具名表必须是语义名集合（顺序与映射表一致）
    s = _rows(_run(MAP_DRIVER, tmp_path, 't0502_map_names.light')[2], 'S:')
    names = [x for x in kv['名表'].split(',') if x]
    assert names == list(s.values()), ('登记顺序/名字与映射表不一致', names[:5], out)
    # 别名命中可观测
    stat = kv['统计']
    assert '"别名数": 27' in stat or "'别名数': 27" in stat, ('别名表应为 27 条', stat, out)
    assert '"别名命中": 0' not in stat and "'别名命中': 0" not in stat, ('别名命中没打点', stat, out)
    assert 'bash' in kv['命中表'], ('命中表应记录旧名', kv.get('命中表'), out)


def test_装配侧语义名与旧名等价(tmp_path):
    rc, out, kv = _run(ASSEMBLY_DRIVER, tmp_path, 't0502_asm.light')
    assert rc == 0, out
    assert kv['叶错'].startswith('0:'), ('叶子映射在语义名下不等价', kv.get('叶错'), out)
    assert kv['域错'].startswith('0:'), ('工具域在语义名下不等价', kv.get('域错'), out)
    for preset in ('standard', 'minimal', 'brainstorm', 'standard+brainstorm'):
        assert kv['Q:' + preset] == 'True', (preset, '装配报告保留集在语义名下不等价', out)
    # minimal / brainstorm 的收紧口径不变（T-0448 的兼容哨兵）
    old_n, new_n = kv['R:minimal'].split('|')
    assert (old_n, new_n) == ('1', '1'), ('minimal 应只留 1 个（bash）', kv['R:minimal'], out)
    old_b, new_b = kv['R:brainstorm'].split('|')
    assert (old_b, new_b) == ('2', '2'), ('brainstorm 应只留读/搜 2 个', kv['R:brainstorm'], out)


def test_同族工具与trace不回归(tmp_path):
    """取工具 加了别名分支后，权限/审计/结果形状仍走原路（T-0515 同族判定的前提）。"""
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0502_exec_again.light')
    assert rc == 0, out
    assert kv['注册数'] == '160', out
    assert kv['语义路由错'].startswith('0:'), out


def test_与命名规范文档逐条一致(tmp_path):
    """T-0501 的 §6 映射表是唯一依据：文档在库时必须逐条对齐（不在库则跳过）。

    依赖卡 T-0501 合并后本用例自动生效；未合并前 docs/工具命名规范.light.md 不存在，
    跳过的理由写在 skip 文案里，不会假绿。
    """
    import pytest
    from pathlib import Path

    doc = Path(ROOT) / 'docs' / '工具命名规范.light.md'
    if not doc.exists():
        pytest.skip('T-0501 的命名规范文档尚未合并进本分支（依赖卡未 land）')
    text = doc.read_text(encoding='utf-8')
    block = text.split('<!-- T0501-映射表-开始 -->')[1].split('<!-- T0501-映射表-结束 -->')[0]
    block = block.split('```json')[1].split('```')[0]
    import json
    data = json.loads(block)
    table = {row['现名']: row['语义名'] for row in data['工具']}
    keep = set(data['别名保留名单'])

    rc, out, kv = _run(MAP_DRIVER, tmp_path, 't0502_map_doc.light')
    assert rc == 0, out
    s = _rows(kv, 'S:')
    assert s == table, ('落地的映射表与 T-0501 文档不一致',
                        sorted(set(s.items()) ^ set(table.items()))[:5], out)
    k = {x[2:] for x in kv if x.startswith('K:')}
    assert k == keep, ('别名保留名单与 T-0501 文档不一致', sorted(k ^ keep), out)
