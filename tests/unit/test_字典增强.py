# -*- coding: utf-8 -*-
"""字典增强.light 单元测试。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_字典获取_存在键():
    r = run_light_source('''
从 字典增强 导入 字典获取
段落 主程序:
  设 d 为 {"x": 10, "y": 20}
  设 v 为 字典获取(d, "x")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=10")


def test_字典获取_缺失键返回默认值():
    r = run_light_source('''
从 字典增强 导入 字典获取
段落 主程序:
  设 d 为 {"x": 10}
  设 v 为 字典获取(d, "nope", -1)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=-1")


def test_深度设置_嵌套路径写入():
    r = run_light_source('''
从 字典增强 导入 深度设置, 深度获取
段落 主程序:
  设 d 为 {}
  深度设置(d, ["a", "b", "c"], 42)
  设 v 为 深度获取(d, ["a", "b", "c"])
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=42")


def test_深度设置_覆盖已有末键():
    r = run_light_source('''
从 字典增强 导入 深度设置, 深度获取
段落 主程序:
  设 d 为 {"a": {"b": 1}}
  深度设置(d, ["a", "b"], 99)
  设 v 为 深度获取(d, ["a", "b"])
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=99")


def test_深度获取_缺失层返回默认值():
    r = run_light_source('''
从 字典增强 导入 深度获取
段落 主程序:
  设 d 为 {"a": {"b": 1}}
  设 v 为 深度获取(d, ["a", "z", "w"], "DEF")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=DEF")


def test_键规范化_按键排序():
    r = run_light_source('''
从 字典增强 导入 序列化JSON排序
段落 主程序:
  设 j 为 序列化JSON排序({"z": 1, "a": 2, "m": 3})
  打印("JSON=" + j)
''')
    assert_success(r)
    # 键应按 a, m, z 顺序排列
    out = r.stdout
    ia = out.find('"a"')
    im = out.find('"m"')
    iz = out.find('"z"')
    assert -1 < ia < im < iz, f"键未按序排列: {out}"


def test_键规范化_嵌套递归排序():
    r = run_light_source('''
从 字典增强 导入 序列化JSON排序
段落 主程序:
  设 j 为 序列化JSON排序({"outer": {"z": 1, "a": 2}})
  打印("JSON=" + j)
''')
    assert_success(r)
    out = r.stdout
    ia = out.find('"a"')
    iz = out.find('"z"')
    assert -1 < ia < iz, f"嵌套键未按序: {out}"


def test_字典合并_覆盖策略():
    r = run_light_source('''
从 字典增强 导入 字典合并, 字典获取
段落 主程序:
  设 a 为 {"x": 1, "y": 2}
  设 b 为 {"y": 200, "z": 3}
  设 c 为 字典合并(a, b, 真)
  打印("Y=" + 转字符串(字典获取(c, "y")))
  打印("Z=" + 转字符串(字典获取(c, "z")))
''')
    assert_success(r)
    out_contains(r, "Y=200")
    out_contains(r, "Z=3")


def test_字典合并_不覆盖A优先():
    r = run_light_source('''
从 字典增强 导入 字典合并, 字典获取
段落 主程序:
  设 a 为 {"x": 1, "y": 2}
  设 b 为 {"y": 200, "z": 3}
  设 c 为 字典合并(a, b, 假)
  打印("Y=" + 转字符串(字典获取(c, "y")))
  打印("Z=" + 转字符串(字典获取(c, "z")))
''')
    assert_success(r)
    out_contains(r, "Y=2")
    out_contains(r, "Z=3")


def test_字典深拷贝_改原不影响副本():
    r = run_light_source('''
从 字典增强 导入 字典深拷贝, 字典获取, 深度设置, 深度获取
段落 主程序:
  设 a 为 {"n": {"v": 1}}
  设 c 为 字典深拷贝(a)
  深度设置(a, ["n", "v"], 999)
  设 副本v 为 深度获取(c, ["n", "v"])
  打印("COPY=" + 转字符串(副本v))
''')
    assert_success(r)
    out_contains(r, "COPY=1")


def test_造身份令牌_两次不同():
    r = run_light_source('''
从 字典增强 导入 造身份令牌
段落 主程序:
  设 t1 为 造身份令牌()
  设 t2 为 造身份令牌()
  打印("T1=" + t1)
  打印("T2=" + t2)
''')
    assert_success(r)
    out_contains(r, "T1=id_")
    out_contains(r, "T2=id_")
    # 两次调用令牌应不同（模块内计数器递增）
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("T")]
    assert len(lines) == 2, f"输出异常: {r.stdout}"
    assert lines[0] != lines[1], f"身份令牌重复: {lines}"


def test_属性获取_字典取值():
    r = run_light_source('''
从 字典增强 导入 属性获取
段落 主程序:
  设 d 为 {"k": "v"}
  设 v 为 属性获取(d, "k", "NA")
  打印("VAL=" + v)
''')
    assert_success(r)
    out_contains(r, "VAL=v")


def test_空字典_为空字典():
    r = run_light_source('''
从 字典增强 导入 空字典
段落 主程序:
  设 e 为 空字典()
  打印("LEN=" + 转字符串(长(e)))
''')
    assert_success(r)
    out_contains(r, "LEN=0")


def test_深度设置_空键路径报错():
    r = run_light_source('''
从 字典增强 导入 深度设置
段落 主程序:
  设 d 为 {}
  深度设置(d, [], 1)
  打印("SHOULD_NOT_PRINT")
''')
    assert_failure(r)


def test_深度设置_中间层非字典报错():
    r = run_light_source('''
从 字典增强 导入 深度设置
段落 主程序:
  设 d 为 {"a": 1}
  深度设置(d, ["a", "b"], 2)
  打印("SHOULD_NOT_PRINT")
''')
    assert_failure(r)
