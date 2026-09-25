# -*- coding: utf-8 -*-
"""字符串增强.light 单元测试。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_码转字符_数字码位():
    r = run_light_source('''
从 字符串增强 导入 码转字符
段落 主程序:
  设 c 为 码转字符(65)
  打印("CHAR=" + c)
''')
    assert_success(r)
    out_contains(r, "CHAR=A")


def test_字符转码_字母码位():
    r = run_light_source('''
从 字符串增强 导入 字符转码
段落 主程序:
  设 n 为 字符转码("Z")
  打印("CODE=" + 转字符串(n))
''')
    assert_success(r)
    out_contains(r, "CODE=90")


def test_码转字符_字符转码往返():
    r = run_light_source('''
从 字符串增强 导入 码转字符, 字符转码
段落 主程序:
  设 原码 为 233
  设 c 为 码转字符(原码)
  设 回程 为 字符转码(c)
  打印("ROUND=" + 转字符串(回程))
''')
    assert_success(r)
    out_contains(r, "ROUND=233")


def test_构造JSON字符串_字典序列化():
    r = run_light_source('''
从 字符串增强 导入 构造JSON字符串
段落 主程序:
  设 j 为 构造JSON字符串({"name": "x", "n": 1})
  打印("JSON=" + j)
''')
    assert_success(r)
    out_contains(r, '"name"')
    out_contains(r, '"x"')


def test_转义花括号_单花括号成对():
    r = run_light_source('''
从 字符串增强 导入 转义花括号, 码转字符
段落 主程序:
  设 左 为 码转字符(123)
  设 右 为 码转字符(125)
  设 原 为 "a" + 左 + "b" + 右 + "c"
  设 s 为 转义花括号(原)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=a{{b}}c")


def test_拼接量词_构造花括号量词():
    r = run_light_source('''
从 字符串增强 导入 拼接量词
段落 主程序:
  设 q 为 拼接量词("ab", 2, 4, "cd")
  打印("Q=" + q)
''')
    assert_success(r)
    out_contains(r, "Q=ab{2,4}cd")


def test_安全正则匹配_命中返回真():
    r = run_light_source('''
从 字符串增强 导入 安全正则匹配
段落 主程序:
  设 b 为 安全正则匹配("ab+", "xxabbbcd")
  打印("HIT=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "HIT=真")


def test_安全正则匹配_不命中返回假():
    r = run_light_source('''
从 字符串增强 导入 安全正则匹配
段落 主程序:
  设 b 为 安全正则匹配("zzz", "abcdef")
  打印("HIT=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "HIT=假")


def test_字符串重复文本_重复多次():
    r = run_light_source('''
从 字符串增强 导入 字符串重复文本
段落 主程序:
  设 s 为 字符串重复文本("ab", 3)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=ababab")


def test_填充左_补零到宽度():
    r = run_light_source('''
从 字符串增强 导入 填充左
段落 主程序:
  设 s 为 填充左("5", 3, "0")
  打印("OUT=[" + s + "]")
''')
    assert_success(r)
    out_contains(r, "OUT=[005]")


def test_填充右_补空格到宽度():
    r = run_light_source('''
从 字符串增强 导入 填充右
段落 主程序:
  设 s 为 填充右("ab", 5, "-")
  打印("OUT=[" + s + "]")
''')
    assert_success(r)
    out_contains(r, "OUT=[ab---]")


def test_截断文本_超长加省略号():
    r = run_light_source('''
从 字符串增强 导入 截断文本
段落 主程序:
  设 s 为 截断文本("abcdefgh", 5, "...")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=ab...")


def test_截断文本_未超长原样返回():
    r = run_light_source('''
从 字符串增强 导入 截断文本
段落 主程序:
  设 s 为 截断文本("abc", 10, "...")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=abc")


def test_分割保持分隔符_分号保留():
    r = run_light_source('''
从 字符串增强 导入 分割保持分隔符
段落 主程序:
  设 段 为 分割保持分隔符("a;b;c", ";")
  打印("LEN=" + 转字符串(长(段)))
  打印("P1=" + 段[0])
  打印("P2=" + 段[1])
''')
    assert_success(r)
    out_contains(r, "LEN=3")
    out_contains(r, "P1=a")
    out_contains(r, "P2=;b")
