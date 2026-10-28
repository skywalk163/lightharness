# -*- coding: utf-8 -*-
"""R175（T-0175）B3 路：子代理活化单测。

上游：packages/subagent/subagent/src/activation.ts（dsh-v0.2.1-rc.3，186 行新增）的纯逻辑段。
被测模块：src/子代理活化.light。
"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)

_导入 = '从 子代理活化 导入 活化新池, 活化占用, 活化释放, 活化在飞, 活化本地的, 活化外部的, 活化取代理, 活化要求本地, 活化新锁, 活化排队, 活化收尾, 活化活跃子数'


def test_名额池_占用释放与令牌单调():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 池 为 活化新池(2)
  设 一 为 活化占用(池)
  设 二 为 活化占用(池)
  打印("在飞=" + 转字符串(活化在飞(池)))
  打印("一放=" + 转字符串(活化释放(池, 一)))
  打印("重复放=" + 转字符串(活化释放(池, 一)))
  打印("未知放=" + 转字符串(活化释放(池, 777)))
  设 三 为 活化占用(池)
  打印("三=" + 转字符串(三) + " 二=" + 转字符串(二))
  打印("再飞=" + 转字符串(活化在飞(池)))
''')
    assert_success(r)
    out_contains(r, "在飞=2")
    out_contains(r, "一放=True")
    out_contains(r, "重复放=False")
    out_contains(r, "未知放=False")
    out_contains(r, "三=3 二=2")
    out_contains(r, "再飞=2")


def test_名额池_超出容量即拒():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 池 为 活化新池(1)
  活化占用(池)
  活化占用(池)
''')
    assert_failure(r)
    out_contains(r, "subagent limit reached (active child limit: 1)")
    out_contains(r, "ACTIVATION_LIMIT_REACHED")


def test_本地活化可取代理_外部活化拒后续输入():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 本 为 活化本地的("子会话-1", {"名": "child"})
  打印("本=" + 转字符串(活化取代理(本)["名"]))
  打印("外=" + 转字符串(活化取代理(活化外部的("子会话-2", {"运行": 1}))))
  打印("要求本=" + 转字符串(活化要求本地(本)["标识"]))
''')
    assert_success(r)
    out_contains(r, "本=child")
    out_contains(r, "外=None")
    out_contains(r, "要求本=子会话-1")

    r2 = run_light_source(_导入 + '''
段落 主程序():
  活化要求本地(活化外部的("子会话-2", {"运行": 1}))
''')
    assert_failure(r2)
    out_contains(r2, "does not accept follow-up input")
    out_contains(r2, "NOT_CONTINUABLE")


def test_子代串行锁_尾替换与条件收尾():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 锁 为 活化新锁()
  设 一 为 活化排队(锁, "S1")
  设 二 为 活化排队(锁, "S1")
  设 三 为 活化排队(锁, "S2")
  打印("一前=" + 转字符串(一["前序号"]))
  打印("二前=" + 转字符串(二["前序号"]))
  打印("三前=" + 转字符串(三["前序号"]))
  打印("非尾收=" + 转字符串(活化收尾(锁, "S1", 一["序号"])))
  打印("尾收=" + 转字符串(活化收尾(锁, "S1", 二["序号"])))
  打印("活跃=" + 转字符串(活化活跃子数(锁)))
''')
    assert_success(r)
    out_contains(r, "一前=None")
    out_contains(r, "二前=1")
    out_contains(r, "三前=None")
    out_contains(r, "非尾收=False")
    out_contains(r, "尾收=True")
    out_contains(r, "活跃=1")


def test_活化池容量守卫():
    r = run_light_source(_导入 + '''
段落 主程序():
  活化新池(-1)
''')
    assert_failure(r)
    out_contains(r, "capacity must be a non-negative integer")