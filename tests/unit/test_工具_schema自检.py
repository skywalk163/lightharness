# -*- coding: utf-8 -*-
"""工具 schema 注册期形状自检（缺陷修复验收）。

缺陷
====
工具 schema 注册时不校验形状，错误要等到 执行 按 schema 造参时才炸在
stdlib 内部，报错位置离真因远。

修复
====
在 工具注册表.注册 入口加 schema 形状自检（src/工具.light）：
  工具级必填字段（name / description / parameters）
  + type 合法性 + required 合法性 + enum 合法性
  + properties·items·additionalProperties·oneOf 结构合法性（递归）。
注册期即抛清晰中文错，明确给出「哪个工具的哪个参数 schema 不合法」。

验收
====
  A) 故意注册坏 schema → 注册期即报 INVALID_TOOL_SCHEMA，含工具名与参数名。
  B) 正常 100 工具冒烟不受影响（注册成功、名单齐全）。
"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_坏schema_非法type_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  设 坏 为 造工具定义("bad_tool", "坏工具", ["type": "object", "properties": ["count": ["type": "str"]], "required": ["count"]], 空)
  reg.注册(坏)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")
    out_contains(r, "bad_tool")
    out_contains(r, "count")


def test_坏schema_enum非列表_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  设 坏 为 造工具定义("e_tool", "d", ["type": "object", "properties": ["m": ["type": "string", "enum": "x"]]], 空)
  reg.注册(坏)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")
    out_contains(r, "enum")
    out_contains(r, "m")


def test_坏schema_enum类型不符_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  设 坏 为 造工具定义("e2_tool", "d", ["type": "object", "properties": ["m": ["type": "string", "enum": [1, 2]]]], 空)
  reg.注册(坏)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")
    out_contains(r, "enum")


def test_坏schema_required未知属性_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  设 坏 为 造工具定义("r_tool", "d", ["type": "object", "properties": ["m": ["type": "string"]], "required": ["no_such"]], 空)
  reg.注册(坏)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")
    out_contains(r, "no_such")


def test_坏schema_items非schema_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  设 坏 为 造工具定义("i_tool", "d", ["type": "object", "properties": ["m": ["type": "array", "items": "bad"]]], 空)
  reg.注册(坏)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")
    out_contains(r, "items")


def test_坏schema_缺name_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表
段落 主程序:
  设 reg 为 新建 工具注册表()
  reg.注册(["description": "d", "parameters": ["type": "object"]])
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")


def test_坏schema_缺parameters_注册期报错():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  reg.注册(造工具定义("p_tool", "d", 空, 空))
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_SCHEMA")


def test_正常schema_注册成功():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  reg.注册(造工具定义("good", "好工具", ["type": "object", "properties": ["x": ["type": "string"]], "required": ["x"]], 空))
  打印("OK=" + 转字符串(长(reg.名单())))
''')
    assert_success(r)
    out_contains(r, "OK=1")


def test_正常100工具冒烟():
    r = run_light_source('''
从 工具 导入 工具注册表, 造工具定义
段落 主程序:
  设 reg 为 新建 工具注册表()
  设 i 为 0
  当 i < 100:
    设 nm 为 "t" + 转字符串(i)
    设 模式 为 ["type": "object", "properties": ["x": ["type": "string"]], "required": ["x"]]
    reg.注册(造工具定义(nm, "desc", 模式, 空))
    设 i 为 i + 1
  打印("COUNT=" + 转字符串(长(reg.名单())))
''')
    assert_success(r)
    out_contains(r, "COUNT=100")
