# -*- coding: utf-8 -*-
"""会话格式.light 单元测试（安全整数/版本往返/事件编解码往返/文件名/块判定）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_安全整数_零通过():
    r = run_light_source('''
从 会话格式 导入 安全整数
段落 主程序:
  设 b 为 安全整数(0, "seq")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_安全整数_正整数通过():
    r = run_light_source('''
从 会话格式 导入 安全整数
段落 主程序:
  设 b 为 安全整数(42, "seq")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_安全整数_大数通过():
    r = run_light_source('''
从 会话格式 导入 安全整数
段落 主程序:
  设 b 为 安全整数(9007199254740991, "seq")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_安全整数_负数报错():
    r = run_light_source('''
从 会话格式 导入 安全整数
段落 主程序:
  设 b 为 安全整数(-1, "seq")
  打印("VAL=" + 转字符串(b))
''')
    assert_failure(r)


def test_安全整数_浮点报错():
    r = run_light_source('''
从 会话格式 导入 安全整数
段落 主程序:
  设 b 为 安全整数(1.5, "seq")
  打印("VAL=" + 转字符串(b))
''')
    assert_failure(r)


def test_判版本_版本文本往返():
    r = run_light_source('''
从 会话格式 导入 判版本, 版本文本
段落 主程序:
  设 v 为 判版本(3, 0)
  设 s 为 版本文本(v)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=3.0")


def test_同版本_相等为真():
    r = run_light_source('''
从 会话格式 导入 判版本, 同版本
段落 主程序:
  设 a 为 判版本(3, 0)
  设 b 为 判版本(3, 0)
  设 c 为 同版本(a, b)
  打印("VAL=" + 转字符串(c))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_版本小_次版本比较():
    r = run_light_source('''
从 会话格式 导入 判版本, 版本小
段落 主程序:
  设 a 为 判版本(3, 0)
  设 b 为 判版本(3, 1)
  设 c 为 版本小(a, b)
  打印("VAL=" + 转字符串(c))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_造事件_字段齐全():
    r = run_light_source('''
从 会话格式 导入 造事件
段落 主程序:
  设 e 为 造事件("user/message", 1, 1000, {"消息": "x"})
  打印("TYPE=" + e["类型"])
  打印("SEQ=" + 转字符串(e["序号"]))
''')
    assert_success(r)
    out_contains(r, "TYPE=user/message")
    out_contains(r, "SEQ=1")


def test_事件带来源_附加来源表():
    r = run_light_source('''
从 会话格式 导入 造事件, 事件带来源
段落 主程序:
  设 e 为 造事件("user/message", 1, 1000, {"消息": "x"})
  设 e2 为 事件带来源(e, [0, 1])
  打印("HAS=" + 转字符串(字典包含键(e2, "来源事件序号")))
''')
    assert_success(r)
    out_contains(r, "HAS=真")


def test_编码V2事件_解码V3事件往返():
    r = run_light_source('''
从 会话格式 导入 造事件, 编码V2事件, 解码V3事件
段落 主程序:
  设 e 为 造事件("user/message", 1, 1000, {"消息": {"content": []}})
  设 row 为 编码V2事件(e)
  设 d 为 解码V3事件(row, 0)
  打印("TYPE=" + d["类型"])
  打印("SEQ=" + 转字符串(d["序号"]))
''')
    assert_success(r)
    out_contains(r, "TYPE=user/message")
    out_contains(r, "SEQ=1")


def test_日志文件名_加后缀():
    r = run_light_source('''
从 会话格式 导入 日志文件名
段落 主程序:
  设 s 为 日志文件名("abc123")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=abc123.session.jsonl")


def test_是图像块_图像为真():
    r = run_light_source('''
从 会话格式 导入 是图像块
段落 主程序:
  设 b 为 是图像块({"type": "image"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是图像块_文本为假():
    r = run_light_source('''
从 会话格式 导入 是图像块
段落 主程序:
  设 b 为 是图像块({"type": "text"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_是工具结果块_工具结果为真():
    r = run_light_source('''
从 会话格式 导入 是工具结果块
段落 主程序:
  设 b 为 是工具结果块({"type": "tool-result"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_已知事件类型_已知为真():
    r = run_light_source('''
从 会话格式 导入 已知事件类型
段落 主程序:
  设 b 为 已知事件类型("user/message")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_已知事件类型_未知为假():
    r = run_light_source('''
从 会话格式 导入 已知事件类型
段落 主程序:
  设 b 为 已知事件类型("no/such/thing")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")
