# -*- coding: utf-8 -*-
"""R175（T-0175）B3 路：子代理预设选择单测。

上游：packages/subagent/tool-subagent/src/preset-selection.ts（dsh-v0.2.1-rc.3，98 行新增）。
被测模块：src/子代理预设选择.light。
判据口径：正向看 stdout 关键值；拒收路径断言 rc!=0 且输出含上游逐字文案。
"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)

_导入 = '从 子代理预设选择 导入 预选新建, 预选已配置, 预选可选表, 预选描述, 预选解析, 预选断言提供方, 预选校验服务'


def test_白名单_默认值与可选表():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "assist", "白名单": ["assist", "isolated"]})
  打印("已配置=" + 转字符串(预选已配置(s)))
  打印("可选=" + 连接字符串(预选可选表(s), ","))
''')
    assert_success(r)
    out_contains(r, "已配置=True")
    out_contains(r, "可选=assist,isolated")


def test_描述_回落与可用清单():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "assist", "白名单": ["assist"]})
  打印("A=" + 预选描述(s))
  打印("B=" + 预选描述(s, ["assist: 只读", "other: 别选"]))
  设 t 为 预选新建({"默认": 空, "白名单": ["isolated"]})
  打印("C=" + 预选描述(t))
''')
    assert_success(r)
    out_contains(r, "A=Agent preset for this child. Omit to use assist.")
    out_contains(r, "B=Agent preset for this child. Omit to use assist. Available presets: assist: 只读; other: 别选")
    out_contains(r, "C=Agent preset for this child. Omit to inherit the parent agent's current preset.")


def test_解析_缺省兜底与白名单命中():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "assist", "白名单": ["assist", "isolated"]})
  打印("缺省=" + 转字符串(预选解析(s, {})))
  打印("命中=" + 转字符串(预选解析(s, {"agent_preset": "isolated"})))
''')
    assert_success(r)
    out_contains(r, "缺省=assist")
    out_contains(r, "命中=isolated")


def test_构造拒绝重复白名单():
    r = run_light_source(_导入 + '''
段落 主程序():
  预选新建({"默认": 空, "白名单": ["a", "a"]})
''')
    assert_failure(r)
    out_contains(r, "allowedAgentPresets contains duplicate preset ids")


def test_构造拒绝默认值不在白名单():
    r = run_light_source(_导入 + '''
段落 主程序():
  预选新建({"默认": "x", "白名单": ["a", "b"]})
''')
    assert_failure(r)
    out_contains(r, "agentPreset must be included in allowedAgentPresets")


def test_构造拒绝非字符串白名单():
    r = run_light_source(_导入 + '''
段落 主程序():
  预选新建({"默认": 空, "白名单": [1, 2]})
''')
    assert_failure(r)
    out_contains(r, "allowedAgentPresets must be an array of strings")


def test_解析拒绝未开白名单():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": 空, "白名单": 空})
  预选解析(s, {"agent_preset": "x"})
''')
    assert_failure(r)
    out_contains(r, "agent_preset selection is disabled for this tool instance")


def test_解析拒绝不在白名单():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": 空, "白名单": ["a", "b"]})
  预选解析(s, {"agent_preset": "c"})
''')
    assert_failure(r)
    out_contains(r, "agent_preset must be one of: a, b")


def test_提供方断言_不支持独立预设即拒():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "a", "白名单": 空})
  预选断言提供方(s, {"名字": "不支持的", "支持预设": 假, "继承父上下文": 假})
''')
    assert_failure(r)
    out_contains(r, "does not support independent agent preset selection")


def test_提供方断言_继承父上下文即拒():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "a", "白名单": 空})
  预选断言提供方(s, {"名字": "继承的", "支持预设": 真, "继承父上下文": 真})
''')
    assert_failure(r)
    out_contains(r, "does not support independent agent preset selection")


def test_校验服务_未配置放行_已配置缺服务即拒():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 t 为 预选新建({"默认": 空, "白名单": 空})
  打印("未配置=" + 转字符串(长度(预选校验服务(t, 假, {}))))
  设 s 为 预选新建({"默认": "a", "白名单": 空})
  预选校验服务(s, 假, {})
''')
    assert_failure(r)
    out_contains(r, "未配置=0")
    out_contains(r, "requires the agent-presets service")


def test_校验服务_只收白名单内带描述_缺文档即拒():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "a", "白名单": ["a", "b"]})
  打印("描述=" + 连接字符串(预选校验服务(s, 真, {"a": {"description": "甲"}, "b": {"description": 空}}), "|"))
''')
    assert_success(r)
    out_contains(r, "描述=a: 甲")

    r2 = run_light_source(_导入 + '''
段落 主程序():
  设 s 为 预选新建({"默认": "a", "白名单": ["a", "b"]})
  预选校验服务(s, 真, {"a": {"description": "甲"}})
''')
    assert_failure(r2)
    out_contains(r2, 'is not registered')