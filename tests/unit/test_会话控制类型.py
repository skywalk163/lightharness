# -*- coding: utf-8 -*-
"""会话控制类型.light 单元测试（状态/队列动作/会话地址/模型选择/流帧/远程事件）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_是否会话状态_已知为真():
    r = run_light_source('''
从 会话控制类型 导入 是否会话状态
段落 主程序:
  设 b 为 是否会话状态("running")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是否会话状态_未知为假():
    r = run_light_source('''
从 会话控制类型 导入 是否会话状态
段落 主程序:
  设 b 为 是否会话状态("bogus")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_状态运行中_running为真():
    r = run_light_source('''
从 会话控制类型 导入 状态运行中
段落 主程序:
  设 b 为 状态运行中("running")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_状态运行中_idle为假():
    r = run_light_source('''
从 会话控制类型 导入 状态运行中
段落 主程序:
  设 b 为 状态运行中("idle")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_造会话状态值_running带标记():
    r = run_light_source('''
从 会话控制类型 导入 造会话状态值
段落 主程序:
  设 v 为 造会话状态值("running")
  打印("ST=" + v["status"])
  打印("RUN=" + 转字符串(v["running"]))
''')
    assert_success(r)
    out_contains(r, "ST=running")
    out_contains(r, "RUN=真")


def test_造会话状态值_idle不运行():
    r = run_light_source('''
从 会话控制类型 导入 造会话状态值
段落 主程序:
  设 v 为 造会话状态值("idle")
  打印("RUN=" + 转字符串(v["running"]))
''')
    assert_success(r)
    out_contains(r, "RUN=假")


def test_造会话状态值_未知状态报错():
    r = run_light_source('''
从 会话控制类型 导入 造会话状态值
段落 主程序:
  设 v 为 造会话状态值("bogus")
  打印("SHOULD_NOT_PRINT")
''')
    assert_failure(r)


def test_会话错误种类_已知返回键表():
    r = run_light_source('''
从 会话控制类型 导入 会话错误种类
段落 主程序:
  设 k 为 会话错误种类("session/model-unavailable")
  打印("N=" + 转字符串(长(k)))
''')
    assert_success(r)
    out_contains(r, "N=2")


def test_会话错误种类_未知返回空():
    r = run_light_source('''
从 会话控制类型 导入 会话错误种类
段落 主程序:
  设 k 为 会话错误种类("nope/thing")
  设 b 为 k == 空
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是否提示内容部件_text部件合法():
    r = run_light_source('''
从 会话控制类型 导入 是否提示内容部件
段落 主程序:
  设 b 为 是否提示内容部件({"type": "text", "text": "hi"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是否提示内容部件_缺text非法():
    r = run_light_source('''
从 会话控制类型 导入 是否提示内容部件
段落 主程序:
  设 b 为 是否提示内容部件({"type": "text"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_是否队列动作_remove为真():
    r = run_light_source('''
从 会话控制类型 导入 是否队列动作
段落 主程序:
  设 b 为 是否队列动作({"kind": "remove"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是否队列动作_edit空内容为假():
    r = run_light_source('''
从 会话控制类型 导入 是否队列动作
段落 主程序:
  设 b 为 是否队列动作({"kind": "edit", "content": []})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_是否会话地址_session合法():
    r = run_light_source('''
从 会话控制类型 导入 是否会话地址
段落 主程序:
  设 b 为 是否会话地址({"kind": "session", "sessionId": "abc"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_造模型选择_字段齐全():
    r = run_light_source('''
从 会话控制类型 导入 造模型选择
段落 主程序:
  设 s 为 造模型选择("openai", "gpt-4", "low")
  打印("P=" + s["provider"])
  打印("M=" + s["model"])
''')
    assert_success(r)
    out_contains(r, "P=openai")
    out_contains(r, "M=gpt-4")


def test_模型投影回退_next空回退上次():
    r = run_light_source('''
从 会话控制类型 导入 模型投影回退
段落 主程序:
  设 p 为 模型投影回退("old-model", 空)
  打印("NEXT=" + p["next"])
''')
    assert_success(r)
    out_contains(r, "NEXT=old-model")


def test_模型投影回退_next有值用next():
    r = run_light_source('''
从 会话控制类型 导入 模型投影回退
段落 主程序:
  设 p 为 模型投影回退("old-model", "new-model")
  打印("NEXT=" + p["next"])
''')
    assert_success(r)
    out_contains(r, "NEXT=new-model")


def test_是远程事件种类_已知为真():
    r = run_light_source('''
从 会话控制类型 导入 是远程事件种类
段落 主程序:
  设 b 为 是远程事件种类("api-session/status")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_是远程事件种类_未知为假():
    r = run_light_source('''
从 会话控制类型 导入 是远程事件种类
段落 主程序:
  设 b 为 是远程事件种类("session/local")
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")
