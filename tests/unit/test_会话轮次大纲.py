# -*- coding: utf-8 -*-
"""会话轮次大纲：列表工具 / 预览文本 / 折叠状态机。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_列表取_正常索引():
    r = run_light_source('''
从 会话轮次大纲 导入 列表取
段落 主程序:
  设 v 为 列表取(["a", "b", "c"], 1)
  打印("V=" + v)
''')
    assert_success(r)
    out_contains(r, "V=b")


def test_列表取_越界返回空():
    r = run_light_source('''
从 会话轮次大纲 导入 列表取
段落 主程序:
  设 v 为 列表取(["a"], 99)
  设 s 为 "NO"
  如果 v == 空: 设 s 为 "YES"
  打印("EMPTY=" + s)
''')
    assert_success(r)
    out_contains(r, "EMPTY=YES")


def test_追加项_不可变新增():
    r = run_light_source('''
从 会话轮次大纲 导入 追加项
段落 主程序:
  设 a 为 [1, 2]
  设 b 为 追加项(a, 3)
  打印("LEN_A=" + 转字符串(列表长度(a)))
  打印("LEN_B=" + 转字符串(列表长度(b)))
''')
    assert_success(r)
    out_contains(r, "LEN_A=2")
    out_contains(r, "LEN_B=3")


def test_替换末项_生效():
    r = run_light_source('''
从 会话轮次大纲 导入 替换末项
段落 主程序:
  设 b 为 替换末项(["x", "y"], "z")
  打印("LAST=" + b[列表长度(b)-1])
  打印("FIRST=" + b[0])
''')
    assert_success(r)
    out_contains(r, "LAST=z")
    out_contains(r, "FIRST=x")


def test_空大纲_形状():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲
段落 主程序:
  设 s 为 空大纲()
  打印("TURNS=" + 转字符串(列表长度(s["turns"])))
  打印("DRAFT=[" + s["draft"] + "]")
''')
    assert_success(r)
    out_contains(r, "TURNS=0")
    out_contains(r, "DRAFT=[]")


def test_预览文本_短文本原样():
    r = run_light_source('''
从 会话轮次大纲 导入 预览文本, 提示预览上限
段落 主程序:
  设 c 为 [{"type": "text", "text": "你好世界"}]
  设 t 为 预览文本(c, 提示预览上限())
  打印("T=" + t)
''')
    assert_success(r)
    out_contains(r, "T=你好世界")


def test_预览文本_超长截断加省略号():
    r = run_light_source('''
从 会话轮次大纲 导入 预览文本
段落 主程序:
  设 长 为 ""
  设 i 为 0
  当 i < 60:
    设 长 为 长 + "测"
    设 i 为 i + 1
  设 c 为 [{"type": "text", "text": 长}]
  设 t 为 预览文本(c, 50)
  打印("TAIL=" + 截取(t, 字符串长度(t)-1, 字符串长度(t)))
  打印("LEN=" + 转字符串(字符串长度(t)))
''')
    assert_success(r)
    out_contains(r, "TAIL=…")


def test_预览文本_非列表内容为空():
    r = run_light_source('''
从 会话轮次大纲 导入 预览文本
段落 主程序:
  设 t 为 预览文本(空, 50)
  设 s 为 "NO"
  如果 t == "": 设 s 为 "YES"
  打印("EMPTY=" + s)
''')
    assert_success(r)
    out_contains(r, "EMPTY=YES")


def test_预览文本收集_大块标记未读完():
    r = run_light_source('''
从 会话轮次大纲 导入 预览文本收集
段落 主程序:
  设 长 为 ""
  设 i 为 0
  当 i < 120:
    设 长 为 长 + "A"
    设 i 为 i + 1
  设 c 为 [{"type": "text", "text": 长}]
  设 果 为 预览文本收集(c, 50)
  打印("DONE=" + 转字符串(果["未读完"]))
''')
    assert_success(r)
    out_contains(r, "DONE=真")


def test_折叠_轮次开始开新条目():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠
段落 主程序:
  设 s 为 空大纲()
  设 e 为 {"type": "turn/start", "seq": 0, "data": {"turn": 1}}
  设 s2 为 轮次大纲折叠(s, e)
  打印("N=" + 转字符串(列表长度(s2["turns"])))
  打印("TURN=" + 转字符串(s2["turns"][0]["turn"]))
''')
    assert_success(r)
    out_contains(r, "N=1")
    out_contains(r, "TURN=1")


def test_折叠_非递增轮次被忽略():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠
段落 主程序:
  设 s 为 空大纲()
  设 s1 为 轮次大纲折叠(s, {"type": "turn/start", "seq": 0, "data": {"turn": 1}})
  设 s2 为 轮次大纲折叠(s1, {"type": "turn/start", "seq": 1, "data": {"turn": 1}})
  打印("N=" + 转字符串(列表长度(s2["turns"])))
''')
    assert_success(r)
    out_contains(r, "N=1")


def test_折叠_用户消息填入提示():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠
段落 主程序:
  设 s 为 空大纲()
  设 s1 为 轮次大纲折叠(s, {"type": "turn/start", "seq": 0, "data": {"turn": 1}})
  设 um 为 {"type": "user/message", "seq": 1, "data": {"source": {"kind": "user"}, "content": [{"type": "text", "text": "帮我查天气"}]}}
  设 s2 为 轮次大纲折叠(s1, um)
  打印("PROMPT=" + s2["turns"][0]["prompt"])
''')
    assert_success(r)
    out_contains(r, "PROMPT=帮我查天气")


def test_折叠_助手消息写草稿():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠
段落 主程序:
  设 s 为 空大纲()
  设 s1 为 轮次大纲折叠(s, {"type": "turn/start", "seq": 0, "data": {"turn": 1}})
  设 am 为 {"type": "assistant/message", "seq": 1, "data": {"message": {"content": [{"type": "text", "text": "答案是42"}]}}}
  设 s2 为 轮次大纲折叠(s1, am)
  打印("DRAFT=" + s2["draft"])
''')
    assert_success(r)
    out_contains(r, "DRAFT=答案是42")


def test_折叠_轮次结束提交草稿():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠
段落 主程序:
  设 s 为 空大纲()
  设 s1 为 轮次大纲折叠(s, {"type": "turn/start", "seq": 0, "data": {"turn": 1}})
  设 am 为 {"type": "assistant/message", "seq": 1, "data": {"message": {"content": [{"type": "text", "text": "最终回答"}]}}}
  设 s2 为 轮次大纲折叠(s1, am)
  设 s3 为 轮次大纲折叠(s2, {"type": "turn/end", "seq": 2, "data": {}})
  打印("RESP=" + s3["turns"][0]["response"])
  设 d 为 "NO"
  如果 s3["draft"] == "": 设 d 为 "YES"
  打印("DRAFT_EMPTY=" + d)
''')
    assert_success(r)
    out_contains(r, "RESP=最终回答")
    out_contains(r, "DRAFT_EMPTY=YES")


def test_折叠_未知类型不改变状态():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠
段落 主程序:
  设 s 为 空大纲()
  设 s2 为 轮次大纲折叠(s, {"type": "bogus/thing", "seq": 0, "data": {}})
  打印("N=" + 转字符串(列表长度(s2["turns"])))
''')
    assert_success(r)
    out_contains(r, "N=0")


def test_视图_返回轮次表():
    r = run_light_source('''
从 会话轮次大纲 导入 空大纲, 轮次大纲折叠, 轮次大纲视图
段落 主程序:
  设 s 为 空大纲()
  设 s1 为 轮次大纲折叠(s, {"type": "turn/start", "seq": 0, "data": {"turn": 7}})
  设 v 为 轮次大纲视图(s1)
  打印("V=" + 转字符串(v[0]["turn"]))
''')
    assert_success(r)
    out_contains(r, "V=7")
