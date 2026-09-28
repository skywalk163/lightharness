# -*- coding: utf-8 -*-
"""存储域：配置校验 / 记录解析 / 域设施打开-校验-关闭。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_校验贮配_合法返回规范化():
    r = run_light_source('''
从 存储域 导入 校验贮配
段落 主程序:
  设 c 为 校验贮配({"backend": "local", "routes": {"d1": "be2"}})
  打印("B=" + c["backend"])
  打印("R=" + c["routes"]["d1"])
''')
    assert_success(r)
    out_contains(r, "B=local")
    out_contains(r, "R=be2")


def test_校验贮配_缺省路由为空表():
    r = run_light_source('''
从 存储域 导入 校验贮配
段落 主程序:
  设 c 为 校验贮配({"backend": "local"})
  设 n 为 转字符串(列表长度(字典键列表(c["routes"])))
  打印("N=" + n)
''')
    assert_success(r)
    out_contains(r, "N=0")


def test_校验贮配_空配置抛错():
    r = run_light_source('''
从 存储域 导入 校验贮配
段落 主程序:
  设 c 为 校验贮配(空)
  打印(c)
''')
    assert_failure(r)


def test_校验贮配_缺backend抛错():
    r = run_light_source('''
从 存储域 导入 校验贮配
段落 主程序:
  设 c 为 校验贮配({"routes": {}})
  打印(c)
''')
    assert_failure(r)


def test_校验贮配_非字符串backend抛错():
    r = run_light_source('''
从 存储域 导入 校验贮配
段落 主程序:
  设 c 为 校验贮配({"backend": 123})
  打印(c)
''')
    assert_failure(r)


def test_校验贮配_路由值非字符串抛错():
    r = run_light_source('''
从 存储域 导入 校验贮配
段落 主程序:
  设 c 为 校验贮配({"backend": "b", "routes": {"d1": 5}})
  打印(c)
''')
    assert_failure(r)


def test_解析记录_成功返回值():
    r = run_light_source('''
从 存储域 导入 解析记录, 恒等
段落 主程序:
  设 v 为 解析记录("dom", "t", "k", 恒等, "rawval")
  打印("V=" + v)
''')
    assert_success(r)
    out_contains(r, "V=rawval")


def test_解析记录_解析失败转invalidrecord():
    r = run_light_source('''
从 存储域 导入 解析记录, 解析整数
段落 主程序:
  设 v 为 解析记录("dom", "t", "k", 解析整数, "abc")
  打印(v)
''')
    assert_failure(r)


def test_解析整数_合法():
    r = run_light_source('''
从 存储域 导入 解析整数
段落 主程序:
  设 v 为 解析整数("42")
  打印("V=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "V=42")


def test_域设施_打开并读回记录():
    r = run_light_source('''
从 存储域 导入 域设施, 解析整数
段落 快照看:
  返回 {"tables": {"t1": {"k1": "5"}}}
段落 主程序:
  设 f 为 新建 域设施("be", {})
  设 规格 为 {"name": "d1", "tables": {"t1": {"值解析": 解析整数}}}
  设 能力 为 {"kv": 真, "读取全部": 快照看}
  设 d 为 f.打开域(规格, 能力)
  打印("V=" + 转字符串(d["tables"]["t1"]["k1"]))
''')
    assert_success(r)
    out_contains(r, "V=5")


def test_域设施_重复打开抛错():
    r = run_light_source('''
从 存储域 导入 域设施, 解析整数
段落 快照看:
  返回 {"tables": {}}
段落 主程序:
  设 f 为 新建 域设施("be", {})
  设 规格 为 {"name": "d1", "tables": {}}
  设 能力 为 {"kv": 真, "读取全部": 快照看}
  f.打开域(规格, 能力)
  f.打开域(规格, 能力)
''')
    assert_failure(r)


def test_域设施_无kv切面抛错():
    r = run_light_source('''
从 存储域 导入 域设施, 解析整数
段落 快照看:
  返回 {"tables": {}}
段落 主程序:
  设 f 为 新建 域设施("be", {})
  设 规格 为 {"name": "d1", "tables": {}}
  设 能力 为 {"读取全部": 快照看}
  设 d 为 f.打开域(规格, 能力)
  打印(转字符串(d))
''')
    assert_failure(r)


def test_域设施_收域后可重开():
    r = run_light_source('''
从 存储域 导入 域设施, 解析整数
段落 快照看:
  返回 {"tables": {}}
段落 主程序:
  设 f 为 新建 域设施("be", {})
  设 规格 为 {"name": "d1", "tables": {}}
  设 能力 为 {"kv": 真, "读取全部": 快照看}
  f.打开域(规格, 能力)
  f.收域("d1")
  设 d 为 f.打开域(规格, 能力)
  设 got 为 f.读域("d1")
  设 s 为 "NO"
  如果 got != 空: 设 s 为 "YES"
  打印("OPEN=" + s)
''')
    assert_success(r)
    out_contains(r, "OPEN=YES")


def test_构造设施_合法配置():
    r = run_light_source('''
从 存储域 导入 构造设施
段落 主程序:
  设 f 为 构造设施({"backend": "local"})
  设 s 为 "NO"
  如果 f.后端名 == "local": 设 s 为 "YES"
  打印("B=" + s)
''')
    assert_success(r)
    out_contains(r, "B=YES")
