# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_造根上下文_形状():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  打印("标识=" + root["标识"])
  如果 root["父"] == 空:
    打印("父=空")
  否则:
    打印("父=非空")
  打印("销毁=" + 转字符串(root["已销毁"]))
''')
    assert_success(r)
    out_contains(r, "标识=root")
    out_contains(r, "父=空")
    out_contains(r, "销毁=假")


def test_造子上下文_标识递增():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 造子上下文
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设 c1 为 造子上下文(root, 空, 101)
  设 c2 为 造子上下文(root, 空, 102)
  打印("C1=" + c1["标识"])
  打印("C2=" + c2["标识"])
''')
    assert_success(r)
    out_contains(r, "C1=root-1")
    out_contains(r, "C2=root-2")


def test_设置与获取_当前层():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 设置属性, 获取属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "a", 1)
  打印("A=" + 转字符串(获取属性(root, "a")))
''')
    assert_success(r)
    out_contains(r, "A=1")


def test_获取属性_父链继承():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 造子上下文, 设置属性, 获取属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "a", 1)
  设 child 为 造子上下文(root, 空, 101)
  设置属性(child, "b", 2)
  打印("继承=" + 转字符串(获取属性(child, "a")))
  打印("自有=" + 转字符串(获取属性(child, "b")))
''')
    assert_success(r)
    out_contains(r, "继承=1")
    out_contains(r, "自有=2")


def test_自有属性_不泄露父层():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 造子上下文, 设置属性, 自有属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "a", 1)
  设 child 为 造子上下文(root, 空, 101)
  打印("子有a=" + 转字符串(自有属性(child, "a")))
  打印("根有a=" + 转字符串(自有属性(root, "a")))
''')
    assert_success(r)
    out_contains(r, "子有a=假")
    out_contains(r, "根有a=真")


def test_获取属性_未命中返回空():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 获取属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  如果 获取属性(root, "missing") == 空:
    打印("空=空")
  否则:
    打印("空=非空")
''')
    assert_success(r)
    out_contains(r, "空=空")


def test_删除属性_仅当前层():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 设置属性, 获取属性, 删除属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "a", 1)
  删除属性(root, "a")
  如果 获取属性(root, "a") == 空:
    打印("删后=空")
  否则:
    打印("删后=非空")
  删除属性(root, "不存在")
  打印("不崩=真")
''')
    assert_success(r)
    out_contains(r, "删后=空")
    out_contains(r, "不崩=真")


def test_列举属性_子父合并():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 造子上下文, 设置属性, 列举属性
从 JSON 导入 序列化JSON
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "rootkey", 1)
  设 child 为 造子上下文(root, 空, 101)
  设置属性(child, "childkey", 2)
  设 名单 为 列举属性(child)
  打印("名单=" + 序列化JSON(名单))
''')
    assert_success(r)
    out_contains(r, "childkey")
    out_contains(r, "rootkey")


def test_快照与恢复():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 设置属性, 获取属性, 上下文快照, 恢复上下文, 删除属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "x", 1)
  设 s 为 上下文快照(root)
  删除属性(root, "x")
  打印("删后=" + 转字符串(获取属性(root, "x")))
  恢复上下文(root, s)
  打印("恢复=" + 转字符串(获取属性(root, "x")))
''')
    assert_success(r)
    out_contains(r, "删后=空")
    out_contains(r, "恢复=1")


def test_销毁上下文_标记与读取():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 销毁上下文, 是已销毁, 设置属性, 获取属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设置属性(root, "a", 1)
  销毁上下文(root, 999)
  打印("已销毁=" + 转字符串(是已销毁(root)))
  打印("读后=" + 转字符串(获取属性(root, "a")))
''')
    assert_success(r)
    out_contains(r, "已销毁=真")
    out_contains(r, "读后=1")


def test_销毁后_设置抛错():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 销毁上下文, 设置属性
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  销毁上下文(root, 999)
  设置属性(root, "a", 1)
  打印("不应到达")
''')
    assert_failure(r)


def test_销毁后_造子抛错():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 销毁上下文, 造子上下文
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  销毁上下文(root, 999)
  设 c 为 造子上下文(root, 空, 1000)
  打印("不应到达")
''')
    assert_failure(r)


def test_作用域匹配_global通配():
    r = run_light_source('''
从 宿主上下文 导入 造作用域, 作用域匹配
段落 主程序:
  设 global 为 造作用域("global", "*", 空)
  设 ev 为 造作用域("session", "s1", 空)
  打印("匹配=" + 转字符串(作用域匹配(ev, global)))
''')
    assert_success(r)
    out_contains(r, "匹配=真")


def test_作用域匹配_同类型同目标():
    r = run_light_source('''
从 宿主上下文 导入 造作用域, 作用域匹配
段落 主程序:
  设 parent 为 造作用域("session", "s1", 空)
  设 ev 为 造作用域("session", "s1", parent)
  设 other 为 造作用域("session", "s2", 空)
  打印("同=" + 转字符串(作用域匹配(ev, parent)))
  打印("异=" + 转字符串(作用域匹配(ev, other)))
''')
    assert_success(r)
    out_contains(r, "同=真")
    out_contains(r, "异=假")


def test_作用域匹配_祖先链():
    r = run_light_source('''
从 宿主上下文 导入 造作用域, 作用域匹配
段落 主程序:
  设 root 为 造作用域("session", "s1", 空)
  设 child 为 造作用域("turn", "t1", root)
  打印("祖先=" + 转字符串(作用域匹配(child, root)))
''')
    assert_success(r)
    out_contains(r, "祖先=真")


def test_作用域链():
    r = run_light_source('''
从 宿主上下文 导入 造作用域, 作用域链
从 JSON 导入 序列化JSON
段落 主程序:
  设 root 为 造作用域("session", "s1", 空)
  设 child 为 造作用域("turn", "t1", root)
  设 链 为 作用域链(child)
  打印("链=" + 序列化JSON(链))
''')
    assert_success(r)
    out_contains(r, 'turn:t1')
    out_contains(r, 'session:s1')


def test_传递上下文():
    r = run_light_source('''
从 宿主上下文 导入 造根上下文, 传递上下文
段落 看标识(ctx):
  返回 ctx["标识"]
段落 主程序:
  设 root 为 造根上下文(空, "root", 100)
  设 出 为 传递上下文(看标识, root)
  打印("出=" + 出)
''')
    assert_success(r)
    out_contains(r, "出=root")
