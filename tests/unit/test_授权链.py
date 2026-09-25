# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_构造授权错误_格式():
    r = run_light_source('''
从 授权链 导入 构造授权错误
段落 主程序:
  设 e 为 构造授权错误("没有流程", "NO_FLOW")
  打印("E=" + e)
''')
    assert_success(r)
    out_contains(r, "E=[NO_FLOW] 没有流程")


def test_解析授权错误_往返():
    r = run_light_source('''
从 授权链 导入 构造授权错误, 解析授权错误
段落 主程序:
  设 e 为 构造授权错误("方法不对", "UNKNOWN_METHOD")
  设 p 为 解析授权错误(e)
  打印("码=" + p["码"])
  打印("消息=" + p["消息"])
''')
    assert_success(r)
    out_contains(r, "码=UNKNOWN_METHOD")
    out_contains(r, "消息=方法不对")


def test_解析授权错误_短文本():
    r = run_light_source('''
从 授权链 导入 解析授权错误
段落 主程序:
  设 p 为 解析授权错误("ab")
  打印("码=" + p["码"])
''')
    assert_success(r)
    out_contains(r, "码=未知")


def test_解析授权错误_无方括号():
    r = run_light_source('''
从 授权链 导入 解析授权错误
段落 主程序:
  设 p 为 解析授权错误("NO_FLOW 没有方括号")
  打印("码=" + p["码"])
  打印("消息=" + p["消息"])
''')
    assert_success(r)
    out_contains(r, "码=未知")
    out_contains(r, "消息=NO_FLOW 没有方括号")


def test_解析授权错误_无闭合括号():
    r = run_light_source('''
从 授权链 导入 解析授权错误
段落 主程序:
  设 p 为 解析授权错误("[NO_FLOW 没有闭括号")
  打印("码=" + p["码"])
''')
    assert_success(r)
    out_contains(r, "码=未知")


def test_构造方法_形状():
    r = run_light_source('''
从 授权链 导入 构造方法
段落 主程序:
  设 m 为 构造方法("m1", "口令登录")
  打印("ID=" + m["id"])
  打印("标签=" + m["标签"])
''')
    assert_success(r)
    out_contains(r, "ID=m1")
    out_contains(r, "标签=口令登录")


def test_构造通知_仅消息():
    r = run_light_source('''
从 授权链 导入 构造通知
段落 主程序:
  设 n 为 构造通知("请查收邮件", 空, 空)
  打印("消息=" + n["消息"])
  设 有url 为 字典包含键(n, "url")
  设 有码 为 字典包含键(n, "码")
  打印("URL=" + 转字符串(有url))
  打印("码=" + 转字符串(有码))
''')
    assert_success(r)
    out_contains(r, "消息=请查收邮件")
    out_contains(r, "URL=假")
    out_contains(r, "码=假")


def test_构造通知_带url带码():
    r = run_light_source('''
从 授权链 导入 构造通知
段落 主程序:
  设 n 为 构造通知("点链接", "https://x", "OTP")
  打印("URL=" + n["url"])
  打印("码=" + n["码"])
''')
    assert_success(r)
    out_contains(r, "URL=https://x")
    out_contains(r, "码=OTP")


def test_构造选项_带描述与无描述():
    r = run_light_source('''
从 授权链 导入 构造选项
段落 主程序:
  设 o1 为 构造选项("a", "苹果", "红的")
  设 o2 为 构造选项("b", "香蕉", 空)
  打印("D1=" + o1["描述"])
  设 有2 为 字典包含键(o2, "描述")
  打印("D2=" + 转字符串(有2))
''')
    assert_success(r)
    out_contains(r, "D1=红的")
    out_contains(r, "D2=假")


def test_构造提问文本_占位():
    r = run_light_source('''
从 授权链 导入 构造提问文本
段落 主程序:
  设 q 为 构造提问文本("输入口令", "例如 123456")
  设 q2 为 构造提问文本("再来一个", 空)
  打印("种类=" + q["种类"])
  打印("占位=" + q["占位"])
  设 有2 为 字典包含键(q2, "占位")
  打印("无占位=" + 转字符串(有2))
''')
    assert_success(r)
    out_contains(r, "种类=text")
    out_contains(r, "占位=例如 123456")
    out_contains(r, "无占位=假")


def test_构造提问机密与选择():
    r = run_light_source('''
从 授权链 导入 构造提问机密, 构造提问选择, 构造选项
段落 主程序:
  设 s 为 构造提问机密("输入密码", "******")
  设 opt1 为 构造选项("x", "X", 空)
  设 sel 为 构造提问选择("选一个", [opt1])
  打印("种类=" + s["种类"])
  打印("S占位=" + s["占位"])
  打印("SEL=" + sel["种类"])
''')
    assert_success(r)
    out_contains(r, "种类=secret")
    out_contains(r, "S占位=******")
    out_contains(r, "SEL=select")


