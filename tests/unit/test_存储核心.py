# -*- coding: utf-8 -*-
"""存储核心：名称规则 / 后端注册表 / 单元文档编解码 / 记录单元与单文件单元。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_存储错误文本_格式():
    r = run_light_source('''
从 存储核心 导入 存储错误文本
段落 主程序:
  设 s 为 存储错误文本("closed", "unit x is closed")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "StorageError[closed] unit x is closed")


def test_断言单元名_合法通过():
    r = run_light_source('''
从 存储核心 导入 断言单元名
段落 主程序:
  设 n 为 断言单元名("my_unit1")
  打印("N=" + n)
''')
    assert_success(r)
    out_contains(r, "N=my_unit1")


def test_断言单元名_大写抛错():
    r = run_light_source('''
从 存储核心 导入 断言单元名
段落 主程序:
  设 n 为 断言单元名("BadName")
  打印(n)
''')
    assert_failure(r)


def test_断言记录键_合法通过():
    r = run_light_source('''
从 存储核心 导入 断言记录键
段落 主程序:
  设 k 为 断言记录键("u", "key-1_AZ")
  打印("K=" + k)
''')
    assert_success(r)
    out_contains(r, "K=key-1_AZ")


def test_断言记录键_斜杠抛错():
    r = run_light_source('''
从 存储核心 导入 断言记录键
段落 主程序:
  设 k 为 断言记录键("u", "a/b")
  打印(k)
''')
    assert_failure(r)


def test_注册表_注册取列名():
    r = run_light_source('''
从 存储核心 导入 造后端注册表, 注册后端, 取后端, 列出后端名
段落 主程序:
  设 reg 为 造后端注册表()
  注册后端(reg, "b1", {"x": 1})
  设 b 为 取后端(reg, "b1")
  设 names 为 列出后端名(reg)
  打印("GOT=" + 转字符串(b["x"]))
  打印("N=" + 转字符串(列表长度(names)))
''')
    assert_success(r)
    out_contains(r, "GOT=1")
    out_contains(r, "N=1")


def test_注册后端_重名抛错():
    r = run_light_source('''
从 存储核心 导入 造后端注册表, 注册后端
段落 主程序:
  设 reg 为 造后端注册表()
  注册后端(reg, "b1", {"x": 1})
  注册后端(reg, "b1", {"x": 2})
''')
    assert_failure(r)


def test_取后端_缺失抛错():
    r = run_light_source('''
从 存储核心 导入 造后端注册表, 取后端
段落 主程序:
  设 reg 为 造后端注册表()
  设 b 为 取后端(reg, "nope")
  打印(b)
''')
    assert_failure(r)


def test_移除后端_仅匹配对象才删():
    r = run_light_source('''
从 存储核心 导入 造后端注册表, 注册后端, 取后端, 移除后端, 列出后端名
段落 主程序:
  设 reg 为 造后端注册表()
  注册后端(reg, "b2", {"tag": "real"})
  设 B 为 取后端(reg, "b2")
  移除后端(reg, "b2", {"tag": "fake"})
  设 n1 为 转字符串(列表长度(列出后端名(reg)))
  移除后端(reg, "b2", B)
  设 n2 为 转字符串(列表长度(列出后端名(reg)))
  打印("BEFORE=" + n1)
  打印("AFTER=" + n2)
''')
    assert_success(r)
    out_contains(r, "BEFORE=1")
    out_contains(r, "AFTER=0")


def test_单元文档_序列化解析往返():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 序列化单元文档, 解析单元文档
段落 主程序:
  设 d 为 造单元描述符("app", 1, ["items"], 真, "single", [])
  设 st 为 {"版本": 1, "global": {"g": 1}, "表集合": {"items": {"k1": {"v": 42}}}}
  设 txt 为 序列化单元文档("app", st)
  设 back 为 解析单元文档(txt, d)
  打印("V=" + 转字符串(back["表集合"]["items"]["k1"]["v"]))
  打印("G=" + 转字符串(back["global"]["g"]))
''')
    assert_success(r)
    out_contains(r, "V=42")
    out_contains(r, "G=1")


def test_解析单元文档_坏JSON抛错():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 解析单元文档
段落 主程序:
  设 d 为 造单元描述符("app", 1, ["items"], 假, "single", [])
  设 s 为 解析单元文档("{bad", d)
  打印(s)
''')
    assert_failure(r)


def test_解析单元文档_版本不符抛错():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 序列化单元文档, 解析单元文档
段落 主程序:
  设 d 为 造单元描述符("app", 1, ["items"], 假, "single", [])
  设 st 为 {"版本": 9, "global": 空, "表集合": {}}
  设 txt 为 序列化单元文档("app", st)
  设 s 为 解析单元文档(txt, d)
  打印(s)
''')
    assert_failure(r)


def test_记录文档_往返与坏文档读空():
    r = run_light_source('''
从 存储核心 导入 序列化记录文档, 解析记录文档
段落 主程序:
  设 t 为 序列化记录文档(1, {"a": 1})
  设 v 为 解析记录文档(t, [1])
  打印("V=" + 转字符串(v["a"]))
  设 bad 为 解析记录文档("not json", [1])
  设 s 为 "NO"
  如果 bad == 空: 设 s 为 "YES"
  打印("BAD=" + s)
''')
    assert_success(r)
    out_contains(r, "V=1")
    out_contains(r, "BAD=YES")


def test_记录单元_写入删除载入():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 造单记录单元, 写入记录, 删除记录, 载入全部
段落 主程序:
  设 介质 为 {}
  设 d 为 造单元描述符("users", 1, ["profiles"], 真, "per-record", [])
  设 u 为 造单记录单元(介质, d, "根")
  写入记录(u, "profiles", "alice", {"age": 30})
  设 s1 为 载入全部(u)
  打印("V=" + 转字符串(s1["表集合"]["profiles"]["alice"]["age"]))
  删除记录(u, "profiles", "alice")
  设 s2 为 载入全部(u)
  设 n 为 转字符串(列表长度(字典键列表(s2["表集合"]["profiles"])))
  打印("N=" + n)
''')
    assert_success(r)
    out_contains(r, "V=30")
    out_contains(r, "N=0")


def test_记录单元_设置全局():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 造单记录单元, 设置全局, 载入全部
段落 主程序:
  设 介质 为 {}
  设 d 为 造单元描述符("users", 1, ["profiles"], 真, "per-record", [])
  设 u 为 造单记录单元(介质, d, "根")
  设置全局(u, {"g": 7})
  设 s 为 载入全部(u)
  打印("G=" + 转字符串(s["global"]["g"]))
''')
    assert_success(r)
    out_contains(r, "G=7")


def test_记录单元_关闭后写入抛错():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 造单记录单元, 写入记录, 关闭单元
段落 主程序:
  设 介质 为 {}
  设 d 为 造单元描述符("users", 1, ["profiles"], 真, "per-record", [])
  设 u 为 造单记录单元(介质, d, "根")
  关闭单元(u)
  写入记录(u, "profiles", "a", {"x": 1})
''')
    assert_failure(r)


def test_单文件单元_写入载入():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 造单文件单元, 单文件写入记录, 单文件载入全部
段落 主程序:
  设 介质 为 {}
  设 d 为 造单元描述符("app", 1, ["items"], 假, "single", [])
  设 u 为 造单文件单元(介质, d, "根")
  单文件写入记录(u, "items", "k1", {"v": 42})
  设 snap 为 单文件载入全部(u)
  打印("V=" + 转字符串(snap["表集合"]["items"]["k1"]["v"]))
''')
    assert_success(r)
    out_contains(r, "V=42")


def test_备份记录_重命名():
    r = run_light_source('''
从 存储核心 导入 造单元描述符, 造单记录单元, 写入记录, 备份记录
段落 主程序:
  设 介质 为 {}
  设 d 为 造单元描述符("users", 1, ["profiles"], 真, "per-record", [])
  设 u 为 造单记录单元(介质, d, "根")
  写入记录(u, "profiles", "a", {"x": 1})
  设 p 为 备份记录(u, "profiles", "a", "20260101")
  设 s 为 "NO"
  如果 p.查找(".bak.20260101") >= 0: 设 s 为 "YES"
  打印("BAK=" + s)
''')
    assert_success(r)
    out_contains(r, "BAK=YES")
