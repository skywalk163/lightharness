# -*- coding: utf-8 -*-
"""消息.light 单元测试（块/消息构造/摘要限界/图片卸载判定/base64 长度）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_造文本块_类型与文本():
    r = run_light_source('''
从 消息 导入 造文本块
段落 主程序:
  设 b 为 造文本块("hello")
  打印("T=" + b["type"])
  打印("X=" + b["text"])
''')
    assert_success(r)
    out_contains(r, "T=text")
    out_contains(r, "X=hello")


def test_造推理块_类型推理():
    r = run_light_source('''
从 消息 导入 造推理块
段落 主程序:
  设 b 为 造推理块("think")
  打印("T=" + b["type"])
''')
    assert_success(r)
    out_contains(r, "T=reasoning")


def test_造工具调用块_字段齐全():
    r = run_light_source('''
从 消息 导入 造工具调用块
段落 主程序:
  设 b 为 造工具调用块("call-1", "read_file", "{}")
  打印("T=" + b["type"])
  打印("N=" + b["name"])
''')
    assert_success(r)
    out_contains(r, "T=tool-call")
    out_contains(r, "N=read_file")


def test_造工具结果块_错误标记():
    r = run_light_source('''
从 消息 导入 造工具结果块
段落 主程序:
  设 b 为 造工具结果块("call-1", [], 真)
  打印("T=" + b["type"])
  打印("ERR=" + 转字符串(b["isError"]))
''')
    assert_success(r)
    out_contains(r, "T=tool-result")
    out_contains(r, "ERR=真")


def test_造用户消息_role为user():
    r = run_light_source('''
从 消息 导入 造用户消息, 造文本块
段落 主程序:
  设 m 为 造用户消息([造文本块("hi")])
  打印("R=" + m["role"])
''')
    assert_success(r)
    out_contains(r, "R=user")


def test_造助手消息_role为assistant():
    r = run_light_source('''
从 消息 导入 造助手消息, 造文本块
段落 主程序:
  设 m 为 造助手消息([造文本块("hi")], "openai", "gpt-4")
  打印("R=" + m["role"])
''')
    assert_success(r)
    out_contains(r, "R=assistant")


def test_造系统消息_空文本空内容():
    r = run_light_source('''
从 消息 导入 造系统消息
段落 主程序:
  设 m 为 造系统消息("", "plugin1")
  打印("N=" + 转字符串(长(m["content"])))
''')
    assert_success(r)
    out_contains(r, "N=0")


def test_助手消息内容为空_空内容为真():
    r = run_light_source('''
从 消息 导入 助手消息内容为空
段落 主程序:
  设 b 为 助手消息内容为空({"content": []})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_取消息文本_拼接文本块():
    r = run_light_source('''
从 消息 导入 取消息文本, 造文本块
段落 主程序:
  设 m 为 {"content": [造文本块("AB"), 造文本块("CD")]}
  设 s 为 取消息文本(m)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=ABCD")


def test_摘要限界字符数_返回120():
    r = run_light_source('''
从 消息 导入 摘要限界字符数
段落 主程序:
  设 v 为 摘要限界字符数()
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=120")


def test_限摘要长度_未超限原样():
    r = run_light_source('''
从 消息 导入 限摘要长度
段落 主程序:
  设 s 为 限摘要长度("短摘要")
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=短摘要")


def test_限摘要长度_超长截断加省略():
    r = run_light_source('''
从 消息 导入 限摘要长度
从 字符串增强 导入 字符串重复文本
段落 主程序:
  设 长串 为 字符串重复文本("a", 150)
  设 s 为 限摘要长度(长串)
  打印("LEN=" + 转字符串(长(s)))
''')
    assert_success(r)
    out_contains(r, "LEN=120")


def test_内容含图片_有图片为真():
    r = run_light_source('''
从 消息 导入 内容含图片, 造图片块
段落 主程序:
  设 c 为 [造图片块("data", "image/png")]
  设 b 为 内容含图片(c)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_内容含图片_无图片为假():
    r = run_light_source('''
从 消息 导入 内容含图片, 造文本块
段落 主程序:
  设 c 为 [造文本块("x")]
  设 b 为 内容含图片(c)
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_块已卸载_已标记为真():
    r = run_light_source('''
从 消息 导入 块已卸载
段落 主程序:
  设 b 为 块已卸载({"type": "image", "offloaded": 真})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=真")


def test_块已卸载_未标记为假():
    r = run_light_source('''
从 消息 导入 块已卸载
段落 主程序:
  设 b 为 块已卸载({"type": "image"})
  打印("VAL=" + 转字符串(b))
''')
    assert_success(r)
    out_contains(r, "VAL=假")


def test_基64长度_三字节四字符():
    r = run_light_source('''
从 消息 导入 基64长度
段落 主程序:
  设 v 为 基64长度(3)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=4")


def test_卸载错误码_返回常量():
    r = run_light_source('''
从 消息 导入 卸载错误码
段落 主程序:
  设 s 为 卸载错误码()
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=IMAGE_OFFLOAD_REQUIRED")
