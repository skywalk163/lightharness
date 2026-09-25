# -*- coding: utf-8 -*-
"""会话存储：id 生成 / 标题 / 索引原子写 / 会话 CRUD（隔离临时目录）。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_生成会话标识_格式():
    r = run_light_source('''
从 会话存储 导入 生成会话标识
段落 主程序:
  设 id 为 生成会话标识()
  设 前 为 截取(id, 0, 8)
  设 长 为 转字符串(字符串长度(id))
  打印("PREFIX=" + 前)
  打印("LEN=" + 长)
''')
    assert_success(r)
    out_contains(r, "PREFIX=session_")
    out_contains(r, "LEN=30")


def test_生成会话标识_唯一性():
    r = run_light_source('''
从 会话存储 导入 生成会话标识
段落 主程序:
  设 a 为 生成会话标识()
  设 b 为 生成会话标识()
  设 相同 为 "NO"
  如果 a == b: 设 相同 为 "YES"
  打印("SAME=" + 相同)
''')
    assert_success(r)
    out_contains(r, "SAME=NO")


def test_取现在时间_ISO格式():
    r = run_light_source('''
从 会话存储 导入 取现在时间
段落 主程序:
  设 t 为 取现在时间()
  设 含T 为 "NO"
  如果 t.查找("T") >= 0: 设 含T 为 "YES"
  打印("HAS_T=" + 含T)
  打印("LEN=" + 转字符串(字符串长度(t)))
''')
    assert_success(r)
    out_contains(r, "HAS_T=YES")
    out_contains(r, "LEN=19")


def test_生成标题_短消息整段():
    r = run_light_source('''
从 会话存储 导入 生成标题
段落 主程序:
  设 t 为 生成标题([{"角色": "user", "内容": "你好世界"}])
  打印("TITLE=" + t)
''')
    assert_success(r)
    out_contains(r, "TITLE=你好世界")


def test_生成标题_超长截断三十字():
    r = run_light_source('''
从 会话存储 导入 生成标题
段落 主程序:
  设 长文 为 "这是一段远远超过三十个字符的用户提问内容需要被截断到前三十个字符以便展示为标题的样例文本"
  设 t 为 生成标题([{"角色": "user", "内容": 长文}])
  打印("LEN=" + 转字符串(字符串长度(t)))
''')
    assert_success(r)
    out_contains(r, "LEN=30")


def test_生成标题_无用户消息回落默认():
    r = run_light_source('''
从 会话存储 导入 生成标题
段落 主程序:
  设 t 为 生成标题([{"角色": "assistant", "内容": "助手先说话"}])
  打印("TITLE=" + t)
''')
    assert_success(r)
    out_contains(r, "TITLE=新会话")


def test_生成标题_换行折叠为空格():
    r = run_light_source('''
从 会话存储 导入 生成标题
段落 主程序:
  设 t 为 生成标题([{"角色": "user", "内容": "第一行\\n\\n\\n第二行"}])
  打印("TITLE=" + t)
''')
    assert_success(r)
    out_contains(r, "TITLE=第一行 第二行")


def test_保存索引替换_默认成功():
    r = run_light_source('''
从 会话存储 导入 保存索引替换
从 文件系统 导入 写入文件, 文件存在
段落 主程序:
  写入文件("tmp.json", "{\\"会话\\":[]}")
  设 ok 为 保存索引替换("tmp.json", "idx.json")
  打印("OK=" + 转字符串(ok))
  设 存在 为 "NO"
  如果 文件存在("idx.json"): 设 存在 为 "YES"
  打印("TARGET=" + 存在)
''')
    assert_success(r)
    out_contains(r, "OK=真")
    out_contains(r, "TARGET=YES")


def test_新建会话_默认标题():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootA")
  设 s 为 库.新建会话("")
  打印("TITLE=" + s["标题"])
  打印("CNT=" + 转字符串(s["消息数"]))
''')
    assert_success(r)
    out_contains(r, "TITLE=新会话")
    out_contains(r, "CNT=0")


def test_追加消息_补时间并计数():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootB")
  设 s 为 库.新建会话("t1")
  设 id 为 s["id"]
  设 m 为 库.追加消息(id, {"角色": "user", "内容": "你好"})
  设 有时 为 "NO"
  如果 m.获取("时间", "") != "": 设 有时 为 "YES"
  设 md 为 库.取元数据(id)
  打印("HAS_TIME=" + 有时)
  打印("CNT=" + 转字符串(md["消息数"]))
''')
    assert_success(r)
    out_contains(r, "HAS_TIME=YES")
    out_contains(r, "CNT=1")


def test_获取会话_读回消息():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootC")
  设 s 为 库.新建会话("t2")
  设 id 为 s["id"]
  库.追加消息(id, {"角色": "user", "内容": "第一条"})
  库.追加消息(id, {"角色": "assistant", "内容": "第二条"})
  设 hist 为 库.获取会话(id)
  打印("N=" + 转字符串(列表长度(hist)))
  打印("FIRST=" + hist[0]["内容"])
''')
    assert_success(r)
    out_contains(r, "N=2")
    out_contains(r, "FIRST=第一条")


def test_获取会话_不存在返回错误():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootD")
  设 果 为 库.获取会话("session_nope")
  设 有 为 "NO"
  如果 果.获取("错误", "") != "": 设 有 为 "YES"
  打印("ERR=" + 有)
''')
    assert_success(r)
    out_contains(r, "ERR=YES")


def test_追加消息_不存在返回错误():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootE")
  设 果 为 库.追加消息("session_nope", {"角色": "user", "内容": "x"})
  设 有 为 "NO"
  如果 果.获取("错误", "") != "": 设 有 为 "YES"
  打印("ERR=" + 有)
''')
    assert_success(r)
    out_contains(r, "ERR=YES")


def test_列表会话_计数():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootF")
  库.新建会话("a")
  库.新建会话("b")
  库.新建会话("c")
  设 表 为 库.列表会话()
  打印("N=" + 转字符串(列表长度(表)))
''')
    assert_success(r)
    out_contains(r, "N=3")


def test_更新标题_生效():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootG")
  设 s 为 库.新建会话("旧名")
  设 id 为 s["id"]
  设 n 为 库.更新标题(id, "新名")
  打印("TITLE=" + n["标题"])
''')
    assert_success(r)
    out_contains(r, "TITLE=新名")


def test_删除会话_移除条目():
    r = run_light_source('''
从 会话存储 导入 会话存储
从 文件系统 导入 文件存在
段落 主程序:
  设 库 为 新建 会话存储("rootH")
  设 s 为 库.新建会话("待删")
  设 id 为 s["id"]
  设 删除前 为 "NO"
  如果 文件存在(库.取会话文件(id)): 设 删除前 为 "YES"
  库.删除会话(id)
  设 删除后 为 "NO"
  如果 文件存在(库.取会话文件(id)): 设 删除后 为 "YES"
  设 表 为 库.列表会话()
  打印("BEFORE=" + 删除前)
  打印("AFTER=" + 删除后)
  打印("N=" + 转字符串(列表长度(表)))
''')
    assert_success(r)
    out_contains(r, "BEFORE=YES")
    out_contains(r, "AFTER=NO")
    out_contains(r, "N=0")


def test_删除会话_不存在返回错误():
    r = run_light_source('''
从 会话存储 导入 会话存储
段落 主程序:
  设 库 为 新建 会话存储("rootI")
  设 s 为 库.新建会话("x")
  设 果 为 库.删除会话("session_never_exists_zzz")
  设 有 为 "NO"
  如果 果.获取("错误", "") != "": 设 有 为 "YES"
  打印("ERR=" + 有)
''')
    assert_success(r)
    out_contains(r, "ERR=YES")
