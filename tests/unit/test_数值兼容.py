# -*- coding: utf-8 -*-
"""数值兼容.light 单元测试。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_取整半数上_半点进位():
    r = run_light_source('''
从 数值兼容 导入 取整半数上
段落 主程序:
  设 v 为 取整半数上(2.5)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=3")


def test_取整半数上_小于半点舍去():
    r = run_light_source('''
从 数值兼容 导入 取整半数上
段落 主程序:
  设 v 为 取整半数上(2.4)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=2")


def test_安全除_正常商():
    r = run_light_source('''
从 数值兼容 导入 安全除
段落 主程序:
  设 v 为 安全除(10, 2)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=5")


def test_安全除_除零返回默认值():
    r = run_light_source('''
从 数值兼容 导入 安全除
段落 主程序:
  设 v 为 安全除(10, 0, -1)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=-1")


def test_JS真值_空为假():
    r = run_light_source('''
从 数值兼容 导入 JS真值
段落 主程序:
  设 b 为 JS真值(空)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_JS真值_零为假():
    r = run_light_source('''
从 数值兼容 导入 JS真值
段落 主程序:
  设 b 为 JS真值(0)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_JS真值_空串为假():
    r = run_light_source('''
从 数值兼容 导入 JS真值
段落 主程序:
  设 b 为 JS真值("")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_JS真值_零字符串为真():
    r = run_light_source('''
从 数值兼容 导入 JS真值
段落 主程序:
  设 b 为 JS真值("0")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_JS真值_列表为真():
    r = run_light_source('''
从 数值兼容 导入 JS真值
段落 主程序:
  设 b 为 JS真值([1, 2])
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_JS相等_同值同类型():
    r = run_light_source('''
从 数值兼容 导入 JS相等
段落 主程序:
  设 b 为 JS相等(1, 1)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_JS相等_跨类型严格不等():
    r = run_light_source('''
从 数值兼容 导入 JS相等
段落 主程序:
  设 b 为 JS相等(1, "1")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_指数解析_整数指数():
    r = run_light_source('''
从 数值兼容 导入 指数解析
段落 主程序:
  设 v 为 指数解析("1e3")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=1000")


def test_指数解析_小数系数():
    r = run_light_source('''
从 数值兼容 导入 指数解析
段落 主程序:
  设 v 为 指数解析("1.5e2")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=150")


def test_指数解析_无e返回空():
    r = run_light_source('''
从 数值兼容 导入 指数解析
段落 主程序:
  设 v 为 指数解析("123")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)


def test_科学计数法_负指数():
    r = run_light_source('''
从 数值兼容 导入 科学计数法
段落 主程序:
  设 v 为 科学计数法(2, -3)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0.002")


def test_钳位_低于下限抬到下限():
    r = run_light_source('''
从 数值兼容 导入 钳位
段落 主程序:
  设 v 为 钳位(1, 5, 10)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=5")


def test_钳位_高于上限压到上限():
    r = run_light_source('''
从 数值兼容 导入 钳位
段落 主程序:
  设 v 为 钳位(20, 5, 10)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=10")


def test_除零安全_正常返回商():
    r = run_light_source('''
从 数值兼容 导入 除零安全
段落 主程序:
  设 res 为 除零安全(10, 2)
  打印("OK=" + 转字符串(res["成功"]))
  打印("Q=" + 转字符串(res["商"]))
''')
    assert_success(r)
    out_contains(r, "OK=真")
    out_contains(r, "Q=5")


def test_除零安全_除零返回失败标记():
    r = run_light_source('''
从 数值兼容 导入 除零安全
段落 主程序:
  设 res 为 除零安全(10, 0)
  打印("OK=" + 转字符串(res["成功"]))
  打印("ERR=" + res["错误"])
''')
    assert_success(r)
    out_contains(r, "OK=假")
    out_contains(r, "ERR=除零")