def test_构造授权服务_初始空表():
    r = run_light_source('''
从 授权链 导入 构造授权服务
段落 主程序:
  设 s 为 构造授权服务()
  打印("流程数=" + 转字符串(长度(s["流程表"])))
  打印("监听器数=" + 转字符串(长度(s["监听器表"])))
  打印("日志数=" + 转字符串(长度(s["日志"])))
''')
    assert_success(r)
    out_contains(r, "流程数=0")
    out_contains(r, "监听器数=0")
    out_contains(r, "日志数=0")


def test_注册流程_后列出与描述():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 注册流程, 列出流程, 描述流程, 构造方法
段落 主程序:
  设 s 为 构造授权服务()
  设 流程 为 ["键":"k1", "标签":"流程一", "方法表":[构造方法("m1","方法")]]
  注册流程(s, 流程)
  设 列表 为 列出流程(s)
  打印("数量=" + 转字符串(长度(列表)))
  打印("首键=" + 列表[0]["键"])
  设 d 为 描述流程(s, "k1")
  打印("描述标签=" + d["标签"])
  设 空d 为 描述流程(s, "不存在")
  如果 空d == 空:
    打印("不存在=空")
  否则:
    打印("不存在=非空")
''')
    assert_success(r)
    out_contains(r, "数量=1")
    out_contains(r, "首键=k1")
    out_contains(r, "描述标签=流程一")
    out_contains(r, "不存在=空")


def test_注册流程_重复键报错():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 注册流程
段落 主程序:
  设 s 为 构造授权服务()
  设 f1 为 ["键":"k1", "标签":"a", "方法表":[]]
  设 f2 为 ["键":"k1", "标签":"b", "方法表":[]]
  注册流程(s, f1)
  注册流程(s, f2)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "DUPLICATE_FLOW")


def test_开始授权_无流程报错():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 开始授权
段落 主程序:
  设 s 为 构造授权服务()
  设 req 为 ["键":"nope"]
  设 x 为 开始授权(s, req)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "NO_FLOW")


def test_开始授权_未知方法报错():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 注册流程, 开始授权, 构造方法
段落 主程序:
  设 s 为 构造授权服务()
  设 流程 为 ["键":"k1", "标签":"t", "方法表":[构造方法("m1","方法")]]
  注册流程(s, 流程)
  设 req 为 ["键":"k1", "方法":"不存在的方法"]
  设 x 为 开始授权(s, req)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "UNKNOWN_METHOD")


_HELPERS = '''
段落 成功运行(会话):
  会话["提交"]("flowok")
段落 空通知(n):
  设 z 为 0
段落 空提问(q):
  返回 "ok"
'''


def test_开始授权_已中止直接cancelled():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 注册流程, 开始授权, 构造方法
''' + _HELPERS + '''
段落 主程序:
  设 s 为 构造授权服务()
  设 流程 为 ["键":"flowok", "标签":"t", "方法表":[构造方法("m1","m")]]
  注册流程(s, 流程)
  设 交互 为 ["通知":空通知, "提问":空提问]
  设 req 为 ["键":"flowok", "已中止":真, "交互":交互]
  设 结果 为 开始授权(s, req)
  打印("状态=" + 结果["状态"])
''')
    assert_success(r)
    out_contains(r, "状态=cancelled")


def test_开始授权_成功authorized():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 注册流程, 开始授权, 构造方法
''' + _HELPERS + '''
段落 主程序:
  设 s 为 构造授权服务()
  设 流程 为 ["键":"flowok", "标签":"t", "方法表":[构造方法("m1","m")], "运行":成功运行]
  注册流程(s, 流程)
  设 交互 为 ["通知":空通知, "提问":空提问]
  设 req 为 ["键":"flowok", "交互":交互]
  设 结果 为 开始授权(s, req)
  打印("状态=" + 结果["状态"])
''')
    assert_success(r)
    out_contains(r, "状态=authorized")


def test_开始授权_默认方法回退():
    r = run_light_source('''
从 授权链 导入 构造授权服务, 注册流程, 开始授权, 构造方法
''' + _HELPERS + '''
段落 主程序:
  设 s 为 构造授权服务()
  设 流程 为 ["键":"flowok", "标签":"t", "方法表":[构造方法("m9","默认")], "运行":成功运行]
  注册流程(s, 流程)
  设 交互 为 ["通知":空通知, "提问":空提问]
  设 req 为 ["键":"flowok", "交互":交互]
  设 结果 为 开始授权(s, req)
  打印("状态=" + 结果["状态"])
''')
    assert_success(r)
    out_contains(r, "状态=authorized")
