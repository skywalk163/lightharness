# -*- coding: utf-8 -*-
"""T-0530：R107 预设页分组与预设清单口径一致性（T-0439 分组化之后的判据）。

背景：T-0439 把内置预设按 `类别` 拆成 3 组（Agent 模式 / 工作方法 / 自定义），
`examples/test_web路由.light` 的 R107 段仍拿组 0（agent 组，4 张卡）去比全量
预设（9 条），于是恒红。本单测把同一口径钉在 Python 侧；字面量 4/9 一律不写死，
预设表后续加模式时判据自动跟随。

被测：
  src/设置预设页.light  分组列表()
  src/预设组合.light    预设清单(类别="")

判据：
  1. 组数 == 3；组 0 类别 "agent"、组 1 类别 "method"；
  2. len(组0) == len(预设清单("agent"))、len(组1) == len(预设清单("method"))、
     三组之和 == len(预设清单())（防分组漏卡这种真缺陷被旧口径掩盖）；
  3. 挂载卡 id 两两唯一，且并集 == 预设清单() 全集（防重复挂载 / 幽灵卡）。
"""
import json

from test_support import run_light_source, assert_success, out_lines

_片段 = '''
从 设置预设页 导入 分组列表
从 预设组合 导入 预设清单
从 内置核心字典 导入 字典获取
从 JSON 导入 序列化JSON
段落 主程序:
  设 组集 为 分组列表(空)
  打印("组数=" + 转字符串(长度(组集)))
  打印("组0类别=" + 转字符串(字典获取(组集[0], "类别", "<无>")))
  打印("组1类别=" + 转字符串(字典获取(组集[1], "类别", "<无>")))
  打印("组0卡数=" + 转字符串(长度(组集[0]["预设"])))
  打印("组1卡数=" + 转字符串(长度(组集[1]["预设"])))
  打印("组2卡数=" + 转字符串(长度(组集[2]["预设"])))
  打印("agent预设数=" + 转字符串(长度(预设清单("agent"))))
  打印("method预设数=" + 转字符串(长度(预设清单("method"))))
  打印("全量预设数=" + 转字符串(长度(预设清单())))
  设 挂载id表 为 []
  遍历 组 之 组集:
    遍历 卡 之 组["预设"]:
      列表追加(挂载id表, 卡["id"])
  打印("挂载id=" + 序列化JSON(挂载id表))
  打印("全量id=" + 序列化JSON(预设清单()))
'''


def _报告():
    """跑一次 .light 片段，把 `键=值` 行解析成字典；同时返回原始结果便于报错。"""
    r = run_light_source(_片段, timeout=120)
    assert_success(r)
    kv = {}
    for ln in out_lines(r):
        if '=' in ln:
            k, v = ln.split('=', 1)
            kv[k] = v
    assert '组数' in kv, f'片段没有打印出 组数，输出：\n{r.output[-1200:]}'
    return kv, r


def test_组数与组类别():
    kv, r = _报告()
    assert int(kv['组数']) == 3, f'组数应为 3，实际 {kv["组数"]}'
    assert kv['组0类别'] == 'agent', f'组 0 类别应为 agent，实际 {kv["组0类别"]}'
    assert kv['组1类别'] == 'method', f'组 1 类别应为 method，实际 {kv["组1类别"]}'


def test_组卡数对齐类别清单():
    kv, r = _报告()
    # 组 0（agent）只承载 agent 类预设；组 1（method）只承载 method 类预设。
    assert int(kv['组0卡数']) == int(kv['agent预设数']), (
        f'组 0 卡数 {kv["组0卡数"]} != 预设清单("agent") {kv["agent预设数"]}'
    )
    assert int(kv['组1卡数']) == int(kv['method预设数']), (
        f'组 1 卡数 {kv["组1卡数"]} != 预设清单("method") {kv["method预设数"]}'
    )
    # 三组之和 == 全量：分组漏卡（有预设没挂到任何组）会在这里立红。
    合计 = int(kv['组0卡数']) + int(kv['组1卡数']) + int(kv['组2卡数'])
    assert 合计 == int(kv['全量预设数']), (
        f'各组合计 {合计} != 预设清单() 全量 {kv["全量预设数"]}'
        + '（分组漏卡？）'
    )


def test_卡id唯一且等于全量():
    kv, r = _报告()
    挂载 = json.loads(kv['挂载id'])
    全量 = json.loads(kv['全量id'])
    assert len(挂载) == len(set(挂载)), (
        f'挂载卡 id 有重复：{sorted({x for x in 挂载 if 挂载.count(x) > 1})}'
    )
    assert set(挂载) == set(全量), (
        f'挂载卡 id 集合与 预设清单() 不一致；'
        f'多挂={sorted(set(挂载) - set(全量))}，漏挂={sorted(set(全量) - set(挂载))}'
    )
