# -*- coding: utf-8 -*-
"""溢出保留：计价/截取/适配/头-尾保留与省略统计。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_计价_文本按字符数():
    r = run_light_source('''
从 溢出保留 导入 计价
段落 主程序:
  设 v 为 计价({"类型": "文本", "文本": "abcd"})
  打印("V=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "V=4")


def test_计价_图片固定1000():
    r = run_light_source('''
从 溢出保留 导入 计价
段落 主程序:
  设 v 为 计价({"类型": "图片", "描述": "x"})
  打印("V=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "V=1000")


def test_截取码点_头与尾():
    r = run_light_source('''
从 溢出保留 导入 截取码点
段落 主程序:
  设 a 为 截取码点("abcdef", 2, 假)
  设 b 为 截取码点("abcdef", 2, 真)
  打印("H=" + a)
  打印("T=" + b)
''')
    assert_success(r)
    out_contains(r, "H=ab")
    out_contains(r, "T=ef")


def test_适配文本_预算内前缀():
    r = run_light_source('''
从 溢出保留 导入 适配文本
段落 主程序:
  设 s 为 适配文本("abcdefgh", 3, 假)
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=abc")


def test_计图片数():
    r = run_light_source('''
从 溢出保留 导入 计图片数
段落 主程序:
  设 n 为 计图片数([{"类型": "图片"}, {"类型": "文本", "文本": "x"}, {"类型": "图片"}])
  打印("N=" + 转字符串(n))
''')
    assert_success(r)
    out_contains(r, "N=2")


def test_保留内容_小预算头尾截断():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 块 为 [{"类型": "文本", "文本": "ABCDEFGHIJ"}]
  设 收 为 保留内容(块, 4)
  打印("H=" + 收["头"][0]["文本"])
  打印("T=" + 收["尾"][0]["文本"])
  打印("B=" + 转字符串(收["省略字节"]))
''')
    assert_success(r)
    out_contains(r, "H=AB")
    out_contains(r, "T=IJ")
    out_contains(r, "B=6")


def test_保留内容_预算内全保留():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 块 为 [{"类型": "文本", "文本": "hi"}]
  设 收 为 保留内容(块, 100)
  设 n 为 转字符串(列表长度(收["头"]))
  设 b 为 转字符串(收["省略字节"])
  打印("N=" + n)
  打印("B=" + b)
''')
    assert_success(r)
    out_contains(r, "N=1")
    out_contains(r, "B=0")


def test_保留内容_图片放不下则跳过并计数():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 块 为 [{"类型": "图片", "描述": "pic"}, {"类型": "文本", "文本": "hello"}]
  设 收 为 保留内容(块, 500)
  打印("SI=" + 转字符串(收["省略图片"]))
''')
    assert_success(r)
    out_contains(r, "SI=1")


def test_保留内容_空内容():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 收 为 保留内容([], 100)
  设 h 为 转字符串(列表长度(收["头"]))
  设 t 为 转字符串(列表长度(收["尾"]))
  打印("H=" + h)
  打印("T=" + t)
''')
    assert_success(r)
    out_contains(r, "H=0")
    out_contains(r, "T=0")


def test_保留内容_预算零全省略():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 收 为 保留内容([{"类型": "文本", "文本": "abc"}], 0)
  打印("B=" + 转字符串(收["省略字节"]))
''')
    assert_success(r)
    out_contains(r, "B=3")


def test_保留内容_图片整块保留():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 收 为 保留内容([{"类型": "图片", "描述": "p"}], 2000)
  设 si 为 "YES"
  如果 收["省略图片"] == 0: 设 si 为 "NO"
  打印("SKIP=" + si)
''')
    assert_success(r)
    out_contains(r, "SKIP=NO")
