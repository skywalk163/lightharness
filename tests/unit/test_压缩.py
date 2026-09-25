# -*- coding: utf-8 -*-
"""压缩.light 单元测试（纯函数：取消息文本/估算token/图像索引收集/绳标记卸载）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)


def test_取消息文本_拼接文本块():
    r = run_light_source('''
从 压缩 导入 取消息文本
段落 主程序:
  设 msg 为 {"content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]}
  设 s 为 取消息文本(msg)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=helloworld")


def test_取消息文本_跳过非文本块():
    r = run_light_source('''
从 压缩 导入 取消息文本
段落 主程序:
  设 msg 为 {"content": [{"type": "text", "text": "AB"}, {"type": "image"}, {"type": "text", "text": "CD"}]}
  设 s 为 取消息文本(msg)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=ABCD")


def test_取消息文本_含推理块():
    r = run_light_source('''
从 压缩 导入 取消息文本
段落 主程序:
  设 msg 为 {"content": [{"type": "reasoning", "text": "think"}, {"type": "text", "text": "done"}]}
  设 s 为 取消息文本(msg)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "OUT=thinkdone")


def test_估算token_按字符数三分之一():
    r = run_light_source('''
从 压缩 导入 估算token
段落 主程序:
  设 msgs 为 [{"content": [{"type": "text", "text": "abcdef"}]}]
  设 t 为 估算token(msgs)
  打印("TOK=" + 转字符串(t))
''')
    assert_success(r)
    out_contains(r, "TOK=2")


def test_估算token_多消息累加():
    r = run_light_source('''
从 压缩 导入 估算token
段落 主程序:
  设 msgs 为 [
    {"content": [{"type": "text", "text": "aaaaaa"}]},
    {"content": [{"type": "text", "text": "bbbbbbbbbbbb"}]}
  ]
  设 t 为 估算token(msgs)
  打印("TOK=" + 转字符串(t))
''')
    assert_success(r)
    out_contains(r, "TOK=6")


def test_估算token_无content跳过():
    r = run_light_source('''
从 压缩 导入 估算token
段落 主程序:
  设 msgs 为 [{"role": "sys"}]
  设 t 为 估算token(msgs)
  打印("TOK=" + 转字符串(t))
''')
    assert_success(r)
    out_contains(r, "TOK=0")


def test_收集块图像索引_跳过已卸载():
    r = run_light_source('''
从 压缩 导入 收集块图像索引
段落 主程序:
  设 块表 为 [{"type": "text", "text": "x"}, {"type": "image"}, {"type": "image", "offloaded": 真}]
  设 状态 为 {"索引表": [], "计数": 0, "剩余": 2}
  收集块图像索引(块表, 状态)
  打印("IDX=" + 转字符串(状态["索引表"]))
''')
    assert_success(r)
    out_contains(r, "IDX=[0]")


def test_收集块图像索引_剩余耗尽停止():
    r = run_light_source('''
从 压缩 导入 收集块图像索引
段落 主程序:
  设 块表 为 [{"type": "image"}, {"type": "image"}, {"type": "image"}]
  设 状态 为 {"索引表": [], "计数": 0, "剩余": 1}
  收集块图像索引(块表, 状态)
  打印("IDX=" + 转字符串(状态["索引表"]))
''')
    assert_success(r)
    out_contains(r, "IDX=[0]")


def test_绳标记图像卸载_标记指定下标():
    r = run_light_source('''
从 压缩 导入 绳标记图像卸载
段落 主程序:
  设 msg 为 {"content": [{"type": "text", "text": "x"}, {"type": "image", "data": "a"}]}
  设 新 为 绳标记图像卸载(msg, [0])
  打印("OFF=" + 转字符串(新["content"][1]["offloaded"]))
''')
    assert_success(r)
    out_contains(r, "OFF=真")


def test_绳标记图像卸载_不改动原消息():
    r = run_light_source('''
从 压缩 导入 绳标记图像卸载
段落 主程序:
  设 msg 为 {"content": [{"type": "image", "data": "a"}]}
  设 新 为 绳标记图像卸载(msg, [0])
  打印("ORIG=" + 转字符串(字典包含键(msg["content"][0], "offloaded")))
''')
    assert_success(r)
    out_contains(r, "ORIG=假")


def test_绳标记图像卸载_下标不存在报错():
    r = run_light_source('''
从 压缩 导入 绳标记图像卸载
段落 主程序:
  设 msg 为 {"content": [{"type": "image", "data": "a"}]}
  设 新 为 绳标记图像卸载(msg, [5])
  打印("SHOULD_NOT_PRINT")
''')
    assert_failure(r)


def test_绳标记图像卸载_已卸载报错():
    r = run_light_source('''
从 压缩 导入 绳标记图像卸载
段落 主程序:
  设 msg 为 {"content": [{"type": "image", "offloaded": 真}]}
  设 新 为 绳标记图像卸载(msg, [0])
  打印("SHOULD_NOT_PRINT")
''')
    assert_failure(r)
