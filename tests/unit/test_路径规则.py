# -*- coding: utf-8 -*-
"""路径规则.light 单元测试（纯逻辑：盘符判定/归一/父目录/观测策略状态机/编辑替换）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_判定盘符头_字母冒号为真():
    r = run_light_source('''
从 路径规则 导入 判定盘符头
段落 主程序:
  设 b 为 判定盘符头("C:")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_判定盘符头_长度不符为假():
    r = run_light_source('''
从 路径规则 导入 判定盘符头
段落 主程序:
  设 b 为 判定盘符头("C:/")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_判定盘符根_盘符斜杠为真():
    r = run_light_source('''
从 路径规则 导入 判定盘符根
段落 主程序:
  设 b 为 判定盘符根("C:/")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_判定盘符根_无斜杠为假():
    r = run_light_source('''
从 路径规则 导入 判定盘符根
段落 主程序:
  设 b 为 判定盘符根("C:rel")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_归一平台路径_win32斜杠转反斜杠():
    r = run_light_source('''
从 路径规则 导入 归一平台路径
段落 主程序:
  设 s 为 归一平台路径("a/b/c", "win32")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=a\\b\\c")


def test_归一平台路径_posix反斜杠转正斜杠():
    r = run_light_source('''
从 路径规则 导入 归一平台路径
从 字符串增强 导入 码转字符
段落 主程序:
  设 bs 为 码转字符(92)
  设 原 为 "a" + bs + "b"
  设 s 为 归一平台路径(原, "posix")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=a/b")


def test_上层路径_posix取父目录():
    r = run_light_source('''
从 路径规则 导入 上层路径
段落 主程序:
  设 s 为 上层路径("/a/b/c", "posix")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=/a/b")


def test_造观测策略_默认缺席():
    r = run_light_source('''
从 路径规则 导入 造观测策略
段落 主程序:
  设 p 为 造观测策略()
  打印("ST=" + p["状态"])
''')
    assert_success(r)
    out_contains(r, "ST=缺席")


def test_记录观测_置在场带内容():
    r = run_light_source('''
从 路径规则 导入 造观测策略, 记录观测
段落 主程序:
  设 p 为 造观测策略()
  设 p2 为 记录观测(p, "快照内容")
  打印("ST=" + p2["状态"])
  打印("SNAP=" + p2["已观测"])
''')
    assert_success(r)
    out_contains(r, "ST=在场")
    out_contains(r, "SNAP=快照内容")


def test_判定读许可_未观测拒绝():
    r = run_light_source('''
从 路径规则 导入 造观测策略, 判定读许可
段落 主程序:
  设 p 为 造观测策略()
  设 b 为 判定读许可(p)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_判定读许可_已观测放行():
    r = run_light_source('''
从 路径规则 导入 造观测策略, 记录观测, 判定读许可
段落 主程序:
  设 p 为 造观测策略()
  设 p2 为 记录观测(p, "x")
  设 b 为 判定读许可(p2)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_判定写许可_缺失即建须缺席():
    r = run_light_source('''
从 路径规则 导入 造观测策略, 判定写许可
段落 主程序:
  设 p 为 造观测策略()
  设 b 为 判定写许可(p, "缺失即建", 假)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_判定写许可_按版本替换须在场():
    r = run_light_source('''
从 路径规则 导入 造观测策略, 记录观测, 判定写许可
段落 主程序:
  设 p 为 记录观测(造观测策略(), "x")
  设 b 为 判定写许可(p, "按版本替换", 假)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_判定写许可_写意图空拒绝():
    r = run_light_source('''
从 路径规则 导入 造观测策略, 判定写许可
段落 主程序:
  设 p 为 造观测策略()
  设 b 为 判定写许可(p, 空, 假)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_补换行_无尾换行补一个():
    r = run_light_source('''
从 路径规则 导入 补换行
段落 主程序:
  设 s 为 补换行("abc")
  打印("LEN=" + 转字符串(长(s)))
''')
    assert_success(r)
    out_contains(r, "LEN=4")


def test_施加编辑_区间替换():
    r = run_light_source('''
从 路径规则 导入 施加编辑
段落 主程序:
  设 s 为 施加编辑("hello", 1, 3, "X")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=hXlo")


def test_判定唯一性_恰好一次为真():
    r = run_light_source('''
从 路径规则 导入 判定唯一性
段落 主程序:
  设 b 为 判定唯一性("abc", "b")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_判定唯一性_多次出现为假():
    r = run_light_source('''
从 路径规则 导入 判定唯一性
段落 主程序:
  设 b 为 判定唯一性("aaa", "a")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_替换文本_唯一替换成功():
    r = run_light_source('''
从 路径规则 导入 替换文本
段落 主程序:
  设 s 为 替换文本("abc", "b", "X")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=aXc")


def test_替换文本_未找到报错():
    r = run_light_source('''
从 路径规则 导入 替换文本
段落 主程序:
  设 s 为 替换文本("abc", "z", "X")
  打印("OUT=" + s)
''')
    assert_failure(r)
