# -*- coding: utf-8 -*-
"""类型系统.light 单元测试（字符判定/定位子串/方法枚举/字段读取/远程错误）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_是词符_小写字母为真():
    r = run_light_source('''
从 类型系统 导入 是词符
段落 主程序:
  设 b 为 是词符("a")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是词符_数字为真():
    r = run_light_source('''
从 类型系统 导入 是词符
段落 主程序:
  设 b 为 是词符("5")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是词符_下划线为真():
    r = run_light_source('''
从 类型系统 导入 是词符
段落 主程序:
  设 b 为 是词符("_")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是词符_标点为假():
    r = run_light_source('''
从 类型系统 导入 是词符
段落 主程序:
  设 b 为 是词符("!")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_是空白符_空格为真():
    r = run_light_source('''
从 类型系统 导入 是空白符
段落 主程序:
  设 b 为 是空白符(" ")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是空白符_字母为假():
    r = run_light_source('''
从 类型系统 导入 是空白符
段落 主程序:
  设 b 为 是空白符("a")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_是段字符_点为真():
    r = run_light_source('''
从 类型系统 导入 是段字符
段落 主程序:
  设 b 为 是段字符(".")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是段字符_减号为真():
    r = run_light_source('''
从 类型系统 导入 是段字符
段落 主程序:
  设 b 为 是段字符("-")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_定位子串_找到返回下标():
    r = run_light_source('''
从 类型系统 导入 定位子串
段落 主程序:
  设 i 为 定位子串("abcdef", "cd")
  打印("VAL=" + 转字符串(i))
''')
    assert_success(r)
    out_contains(r, "VAL=2")


def test_定位子串_未找到返回负一():
    r = run_light_source('''
从 类型系统 导入 定位子串
段落 主程序:
  设 i 为 定位子串("abcdef", "xyz")
  打印("VAL=" + 转字符串(i))
''')
    assert_success(r)
    out_contains(r, "VAL=-1")


def test_是合法方法_已知为真():
    r = run_light_source('''
从 类型系统 导入 是合法方法
段落 主程序:
  设 b 为 是合法方法("analyze")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是合法方法_未知为假():
    r = run_light_source('''
从 类型系统 导入 是合法方法
段落 主程序:
  设 b 为 是合法方法("bogus")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_取字段_多键取首个存在():
    r = run_light_source('''
从 类型系统 导入 取字段
段落 主程序:
  设 v 为 取字段({"a": 1, "b": 2}, ["x", "b"], -1)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=2")


def test_取字段_都缺返回默认():
    r = run_light_source('''
从 类型系统 导入 取字段
段落 主程序:
  设 v 为 取字段({"a": 1}, ["x", "y"], -1)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=-1")


def test_有字段_存在为真():
    r = run_light_source('''
从 类型系统 导入 有字段
段落 主程序:
  设 b 为 有字段({"a": 1}, ["x", "a"])
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_有字段_都无为假():
    r = run_light_source('''
从 类型系统 导入 有字段
段落 主程序:
  设 b 为 有字段({"a": 1}, ["x", "y"])
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_造消息ID_req前缀():
    r = run_light_source('''
从 类型系统 导入 造消息ID
段落 主程序:
  设 s 为 造消息ID(7)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=req_7")


def test_造请求_非法方法报错():
    r = run_light_source('''
从 类型系统 导入 造请求
段落 主程序:
  设 m 为 造请求("req_1", "bogus", {})
  打印("SHOULD_NOT_PRINT")
''')
    assert_failure(r)


def test_是远程错误_合法标记为真():
    r = run_light_source('''
从 类型系统 导入 造远程错误, 是远程错误
段落 主程序:
  设 e 为 造远程错误("E1", "boom", {})
  设 b 为 是远程错误(e)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是远程错误_普通字典为假():
    r = run_light_source('''
从 类型系统 导入 是远程错误
段落 主程序:
  设 b 为 是远程错误({"code": "E1"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")
