# -*- coding: utf-8 -*-
"""令牌估算.light 单元测试（启发式 token 计价纯函数）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_估算内容_空列表为零():
    r = run_light_source('''
从 令牌估算 导入 估算内容
段落 主程序:
  设 v 为 估算内容([])
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0")


def test_估算内容_文本块计价():
    r = run_light_source('''
从 令牌估算 导入 估算内容
段落 主程序:
  设 块 为 [{"type": "text", "text": "abcd"}]
  设 v 为 估算内容(块)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    # ceil(4/4)=1 + 块开销4 = 5
    out_contains(r, "VAL=5")


def test_估算内容_非整除向上取整():
    r = run_light_source('''
从 令牌估算 导入 估算内容
段落 主程序:
  设 块 为 [{"type": "text", "text": "abcde"}]
  设 v 为 估算内容(块)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    # ceil(5/4)=2 + 块开销4 = 6
    out_contains(r, "VAL=6")


def test_估算内容_推理块同文本计价():
    r = run_light_source('''
从 令牌估算 导入 估算内容
段落 主程序:
  设 块 为 [{"type": "reasoning", "text": "abcd"}]
  设 v 为 估算内容(块)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=5")


def test_估算内容_toolCall计价():
    r = run_light_source('''
从 令牌估算 导入 估算内容
段落 主程序:
  设 块 为 [{"type": "tool-call", "name": "ab", "arguments": "cd"}]
  设 v 为 估算内容(块)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    # ceil(2/4)=1 + ceil(2/4)=1 + 块开销4 = 6
    out_contains(r, "VAL=6")


def test_估算内容_toolResult递归计价():
    r = run_light_source('''
从 令牌估算 导入 估算内容
段落 主程序:
  设 块 为 [{"type": "tool-result", "content": [{"type": "text", "text": "abcd"}]}]
  设 v 为 估算内容(块)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    # 内层文本5 + 块开销4 = 9
    out_contains(r, "VAL=9")


def test_估算消息_加角色框架开销():
    r = run_light_source('''
从 令牌估算 导入 估算消息
段落 主程序:
  设 msg 为 {"content": [{"type": "text", "text": "abcd"}]}
  设 v 为 估算消息(msg)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    # 内容5 + 角色开销4 = 9
    out_contains(r, "VAL=9")


def test_估算系统令牌_空头部为零():
    r = run_light_source('''
从 令牌估算 导入 估算系统令牌
段落 主程序:
  设 v 为 估算系统令牌(空)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0")


def test_估算系统令牌_缺system键为零():
    r = run_light_source('''
从 令牌估算 导入 估算系统令牌
段落 主程序:
  设 v 为 估算系统令牌({"other": 1})
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0")


def test_估算系统令牌_有system文本():
    r = run_light_source('''
从 令牌估算 导入 估算系统令牌
段落 主程序:
  设 v 为 估算系统令牌({"system": "abcd"})
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    # ceil(4/4)=1 + 角色开销4 = 5
    out_contains(r, "VAL=5")


def test_估算工具令牌_空头部为零():
    r = run_light_source('''
从 令牌估算 导入 估算工具令牌
段落 主程序:
  设 v 为 估算工具令牌(空)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0")


def test_估算工具令牌_空工具表为零():
    r = run_light_source('''
从 令牌估算 导入 估算工具令牌
段落 主程序:
  设 v 为 估算工具令牌({"tools": []})
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0")


def test_拼接文本_合并text块():
    r = run_light_source('''
从 令牌估算 导入 拼接文本
段落 主程序:
  设 块 为 [{"type": "text", "text": "ab"}, {"type": "reasoning", "text": "XX"}, {"type": "text", "text": "cd"}]
  设 s 为 拼接文本(块)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=abcd")


def test_列表求和_累加数值():
    r = run_light_source('''
从 令牌估算 导入 列表求和
段落 主程序:
  设 v 为 列表求和([1, 2, 3, 4])
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=10")


def test_估算系统消息_空内容为零():
    r = run_light_source('''
从 令牌估算 导入 估算系统消息
段落 主程序:
  设 msg 为 {"content": []}
  设 v 为 估算系统消息(msg)
  打印("VAL=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "VAL=0")


def test_估算上下文分解_拆分三类():
    r = run_light_source('''
从 令牌估算 导入 估算上下文分解
段落 主程序:
  设 头部 为 {"system": "abcd"}
  设 消息表 为 [
    {"role": "system", "content": [{"type": "text", "text": "abcd"}]},
    {"role": "user", "content": [{"type": "text", "text": "abcd"}]}
  ]
  设 res 为 估算上下文分解(头部, 消息表)
  打印("SYS=" + 转字符串(res["systemTokens"]))
  打印("MSG=" + 转字符串(res["messageTokens"]))
''')
    assert_success(r)
    out_contains(r, "SYS=5")
    out_contains(r, "MSG=9")
