# -*- coding: utf-8 -*-
"""压缩E5.light 单元测试（工具结果修剪/省略提示/滑动窗口压缩/配置默认值）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_取工具上限_已知工具bash():
    r = run_light_source('''
从 压缩E5 导入 取工具上限
段落 主程序:
  设 v 为 取工具上限("bash")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=8000")


def test_取工具上限_读文件大上限():
    r = run_light_source('''
从 压缩E5 导入 取工具上限
段落 主程序:
  设 v 为 取工具上限("读文件")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=16000")


def test_取工具上限_未知工具用缺省():
    r = run_light_source('''
从 压缩E5 导入 取工具上限
段落 主程序:
  设 v 为 取工具上限("random_tool")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=8000")


def test_取工具上限_空名用缺省():
    r = run_light_source('''
从 压缩E5 导入 取工具上限
段落 主程序:
  设 v 为 取工具上限("")
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=8000")


def test_修剪工具结果_未超限原样返回():
    r = run_light_source('''
从 压缩E5 导入 修剪工具结果
段落 主程序:
  设 s 为 修剪工具结果("bash", "短文本")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=短文本")


def test_修剪工具结果_空结果返回空():
    r = run_light_source('''
从 压缩E5 导入 修剪工具结果
段落 主程序:
  设 s 为 修剪工具结果("bash", 空)
  打印("LEN=" + 转字符串(长(s)))
''')
    assert_success(r)
    out_contains(r, "LEN=0")


def test_修剪工具结果_超长插入截断提示():
    r = run_light_source('''
从 压缩E5 导入 修剪工具结果
从 字符串增强 导入 字符串重复文本
段落 主程序:
  设 长串 为 字符串重复文本("A", 10000)
  设 剪 为 修剪工具结果("bash", 长串)
  打印("TRIMMED_BEGIN")
  打印(剪)
  打印("TRIMMED_END")
''')
    assert_success(r)
    out_contains(r, "结果已截断")
    out_contains(r, "原长 10000 字符")


def test_生成省略提示_格式正确():
    r = run_light_source('''
从 压缩E5 导入 生成省略提示
段落 主程序:
  设 s 为 生成省略提示(5, 3)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=[已省略 5 条历史消息，保留最近 3 轮]")


def test_生成摘要_含消息总数():
    r = run_light_source('''
从 压缩E5 导入 生成摘要
段落 主程序:
  设 lst 为 [1, 2, 3]
  设 s 为 生成摘要(lst)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "共 3 条历史消息")


def test_滑动窗口压缩_未超阈值不压缩():
    r = run_light_source('''
从 压缩E5 导入 滑动窗口压缩
段落 主程序:
  设 消息表 为 [{"角色": "system", "内容": "sys"}, {"角色": "user", "内容": "hi"}]
  设 res 为 滑动窗口压缩(消息表, 99999999, 3)
  打印("压缩=" + 转字符串(res["压缩"]))
  打印("省略=" + 转字符串(res["省略数"]))
''')
    assert_success(r)
    out_contains(r, "压缩=假")
    out_contains(r, "省略=0")


def test_滑动窗口压缩_超阈值触发省略():
    r = run_light_source('''
从 压缩E5 导入 滑动窗口压缩
段落 主程序:
  设 消息表 为 [
    {"角色": "system", "内容": "sys"},
    {"角色": "user", "内容": "u1"},
    {"角色": "assistant", "内容": "a1"},
    {"角色": "user", "内容": "u2"},
    {"角色": "assistant", "内容": "a2"}
  ]
  设 res 为 滑动窗口压缩(消息表, 0, 1)
  打印("压缩=" + 转字符串(res["压缩"]))
  打印("省略=" + 转字符串(res["省略数"]))
''')
    assert_success(r)
    out_contains(r, "压缩=真")
    out_contains(r, "省略=2")


def test_滑动窗口压缩_保留系统消息():
    r = run_light_source('''
从 压缩E5 导入 滑动窗口压缩
段落 主程序:
  设 消息表 为 [
    {"角色": "system", "内容": "SYSPROMPT"},
    {"角色": "user", "内容": "u1"},
    {"角色": "assistant", "内容": "a1"},
    {"角色": "user", "内容": "u2"}
  ]
  设 res 为 滑动窗口压缩(消息表, 0, 1)
  设 新表 为 res["消息"]
  打印("N=" + 转字符串(长(新表)))
  打印("SYS=" + 新表[0]["内容"])
''')
    assert_success(r)
    out_contains(r, "SYS=SYSPROMPT")
