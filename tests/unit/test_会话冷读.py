# -*- coding: utf-8 -*-
"""会话冷读：拆分行 / 平衡日志 / 中断轮合成 / 错误传播（隔离临时目录）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_拆分行_按换行切分():
    r = run_light_source('''
从 会话冷读 导入 拆分行
段落 主程序:
  设 表 为 拆分行("a\\nb\\nc")
  打印("N=" + 转字符串(列表长度(表)))
  打印("F=" + 表[0])
''')
    assert_success(r)
    out_contains(r, "N=3")
    out_contains(r, "F=a")


def test_拆分行_空文本为空表():
    r = run_light_source('''
从 会话冷读 导入 拆分行
段落 主程序:
  设 表 为 拆分行("")
  打印("N=" + 转字符串(列表长度(表)))
''')
    assert_success(r)
    out_contains(r, "N=0")


def test_拆分行_保留空行占位():
    r = run_light_source('''
从 会话冷读 导入 拆分行
段落 主程序:
  设 表 为 拆分行("a\\n\\nb")
  打印("N=" + 转字符串(列表长度(表)))
''')
    assert_success(r)
    out_contains(r, "N=3")


def test_拆分行_末行无尾换行():
    r = run_light_source('''
从 会话冷读 导入 拆分行
段落 主程序:
  设 表 为 拆分行("x\\ny")
  打印("N=" + 转字符串(列表长度(表)))
  打印("LAST=" + 表[1])
''')
    assert_success(r)
    out_contains(r, "N=2")
    out_contains(r, "LAST=y")


def test_关闭句柄_恒返回真():
    r = run_light_source('''
从 会话冷读 导入 关闭句柄
段落 主程序:
  设 ok 为 关闭句柄({})
  打印("OK=" + 转字符串(ok))
''')
    assert_success(r)
    out_contains(r, "OK=真")


def test_冷读_平衡日志读回():
    r = run_light_source('''
从 持久化 导入 写出会话
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造文本块
从 会话冷读 导入 冷读会话日志, 冷读事件状态
段落 主程序:
  设 根 为 "cr"
  设 工作目录 为 "proj"
  设 s 为 新建会话("sb", 工作目录)
  s.记录事件("user/message", 造用户消息([造文本块("你好")]))
  s.记录轮次开始()
  s.记录轮次结束(["种类": "completed"], 空)
  写出会话(根, s)
  设 果 为 冷读会话日志(根, 工作目录, "sb")
  打印("STATE=" + 果["事件状态"])
  打印("HEAD=" + 果["头"]["标识"])
  打印("N=" + 转字符串(列表长度(果["事件表"])))
''')
    assert_success(r)
    out_contains(r, "STATE=detached")
    out_contains(r, "HEAD=sb")
    out_contains(r, "N=3")


def test_冷读_继承事件数缺省零():
    r = run_light_source('''
从 持久化 导入 写出会话
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造文本块
从 会话冷读 导入 冷读会话日志
段落 主程序:
  设 根 为 "crb"
  设 工作目录 为 "proj"
  设 s 为 新建会话("sc", 工作目录)
  s.记录事件("user/message", 造用户消息([造文本块("hi")]))
  写出会话(根, s)
  设 果 为 冷读会话日志(根, 工作目录, "sc")
  打印("INH=" + 转字符串(果["继承事件数"]))
''')
    assert_success(r)
    out_contains(r, "INH=0")


def test_冷读_未闭合轮合成关闭事件():
    r = run_light_source('''
从 持久化 导入 写出会话
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造文本块
从 会话冷读 导入 冷读会话日志
段落 主程序:
  设 根 为 "cro"
  设 工作目录 为 "proj"
  设 s 为 新建会话("so", 工作目录)
  s.记录事件("user/message", 造用户消息([造文本块("请执行")]))
  s.记录轮次开始()
  设 块 为 {}
  块["type"] 为 "tool-call"
  块["id"] 为 "call_xyz"
  块["name"] 为 "bash"
  设 内容 为 [块]
  设 助手 为 {}
  助手["role"] 为 "assistant"
  助手["content"] 为 内容
  s.记录事件("assistant/message", ["消息": 助手])
  s.记录事件("tool/call", {"callId": "call_xyz", "name": "bash"})
  写出会话(根, s)
  设 果 为 冷读会话日志(根, 工作目录, "so")
  打印("N=" + 转字符串(列表长度(果["事件表"])))
  打印("SYN=" + 果["事件表"][列表长度(果["事件表"])-1]["类型"])
''')
    assert_success(r)
    out_contains(r, "N=6")
    out_contains(r, "SYN=turn/end")


def test_冷读_会话不存在抛错():
    r = run_light_source('''
从 会话冷读 导入 冷读会话日志
段落 主程序:
  设 果 为 冷读会话日志("crx", "proj", "nope")
  打印(转字符串(果))
''')
    assert_failure(r)


def test_打开只读句柄_不存在抛错():
    r = run_light_source('''
从 会话冷读 导入 打开只读句柄
段落 主程序:
  设 h 为 打开只读句柄("cry", "proj", "nope")
  打印(转字符串(h))
''')
    assert_failure(r)


def test_冷读_首行非session抛错():
    r = run_light_source('''
从 持久化 导入 写出会话, 日志路径
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造文本块
从 文件系统 导入 写入文件
从 会话冷读 导入 冷读会话日志
段落 主程序:
  设 根 为 "crh"
  设 工作目录 为 "proj"
  设 s 为 新建会话("bh", 工作目录)
  s.记录事件("user/message", 造用户消息([造文本块("hi")]))
  写出会话(根, s)
  设 p 为 日志路径(根, 工作目录, "bh")
  写入文件(p, "{\\"type\\":\\"note\\",\\"id\\":\\"bh\\"}\\n")
  设 果 为 冷读会话日志(根, 工作目录, "bh")
  打印(转字符串(果))
''')
    assert_failure(r)
