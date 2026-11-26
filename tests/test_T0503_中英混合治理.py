# -*- coding: utf-8 -*-
"""T-0503：W2/T2.3 中英混合工具名治理。

判据分三层：
  1. 清单与结论：151 个基线中文名工具每个都有且只有一档结论（双轨 / 展示 / 退役），
     计数 18 / 44 / 89，每档都有书面理由；三档并集恰好等于全部中文名；
  2. 调用路径红线：模型调用面 100% 语义名（ASCII）；展示名不进注册表、不被解析；
     展示 / 退役档中文名调用即 TOOL_NOT_FOUND；双轨 18 条经 T-0502 别名仍可执行；
  3. 单一事实来源：与 docs/工具命名规范.light.md §10 的机器可读块逐条互校
     （清单 / 分组 / 计数 / 理由），文档漂移即红。

反证（summary 附记录）：把 中文名展示组表 里 "交付登记" 挪进 双轨（即加进别名保留名单
不行，别名名单不动）——改测「把 交付登记 从展示组删掉」，结论兜底成「退役」，
test_治理清单完整且三档计数一致 的 展示数 44 立红。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240
DOC = Path(ROOT) / 'docs' / '工具命名规范.light.md'
SEM_RE = re.compile(r'^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')

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

# ---------------- Driver A：治理清单 / 结论 / 理由 / 展示名 / 漏网 ----------------
MAP_DRIVER = COMMON + '''
从 工具面装配 导入 中文名治理表, 中文名结论, 中文名组, 中文名理由, 中文名治理统计
从 工具面装配 导入 展示名, 是展示专用名, 是中文工具名, 中文名漏网
从 工具面装配 导入 语义名映射表, 别名保留名单, 白名单, 规范工具名, 解析可调名

段落 主程():
  设 统 为 中文名治理统计()
  打印 "统计_双轨=" + 转字符串(字典获取(统, "双轨", 0))
  打印 "统计_展示=" + 转字符串(字典获取(统, "展示", 0))
  打印 "统计_退役=" + 转字符串(字典获取(统, "退役", 0))
  打印 "统计_合计=" + 转字符串(字典获取(统, "合计", 0))
  # 中文名逐一给结论 / 组 / 展示名 / 理由；规范名里出现中文即记为 C:
  设 中文数 为 0
  设 规范混中文 为 0
  遍历 名 之 字典键列表(语义名映射表):
    如果 是中文工具名(名) == 真:
      设 中文数 为 中文数 + 1
      打印 "G:" + 名 + "=" + 中文名结论(名)
      打印 "B:" + 名 + "=" + 中文名组(名)
      打印 "U:" + 名 + "=" + 展示名(名)
      打印 "R:" + 名 + "=" + 中文名理由(名)
      设 规范 为 规范工具名(名)
      如果 是中文工具名(规范) == 真:
        设 规范混中文 为 规范混中文 + 1
        打印 "C:" + 名 + "=" + 规范
    否则:
      打印 "EN:" + 名 + "=" + 展示名(名)
  打印 "中文数=" + 转字符串(中文数)
  打印 "规范混中文=" + 转字符串(规范混中文)
  # 定位判定（选点固定，防止规则被悄悄放宽）
  打印 "展示专用_读文件=" + 转字符串(是展示专用名("读文件"))
  打印 "展示专用_待办添加=" + 转字符串(是展示专用名("待办添加"))
  打印 "展示专用_凭据存入=" + 转字符串(是展示专用名("凭据存入"))
  打印 "展示名_语义=" + 展示名("file.read")
  打印 "展示名_英文=" + 展示名("bash")
  打印 "展示名_退役=" + 展示名("凭据存入")
  打印 "展示名_双轨=" + 展示名("读文件")
  # 模型/白名单面不得有「无法治理」的中文名
  打印 "漏网_标准=" + 逗号连接(中文名漏网(白名单("standard")))
  打印 "漏网_只读=" + 逗号连接(中文名漏网(白名单("brainstorm")))
  打印 "漏网_全旧名=" + 逗号连接(中文名漏网(字典键列表(语义名映射表)))
  设 表外 为 ["临时测试工具", "查天气这种不存在的工具", "copilot_工具", "交付登记", "装配团队面板"]
  打印 "漏网_表外=" + 逗号连接(中文名漏网(表外))
  打印 "解析_展示档=" + 解析可调名("交付登记")
  打印 "解析_退役档=" + 解析可调名("凭据存入")
主程()
'''

# ---------------- Driver B：注册表 / 执行路径（展示名不得可调） ----------------
EXEC_DRIVER = COMMON + '''
从 工具执行 导入 建注册表, 具注册工具, 取工具, 工具名表, 级公开
从 工具执行 导入 建执行器, 执行工具
从 工具面装配 导入 中文名治理表, 中文名结论, 展示名, 是中文工具名
从 工具面装配 导入 语义名映射表, 别名保留名单, 造门控配置, 级不可逆, 门控放行

段落 造处理(标签):
  设 处理 为 段落 接收 参数, 令牌:
    返回 {"工具": 标签}
  返回 处理

段落 主程():
  设 注册 为 建注册表()
  遍历 名 之 字典键列表(语义名映射表):
    具注册工具(注册, 名, 级公开, 造处理(名))
  设 注册名 为 工具名表(注册)
  打印 "注册数=" + 转字符串(长度(注册名))
  设 中文注册数 为 0
  遍历 名 之 注册名:
    如果 是中文工具名(名) == 真:
      设 中文注册数 为 中文注册数 + 1
  打印 "中文注册数=" + 转字符串(中文注册数)
  打印 "注册名=" + 逗号连接(注册名)
  # ① 可调性：双轨必中；展示 / 退役一律不可中
  设 可调错 为 []
  遍历 名 之 字典键列表(中文名治理表):
    设 档 为 中文名结论(名)
    设 命中 为 0
    如果 取工具(注册, 名) != 空:
      设 命中 为 1
    如果 档 == "双轨" 且 命中 != 1:
      可调错.追加("双轨不可调:" + 名)
    如果 档 == "展示" 且 命中 != 0:
      可调错.追加("展示名可调:" + 名)
    如果 档 == "退役" 且 命中 != 0:
      可调错.追加("退役名可调:" + 名)
  打印 "可调错=" + 转字符串(长度(可调错)) + ":" + 逗号连接(可调错)
  # ② 展示标签不得与任何注册键撞名（撞名就等于展示名偷偷进了调用面）
  设 撞键 为 []
  遍历 名 之 字典键列表(中文名治理表):
    如果 中文名结论(名) != "展示":
      继续
    设 标 为 展示名(名)
    如果 列表包含(注册名, 标) == 真:
      如果 列表包含(撞键, 标) == 假:
        撞键.追加(标)
  打印 "展示撞键=" + 转字符串(长度(撞键)) + ":" + 逗号连接(撞键)
  # ③ 执行：双轨 18 条中文名路由到自己的实现；展示 / 退役一律 TOOL_NOT_FOUND
  # T-0509 合入后：不可逆档默认要求确认（无审批通道即拒）。本判据验的是「双轨中文名
  #   能否路由到原实现」，与守卫强度无关，故不可逆档显式放行，避免门控污染命名判据。
  # （字典字面量的标识符键不求值，会用 "级不可逆" 字面文本，故用 字典设置 建覆盖表）
  设 门控覆盖 为 {}
  字典设置(门控覆盖, 级不可逆, 门控放行)
  设 执行器 为 建执行器(1000, 1000, 0, "滑动窗口", 注册, 空, 空,
    造门控配置(门控覆盖))
  设 参数 为 {}
  设 双轨错 为 []
  遍历 名 之 别名保留名单:
    如果 是中文工具名(名) == 假:
      继续
    设 结果 为 执行工具(执行器, 名, 级公开, "测试", 参数, 空)
    如果 结果["状态"] != "ok":
      双轨错.追加("状态:" + 名)
    否则:
      如果 结果["结果"]["工具"] != 名:
        双轨错.追加("路由:" + 名)
  打印 "双轨执行错=" + 转字符串(长度(双轨错)) + ":" + 逗号连接(双轨错)
  设 展示错 为 []
  设 退役错 为 []
  遍历 名 之 字典键列表(中文名治理表):
    设 档 为 中文名结论(名)
    如果 档 == "双轨":
      继续
    设 结果 为 执行工具(执行器, 名, 级公开, "测试", 参数, 空)
    如果 字典获取(结果, "错误码", "") != "TOOL_NOT_FOUND":
      如果 档 == "展示":
        展示错.追加(名)
      否则:
        退役错.追加(名)
  打印 "展示执行错=" + 转字符串(长度(展示错)) + ":" + 逗号连接(展示错)
  打印 "退役执行错=" + 转字符串(长度(退役错)) + ":" + 逗号连接(退役错)
  打印 "别名数=" + 转字符串(长度(注册["别名表"]))
主程()
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


def _rows(kv, prefix):
    out = {}
    for key, val in kv.items():
        if key.startswith(prefix):
            out[key[len(prefix):]] = val
    return out


def _doc_block():
    text = DOC.read_text(encoding='utf-8')
    block = text.split('<!-- T0503-中文名治理-开始 -->')[1]
    block = block.split('<!-- T0503-中文名治理-结束 -->')[0]
    block = block.split('```json')[1].split('```')[0]
    return json.loads(block)


def test_治理清单完整且三档计数一致(tmp_path):
    rc, out, kv = _run(MAP_DRIVER, tmp_path, 't0503_map.light')
    assert rc == 0, out
    assert kv['中文数'] == '151', ('基线中文名应为 151 个', kv.get('中文数'), out)
    assert kv['统计_双轨'] == '18', out
    assert kv['统计_展示'] == '44', out
    assert kv['统计_退役'] == '89', out
    assert kv['统计_合计'] == '151', out
    g = _rows(kv, 'G:')
    b = _rows(kv, 'B:')
    u = _rows(kv, 'U:')
    r = _rows(kv, 'R:')
    assert len(g) == 151, ('中文名清单不完整', len(g), out)
    assert len(set(g.values())) == 3, ('结论取值必须只有三档', set(g.values()), out)
    assert set(g.values()) == {'双轨', '展示', '退役'}, set(g.values())
    assert all(v != '' for v in b.values()), ('组不得为空', [k for k, v in b.items() if v == ''])
    assert all(v != '' for v in u.values()), ('展示名不得为空', [k for k, v in u.items() if v == ''])
    assert all(v != '' for v in r.values()), ('理由不得为空', [k for k, v in r.items() if v == ''])
    # 幸存名字（模型面无中文）——「中英不再无序混用」的直接判据
    assert kv['规范混中文'] == '0', ('语义名里混入了中文', _rows(kv, 'C:'), out)
    # 展示名口径：双轨/展示 → 中文名本身；退役 → 语义名（纯 ASCII）
    for name, verdict in g.items():
        label = u[name]
        if verdict == '退役':
            assert label != name, ('退役档不应保留中文展示名', name, label, out)
            assert not CJK_RE.search(label), ('退役档展示名必须 ASCII', name, label, out)
        else:
            assert label == name, ('展示档标签应保持中文名', name, label, out)
    # 固定选点：防止判定规则被悄悄放宽
    assert kv['展示专用_读文件'] == 'False', out
    assert kv['展示专用_待办添加'] == 'True', out
    assert kv['展示专用_凭据存入'] == 'False', out
    assert kv['展示名_语义'] == '读文件', out
    assert kv['展示名_英文'] == 'bash', out
    assert kv['展示名_退役'] == 'credential.store', out
    assert kv['展示名_双轨'] == '读文件', out
    # 模型面 / 白名单面不得有无法治理的中文名；表外中文名必须被点名
    for key in ('漏网_标准', '漏网_只读', '漏网_全旧名'):
        assert kv.get(key, '') == '', ('模型面出现无法治理的中文名', key, kv.get(key), out)
    assert kv['漏网_表外'] != '', ('表外中文名应被抓出来，不能静默放过', out)
    assert '交付登记' in kv['漏网_表外'], ('main 上晚于基线的 8 个中文名工具必须被点名', kv['漏网_表外'], out)
    # 展示/退役档不得被解析成别的键（不被解析即原样返回）
    assert kv['解析_展示档'] == '交付登记', out
    assert kv['解析_退役档'] == '凭据存入', out


def test_与命名规范文档逐条一致(tmp_path):
    """§10 机器可读块 ↔ 代码表：清单、分组、计数、理由必须一字不差（单一事实来源）。"""
    assert DOC.exists(), ('命名规范文档不在库，本卡结论无法回写', DOC)
    data = _doc_block()
    rc, out, kv = _run(MAP_DRIVER, tmp_path, 't0503_map_doc.light')
    assert rc == 0, out
    g = _rows(kv, 'G:')
    b = _rows(kv, 'B:')
    r = _rows(kv, 'R:')
    assert data['中文名总数'] == 151, data['中文名总数']
    assert data['结论计数'] == {'双轨': 18, '展示': 44, '退役': 89}, data['结论计数']
    # 双轨：名单逐条一致
    keep = set(data['双轨'])
    assert keep == {n for n, v in g.items() if v == '双轨'}, sorted(keep ^ {n for n, v in g.items() if v == '双轨'})
    # 展示 / 退役：分组与成员逐条一致
    for verdict, groups in (('展示', data['展示']), ('退役', data['退役'])):
        doc_names = {n for names in groups.values() for n in names}
        code_names = {n for n, v in g.items() if v == verdict}
        assert doc_names == code_names, (verdict, sorted(doc_names ^ code_names)[:5])
        for group, names in groups.items():
            for n in names:
                assert b[n] == group, ('文档分组与代码不一致', verdict, n, group, b[n])
    # 理由表：文档每个组都有书面理由，且与 中文名理由 逐字一致
    reasons = data['理由']
    assert set(reasons.keys()) == set(b.values()) | {'双轨'}, (
        '理由表应覆盖 双轨 + 全部组', sorted(set(reasons.keys()) ^ (set(b.values()) | {'双轨'})))
    for name in g:
        assert r[name] == reasons[b[name]], ('理由与文档不一致', name, b[name], r[name], reasons[b[name]])


def test_调用路径不被展示名污染(tmp_path):
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0503_exec.light')
    assert rc == 0, out
    assert kv['注册数'] == '160', out
    assert kv['中文注册数'] == '0', ('注册表键里混入中文名', out)
    names = [x for x in kv['注册名'].split(',') if x]
    assert len(names) == 160, out
    assert all(SEM_RE.match(n) for n in names), ('注册键必须是 <域>.<动作>', [n for n in names if not SEM_RE.match(n)][:5])
    assert not any(re.match(r'^tool_\d+$', n) for n in names), ('tool_NN 编号不得登记为工具名', out)
    assert kv['可调错'].startswith('0:'), ('展示/退役名进了调用路径或双轨名调不动', kv['可调错'], out)
    assert kv['展示撞键'].startswith('0:'), ('展示标签与注册键撞名', kv['展示撞键'], out)
    assert kv['别名数'] == '27', ('别名表应仍是 T-0501 §5.1 的 27 条', kv['别名数'], out)
    assert kv['双轨执行错'].startswith('0:'), ('双轨中文名执行未路由到原实现', kv['双轨执行错'], out)
    assert kv['展示执行错'].startswith('0:'), ('展示档中文名竟然可执行', kv['展示执行错'], out)
    assert kv['退役执行错'].startswith('0:'), ('退役档中文名竟然可执行', kv['退役执行错'], out)
