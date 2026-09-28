# -*- coding: utf-8 -*-
"""作用域：作用域键/父链/上下文/载体准入/命名-匿名条目表/层组。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_建作用域键_判型():
    r = run_light_source('''
从 作用域 导入 建作用域键, 是作用域键
段落 主程序:
  设 k 为 建作用域键()
  设 a 为 "NO"
  如果 是作用域键(k): 设 a 为 "YES"
  设 b 为 "NO"
  如果 是作用域键({}): 设 b 为 "YES"
  打印("KEY=" + a)
  打印("DICT=" + b)
''')
    assert_success(r)
    out_contains(r, "KEY=YES")
    out_contains(r, "DICT=NO")


def test_作用域键ID_非键抛错():
    r = run_light_source('''
从 作用域 导入 作用域键ID
段落 主程序:
  设 v 为 作用域键ID({})
  打印(转字符串(v))
''')
    assert_failure(r)


def test_作用域相等_同键():
    r = run_light_source('''
从 作用域 导入 建作用域键, 作用域相等
段落 主程序:
  设 k 为 建作用域键()
  设 s 为 "NO"
  如果 作用域相等(k, k): 设 s 为 "YES"
  打印("EQ=" + s)
''')
    assert_success(r)
    out_contains(r, "EQ=YES")


def test_绑定父作用域_取父():
    r = run_light_source('''
从 作用域 导入 建作用域键, 绑定父作用域, 取父作用域, 作用域相等
段落 主程序:
  设 p 为 建作用域键()
  设 c 为 建作用域键()
  绑定父作用域(c, p)
  设 父 为 取父作用域(c)
  设 s 为 "NO"
  如果 作用域相等(父, p): 设 s 为 "YES"
  打印("PAR=" + s)
''')
    assert_success(r)
    out_contains(r, "PAR=YES")


def test_重复绑定抛错():
    r = run_light_source('''
从 作用域 导入 建作用域键, 绑定父作用域
段落 主程序:
  设 p 为 建作用域键()
  设 c 为 建作用域键()
  绑定父作用域(c, p)
  绑定父作用域(c, p)
''')
    assert_failure(r)


def test_写父作用域_成环抛错():
    r = run_light_source('''
从 作用域 导入 建作用域键, 写父作用域
段落 主程序:
  设 a 为 建作用域键()
  设 b 为 建作用域键()
  写父作用域(a, b)
  写父作用域(b, a)
''')
    assert_failure(r)


def test_取作用域链_长度():
    r = run_light_source('''
从 作用域 导入 建作用域键, 绑定父作用域, 取作用域链
段落 主程序:
  设 root 为 建作用域键()
  设 c 为 建作用域键()
  设 g 为 建作用域键()
  绑定父作用域(c, root)
  绑定父作用域(g, c)
  设 链 为 取作用域链(g)
  打印("N=" + 转字符串(列表长度(链)))
''')
    assert_success(r)
    out_contains(r, "N=3")


def test_上下文作用域_最近胜出():
    r = run_light_source('''
从 作用域 导入 建作用域键, 建上下文, 扩展作用域上下文, 取上下文作用域, 作用域相等
段落 主程序:
  设 ctx 为 建上下文()
  设 k 为 建作用域键()
  设 ectx 为 扩展作用域上下文(ctx, k)
  设 s 为 取上下文作用域(ectx)
  设 ok 为 "NO"
  如果 作用域相等(s, k): 设 ok 为 "YES"
  打印("SCOPE=" + ok)
''')
    assert_success(r)
    out_contains(r, "SCOPE=YES")


def test_建作用域_注销幂等():
    r = run_light_source('''
从 作用域 导入 建作用域键, 建上下文, 建作用域, 注销作用域
段落 主程序:
  设 host 为 建上下文()
  设 k 为 建作用域键()
  设 d 为 建作用域(host, k)
  注销作用域(d)
  设 ok 为 注销作用域(d)
  打印("DISP=" + 转字符串(ok))
''')
    assert_success(r)
    out_contains(r, "DISP=True")


def test_是作用域载体():
    r = run_light_source('''
从 作用域 导入 建作用域键, 建作用域目标, 是作用域载体
段落 主程序:
  设 k 为 建作用域键()
  设 v 为 建作用域目标(k)
  设 a 为 "NO"
  如果 是作用域载体(v): 设 a 为 "YES"
  设 b 为 "NO"
  如果 是作用域载体({}): 设 b 为 "YES"
  打印("CAR=" + a)
  打印("DICT=" + b)
''')
    assert_success(r)
    out_contains(r, "CAR=YES")
    out_contains(r, "DICT=NO")


def test_取载体作用域():
    r = run_light_source('''
从 作用域 导入 建作用域键, 建作用域目标, 取载体作用域, 作用域相等
段落 主程序:
  设 k 为 建作用域键()
  设 v 为 建作用域目标(k)
  设 got 为 取载体作用域(v)
  设 ok 为 "NO"
  如果 作用域相等(got, k): 设 ok 为 "YES"
  打印("KEY=" + ok)
''')
    assert_success(r)
    out_contains(r, "KEY=YES")


def test_命名条目表_插入与取():
    r = run_light_source('''
从 作用域 导入 命名条目表
段落 主程序:
  设 t 为 新建 命名条目表()
  t.插入("a", "val")
  打印("V=" + 转字符串(t.取("a")))
  打印("N=" + 转字符串(t.条目数()))
''')
    assert_success(r)
    out_contains(r, "V=val")
    out_contains(r, "N=1")


def test_命名条目表_重复名抛错():
    r = run_light_source('''
从 作用域 导入 命名条目表
段落 主程序:
  设 t 为 新建 命名条目表()
  t.插入("a", 1)
  t.插入("a", 2)
''')
    assert_failure(r)


def test_命名条目表_撤销():
    r = run_light_source('''
从 作用域 导入 命名条目表
段落 主程序:
  设 t 为 新建 命名条目表()
  设 h 为 t.插入("a", 1)
  t.撤销插入(h)
  设 n 为 转字符串(t.条目数())
  打印("N=" + n)
''')
    assert_success(r)
    out_contains(r, "N=0")


def test_匿名条目表_追加与撤销():
    r = run_light_source('''
从 作用域 导入 匿名条目表
段落 主程序:
  设 t 为 新建 匿名条目表()
  设 h 为 t.追加("x")
  打印("N1=" + 转字符串(t.条目数()))
  t.撤销追加(h)
  打印("N2=" + 转字符串(t.条目数()))
''')
    assert_success(r)
    out_contains(r, "N1=1")
    out_contains(r, "N2=0")


def test_层组_确保层合并命名():
    r = run_light_source('''
从 作用域 导入 建作用域键, 造作用域层组
段落 主程序:
  设 g 为 造作用域层组()
  设 k 为 建作用域键()
  设 layer 为 g.确保层(k)
  layer.命名.插入("n", "v")
  设 m 为 g.合并命名(k)
  打印("V=" + m["n"])
''')
    assert_success(r)
    out_contains(r, "V=v")
